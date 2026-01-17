import time
import os
import math
from machine import PWM, FPIOA, Pin
from media.sensor import *
from media.display import *
from media.media import *

# ======================= 1. 全局配置 =======================
# 定义状态机常量
STATE_INITIAL_RESET = 0  # 初始复位状态
STATE_SEARCHING = 1      # 搜索目标状态
STATE_TRACKING = 2       # 追踪目标状态
STATE_LOCKED = 3         # 锁定目标状态

ENABLE_DISPLAY = True          # 是否启用显示屏
SENSOR_ID = 2                  # 摄像头传感器ID
DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480 # 显示屏分辨率

# 硬件引脚定义
LED_G_PIN = 20                 # 绿色LED灯的GPIO引脚
BEEP_PIN = 43                  # 蜂鸣器的GPIO引脚 (连接到PWM1)

# 蜂鸣器参数
BEEP_FREQ = 4000               # 蜂鸣器频率 (Hz)
BEEP_DUTY = 50                 # 蜂鸣器占空比 (%)
BEEP_DURATION_MS = 80          # 蜂鸣一声的持续时间 (ms)
PAUSE_DURATION_MS = 100        # 蜂鸣声之间的间隔时间 (ms)

# 舵机配置
X_SERVO_GPIO, Y_SERVO_GPIO = 42, 52    # X轴和Y轴舵机GPIO引脚
X_SERVO_PWM_ID, Y_SERVO_PWM_ID = 0, 4  # X轴和Y轴舵机PWM控制器ID
SERVO_FREQ_HZ = 50                     # 舵机PWM频率
PULSE_CENTER_MS = 1.5                  # 舵机居中脉宽 (ms)
PULSE_MIN_MS = 0.5                     # 舵机最小脉宽 (ms)
PULSE_MAX_MS = 2.5                     # 舵机最大脉宽 (ms)

# 图像处理阈值和参数
RED_THRESHOLD = [(60, 74, 37, 66, -13, 34)]   # 红色目标颜色阈值 (L*, a*, b* 范围)
GREEN_THRESHOLD = [(40, 98, -80, -30, 20, 80)] # 绿色目标颜色阈值 (L*, a*, b* 范围)
BLOB_AREA_THRESHOLD = 5                        # 颜色块最小面积阈值

# 控制参数
X_CONTROL_DIRECTION = -1 # X轴控制方向 (根据实际舵机安装决定，-1或1)
Y_CONTROL_DIRECTION = 1  # Y轴控制方向 (根据实际舵机安装决定，-1或1)
P_GAIN = 0.00005         # 比例增益 (P控制器参数)
SUCCESS_DISTANCE_PX = 25 # 追踪成功判断的像素距离阈值
LOCK_DURATION_S = 2.0    # 锁定成功后保持锁定的时长 (秒)

# ======================= 2. 舵机云台类 =======================
class Gimbal:
    """
    舵机云台控制类，封装舵机初始化、脉宽设置、复位和资源释放功能。
    """
    def __init__(self, fpioa):
        """
        初始化Gimbal对象，配置舵机引脚并启用PWM。

        参数:
            fpioa: FPIOA实例，用于引脚功能映射。
        """
        self.fpioa = fpioa
        # 将舵机GPIO引脚映射到相应的PWM功能
        self.fpioa.set_function(X_SERVO_GPIO, getattr(FPIOA, f'PWM{X_SERVO_PWM_ID}'))
        self.fpioa.set_function(Y_SERVO_GPIO, getattr(FPIOA, f'PWM{Y_SERVO_PWM_ID}'))
        
        # 初始化PWM对象，设置频率并启用
        self.pwm_x = PWM(X_SERVO_PWM_ID, SERVO_FREQ_HZ)
        self.pwm_y = PWM(Y_SERVO_PWM_ID, SERVO_FREQ_HZ)
        self.pwm_x.enable(True)
        self.pwm_y.enable(True)
        
        # 初始化当前舵机脉宽为中心值
        self.current_pulse_x, self.current_pulse_y = PULSE_CENTER_MS, PULSE_CENTER_MS
        self.period_ms = 1000 / SERVO_FREQ_HZ # 计算PWM周期 (ms)

    def set_pulse(self, pulse_x, pulse_y):
        """
        设置X轴和Y轴舵机的脉宽，并限制在最小/最大范围之内。

        参数:
            pulse_x: X轴舵机目标脉宽 (ms)。
            pulse_y: Y轴舵机目标脉宽 (ms)。
        """
        # 限制脉宽在允许的最小和最大值之间
        self.current_pulse_x = max(PULSE_MIN_MS, min(PULSE_MAX_MS, pulse_x))
        self.current_pulse_y = max(PULSE_MIN_MS, min(PULSE_MAX_MS, pulse_y))
        
        # 根据脉宽计算占空比并设置
        self.pwm_x.duty((self.current_pulse_x / self.period_ms) * 100)
        self.pwm_y.duty((self.current_pulse_y / self.period_ms) * 100)

    def reset(self):
        """
        将云台舵机复位到中心位置。
        """
        print("Gimbal: Resetting...")
        self.set_pulse(PULSE_CENTER_MS, PULSE_CENTER_MS)

    def deinit(self):
        """
        释放舵机PWM资源，禁用PWM输出。
        """
        self.pwm_x.deinit()
        self.pwm_y.deinit()

# ======================= 3. 声光提示函数 =======================
def play_success_signal(led, buzzer):
    """
    播放追踪成功提示音和灯光闪烁。

    参数:
        led: 绿色LED的Pin对象。
        buzzer: 蜂鸣器的PWM对象。
    """
    print("Playing success signal...")
    for _ in range(2): # 蜂鸣和闪烁两次
        buzzer.freq(BEEP_FREQ)     # 设置蜂鸣器频率
        led.low()                  # 绿色LED亮 (假设低电平有效)
        buzzer.enable(True)        # 启用蜂鸣器
        time.sleep_ms(BEEP_DURATION_MS) # 持续BEEP_DURATION_MS毫秒
        led.high()                 # 绿色LED灭 (假设高电平关闭)
        buzzer.enable(False)       # 禁用蜂鸣器
        time.sleep_ms(PAUSE_DURATION_MS) # 暂停PAUSE_DURATION_MS毫秒

# ======================= 4. 主程序 =======================
def main():
    """
    主函数，实现自动追踪系统的核心逻辑。
    包含初始化、状态机管理、图像处理、舵机控制、显示更新和资源清理。
    """
    # --- 初始化硬件和媒体管理器 ---
    fpioa = FPIOA() # 创建FPIOA实例用于引脚映射
    
    # 传感器（摄像头）初始化
    sensor = Sensor(id=SENSOR_ID)
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
    sensor.set_pixformat(Sensor.RGB565)
    
    # 显示屏初始化 (如果启用)
    if ENABLE_DISPLAY:
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    
    MediaManager.init() # 初始化媒体管理器
    sensor.run()        # 启动传感器捕获

    print("系统初始化中...")
    
    # 绿色LED初始化
    fpioa.set_function(LED_G_PIN, getattr(FPIOA, f'GPIO{LED_G_PIN}'))
    led_g = Pin(LED_G_PIN, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
    led_g.high() # 默认关闭LED (高电平)

    # 蜂鸣器初始化 (使用PWM1)
    fpioa.set_function(BEEP_PIN, FPIOA.PWM1)
    beep_pwm = PWM(1, BEEP_FREQ, BEEP_DUTY, enable=False) # 默认不启用蜂鸣器

    gimbal = Gimbal(fpioa) # 实例化Gimbal对象

    # --- 状态变量 ---
    state = STATE_INITIAL_RESET     # 当前系统状态
    lock_entry_time = 0             # 进入锁定状态的时间戳
    frozen_img = None               # 锁定状态下用于显示的冻结图像
    signal_played = False           # 标志位：成功信号是否已播放，防止重复播放

    try:
        while True:
            os.exitpoint() # 允许操作系统进行上下文切换，防止程序阻塞

            # 根据当前状态选择图像来源：锁定状态使用冻结图像，否则从传感器获取
            if state != STATE_LOCKED:
                img = sensor.snapshot() # 从摄像头获取实时图像
            else:
                img = frozen_img # 使用之前锁定的图像

            # --- 状态机逻辑 ---
            if state == STATE_INITIAL_RESET:
                # 初始复位状态：云台归中，然后进入搜索状态
                gimbal.reset()
                time.sleep(1) # 给予舵机一些时间到达中心位置
                state = STATE_SEARCHING

            elif state == STATE_SEARCHING:
                # 搜索目标状态：在图像中寻找红色和绿色目标
                if ENABLE_DISPLAY:
                    img.draw_string_advanced(10, 10, 30, "搜索中...", color=(255, 128, 0)) # 在屏幕上显示“搜索中”
                
                # 查找图像中的红色和绿色颜色块
                red_blobs = img.find_blobs(RED_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                green_blobs = img.find_blobs(GREEN_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                
                if red_blobs and green_blobs:
                    # 如果同时找到红绿目标，则进入追踪状态
                    state = STATE_TRACKING

            elif state == STATE_TRACKING:
                # 追踪目标状态：控制云台使绿色目标追踪红色目标
                red_blobs = img.find_blobs(RED_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                green_blobs = img.find_blobs(GREEN_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                
                if red_blobs and green_blobs:
                    # 获取红色目标（被追踪者）和绿色目标（追踪者）的中心坐标
                    target_pos = (red_blobs[0].cx(), red_blobs[0].cy())
                    tracker_pos = (green_blobs[0].cx(), green_blobs[0].cy())
                    
                    # 计算两个目标之间的像素误差
                    error_x = target_pos[0] - tracker_pos[0]
                    error_y = target_pos[1] - tracker_pos[1]
                    distance = math.sqrt(error_x**2 + error_y**2) # 计算欧氏距离
                    
                    if distance < SUCCESS_DISTANCE_PX:
                        # 如果距离小于成功阈值，认为目标已锁定
                        print("Target acquired! Locking frame.")
                        state = STATE_LOCKED          # 切换到锁定状态
                        lock_entry_time = time.ticks_ms() # 记录进入锁定状态的时间
                        frozen_img = img.copy()       # 复制当前图像，以便在锁定期间显示静态画面
                        gimbal.set_pulse(gimbal.current_pulse_x, gimbal.current_pulse_y) # 保持当前舵机位置
                        signal_played = False         # 重置信号播放标志，以便在锁定开始时播放信号
                    else:
                        # 否则，根据误差调整舵机位置进行追踪 (P比例控制)
                        correction_x = error_x * P_GAIN # 计算X轴的校正量
                        correction_y = error_y * P_GAIN # 计算Y轴的校正量
                        
                        # 计算新的舵机脉宽并设置
                        new_pulse_x = gimbal.current_pulse_x + correction_x * X_CONTROL_DIRECTION
                        new_pulse_y = gimbal.current_pulse_y + correction_y * Y_CONTROL_DIRECTION
                        gimbal.set_pulse(new_pulse_x, new_pulse_y)
                        
                        if ENABLE_DISPLAY:
                            img.draw_string_advanced(10, 10, 30, "追踪中...", color=(255, 255, 0)) # 在屏幕上显示“追踪中”
                else:
                    # 如果红色或绿色目标之一或两者都消失，返回搜索状态
                    state = STATE_SEARCHING

            elif state == STATE_LOCKED:
                # 锁定目标状态：保持锁定一段时间并播放成功信号
                # 1. 刚进入锁定状态时，立刻播放一次信号
                if not signal_played:
                    play_success_signal(led_g, beep_pwm)
                    signal_played = True # 设置标志，防止重复播放

                # 2. 持续在屏幕上显示锁定的状态信息和剩余时间
                if ENABLE_DISPLAY:
                    # 计算剩余锁定时间并显示
                    remaining_time = LOCK_DURATION_S - time.ticks_diff(time.ticks_ms(), lock_entry_time) / 1000.0
                    img.draw_string_advanced(10, 10, 30, f"锁定成功 {remaining_time:.1f}s", color=(0, 255, 0))

                # 3. 检查锁定时间是否已到
                if time.ticks_diff(time.ticks_ms(), lock_entry_time) > (LOCK_DURATION_S * 1000):
                    # 锁定时间结束，返回搜索状态以重新开始追踪
                    state = STATE_SEARCHING

            # --- 图像显示和绘制 ---
            if ENABLE_DISPLAY:
                # 重新查找blob用于绘制，确保显示的是当前帧的最新目标位置（即使在锁定状态也绘制冻结图像上的点）
                red_blobs_draw = img.find_blobs(RED_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                green_blobs_draw = img.find_blobs(GREEN_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                
                # 绘制红色目标的中心十字
                if red_blobs_draw:
                    img.draw_cross(red_blobs_draw[0].cx(), red_blobs_draw[0].cy(), color=(255,0,0), size=15, thickness=2)
                
                # 绘制绿色目标的中心十字
                if green_blobs_draw:
                    img.draw_cross(green_blobs_draw[0].cx(), green_blobs_draw[0].cy(), color=(0,255,0), size=15, thickness=2)
                
                # 在追踪中状态下，如果红绿目标都存在，绘制一个圆圈表示成功追踪的区域
                if red_blobs_draw and green_blobs_draw and state != STATE_LOCKED:
                    img.draw_circle(red_blobs_draw[0].cx(), red_blobs_draw[0].cy(), SUCCESS_DISTANCE_PX, color=(0,255,0), thickness=1)
                
                Display.show_image(img) # 显示处理后的图像到屏幕

    except KeyboardInterrupt:
        print("\n程序被用户中断。")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # --- 资源清理 ---
        # 禁用并释放蜂鸣器PWM资源
        if beep_pwm:
            beep_pwm.deinit()
        # 将LED引脚设置回输入状态，释放控制
        if led_g:
            led_g = Pin(LED_G_PIN, Pin.IN, pull=Pin.PULL_NONE)
        # 释放舵机资源
        if gimbal:
            gimbal.deinit()
        # 停止传感器捕获
        if sensor:
            sensor.stop()
        # 释放显示屏资源 (如果启用)
        if ENABLE_DISPLAY:
            Display.deinit()
        # 释放媒体管理器资源
        MediaManager.deinit()
        print("清理完成。程序退出。")

if __name__ == "__main__":
    main()
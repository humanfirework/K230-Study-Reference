# ====================================================================================
# 立创·庐山派-K230-CanMV - 运动目标控制与自动追踪系统 (最终版)
# ====================================================================================
#
# 该系统提供三种主要功能，通过按键触发：
#   - 按下 KEY2 (GPIO 14): [功能1] 舵机云台绘制正方形轨迹
#   - 按下 KEY3 (GPIO 61): [功能2] 视觉引导的矢量循迹
#   - 按下 KEY4 (GPIO 40): [功能3] 自动追踪红绿目标并锁定
#
# ----------------------------------------------------------------------------------
# 全局控制按键:
#   - 按下 KEY1 (GPIO 27): [复位] 停止当前任务，云台回中，返回主菜单
#   - 按下 KEY5 (GPIO 46): [暂停/继续] 暂停或继续当前正在运行的任务
# ====================================================================================

from machine import Pin, FPIOA, PWM
import time
import os
import math
from media.sensor import *
from media.display import *
from media.media import *

# ====================================================================================
# 全局硬件和按键定义
# ====================================================================================
# --- 1. 初始化FPIOA (仅执行一次) ---
# FPIOA (Flexible Pin IO Array) 用于将内部功能（如GPIO、PWM）映射到物理引脚。
fpioa = FPIOA()
fpioa.set_function(27, FPIOA.GPIO27) # KEY1: 复位按键的GPIO引脚
fpioa.set_function(14, FPIOA.GPIO14) # KEY2: 功能1按键的GPIO引脚
fpioa.set_function(61, FPIOA.GPIO61) # KEY3: 功能2按键的GPIO引脚
fpioa.set_function(40, FPIOA.GPIO40) # KEY4: 功能3按键的GPIO引脚
fpioa.set_function(46, FPIOA.GPIO46) # KEY5: 暂停/继续按键的GPIO引脚

# --- 2. 初始化按键引脚对象 ---
# 将配置好的GPIO引脚实例化为Pin对象，并设置为上拉输入模式。
key1 = Pin(27, Pin.IN, Pin.PULL_UP) # 复位键 (PULL_UP表示默认高电平，按下为低电平)
key2 = Pin(14, Pin.IN, Pin.PULL_UP) # 功能1: 舵机画图键
key3 = Pin(61, Pin.IN, Pin.PULL_UP) # 功能2: 矢量循迹键
key4 = Pin(40, Pin.IN, Pin.PULL_UP) # 功能3: 自动追踪键
key5 = Pin(46, Pin.IN, Pin.PULL_UP) # 暂停/继续键

# --- 全局暂停状态标志 ---
is_paused = False

# ====================================================================================
# 辅助函数: 检查全局暂停和复位指令
# ====================================================================================
def check_global_controls(gimbal_instance, display_instance=None):
    """
    检查暂停和复位键，并执行相应操作。
    如果检测到复位指令，则返回 'reset'，否则返回 None。
    
    参数:
        gimbal_instance: 舵机云台实例，用于执行复位操作。
        display_instance: 显示屏实例 (可选)，用于在暂停时显示信息。
    """
    global is_paused

    # --- 检查暂停键 (KEY5) ---
    if key5.value() == 0:
        time.sleep_ms(50) # 按键消抖
        if key5.value() == 0:
            is_paused = not is_paused # 切换暂停状态
            print(f"系统已 {'暂停' if is_paused else '继续'}.")
            if display_instance and is_paused:
                # 在屏幕上显示暂停状态
                img = display_instance.snapshot()
                if img:
                    img.draw_string_advanced(250, 220, 40, "--- 已暂停 ---", color=(255, 0, 0))
                    Display.show_image(img)

            # 等待按键释放，防止重复触发
            while key5.value() == 0:
                time.sleep_ms(20)

    # --- 如果处于暂停状态，则进入等待循环 ---
    while is_paused:
        # 在暂停期间，仍然要检查复位键和继续键
        if key1.value() == 0: # 暂停时也可复位
            return 'reset'
        if key5.value() == 0: # 再次按下暂停键以继续
            time.sleep_ms(50) # 消抖
            if key5.value() == 0:
                is_paused = False # 恢复运行
                print("系统已继续.")
                while key5.value() == 0: time.sleep_ms(20) # 等待按键释放
                break # 退出暂停循环
        time.sleep_ms(50) # 减少CPU占用

    # --- 检查复位键 (KEY1) ---
    if key1.value() == 0:
        return 'reset'

    return None

# ====================================================================================
# 功能 1: 双轴舵机绘制正方形 (由 key2 / GPIO 14 触发)
# ====================================================================================
def run_servo_square_pattern():
    """
    控制双轴舵机绘制一个正方形轨迹。
    该功能包含舵机初始化、位置计算、运动序列执行及资源清理。
    在运动过程中会持续检查全局控制按键（暂停/复位）。
    """
    print("\n>>> 功能1启动：双轴舵机绘制正方形 <<<")
    # --- 参数配置 ---
    X_SERVO_GPIO, X_SERVO_PWM_ID = 42, 0 # X轴舵机GPIO引脚和PWM控制器ID
    Y_SERVO_GPIO, Y_SERVO_PWM_ID = 52, 4 # Y轴舵机GPIO引脚和PWM控制器ID
    SERVO_FREQ_HZ = 50                 # 舵机PWM频率 (Hz)
    PULSE_CENTER_MS = 1.6              # 舵机居中时的脉宽 (ms)
    PULSE_MIN_MS = 0.5                 # 舵机最小脉宽 (ms)
    PULSE_MAX_MS = 2.5                 # 舵机最大脉宽 (ms)
    SQUARE_OFFSET_MS = 0.1             # 正方形顶点相对于中心的脉宽偏移量 (ms)
    STEP_DELAY_S = 1.5                 # 每次移动之间的延时 (秒)

    # 计算正方形的四个顶点和初始居中位置的脉宽
    INITIAL_POS = (PULSE_CENTER_MS, PULSE_CENTER_MS)
    TOP_LEFT = (PULSE_CENTER_MS - SQUARE_OFFSET_MS, PULSE_CENTER_MS + SQUARE_OFFSET_MS)
    TOP_RIGHT = (PULSE_CENTER_MS + SQUARE_OFFSET_MS, PULSE_CENTER_MS + SQUARE_OFFSET_MS)
    BOTTOM_RIGHT = (PULSE_CENTER_MS + SQUARE_OFFSET_MS, PULSE_CENTER_MS - SQUARE_OFFSET_MS)
    BOTTOM_LEFT = (PULSE_CENTER_MS - SQUARE_OFFSET_MS, PULSE_CENTER_MS - SQUARE_OFFSET_MS)

    def move_servos(pwm_x, pwm_y, target_pos):
        """
        设置X轴和Y轴舵机的脉宽。
        
        参数:
            pwm_x: X轴舵机的PWM对象。
            pwm_y: Y轴舵机的PWM对象。
            target_pos: 目标位置的元组 (pulse_x_ms, pulse_y_ms)。
        """
        pos_x_ms, pos_y_ms = target_pos
        period_ms = 1000 / SERVO_FREQ_HZ # PWM周期 (ms)
        duty_x = (pos_x_ms / period_ms) * 100 # X轴占空比
        pwm_x.duty(duty_x)
        duty_y = (pos_y_ms / period_ms) * 100 # Y轴占空比
        pwm_y.duty(duty_y)
        print(f"--> 移动到 X: {pos_x_ms:.1f}ms, Y: {pos_y_ms:.1f}ms")

    def controlled_sleep(duration_s):
        """
        带有全局控制检查的延时函数。
        在延时期间会周期性检查暂停和复位按键。
        
        参数:
            duration_s: 延时时长 (秒)。
        
        返回:
            'reset' 如果检测到复位指令，否则返回 'ok'。
        """
        end_time = time.ticks_add(time.ticks_ms(), int(duration_s * 1000))
        while time.ticks_diff(end_time, time.ticks_ms()) > 0:
            if check_global_controls(None) == 'reset': # 舵机画图功能不需要gimbal_instance
                return 'reset'
            time.sleep_ms(50)
        return 'ok'

    servo_x, servo_y = None, None
    try:
        # 1. 初始化舵机PWM引脚和对象
        local_fpioa = FPIOA() # 在函数内部创建独立的FPIOA实例，防止与其他功能冲突
        local_fpioa.set_function(X_SERVO_GPIO, getattr(FPIOA, f'PWM{X_SERVO_PWM_ID}'))
        local_fpioa.set_function(Y_SERVO_GPIO, getattr(FPIOA, f'PWM{Y_SERVO_PWM_ID}'))
        servo_x = PWM(X_SERVO_PWM_ID, SERVO_FREQ_HZ, enable=True)
        servo_y = PWM(Y_SERVO_PWM_ID, SERVO_FREQ_HZ, enable=True)

        # 定义一个简单的Gimbal对象用于复位回调
        class SimpleGimbal:
            def reset(self):
                print("复位：云台回中...")
                move_servos(servo_x, servo_y, INITIAL_POS)
                time.sleep(1)
        gimbal = SimpleGimbal() # 实例化SimpleGimbal

        # 2. 执行运动序列
        trajectory = [
            ("步骤 1: 移动到初始位置...", INITIAL_POS, 3),
            ("步骤 2: 移动到正方形左上角...", TOP_LEFT, STEP_DELAY_S),
            ("步骤 3.1: 绘制: 左上 -> 右上", TOP_RIGHT, STEP_DELAY_S),
            ("步骤 3.2: 绘制: 右上 -> 右下", BOTTOM_RIGHT, STEP_DELAY_S),
            ("步骤 3.3: 绘制: 右下 -> 左下", BOTTOM_LEFT, STEP_DELAY_S),
            ("步骤 3.4: 绘制: 左下 -> 左上", TOP_LEFT, STEP_DELAY_S),
            ("步骤 4: 返回初始位置...", INITIAL_POS, 3)
        ]

        for description, pos, delay in trajectory:
            print(description)
            move_servos(servo_x, servo_y, pos)
            # 检查是否有复位指令，如果有则中断当前任务
            if controlled_sleep(delay) == 'reset':
                gimbal.reset() # 执行云台复位
                raise KeyboardInterrupt("复位指令已接收") # 抛出异常以跳到finally块

        print("正方形绘制完成。")

    except KeyboardInterrupt:
        print("\n任务被复位指令或用户中断。")
    except Exception as e:
        print(f"\n功能1发生错误: {e}")
    finally:
        # 3. 清理资源
        # 禁用并释放PWM资源，确保下次启动时状态干净。
        if servo_x: servo_x.deinit()
        if servo_y: servo_y.deinit()
        print("功能1 PWM资源已释放。")
        print(">>> 功能1结束，返回主循环 <<<")

# ====================================================================================
# 功能 2: 视觉矢量循迹 (由 key3 / GPIO 61 触发)
# ====================================================================================
def run_vector_control_trace():
    """
    通过摄像头识别特定矩形目标，并引导舵机云台进行矢量循迹。
    功能包含摄像头初始化、图像处理、目标识别、舵机控制及资源清理。
    支持全局暂停和复位。
    """
    print("\n>>> 功能2启动：视觉矢量循迹 <<<")
    # --- 配置 ---
    # 状态机定义
    STATE_INITIAL_RESET = 0  # 初始复位状态
    STATE_DETECT_TARGET = 1  # 检测目标状态
    STATE_CONFIRM_TARGET = 2 # 确认目标状态
    STATE_TRACING = 3        # 追踪目标状态
    STATE_FINISH = 4         # 完成状态

    ENABLE_DISPLAY = True          # 是否启用显示屏
    SENSOR_ID = 2                  # 传感器ID
    DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480 # 显示屏分辨率
    
    # 舵机配置
    X_SERVO_GPIO, Y_SERVO_GPIO = 42, 52    # X轴和Y轴舵机GPIO引脚
    X_SERVO_PWM_ID, Y_SERVO_PWM_ID = 0, 4  # X轴和Y轴舵机PWM控制器ID
    SERVO_FREQ_HZ = 50                     # 舵机PWM频率
    PULSE_CENTER_MS = 1.5                  # 舵机居中脉宽
    PULSE_MIN_MS = 0.5                     # 舵机最小脉宽
    PULSE_MAX_MS = 2.5                     # 舵机最大脉宽

    # 图像处理阈值和参数
    RED_THRESHOLD = [(85, 100, -18, 50, -18, 51)] # 红色目标颜色阈值 (L*, a*, b* 范围)
    RECT_BINARY_THRESHOLD = [(82, 212)]           # 矩形检测二值化阈值 (灰度值范围)
    RECT_AREA_THRESHOLD = 20000                    # 矩形最小面积阈值
    BLOB_AREA_THRESHOLD = 5                        # 颜色块最小面积阈值
    CONFIRMATION_DURATION_S = 2.0                  # 目标确认时长 (秒)
    
    # 控制参数
    X_CONTROL_DIRECTION = -1 # X轴控制方向 (根据实际舵机安装决定，-1或1)
    Y_CONTROL_DIRECTION = 1  # Y轴控制方向 (根据实际舵机安装决定，-1或1)
    NUM_LAPS = 10            # 循迹循环次数
    TRACE_DURATION_PER_EDGE_S = 1 # 每条边循迹时长 (秒)
    P_GAIN = 0.00004         # 比例增益 (P控制器参数)

    # --- 舵机云台类 ---
    class Gimbal:
        def __init__(self):
            """初始化舵机PWM引脚和对象，设置初始脉宽。"""
            fpioa = FPIOA() # 创建独立的FPIOA实例
            fpioa.set_function(X_SERVO_GPIO, getattr(FPIOA, f'PWM{X_SERVO_PWM_ID}'))
            fpioa.set_function(Y_SERVO_GPIO, getattr(FPIOA, f'PWM{Y_SERVO_PWM_ID}'))
            self.pwm_x = PWM(X_SERVO_PWM_ID, SERVO_FREQ_HZ)
            self.pwm_y = PWM(Y_SERVO_PWM_ID, SERVO_FREQ_HZ)
            self.pwm_x.enable(True)
            self.pwm_y.enable(True)
            self.current_pulse_x = PULSE_CENTER_MS # 当前X轴舵机脉宽
            self.current_pulse_y = PULSE_CENTER_MS # 当前Y轴舵机脉宽
            self.period_ms = 1000 / SERVO_FREQ_HZ  # PWM周期 (ms)

        def set_pulse(self, pulse_x, pulse_y):
            """
            设置舵机脉宽，并限制在合法范围内。
            
            参数:
                pulse_x: X轴舵机目标脉宽 (ms)。
                pulse_y: Y轴舵机目标脉宽 (ms)。
            """
            self.current_pulse_x = max(PULSE_MIN_MS, min(PULSE_MAX_MS, pulse_x))
            self.current_pulse_y = max(PULSE_MIN_MS, min(PULSE_MAX_MS, pulse_y))
            self.pwm_x.duty((self.current_pulse_x / self.period_ms) * 100)
            self.pwm_y.duty((self.current_pulse_y / self.period_ms) * 100)

        def reset(self):
            """将云台复位到中心位置。"""
            print("复位：云台回中...")
            self.set_pulse(PULSE_CENTER_MS, PULSE_CENTER_MS)
            time.sleep(1)

        def deinit(self):
            """释放舵机PWM资源。"""
            self.pwm_x.deinit()
            self.pwm_y.deinit()

    # --- 辅助函数 ---
    def sort_corners_clockwise(corners):
        """
        将矩形的四个角点按顺时针顺序排序。
        
        参数:
            corners: 包含四个角点坐标的元组列表。
            
        返回:
            按顺时针排序后的角点列表。
        """
        corners_list = list(corners)
        # 找到左上角的点作为起始点 (x+y最小)
        corners_list.sort(key=lambda p: p[0] + p[1])
        start_point = corners_list[0]
        # 根据相对于起始点的角度进行排序 (逆时针)
        sorted_remaining_corners = sorted(corners_list[1:], key=lambda p: -math.atan2(p[1]-start_point[1], p[0]-start_point[0]))
        return [start_point] + sorted_remaining_corners

    sensor, gimbal = None, None
    try:
        # 1. 初始化硬件和媒体管理器
        sensor = Sensor(id=SENSOR_ID)
        sensor.reset() # 重置传感器
        sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT) # 设置帧大小
        sensor.set_pixformat(Sensor.RGB565) # 设置像素格式为RGB565
        if ENABLE_DISPLAY:
            Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True) # 初始化显示屏
        MediaManager.init() # 初始化媒体管理器
        sensor.run() # 启动传感器
        gimbal = Gimbal() # 实例化Gimbal对象
        
        # 初始化状态机变量
        state = STATE_INITIAL_RESET
        target_corners, confirmation_start_time, trace_start_time = [], 0, 0

        # 等待KEY3按键释放，避免立即退出
        while key3.value() == 0:
            time.sleep_ms(10)

        # 2. 主循环
        while key3.value() != 0: # 当KEY3未按下时（即正在运行此功能）
            # 检查全局控制按键（暂停/复位）
            if check_global_controls(gimbal, sensor) == 'reset':
                gimbal.reset() # 执行云台复位
                raise KeyboardInterrupt("复位指令已接收") # 抛出异常以中断任务

            os.exitpoint() # 允许系统调度其他任务
            img = sensor.snapshot() # 获取图像帧

            # 状态机逻辑
            if state == STATE_INITIAL_RESET:
                # 初始复位状态：云台归中，然后进入目标检测状态
                gimbal.reset()
                time.sleep(1)
                state = STATE_DETECT_TARGET
            elif state == STATE_DETECT_TARGET:
                # 检测目标状态：寻找两个符合条件的矩形目标
                if ENABLE_DISPLAY:
                    img.draw_string_advanced(10, 10, 25, "Searching...", color=(255, 255, 0))
                img_gray = img.to_grayscale(copy=True).binary(RECT_BINARY_THRESHOLD) # 图像灰度化并二值化
                rects = img_gray.find_rects(threshold=RECT_AREA_THRESHOLD) # 查找矩形
                if len(rects) >= 2:
                    # 如果找到两个矩形，进入目标确认状态
                    confirmation_start_time = time.ticks_ms()
                    state = STATE_CONFIRM_TARGET
            elif state == STATE_CONFIRM_TARGET:
                # 确认目标状态：持续确认目标存在一段时间
                if ENABLE_DISPLAY:
                    img.draw_string_advanced(10, 10, 25, "Confirming...", color=(0, 255, 0))
                img_gray = img.to_grayscale(copy=True).binary(RECT_BINARY_THRESHOLD)
                rects = img_gray.find_rects(threshold=RECT_AREA_THRESHOLD)
                if len(rects) < 2:
                    # 如果目标消失，返回检测状态
                    state = STATE_DETECT_TARGET
                    continue
                # 如果确认时间达到，计算循迹路径并进入追踪状态
                if time.ticks_diff(time.ticks_ms(), confirmation_start_time) > CONFIRMATION_DURATION_S * 1000:
                    rects.sort(key=lambda r: r.w() * r.h(), reverse=True) # 按面积降序排序
                    corners_outer = sort_corners_clockwise(rects[0].corners()) # 外部矩形角点
                    corners_inner = sort_corners_clockwise(rects[1].corners()) # 内部矩形角点
                    
                    # 计算内外矩形之间的中点作为循迹目标点
                    target_corners = []
                    for i in range(4):
                        mid_x = (corners_outer[i][0] + corners_inner[i][0]) // 2
                        mid_y = (corners_outer[i][1] + corners_inner[i][1]) // 2
                        target_corners.append((mid_x, mid_y))
                    
                    state = STATE_TRACING
                    trace_start_time = time.ticks_ms()
            elif state == STATE_TRACING:
                # 追踪目标状态：根据预设路径和红色目标进行循迹控制
                elapsed_time = time.ticks_diff(time.ticks_ms(), trace_start_time) / 1000.0 #  elapsed time in seconds
                total_edges = 4 * NUM_LAPS # 总循迹边数 (4条边 * 循环次数)
                current_edge_index = int(elapsed_time / TRACE_DURATION_PER_EDGE_S) # 当前循迹的边索引
                
                if current_edge_index >= total_edges:
                    # 如果完成所有循迹，进入完成状态
                    state = STATE_FINISH
                    continue
                
                # 计算当前循迹目标点 (胡萝卜点)
                progress_on_edge = (elapsed_time % TRACE_DURATION_PER_EDGE_S) / TRACE_DURATION_PER_EDGE_S
                start_node = target_corners[current_edge_index % 4]
                end_node = target_corners[(current_edge_index + 1) % 4]
                carrot_x = start_node[0] + (end_node[0] - start_node[0]) * progress_on_edge
                carrot_y = start_node[1] + (end_node[1] - start_node[1]) * progress_on_edge
                carrot_pos = (int(carrot_x), int(carrot_y))

                # 寻找红色目标块，并根据其位置进行PID控制 (这里是P控制)
                red_blobs = img.find_blobs(RED_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                if red_blobs:
                    current_pos = (red_blobs[0].cx(), red_blobs[0].cy()) # 当前红色目标中心
                    error_x = carrot_pos[0] - current_pos[0] # X轴误差
                    error_y = carrot_pos[1] - current_pos[1] # Y轴误差
                    
                    correction_x = error_x * P_GAIN # X轴修正量
                    correction_y = error_y * P_GAIN # Y轴修正量
                    
                    new_pulse_x = gimbal.current_pulse_x + correction_x * X_CONTROL_DIRECTION
                    new_pulse_y = gimbal.current_pulse_y + correction_y * Y_CONTROL_DIRECTION
                    gimbal.set_pulse(new_pulse_x, new_pulse_y) # 设置舵机脉宽
                
                # 绘制显示信息
                if ENABLE_DISPLAY:
                    if red_blobs:
                        img.draw_cross(current_pos[0], current_pos[1], color=(255, 0, 0), size=10) # 绘制红色目标中心
                    img.draw_circle(carrot_pos[0], carrot_pos[1], 10, color=(0, 255, 255), thickness=2) # 绘制胡萝卜点
                    if target_corners:
                        for i in range(4):
                            p1, p2 = target_corners[i], target_corners[(i + 1) % 4]
                            img.draw_line(p1[0], p1[1], p2[0], p2[1], color=(0, 255, 0), thickness=2) # 绘制循迹路径
            elif state == STATE_FINISH:
                # 完成状态：打印信息并复位，然后返回初始检测状态
                print(f"Task complete! Finished {NUM_LAPS} laps. Resetting...")
                gimbal.reset()
                time.sleep(2)
                state = STATE_INITIAL_RESET

            # 显示图像到屏幕
            if ENABLE_DISPLAY:
                Display.show_image(img)

    except KeyboardInterrupt:
        print("\n任务被复位指令或用户中断。")
    except Exception as e:
        print(f"功能2发生错误: {e}")
    finally:
        # 3. 清理资源
        # 释放舵机、传感器和显示屏资源，确保系统稳定。
        if gimbal: gimbal.deinit()
        if sensor: sensor.stop()
        if ENABLE_DISPLAY: Display.deinit()
        MediaManager.deinit() # 释放媒体管理器资源
        print("功能2资源已释放。")
        print(">>> 功能2结束，返回主循环 <<<")

# ====================================================================================
# 功能 3: 自动追踪红绿目标 (由 key4 / GPIO 40 触发)
# ====================================================================================
def run_auto_tracker():
    """
    通过摄像头识别红色和绿色目标，并控制云台使绿色目标追踪红色目标。
    功能包含硬件初始化、图像处理、目标识别、舵机控制、声光提示及资源清理。
    支持全局暂停和复位。
    """
    print("\n>>> 功能3启动：自动追踪红绿目标 <<<")
    # --- 配置 ---
    # 状态机定义
    STATE_INITIAL_RESET = 0 # 初始复位状态
    STATE_SEARCHING = 1     # 搜索目标状态
    STATE_TRACKING = 2      # 追踪目标状态
    STATE_LOCKED = 3        # 锁定目标状态

    ENABLE_DISPLAY = True          # 是否启用显示屏
    SENSOR_ID = 2                  # 传感器ID
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
    PULSE_CENTER_MS = 1.5                  # 舵机居中脉宽
    PULSE_MIN_MS = 0.5                     # 舵机最小脉宽
    PULSE_MAX_MS = 2.5                     # 舵机最大脉宽

    # 图像处理阈值和参数
    RED_THRESHOLD = [(60, 74, 37, 66, -13, 34)]   # 红色目标颜色阈值 (L*, a*, b* 范围)
    GREEN_THRESHOLD = [(40, 98, -80, -30, 20, 80)] # 绿色目标颜色阈值 (L*, a*, b* 范围)
    BLOB_AREA_THRESHOLD = 5                        # 颜色块最小面积阈值

    # 控制参数
    X_CONTROL_DIRECTION = -1 # X轴控制方向 (根据实际舵机安装决定，-1或1)
    Y_CONTROL_DIRECTION = 1  # Y轴控制方向 (根据实际舵机安装决定，-1或1)
    P_GAIN = 0.00005         # 比例增益 (P控制器参数)
    SUCCESS_DISTANCE_PX = 30 # 追踪成功判断的像素距离阈值
    LOCK_DURATION_S = 2.0    # 锁定成功后保持锁定的时长 (秒)

    # --- 舵机云台类 ---
    class Gimbal:
        def __init__(self, fpioa_instance):
            """
            初始化舵机PWM引脚和对象，设置初始脉宽。
            
            参数:
                fpioa_instance: FPIOA实例，用于引脚映射。
            """
            self.fpioa = fpioa_instance # 使用传入的FPIOA实例
            self.fpioa.set_function(X_SERVO_GPIO, getattr(FPIOA, f'PWM{X_SERVO_PWM_ID}'))
            self.fpioa.set_function(Y_SERVO_GPIO, getattr(FPIOA, f'PWM{Y_SERVO_PWM_ID}'))
            self.pwm_x = PWM(X_SERVO_PWM_ID, SERVO_FREQ_HZ)
            self.pwm_y = PWM(Y_SERVO_PWM_ID, SERVO_FREQ_HZ)
            self.pwm_x.enable(True)
            self.pwm_y.enable(True)
            self.current_pulse_x = PULSE_CENTER_MS
            self.current_pulse_y = PULSE_CENTER_MS
            self.period_ms = 1000 / SERVO_FREQ_HZ

        def set_pulse(self, pulse_x, pulse_y):
            """
            设置舵机脉宽，并限制在合法范围内。
            
            参数:
                pulse_x: X轴舵机目标脉宽 (ms)。
                pulse_y: Y轴舵机目标脉宽 (ms)。
            """
            self.current_pulse_x = max(PULSE_MIN_MS, min(PULSE_MAX_MS, pulse_x))
            self.current_pulse_y = max(PULSE_MIN_MS, min(PULSE_MAX_MS, pulse_y))
            self.pwm_x.duty((self.current_pulse_x / self.period_ms) * 100)
            self.pwm_y.duty((self.current_pulse_y / self.period_ms) * 100)

        def reset(self):
            """将云台复位到中心位置。"""
            print("复位：云台回中...")
            self.set_pulse(PULSE_CENTER_MS, PULSE_CENTER_MS)
            time.sleep(1)

        def deinit(self):
            """释放舵机PWM资源。"""
            self.pwm_x.deinit()
            self.pwm_y.deinit()

    # --- 声光提示函数 ---
    def play_success_signal(led, buzzer):
        """
        播放追踪成功提示音和灯光闪烁。
        
        参数:
            led: 绿色LED的Pin对象。
            buzzer: 蜂鸣器的PWM对象。
        """
        print("Playing success signal...")
        for _ in range(2): # 蜂鸣和闪烁两次
            buzzer.freq(BEEP_FREQ)
            led.low() # LED亮
            buzzer.enable(True) # 蜂鸣器响
            time.sleep_ms(BEEP_DURATION_MS)
            led.high() # LED灭
            buzzer.enable(False) # 蜂鸣器停
            time.sleep_ms(PAUSE_DURATION_MS)

    sensor, gimbal, beep_pwm, led_g = None, None, None, None
    try:
        # 1. 初始化硬件和媒体管理器
        local_fpioa = FPIOA() # 创建独立的FPIOA实例
        
        sensor = Sensor(id=SENSOR_ID)
        sensor.reset()
        sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        sensor.set_pixformat(Sensor.RGB565)
        if ENABLE_DISPLAY:
            Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
        MediaManager.init()
        sensor.run()

        # 初始化绿色LED (GPIO 20)
        local_fpioa.set_function(LED_G_PIN, getattr(FPIOA, f'GPIO{LED_G_PIN}'))
        led_g = Pin(LED_G_PIN, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
        led_g.high() # 默认关闭LED (高电平)

        # 初始化蜂鸣器 (PWM1)
        local_fpioa.set_function(BEEP_PIN, FPIOA.PWM1)
        beep_pwm = PWM(1, BEEP_FREQ, BEEP_DUTY, enable=False) # 默认不启用蜂鸣器

        gimbal = Gimbal(local_fpioa) # 实例化Gimbal对象

        # 初始化状态机变量
        state = STATE_INITIAL_RESET
        lock_entry_time = 0
        frozen_img = None # 锁定状态下用于显示静止图像
        signal_played = False # 标志位，确保成功信号只播放一次

        # 等待KEY4按键释放，避免立即退出
        while key4.value() == 0:
            time.sleep_ms(10)

        # 2. 主循环
        while key4.value() != 0: # 当KEY4未按下时（即正在运行此功能）
            # 检查全局控制按键（暂停/复位）
            if check_global_controls(gimbal, sensor) == 'reset':
                gimbal.reset() # 执行云台复位
                raise KeyboardInterrupt("复位指令已接收") # 抛出异常以中断任务

            os.exitpoint() # 允许系统调度其他任务

            # 在锁定状态下使用冻结的图像，否则获取新图像
            if state != STATE_LOCKED:
                img = sensor.snapshot()
            else:
                img = frozen_img

            # 状态机逻辑
            if state == STATE_INITIAL_RESET:
                # 初始复位状态：云台归中，然后进入搜索状态
                gimbal.reset()
                time.sleep(1)
                state = STATE_SEARCHING
            elif state == STATE_SEARCHING:
                # 搜索目标状态：寻找红色和绿色目标
                if ENABLE_DISPLAY:
                    img.draw_string_advanced(10, 10, 30, "搜索中...", color=(255, 128, 0))
                red_blobs = img.find_blobs(RED_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                green_blobs = img.find_blobs(GREEN_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                if red_blobs and green_blobs:
                    # 如果同时找到红绿目标，进入追踪状态
                    state = STATE_TRACKING
            elif state == STATE_TRACKING:
                # 追踪目标状态：控制云台使绿色目标追踪红色目标
                red_blobs = img.find_blobs(RED_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                green_blobs = img.find_blobs(GREEN_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                if red_blobs and green_blobs:
                    target_pos = (red_blobs[0].cx(), red_blobs[0].cy()) # 红色目标中心 (被追踪者)
                    tracker_pos = (green_blobs[0].cx(), green_blobs[0].cy()) # 绿色目标中心 (追踪者)
                    
                    error_x = target_pos[0] - tracker_pos[0] # X轴误差
                    error_y = target_pos[1] - tracker_pos[1] # Y轴误差
                    distance = math.sqrt(error_x**2 + error_y**2) # 目标与追踪者之间的距离
                    
                    if distance < SUCCESS_DISTANCE_PX:
                        # 如果距离小于阈值，认为锁定成功，进入锁定状态
                        state = STATE_LOCKED
                        lock_entry_time = time.ticks_ms()
                        frozen_img = img.copy() # 锁定当前帧图像
                        gimbal.set_pulse(gimbal.current_pulse_x, gimbal.current_pulse_y) # 保持当前舵机位置
                        signal_played = False # 重置信号播放标志
                    else:
                        # 否则，根据误差调整舵机位置进行追踪 (P控制)
                        correction_x = error_x * P_GAIN
                        correction_y = error_y * P_GAIN
                        
                        new_pulse_x = gimbal.current_pulse_x + correction_x * X_CONTROL_DIRECTION
                        new_pulse_y = gimbal.current_pulse_y + correction_y * Y_CONTROL_DIRECTION
                        gimbal.set_pulse(new_pulse_x, new_pulse_y)
                        if ENABLE_DISPLAY:
                            img.draw_string_advanced(10, 10, 30, "追踪中...", color=(255, 255, 0))
                else:
                    # 如果红绿目标之一或两者都消失，返回搜索状态
                    state = STATE_SEARCHING
            elif state == STATE_LOCKED:
                # 锁定目标状态：播放成功信号并保持锁定一段时间
                if not signal_played:
                    play_success_signal(led_g, beep_pwm) # 播放声光信号
                    signal_played = True
                if ENABLE_DISPLAY:
                    remaining_time = LOCK_DURATION_S - time.ticks_diff(time.ticks_ms(), lock_entry_time) / 1000.0
                    img.draw_string_advanced(10, 10, 30, f"锁定成功 {remaining_time:.1f}s", color=(0, 255, 0))
                
                if time.ticks_diff(time.ticks_ms(), lock_entry_time) > (LOCK_DURATION_S * 1000):
                    # 锁定时间到，返回搜索状态
                    state = STATE_SEARCHING

            # 绘制图像到显示屏 (在每次循环结束时更新)
            if ENABLE_DISPLAY:
                # 再次查找blob用于绘制，确保显示的是最新检测到的目标位置
                red_blobs_draw = img.find_blobs(RED_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                green_blobs_draw = img.find_blobs(GREEN_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                
                # 绘制目标中心十字
                if red_blobs_draw:
                    img.draw_cross(red_blobs_draw[0].cx(), red_blobs_draw[0].cy(), color=(255,0,0), size=15, thickness=2)
                if green_blobs_draw:
                    img.draw_cross(green_blobs_draw[0].cx(), green_blobs_draw[0].cy(), color=(0,255,0), size=15, thickness=2)
                
                # 在追踪中状态下，绘制一个圆圈表示成功追踪的区域
                if red_blobs_draw and green_blobs_draw and state != STATE_LOCKED:
                    img.draw_circle(red_blobs_draw[0].cx(), red_blobs_draw[0].cy(), SUCCESS_DISTANCE_PX, color=(0,255,0), thickness=1)
                
                Display.show_image(img) # 显示处理后的图像

    except KeyboardInterrupt:
        print("\n任务被复位指令或用户中断。")
    except Exception as e:
        print(f"功能3发生错误: {e}")
    finally:
        # 3. 清理资源
        # 释放蜂鸣器、LED、舵机、传感器和显示屏资源。
        if beep_pwm: beep_pwm.deinit()
        if led_g: led_g = Pin(LED_G_PIN, Pin.IN, pull=Pin.PULL_NONE) # 将LED引脚设回输入状态，释放控制
        if gimbal: gimbal.deinit()
        if sensor: sensor.stop()
        if ENABLE_DISPLAY: Display.deinit()
        MediaManager.deinit()
        print("功能3资源已释放。")
        print(">>> 功能3结束，返回主循环 <<<")


# ====================================================================================
# 主程序入口: 按键检测与功能分派
# ====================================================================================
if __name__ == "__main__":
    """
    程序主入口点。
    显示系统启动信息和操作指南，然后进入无限循环，
    持续检测按键输入以分派并执行相应的功能。
    """
    print("\n" + "="*50)
    print("           运动目标控制与自动追踪系统 已启动")
    print("="*50)
    print("请按以下按键选择功能:")
    print("   - KEY 2 (GPIO 14): [功能1] 舵机绘制正方形")
    print("   - KEY 3 (GPIO 61): [功能2] 视觉矢量循迹")
    print("   - KEY 4 (GPIO 40): [功能3] 自动追踪目标")
    print("-"*50)
    print("在功能运行时:")
    print("   - KEY 1 (GPIO 27): [复位] 停止任务并返回主菜单")
    print("   - KEY 5 (GPIO 46): [暂停/继续] 切换任务状态")
    print("="*50)

    while True:
        try:
            # 确保全局暂停标志在主菜单时为False
            is_paused = False

            # --- 功能1：舵机绘制正方形 (通过KEY2触发) ---
            if key2.value() == 0:
                time.sleep_ms(50) # 消抖
                if key2.value() == 0:
                    run_servo_square_pattern() # 调用功能1函数
                while key2.value() == 0: time.sleep_ms(100) # 等待按键释放
                print("\n等待新的按键指令...")

            # --- 功能2：视觉矢量循迹 (通过KEY3触发) ---
            elif key3.value() == 0:
                time.sleep_ms(50) # 消抖
                if key3.value() == 0:
                    run_vector_control_trace() # 调用功能2函数
                while key3.value() == 0: time.sleep_ms(100) # 等待按键释放
                print("\n等待新的按键指令...")

            # --- 功能3：自动追踪红绿目标 (通过KEY4触发) ---
            elif key4.value() == 0:
                time.sleep_ms(50) # 消抖
                if key4.value() == 0:
                    run_auto_tracker() # 调用功能3函数
                while key4.value() == 0: time.sleep_ms(100) # 等待按键释放
                print("\n等待新的按键指令...")

            # 主菜单循环延时，减少CPU占用
            time.sleep_ms(20)

        except KeyboardInterrupt:
            # 捕获KeyboardInterrupt异常，用于优雅退出程序
            print("\n主程序被中断，正在退出...")
            break
        except Exception as e:
            # 捕获其他未知异常，并打印错误信息后退出
            print(f"主循环发生严重错误: {e}")
            break
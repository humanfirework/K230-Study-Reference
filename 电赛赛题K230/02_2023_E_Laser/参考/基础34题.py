import time
import os
import math # 引入math库用于角点排序
from machine import PWM, FPIOA
from media.sensor import *
from media.display import *
from media.media import *

# ======================= 1. 全局配置 =======================

# --- 状态定义 ---
STATE_INITIAL_RESET = 0  # 初始复位状态
STATE_DETECT_TARGET = 1  # 检测目标状态
STATE_CONFIRM_TARGET = 2 # 确认目标状态
STATE_TRACING = 3        # 追踪目标状态
STATE_FINISH = 4         # 完成状态

# --- 显示功能开关 ---
ENABLE_DISPLAY = True    # 是否启用显示屏输出

# --- 摄像头与显示配置 ---
SENSOR_ID = 2                  # 摄像头传感器ID
DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480 # 显示屏分辨率

# --- 舵机配置 ---
X_SERVO_GPIO, Y_SERVO_GPIO = 42, 52    # X轴和Y轴舵机GPIO引脚
X_SERVO_PWM_ID, Y_SERVO_PWM_ID = 0, 4  # X轴和Y轴舵机PWM控制器ID
SERVO_FREQ_HZ = 50                     # 舵机PWM频率 (Hz)
PULSE_CENTER_MS = 1.5                  # 舵机居中时的脉宽 (ms)
PULSE_MIN_MS = 0.5                     # 舵机最小脉宽 (ms)
PULSE_MAX_MS = 2.5                     # 舵机最大脉宽 (ms)

# --- 视觉识别配置 ---
RED_THRESHOLD = [(85, 100, -18, 50, -18, 51)] # 红色目标颜色阈值 (L*, a*, b* 范围)
RECT_BINARY_THRESHOLD = [(82, 212)]           # 矩形检测二值化阈值 (灰度值范围)
RECT_AREA_THRESHOLD = 20000                    # 矩形最小面积阈值，用于过滤小噪声
BLOB_AREA_THRESHOLD = 5                        # 颜色块最小面积阈值，用于过滤小噪声

# --- 追踪逻辑配置 ---
CONFIRMATION_DURATION_S = 2.0                  # 目标确认时长 (秒)
X_CONTROL_DIRECTION = -1                       # X轴控制方向 (根据实际舵机安装决定，-1或1)
Y_CONTROL_DIRECTION = 1                        # Y轴控制方向 (根据实际舵机安装决定，-1或1)
NUM_LAPS = 2                                   # 循迹循环次数
TRACE_DURATION_PER_EDGE_S = 7                  # 每条边循迹时长 (秒)，可适当调小以加快速度

# --- 矢量比例控制参数 ---
# 这是现在唯一需要微调的追踪参数。
# 它决定了云台追踪的“积极性”或“响应速度”。
# 值越大，追踪越快越“猛”；值越小，追踪越柔和。
# 建议从 0.0005 开始尝试。
P_GAIN = 0.00005 # Proportional Gain (比例增益)

# ======================= 2. 舵机云台类 =======================
class Gimbal:
    """
    舵机云台控制类，封装舵机初始化、脉宽设置、复位和资源释放功能。
    """
    def __init__(self):
        """
        初始化Gimbal对象，配置舵机引脚并启用PWM。
        """
        fpioa = FPIOA()
        # 将舵机GPIO引脚映射到相应的PWM功能
        fpioa.set_function(X_SERVO_GPIO, getattr(FPIOA, f'PWM{X_SERVO_PWM_ID}'))
        fpioa.set_function(Y_SERVO_GPIO, getattr(FPIOA, f'PWM{Y_SERVO_PWM_ID}'))
        
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
        print("Gimbal: Resetting to center...")
        self.set_pulse(PULSE_CENTER_MS, PULSE_CENTER_MS)

    def deinit(self):
        """
        释放舵机PWM资源，禁用PWM输出。
        """
        self.pwm_x.deinit()
        self.pwm_y.deinit()

# ======================= 3. 辅助函数 =======================
def sort_corners_clockwise(corners):
    """
    将矩形的四个角点按顺时针顺序排序。
    这对于确定循迹路径的顺序至关重要。

    参数:
        corners: 包含四个角点坐标 (x, y) 的元组列表。

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

# ======================= 4. 主程序 =======================
def main():
    """
    主函数，实现视觉引导的矢量循迹系统的核心逻辑。
    包含初始化、状态机管理、图像处理、目标识别、路径规划、舵机控制、显示更新和资源清理。
    """
    # --- 初始化硬件和媒体管理器 ---
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
    
    gimbal = Gimbal() # 实例化Gimbal对象

    # --- 状态变量 ---
    state = STATE_INITIAL_RESET     # 当前系统状态
    target_corners = []             # 循迹目标的四个角点
    confirmation_start_time = 0     # 进入目标确认状态的时间戳
    trace_start_time = 0            # 进入追踪状态的时间戳

    try:
        while True:
            os.exitpoint() # 允许操作系统进行上下文切换，防止程序阻塞
            img = sensor.snapshot() # 获取当前图像帧

            # --- 状态机逻辑 ---
            if state == STATE_INITIAL_RESET:
                # 初始复位状态：云台归中，然后进入目标检测状态
                gimbal.reset()
                time.sleep(1) # 给予舵机一些时间到达中心位置
                state = STATE_DETECT_TARGET

            elif state == STATE_DETECT_TARGET:
                # 检测目标状态：寻找两个符合矩形阈值的目标
                if ENABLE_DISPLAY:
                    img.draw_string_advanced(10, 10, 25, "Searching for target...", color=(255, 255, 0)) # 在屏幕上显示“搜索中”
                else:
                    print("Searching for target...")
                
                # 图像灰度化并二值化，用于矩形检测
                img_gray = img.to_grayscale(copy=True).binary(RECT_BINARY_THRESHOLD)
                rects = img_gray.find_rects(threshold=RECT_AREA_THRESHOLD) # 查找矩形
                
                if len(rects) >= 2:
                    # 如果找到两个或更多矩形，进入目标确认状态
                    confirmation_start_time = time.ticks_ms()
                    state = STATE_CONFIRM_TARGET
                else:
                    if not ENABLE_DISPLAY:
                        print(f"Found only {len(rects)} rectangles, need 2.")

            elif state == STATE_CONFIRM_TARGET:
                # 确认目标状态：持续确认目标存在一段时间
                if ENABLE_DISPLAY:
                    img.draw_string_advanced(10, 10, 25, "Confirming target...", color=(0, 255, 0)) # 在屏幕上显示“确认中”
                else:
                    print("Confirming target...")
                
                # 再次进行矩形检测以确认目标稳定性
                img_gray = img.to_grayscale(copy=True).binary(RECT_BINARY_THRESHOLD)
                rects = img_gray.find_rects(threshold=RECT_AREA_THRESHOLD)
                
                if len(rects) < 2:
                    # 如果目标消失，返回检测状态
                    state = STATE_DETECT_TARGET
                    continue # 跳过当前循环的剩余部分，重新开始检测

                if time.ticks_diff(time.ticks_ms(), confirmation_start_time) > CONFIRMATION_DURATION_S * 1000:
                    # 如果确认时间达到，计算循迹路径并进入追踪状态
                    print("Target locked. Calculating center path...")
                    rects.sort(key=lambda r: r.w() * r.h(), reverse=True) # 按面积降序排序，大的在前
                    
                    # 获取内外两个矩形的角点并顺时针排序
                    corners_outer = sort_corners_clockwise(rects[0].corners())
                    corners_inner = sort_corners_clockwise(rects[1].corners())
                    print(f"Outer corners: {corners_outer}")
                    print(f"Inner corners: {corners_inner}")
                    
                    # 计算内外矩形之间的中点作为循迹的目标路径点
                    target_corners = []
                    for i in range(4):
                        mid_x = (corners_outer[i][0] + corners_inner[i][0]) // 2
                        mid_y = (corners_outer[i][1] + corners_inner[i][1]) // 2
                        target_corners.append((mid_x, mid_y))
                    
                    print(f"Center path calculated: {target_corners}")
                    state = STATE_TRACING # 切换到追踪状态
                    trace_start_time = time.ticks_ms() # 记录进入追踪状态的时间

            elif state == STATE_TRACING:
                # 追踪状态：根据预设的路径（由target_corners定义）引导红色目标运动
                elapsed_time = time.ticks_diff(time.ticks_ms(), trace_start_time) / 1000.0 # 计算已追踪的时间 (秒)
                total_edges = 4 * NUM_LAPS # 计算循迹的总边数 (一个正方形有4条边)
                current_edge_index = int(elapsed_time / TRACE_DURATION_PER_EDGE_S) # 计算当前正在循迹的边索引
                
                if current_edge_index >= total_edges:
                    # 如果完成所有循迹循环，进入完成状态
                    state = STATE_FINISH
                    continue # 跳过当前循环的剩余部分

                # 计算当前循迹的“胡萝卜点”（即虚拟目标点）
                progress_on_edge = (elapsed_time % TRACE_DURATION_PER_EDGE_S) / TRACE_DURATION_PER_EDGE_S
                start_node = target_corners[current_edge_index % 4]       # 当前边的起始点
                end_node = target_corners[(current_edge_index + 1) % 4] # 当前边的结束点
                
                # 在起始点和结束点之间插值计算胡萝卜点的坐标
                carrot_x = start_node[0] + (end_node[0] - start_node[0]) * progress_on_edge
                carrot_y = start_node[1] + (end_node[1] - start_node[1]) * progress_on_edge
                carrot_pos = (int(carrot_x), int(carrot_y)) # 将胡萝卜点坐标转换为整数

                # --- 使用矢量比例控制进行追踪 ---
                red_blobs = img.find_blobs(RED_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
                if red_blobs:
                    current_pos = (red_blobs[0].cx(), red_blobs[0].cy()) # 获取红色目标的当前位置

                    # 1. 计算误差矢量：胡萝卜点与当前红色目标点之间的距离
                    error_x = carrot_pos[0] - current_pos[0]
                    error_y = carrot_pos[1] - current_pos[1]

                    # 2. 根据误差和比例增益 (P_GAIN) 计算舵机脉宽的调整量
                    correction_x = error_x * P_GAIN
                    correction_y = error_y * P_GAIN

                    # 3. 计算新的舵机脉宽值 (X和Y轴同时修正)
                    new_pulse_x = gimbal.current_pulse_x + correction_x * X_CONTROL_DIRECTION
                    new_pulse_y = gimbal.current_pulse_y + correction_y * Y_CONTROL_DIRECTION

                    gimbal.set_pulse(new_pulse_x, new_pulse_y) # 设置舵机到新的位置
                    if ENABLE_DISPLAY:
                        img.draw_cross(current_pos[0], current_pos[1], color=(255, 0, 0), size=10) # 绘制红色目标中心
                else:
                    # 如果未找到红色目标，保持舵机当前位置并提示
                    gimbal.set_pulse(gimbal.current_pulse_x, gimbal.current_pulse_y)
                    if ENABLE_DISPLAY:
                        img.draw_string_advanced(10, 50, 25, "Laser not found! HOLDING.", color=(255, 128, 0))
                    else:
                        print("Laser not found! HOLDING.")

                # 绘制显示信息
                if ENABLE_DISPLAY:
                    img.draw_circle(carrot_pos[0], carrot_pos[1], 10, color=(0, 255, 255), thickness=2) # 绘制胡萝卜点
                    if target_corners:
                        # 绘制循迹路径（连接四个目标角点）
                        for i in range(4):
                            p1, p2 = target_corners[i], target_corners[(i + 1) % 4]
                            img.draw_line(p1[0], p1[1], p2[0], p2[1], color=(0, 255, 0), thickness=2)

            elif state == STATE_FINISH:
                # 完成状态：打印任务完成信息并复位，然后返回初始检测状态
                print(f"Task complete! Finished {NUM_LAPS} laps. Resetting...")
                gimbal.reset()
                time.sleep(2) # 暂停一段时间，让用户看到完成信息
                state = STATE_INITIAL_RESET

            # 在每次循环结束时，如果启用显示，则将图像显示到屏幕
            if ENABLE_DISPLAY:
                Display.show_image(img)

    except KeyboardInterrupt:
        # 捕获KeyboardInterrupt异常（例如，通过Ctrl+C）用于优雅退出程序
        print("\n程序被用户中断。")
    except Exception as e:
        # 捕获其他所有未预期的异常，并打印错误信息
        print(f"发生错误: {e}")
    finally:
        # --- 资源清理 ---
        # 确保在程序退出前释放所有硬件资源
        if gimbal:
            gimbal.deinit() # 释放舵机PWM资源
        if sensor:
            sensor.stop()   # 停止传感器捕获
        if ENABLE_DISPLAY:
            Display.deinit() # 释放显示屏资源
        MediaManager.deinit() # 释放媒体管理器资源
        print("清理完成。程序退出。")

if __name__ == "__main__":
    # 当脚本作为主程序运行时，调用main函数
    main()
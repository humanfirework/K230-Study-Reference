import time
import os
import math
from machine import PWM, FPIOA, Pin
from media.sensor import *
from media.display import *
from media.media import *

# ======================= 1. 全局配置 =======================
# --- 状态机定义 ---
STATE_SEARCHING_RECT = 0         # 状态：搜索矩形识别区域
STATE_MOVING_TO_START = 1        # 状态：移动至绘图路径的起始点
STATE_DRAWING_VECTOR_CONTROL = 2 # 状态：执行矢量闭环控制进行绘图
STATE_FINISH_RESET = 3           # 状态：任务完成并复位

# --- 硬件与显示配置 ---
SENSOR_ID = 2
DISPLAY_WIDTH, DISPLAY_HEIGHT = 640, 480

# --- 舵机物理参数 ---
X_SERVO_GPIO, Y_SERVO_GPIO = 42, 52
X_SERVO_PWM_ID, Y_SERVO_PWM_ID = 0, 4
SERVO_FREQ_HZ = 50
PULSE_CENTER_MS = 1.5
PULSE_MIN_MS = 0.5
PULSE_MAX_MS = 2.5

# --- 视觉识别阈值 ---
UV_LASER_THRESHOLD = [(85, 100, -18, 50, -18, 51)] # 紫外激光点的LAB颜色阈值
RECT_BINARY_THRESHOLD = [(100, 255)]              # 矩形识别的二值化阈值
RECT_AREA_THRESHOLD = 20000                       # 矩形识别的最小面积过滤器
BLOB_AREA_THRESHOLD = 5                           # 激光点识别的最小面积过滤器

# --- 绘图与运动逻辑参数 ---
STAR_SIZE_RATIO = 0.9           # 绘制图形占识别矩形的尺寸比例
X_CONTROL_DIRECTION = -1        # X轴舵机的运动方向与像素坐标误差的对应关系
Y_CONTROL_DIRECTION = 1         # Y轴舵机的运动方向与像素坐标误差的对应关系
NUM_DRAWING_LAPS = 1            # 绘图的总圈数

# --- 实时矢量PD闭环控制参数 ---
Kp = 0.00001                      # P (比例) 增益：决定对位置误差的反应强度
Kd = 0.00001                      # D (微分) 增益：提供阻尼，抑制系统振荡
ARRIVAL_THRESHOLD_PX = 15       # 到达目标点的判定阈值（像素）
MAX_SPEED_PPS = 150             # 激光点在屏幕上的最大期望移动速度（像素/秒）

# ======================= 2. PD控制器与舵机云台类 =======================
class PD_Controller:
    """实现一个基础的比例-微分(PD)控制器。"""
    def __init__(self, kp, kd):
        self.kp = kp
        self.kd = kd
        self.last_error = 0
    def update(self, error):
        """根据当前误差计算PD控制器的输出。"""
        derivative = error - self.last_error
        output = self.kp * error + self.kd * derivative
        self.last_error = error
        return output
    def reset(self):
        """重置控制器状态，防止历史误差影响下一次控制。"""
        self.last_error = 0

class Gimbal:
    """舵机云台硬件抽象层，封装底层PWM控制。"""
    def __init__(self):
        fpioa = FPIOA()
        fpioa.set_function(X_SERVO_GPIO, getattr(FPIOA, f'PWM{X_SERVO_PWM_ID}'))
        fpioa.set_function(Y_SERVO_GPIO, getattr(FPIOA, f'PWM{Y_SERVO_PWM_ID}'))
        self.pwm_x = PWM(X_SERVO_PWM_ID, SERVO_FREQ_HZ)
        self.pwm_y = PWM(Y_SERVO_PWM_ID, SERVO_FREQ_HZ)
        self.pwm_x.enable(True)
        self.pwm_y.enable(True)
        self.current_pulse_x, self.current_pulse_y = PULSE_CENTER_MS, PULSE_CENTER_MS
        self.period_ms = 1000 / SERVO_FREQ_HZ
        self.reset()
        time.sleep(1)

    def set_pulse(self, pulse_x, pulse_y):
        """设定并限制舵机脉宽，并将其转换为占空比应用到硬件。"""
        self.current_pulse_x = max(PULSE_MIN_MS, min(PULSE_MAX_MS, pulse_x))
        self.current_pulse_y = max(PULSE_MIN_MS, min(PULSE_MAX_MS, pulse_y))
        self.pwm_x.duty((self.current_pulse_x / self.period_ms) * 100)
        self.pwm_y.duty((self.current_pulse_y / self.period_ms) * 100)

    def reset(self):
        """将舵机复位至中心位置。"""
        print("Gimbal: Resetting to center...")
        self.set_pulse(PULSE_CENTER_MS, PULSE_CENTER_MS)

    def deinit(self):
        """释放PWM硬件资源。"""
        self.pwm_x.deinit()
        self.pwm_y.deinit()

# ======================= 3. 辅助函数 =======================
def calculate_star_path(rect):
    """根据输入的矩形对象，计算其内接五角星的顶点像素路径。"""
    bbox = rect.rect()
    cx = bbox[0] + bbox[2] // 2
    cy = bbox[1] + bbox[3] // 2
    radius = min(rect.w(), rect.h()) / 2 * STAR_SIZE_RATIO
    path_pixel = []
    for i in range(5):
        angle_deg = -90 + i * 72 # 从顶部开始计算顶点
        angle_rad = math.radians(angle_deg)
        px = int(cx + radius * math.cos(angle_rad))
        py = int(cy + radius * math.sin(angle_rad))
        path_pixel.append((px, py))
    # 按五角星的笔画顺序返回顶点
    return [path_pixel[0], path_pixel[2], path_pixel[4], path_pixel[1], path_pixel[3]]

# ======================= 4. 主程序 =======================
def main():
    sensor, gimbal = None, None
    try:
        # --- 初始化所有硬件模块 ---
        sensor = Sensor(id=SENSOR_ID)
        sensor.reset()
        sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        sensor.set_pixformat(Sensor.RGB565)
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
        MediaManager.init()
        sensor.run()
        gimbal = Gimbal()

        # --- 初始化状态变量和控制器 ---
        state = STATE_SEARCHING_RECT
        star_pixel_path = []
        target_vertex_index = 0
        laps_completed = 0
        pd_x = PD_Controller(Kp, Kd)
        pd_y = PD_Controller(Kp, Kd)

        # --- 主循环 ---
        while True:
            os.exitpoint()
            img = sensor.snapshot()

            if state == STATE_SEARCHING_RECT:
                # 在此状态下，程序不断寻找一个足够大的矩形作为绘图区域
                img.draw_string_advanced(10, 10, 25, "Searching for paper...", color=(255, 255, 0))
                img_gray = img.to_grayscale(copy=True).binary(RECT_BINARY_THRESHOLD)
                rects = img_gray.find_rects(threshold=RECT_AREA_THRESHOLD)
                del img_gray

                if rects:
                    # 找到后，计算路径并切换到下一状态
                    main_rect = sorted(rects, key=lambda r: r.w() * r.h(), reverse=True)[0]
                    img.draw_rectangle(main_rect.rect(), color=(0, 255, 0), thickness=2)
                    Display.show_image(img)
                    print("Paper found. Calculating path...")

                    star_pixel_path = calculate_star_path(main_rect)
                    star_pixel_path.append(star_pixel_path[0]) # 添加路径终点以闭合图形

                    time.sleep(1)
                    state = STATE_MOVING_TO_START
                    target_vertex_index = 0
                    laps_completed = 0
                    pd_x.reset(); pd_y.reset()

            elif state == STATE_MOVING_TO_START or state == STATE_DRAWING_VECTOR_CONTROL:
                # 移动至起点或绘图状态下的核心闭环控制逻辑
                target_pos = star_pixel_path[target_vertex_index]
                laser_blobs = img.find_blobs(UV_LASER_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)

                if laser_blobs:
                    current_pos = (laser_blobs[0].cx(), laser_blobs[0].cy())
                    error_x = target_pos[0] - current_pos[0]
                    error_y = target_pos[1] - current_pos[1]
                    distance_to_target = math.sqrt(error_x**2 + error_y**2)

                    # 检查是否已到达当前目标顶点
                    if distance_to_target < ARRIVAL_THRESHOLD_PX:
                        if state == STATE_MOVING_TO_START:
                            print("Arrived at start point. Begin drawing.")
                            state = STATE_DRAWING_VECTOR_CONTROL
                            time.sleep(0.5) # 落笔停顿

                        target_vertex_index += 1 # 切换到路径的下一个顶点
                        if target_vertex_index >= len(star_pixel_path):
                            laps_completed += 1
                            if laps_completed >= NUM_DRAWING_LAPS:
                                state = STATE_FINISH_RESET # 所有圈数完成
                                continue
                            else:
                                target_vertex_index = 0 # 开始新的一圈

                        pd_x.reset(); pd_y.reset()
                        # 更新目标点并重新计算误差
                        target_pos = star_pixel_path[target_vertex_index]
                        error_x = target_pos[0] - current_pos[0]
                        error_y = target_pos[1] - current_pos[1]
                        distance_to_target = math.sqrt(error_x**2 + error_y**2)

                    # --- 实时矢量控制核心 ---
                    # 1. 计算指向目标的单位矢量，确定运动方向
                    dir_x = error_x / distance_to_target if distance_to_target > 0 else 0
                    dir_y = error_y / distance_to_target if distance_to_target > 0 else 0

                    # 2. 根据距离动态调整速度，实现近处减速，防止过冲
                    speed_factor = min(1.0, distance_to_target / 100) # 在100像素内线性减速
                    speed = (MAX_SPEED_PPS if state == STATE_DRAWING_VECTOR_CONTROL else MAX_SPEED_PPS * 1.5) * speed_factor

                    # 3. PD控制器计算修正量，施加一个指向目标的“力”
                    correction_x = pd_x.update(error_x)
                    correction_y = pd_y.update(error_y)

                    # 4. 应用修正量到舵机脉宽
                    new_pulse_x = gimbal.current_pulse_x + correction_x * X_CONTROL_DIRECTION
                    new_pulse_y = gimbal.current_pulse_y + correction_y * Y_CONTROL_DIRECTION
                    gimbal.set_pulse(new_pulse_x, new_pulse_y)

                    img.draw_cross(current_pos[0], current_pos[1], color=(255, 0, 0), size=10)
                else:
                    print("Warning: UV Laser not found!")

                # --- 绘制辅助信息 ---
                img.draw_cross(target_pos[0], target_pos[1], 15, color=(0, 255, 255), thickness=2) # 目标点
                for i in range(len(star_pixel_path) - 1):
                    p1, p2 = star_pixel_path[i], star_pixel_path[i+1]
                    img.draw_line(p1[0], p1[1], p2[0], p2[1], color=(0, 255, 0), thickness=2) # 理想路径

            elif state == STATE_FINISH_RESET:
                # 绘图完成后复位并返回搜索状态
                print(f"Drawing complete! Resetting...")
                gimbal.reset()
                time.sleep(2)
                state = STATE_SEARCHING_RECT

            Display.show_image(img)
            del img

    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # --- 确保所有硬件资源被安全释放 ---
        if gimbal: gimbal.deinit()
        if sensor: sensor.stop()
        Display.deinit()
        MediaManager.deinit()
        print("Cleanup complete. Exiting.")

if __name__ == "__main__":
    main()

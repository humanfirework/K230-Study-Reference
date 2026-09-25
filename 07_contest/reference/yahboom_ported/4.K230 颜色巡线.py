import time, os, sys
from media.sensor import *
from media.display import *
from media.media import *

from ybUtils.YbUart import YbUart

uart = YbUart(9600)

# 显示参数 / Display parameters
DISPLAY_WIDTH = 640   # LCD显示宽度 / LCD display width
DISPLAY_HEIGHT = 480  # LCD显示高度 / LCD display height

# LAB颜色空间阈值 / LAB color space thresholds
# (L Min, L Max, A Min, A Max, B Min, B Max)
THRESHOLDS = [
    ((21, 33, -15, 9, -9, 6)),    # 黑线
    ((40, 86, -44, -20, -24, 25)), # 绿
]

# PID参数
KP = 1
KI = 0.1
KD = 0.2

# 基础速度
BASE_SPEED = 300

# 屏幕中心点坐标
SCREEN_CENTER = DISPLAY_WIDTH // 2

# 全局变量
prev_error = 0
integral = 0

def get_closest_rgb(lab_threshold):
    """根据LAB阈值计算最接近的RGB颜色 / Calculate closest RGB color based on LAB threshold"""
    # 获取LAB空间的中心点值
    l_center = (lab_threshold[0] + lab_threshold[1]) // 2
    a_center = (lab_threshold[2] + lab_threshold[3]) // 2
    b_center = (lab_threshold[4] + lab_threshold[5]) // 2
    return image.lab_to_rgb((l_center,a_center,b_center))

def init_sensor():
    """初始化摄像头 / Initialize camera sensor"""
    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
    sensor.set_pixformat(Sensor.RGB565)
    return sensor

def init_display():
    """初始化显示 / Initialize display"""
    Display.init(Display.ST7701, to_ide=True)
    MediaManager.init()

def calculate_pid(target, current):
    """计算PID输出 / Calculate PID output"""
    global prev_error, integral

    error = target - current
    integral += error
    derivative = error - prev_error

    # 限制积分项防止积分饱和
    if integral > 100:
        integral = 100
    elif integral < -100:
        integral = -100

    output = KP * error + KI * integral + KD * derivative

    # 计算左右电机速度
    left_speed = BASE_SPEED - output
    right_speed = BASE_SPEED + output

    # 保存当前误差用于下次计算
    prev_error = error

    return int(left_speed), int(right_speed)

def process_blobs(img, blobs, color):
    """处理检测到的色块，只绘制最大的色块 / Process detected color blobs, draw only the largest one"""
    if not blobs:
        # 如果没有检测到色块，发送停车命令
        uart.send("$0,0#")
        return

    # 找出面积最大的色块
    largest_blob = max(blobs, key=lambda b: b[4])

    # 计算PID输出
    target_x = SCREEN_CENTER
    current_x = largest_blob[0] + largest_blob[2] // 2
    left_speed, right_speed = calculate_pid(target_x, current_x)

    # 通过串口发送PID输出数据
    uart.send(f"${left_speed},{right_speed}#")

    # 只绘制最大的色块
    img.draw_rectangle(largest_blob[0:4], color=color, thickness=4)
    img.draw_cross(largest_blob[0] + largest_blob[2]//2, largest_blob[1] + largest_blob[3]//2, color=color, thickness=2)

    # 绘制目标线和当前位置
    img.draw_line(SCREEN_CENTER, 0, SCREEN_CENTER, DISPLAY_HEIGHT, color=(0, 255, 0), thickness=1)
    img.draw_line(current_x, largest_blob[1], current_x, largest_blob[1] + largest_blob[3], color=(255, 0, 0), thickness=2)

def draw_fps(img, fps):
    """绘制FPS信息 / Draw FPS information"""
    img.draw_string_advanced(0, 0, 30, f'FPS: {fps:.3f}', color=(255, 255, 255))

def main():
    try:
        # 初始化设备 / Initialize devices
        sensor = init_sensor()
        init_display()
        sensor.run()

        clock = time.clock()

        # 选择要检测的颜色索引 (0:红, 1:绿, 2:蓝) / Select color index to detect
        color_index = 1  # 可以修改这个值来选择检测不同的颜色
        threshold = THRESHOLDS[color_index]
        detect_color = get_closest_rgb(threshold)

        while True:
            clock.tick()
            img = sensor.snapshot()

            # 检测指定颜色 / Detect specified color
            blobs = img.find_blobs([threshold], roi=(0, DISPLAY_HEIGHT//2, DISPLAY_WIDTH, DISPLAY_HEIGHT//2))
            if blobs:
                process_blobs(img, blobs, detect_color)
            else:
                # 如果没有检测到色块，发送停车命令
                uart.send("$0,0#")

            fps = clock.fps()
            draw_fps(img, fps)
            print(fps)

            Display.show_image(img)

    except KeyboardInterrupt as e:
        print("用户中断 / User interrupted: ", e)
    except Exception as e:
        print(f"发生错误 / Error occurred: {e}")
    finally:
        if 'sensor' in locals() and isinstance(sensor, Sensor):
            sensor.stop()
        Display.deinit()
        MediaManager.deinit()

if __name__ == "__main__":
    main()

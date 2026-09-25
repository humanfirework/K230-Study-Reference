# ========================= 库导入 =========================
import gc
import os
import sys
import time
import math
import struct

from media.sensor import * #导入sensor模块，使用摄像头相关接口
from media.display import *
from media.media import *

from machine import Timer
from machine import FPIOA
from machine import Pin
from machine import UART
from machine import PWM
import image
#from machine import TOUCH      (触控屏)

# ======================= 1. 全局配置 =======================

# --- 状态定义 ---
STATE_RESET = 0  # 初始复位状态


# --- 摄像头与显示配置 ---
sensor_id = 2
sensor = None
DISPLAY_WIDTH, DISPLAY_HEIGHT = 640, 480 # 显示屏分辨率
picture_width, picture_height = 640, 480 # 摄像头图像分辨率


# --- 视觉识别配置 ---
RED_THRESHOLD = [(85, 100, -18, 50, -18, 51), (69, 100, -12, 58, -20, 20), (83, 100, -9, 13, -6, 22)]   # 红色目标颜色阈值 (L*, a*, b* 范围)
rect_binary_threshold = [(82, 212)]             # 矩形检测二值化阈值 (灰度值范围)
rect_area_threshold = 20000                     # 矩形最小面积阈值，用于过滤小噪声
blob_area_threshold = 5                         # 颜色块最小面积阈值，用于过滤小噪声

# --- 全局参数定义 ---
state = 0     #识别状态

# 矩形识别状态
rect_detection_done = False
rect_detection_time = 0

# 三角形识别状态
triangle_detection_done = False
triangle_detection_time = 0


# ======================= 2. 初始化 =======================

# 初始化串口
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart2 = UART(UART.UART2, 115200)

# 创建按键对象，用于触发图像采集
fpioa.set_function(53, FPIOA.GPIO53)  # 设置GPIO53功能
KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)  # GPIO53作为输入引脚，下拉模式

# ======================= 3. 函数定义 =======================

# --- 串口发送数据包 ---
def send_data(x, y):
    # 使用struct.pack构建数据包
    frame = b'\xAA' + struct.pack('<BHHHH', 1, x, y) + b'\x55'
    uart2.write(frame)
    time.sleep_ms(6)  # 单次发送
    return frame  # 返回构建的frame

# --- 状态管理函数 ---
def display_state_info(state_code, duration=2):
    state_definitions = [
        (0, "复位状态", "系统初始化完成", (0, 255, 0)),
        (1, "运行状态", "正在执行识别任务", (0, 255, 255)),
        (2, "暂停状态", "等待用户操作", (255, 255, 0)),
        (3, "错误状态", "检测到异常情况", (255, 0, 0))
    ]

    # 获取当前状态信息
    current_state_info = next((s for s in state_definitions if s[0] == state_code),
                            (state_code, "未知状态", "未知状态", (255, 0, 255)))

    # 创建状态显示画面
    status_img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.RGB565)
    status_img.draw_rectangle(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, color=(30, 30, 30), thickness=2, fill=True)

    # 绘制状态边框
    border_color = current_state_info[3]
    status_img.draw_rectangle(50, 50, DISPLAY_WIDTH-100, DISPLAY_HEIGHT-100,
                          color=border_color, thickness=4, fill=False)

    # 显示状态信息
    status_img.draw_string_advanced(DISPLAY_WIDTH//2 - 120, DISPLAY_HEIGHT//2 - 80, 45,
                                   f"状态: {current_state_info[1]}", color=border_color)
    status_img.draw_string_advanced(DISPLAY_WIDTH//2 - 150, DISPLAY_HEIGHT//2 - 20, 30,
                                   f"描述: {current_state_info[2]}", color=(255, 255, 255))
    status_img.draw_string_advanced(DISPLAY_WIDTH//2 - 80, DISPLAY_HEIGHT//2 + 30, 35,
                                   f"码: {state_code}", color=(200, 200, 200))
    status_img.draw_string_advanced(DISPLAY_WIDTH//2 - 100, DISPLAY_HEIGHT//2 + 80, 25,
                                   f"时间: {time.ticks_ms()//1000}s", color=(150, 150, 150))

    Display.show_image(status_img)
    time.sleep(duration)



def handle_key_state_switch():
    global state, rect_detection_done, rect_detection_time, triangle_detection_done, triangle_detection_time

    # 检测按键状态（GPIO53）
    if KEY.value() == 1:  # 按键按下
        state = (state + 1) % 4  # 循环切换状态 0-3
        print(f"按键触发，状态切换到: {state}")
        display_state_info(state, 1)  # 显示1秒

        # 重置矩形识别状态
        rect_detection_done = False
        rect_detection_time = 0
        
        # 重置三角形识别状态
        triangle_detection_done = False
        triangle_detection_time = 0

        # 防抖延时
        time.sleep_ms(200)  # 简化的防抖延时
        # 等待按键释放
        while KEY.value() == 1:
            time.sleep_ms(10)

    return state





# ======================= 4. 主程序 =======================
try:

    clock = time.clock()
    sensor = Sensor(id = sensor_id) #构建摄像头对象
    sensor.reset() #复位和初始化摄像头
    sensor.set_framesize(width = picture_width, height = picture_height) #设置帧大小为LCD分辨率()，默认通道0    （显示画面的大小）一般小
    sensor.set_pixformat(Sensor.RGB565) #设置输出图像格式，默认通道0

    Display.init(Display.VIRT, width = DISPLAY_WIDTH, height = DISPLAY_HEIGHT) #只使用IDE缓冲区显示图像      （画面大小）一般大
    MediaManager.init() #初始化media资源管理器
    sensor.run() #启动sensor



    # 初始化显示状态
    display_state_info(state, 2)  # 启动时显示初始状态

    while True:
        clock.tick()
        os.exitpoint()  # 退出点，用于调试
        img = sensor.snapshot(chn = CAM_CHN_ID_0)  # 从摄像头通道0获取一帧图像

        # 处理按键状态切换
        handle_key_state_switch()

        # 处理串口状态切换
        if uart2.any():  # 检查是否有数据可读
            Rxbuf = uart2.read(5)  # 读取5个字节
            if Rxbuf and len(Rxbuf) == 5:
                if (Rxbuf[0] == 0xAA and Rxbuf[2] == 0xFF and Rxbuf[3] == 0xFF and Rxbuf[4] == 0xFF):
                    new_state = Rxbuf[1]
                    if 0 <= new_state <= 3 and new_state != state:
                        state = new_state
                        print(f"串口触发，状态切换到: {state}")
                        display_state_info(state, 1)
                        
                        # 重置矩形识别状态
                        rect_detection_done = False
                        rect_detection_time = 0
                        
                        # 重置三角形识别状态
                        triangle_detection_done = False
                        triangle_detection_time = 0

        # 根据当前状态执行不同任务
        if state == 0:  # 复位状态
            # 显示待机画面
            img.draw_string_advanced(10, 10, 30, "复位状态 - 等待开始", color=(0, 255, 0))

        elif state == 1:  # 运行状态
            # 执行图像识别任务
            img.draw_string_advanced(10, 10, 30, "运行状态 - 识别中", color=(0, 255, 0))

        elif state == 2:  # 暂停状态
            # 暂停识别，显示暂停信息
            img.draw_string_advanced(10, 10, 30, "暂停状态 - 按任意键继续", color=(255, 255, 0))


        elif state == 3:  # 错误状态
            # 显示错误信息
            img.draw_string_advanced(10, 10, 30, "错误状态 - 请检查系统", color=(255, 0, 0))

        # 快速状态与帧率显示
        fps = int(clock.fps())

        img.draw_string_advanced(DISPLAY_WIDTH-100, 10, 20, f"{state}状态 {fps}fps", color=(255, 255, 255))

        # 正常显示摄像头画面
        Display.show_image(img)





except KeyboardInterrupt as e:
    print("user stop: ", e)
except BaseException as e:
    print(f"Exception {e}")
finally:
    # sensor stop run
    if isinstance(sensor, Sensor):
        sensor.stop()
    # deinit display
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    # release media buffer
    MediaManager.deinit()

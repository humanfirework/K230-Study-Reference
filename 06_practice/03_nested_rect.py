# ========================= 库导入 =========================
import gc
import os
import sys
import time
import math
import image
import struct

from media.sensor import * 
from media.display import *
from media.media import *

from machine import TOUCH 
from machine import Timer
from machine import FPIOA
from machine import Pin
from machine import UART
from machine import PWM


# ======================= 1. 全局配置 =======================

# --- 状态定义 ---
STATE_RESET = 0  # 初始复位状态


# --- 摄像头与显示配置 ---
sensor_id = 2
sensor = None
DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480 # 显示屏分辨率
picture_width, picture_height = 800, 480 # 摄像头图像分辨率


# --- 视觉识别配置 ---
RED_THRESHOLD = [(85, 100, -18, 50, -18, 51), (69, 100, -12, 58, -20, 20), (83, 100, -9, 13, -6, 22)]   # 红色目标颜色阈值 (L*, a*, b* 范围)
rect_binary_threshold = [(82, 212)]             # 矩形检测二值化阈值 (灰度值范围)
rect_area_threshold = 20000                     # 矩形最小面积阈值，用于过滤小噪声
blob_area_threshold = 5                         # 颜色块最小面积阈值，用于过滤小噪声

# --- 全局参数定义 ---
state = 0     #识别状态
rect_detection_done = False  # 矩形识别完成标志
rect_detection_time = 0      # 矩形识别完成时间
outer_corners = None         # 外框角点数据
inner_corners = None         # 内框角点数据
all_target_points = None     # 所有目标路径点


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

# 几何中心排序：按顺时针方向排序角点
def sort_corners_clockwise(corners):
    # 计算中心点
    cx = sum(p[0] for p in corners) / 4
    cy = sum(p[1] for p in corners) / 4

    # 按角度排序（从右上角开始顺时针）
    def angle_from_center(p):
        x, y = p[0] - cx, p[1] - cy
        return (math.atan2(-y, x) + 2 * math.pi) % (2 * math.pi)

    return sorted(corners, key=angle_from_center)

def handle_running_state(img, RED_THRESHOLD, blob_area_threshold, rect_binary_threshold,
                       rect_area_threshold, clock, DISPLAY_WIDTH, DISPLAY_HEIGHT):
    global state, rect_detection_done, rect_detection_time, outer_corners, inner_corners, target_corners, all_target_points

    img.draw_string_advanced(10, 10, 30, "运行状态 - 识别中", color=(0, 255, 255))

    # 快速矩形识别流程
    if not rect_detection_done:
        # 只在需要识别时进行处理
        img_gray = img.to_grayscale()

        # 优化红色过滤：直接覆盖红色区域为黑色，减少颜色转换
        red_blobs = img.find_blobs(RED_THRESHOLD, pixels_threshold=blob_area_threshold)
        for blob in red_blobs:
            img.draw_rectangle(blob.x(), blob.y(), blob.w(), blob.h(), color=(0,0,0), thickness=-1)
        img_gray = img.to_grayscale()

        # 简化形态学操作
        img_binary = img_gray.binary(rect_binary_threshold)
        img_binary = img_binary.dilate(1).erode(1)

        # 快速矩形检测
        rects = img_binary.find_rects(threshold=int(rect_area_threshold * 1.5))

        # 简化筛选
        valid_rects = []
        for r in rects:
            area = r.w() * r.h()
            if area < rect_area_threshold * 1.5:
                continue

            # 快速长宽比检查
            if min(r.w(), r.h()) == 0:
                continue
            ratio = max(r.w(), r.h()) / min(r.w(), r.h())
            if 0.3 <= ratio <= 3.0:
                valid_rects.append(r)

        # 处理两个矩形
        if len(valid_rects) >= 2:
            valid_rects.sort(key=lambda x: x.w() * x.h(), reverse=True)
            outer_corners = valid_rects[0].corners()
            inner_corners = valid_rects[1].corners()

            # 几何中心排序：按顺时针方向排序角点
            outer_corners = sort_corners_clockwise(outer_corners)
            inner_corners = sort_corners_clockwise(inner_corners)

            # 计算目标矩形的顶点（外框和内框顶点的中点）
            target_corners = []
            for i in range(4):
                mid_x = (outer_corners[i][0] + inner_corners[i][0]) // 2
                mid_y = (outer_corners[i][1] + inner_corners[i][1]) // 2
                target_corners.append((mid_x, mid_y))

            # 对目标矩形顶点进行顺时针排序
            target_corners = sort_corners_clockwise(target_corners)

            # 生成目标矩形边缘的插值路径点
            all_target_points = []
            interpolation_steps = 10  # 每条边的插值点数
            for i in range(4):
                start = target_corners[i]
                end = target_corners[(i + 1) % 4]
                for j in range(interpolation_steps + 1):
                    t = j / interpolation_steps
                    x = int(start[0] + t * (end[0] - start[0]))
                    y = int(start[1] + t * (end[1] - start[1]))
                    all_target_points.append((x, y))

            # 设置矩形识别完成标志
            rect_detection_done = True
            rect_detection_time = time.ticks_ms()
            print("矩形识别完成！3秒后进入激光追踪")

    elif rect_detection_done:
        # 优化的绘制逻辑
        elapsed_time = time.ticks_ms() - rect_detection_time

        # 只在倒计时期间绘制完整信息
        if elapsed_time < 3000:
            remaining_time = 3 - (elapsed_time // 1000)
            # 简化绘制，只绘制矩形边框
            for corners, color in [(outer_corners, (255, 0, 0)), (inner_corners, (0, 255, 0))]:
                for i in range(4):
                    next_i = (i + 1) % 4
                    img.draw_line(corners[i][0], corners[i][1],
                                corners[next_i][0], corners[next_i][1],
                                color=color, thickness=2)

            # 简化路径点显示
            for i, point in enumerate(all_target_points[::4]):  # 间隔绘制
                img.draw_circle(point[0], point[1], 1, color=(0, 0, 255), thickness=1)

            img.draw_string_advanced(DISPLAY_WIDTH//2 - 100, DISPLAY_HEIGHT//2 + 50, 35,
                                   f"倒计时: {remaining_time}", color=(255, 255, 0))

        elif elapsed_time >= 3000:
            # 激光追踪阶段
            red_blobs = img.find_blobs(RED_THRESHOLD, pixels_threshold=blob_area_threshold)

            # 快速绘制矩形边框
            for corners, color in [(outer_corners, (255, 0, 0)), (inner_corners, (0, 255, 0))]:
                for i in range(4):
                    next_i = (i + 1) % 4
                    img.draw_line(corners[i][0], corners[i][1],
                                corners[next_i][0], corners[next_i][1],
                                color=color, thickness=1)

            if red_blobs:
                laser_blob = max(red_blobs, key=lambda x: x.pixels())
                laser_x, laser_y = laser_blob.cx(), laser_blob.cy()

                # 简化的最近点计算
                min_dist = float('inf')
                target_point = all_target_points[0]
                for point in all_target_points:
                    dist = abs(laser_x - point[0]) + abs(laser_y - point[1])  # 曼哈顿距离
                    if dist < min_dist:
                        min_dist = dist
                        target_point = point

                img.draw_circle(laser_x, laser_y, 3, color=(255, 255, 0), thickness=1)
                img.draw_line(laser_x, laser_y, target_point[0], target_point[1],
                            color=(255, 255, 0), thickness=1)

                # 简化信息显示
                img.draw_string_advanced(10, 50, 20, f"激光:({laser_x},{laser_y})", color=(255, 255, 255))
                img.draw_string_advanced(10, 75, 20, f"距离:{int(min_dist)}", color=(255, 255, 255))

                send_data(laser_x, laser_y)

            else:
                img.draw_string_advanced(10, 50, 20, "等待激光点", color=(255, 0, 0))

    else:
        # 简化调试信息
        img.draw_string_advanced(10, 50, 20, f"矩形:{len(valid_rects)}/2", color=(255, 255, 0))

def handle_key_state_switch():
    global state, rect_detection_done, rect_detection_time

    # 检测按键状态（GPIO53）
    if KEY.value() == 1:  # 按键按下
        state = (state + 1) % 4  # 循环切换状态 0-3
        print(f"按键触发，状态切换到: {state}")
        display_state_info(state, 1)  # 显示1秒

        # 重置矩形识别状态
        rect_detection_done = False
        rect_detection_time = 0

        # 防抖延时
        while KEY.value() == 1:
            time.sleep_ms(50)

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
        Rxbuf = bytearray(5)
        Rx_NumBytes = uart2.readinto(Rxbuf, 5)
        if Rx_NumBytes is not None and Rx_NumBytes == 5:
            if (Rxbuf[0] == 0x55 and Rxbuf[2] == 0xFF and Rxbuf[3] == 0xFF and Rxbuf[4] == 0xFF):
                new_state = Rxbuf[1]
                if 0 <= new_state <= 3 and new_state != state:
                    state = new_state
                    print(f"串口触发，状态切换到: {state}")
                    display_state_info(state, 1)

                    # 重置矩形识别状态
                    rect_detection_done = False
                    rect_detection_time = 0

        # 根据当前状态执行不同任务
        if state == 0:  # 复位状态
            # 显示待机画面
            img.draw_string_advanced(10, 10, 30, "复位状态 - 等待开始", color=(0, 255, 0))

        elif state == 1:  # 运行状态
            # 执行图像识别任务
            handle_running_state(img, RED_THRESHOLD, blob_area_threshold, rect_binary_threshold,
                               rect_area_threshold, clock, DISPLAY_WIDTH, DISPLAY_HEIGHT)

        elif state == 2:  # 暂停状态
            # 暂停识别，显示暂停信息
            img.draw_string_advanced(10, 10, 30, "暂停状态 - 按任意键继续", color=(255, 255, 0))

        elif state == 3:  # 错误状态
            # 显示错误信息
            img.draw_string_advanced(10, 10, 30, "错误状态 - 请检查系统", color=(255, 0, 0))

        # 快速状态与帧率显示
        fps = int(clock.fps())

        img.draw_string_advanced(DISPLAY_WIDTH-100, 10, 20, f"{state}状态 {fps}fps", color=(255, 255, 255))
        img = img.copy(roi = (224, 56, 424, 336))
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

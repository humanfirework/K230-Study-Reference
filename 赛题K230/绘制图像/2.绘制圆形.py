import time, os, sys
import math
import struct
from media.sensor import *
from media.display import *
from media.media import *
from machine import FPIOA
from machine import UART
from machine import Pin

picture_width = 800
picture_height = 480
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

sensor_id = 2
sensor = None

rect_binart = [(93, 179)]

# 串口配置
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart2 = UART(UART.UART2, 115200)

# 激光识别阈值
RED_THRESHOLD = [(83, 100, -19, 42, -49, 65)]

# 状态变量
rect_detected = False
rect_corners = []
rect_center = (0, 0)
circle_path = []
current_target_index = 0
tracking_started = False
circle_radius = 0

def find_max_Rect(rects):
    if not rects:
        return None
    max_rect = None
    max_area = 0
    for rect in rects:
        x, y, w, h = rect.rect()
        area = w * h
        if area > max_area:
            max_area = area
            max_rect = rect
    return max_rect

def distance(p1, p2):
    """计算两点间距离"""
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

def find_laser_point(img):
    """识别激光点"""
    blobs = img.find_blobs(RED_THRESHOLD, pixels_threshold=5)
    if blobs:
        # 找到最大的红色区域
        largest_blob = max(blobs, key=lambda b: b.pixels())
        return (largest_blob.cx(), largest_blob.cy())
    return None

def send_data(x, y):
    """发送坐标数据"""
    frame = b'\xAA' + struct.pack('<BHH', 0, x, y) + b'\x55'
    uart2.write(frame)
    uart2.flush()  # 等待发送完成
    print(f"[SEND_DATA] 发送坐标: ({x}, {y})")
    print(f"[SEND_DATA] 数据帧: {frame.hex().upper()}")
    return frame

def send_rect_data(corners, center):
    """发送矩形数据：4个角点+中心点（整合发送）"""
    # 整合所有数据到一个数据帧：
    # 格式：0xAA + 命令字(0x01) + 8个坐标值(x1,y1,x2,y2,x3,y3,x4,y4) + 2个中心坐标(cx,cy) + 0x55
    # 总共发送10个16位数据
    frame = b'\xAA' + struct.pack('<BHHHHHHHHHH', 1,
                                   corners[0][0], corners[0][1],  # 角点1
                                   corners[1][0], corners[1][1],  # 角点2
                                   corners[2][0], corners[2][1],  # 角点3
                                   corners[3][0], corners[3][1],  # 角点4
                                   center[0], center[1]) + b'\x55'  # 中心点
    uart2.write(frame)
    uart2.flush()  # 等待发送完成
    print(f"[SEND_RECT] 发送矩形数据:")
    print(f"[SEND_RECT] 角点1: ({corners[0][0]}, {corners[0][1]})")
    print(f"[SEND_RECT] 角点2: ({corners[1][0]}, {corners[1][1]})")
    print(f"[SEND_RECT] 角点3: ({corners[2][0]}, {corners[2][1]})")
    print(f"[SEND_RECT] 角点4: ({corners[3][0]}, {corners[3][1]})")
    print(f"[SEND_RECT] 中心点: ({center[0]}, {center[1]})")
    print(f"[SEND_RECT] 数据帧: {frame.hex().upper()}")
    return frame

def send_tracking_data(laser_x, laser_y, target_x, target_y):
    """发送激光点和目标点数据"""
    frame = b'\xAA' + struct.pack('<BHHHH', 2, laser_x, laser_y, target_x, target_y) + b'\x55'
    uart2.write(frame)
    uart2.flush()  # 等待发送完成
    print(f"[SEND_TRACK] 发送追踪数据:")
    print(f"[SEND_TRACK] 激光点: ({laser_x}, {laser_y})")
    print(f"[SEND_TRACK] 目标点: ({target_x}, {target_y})")
    print(f"[SEND_TRACK] 数据帧: {frame.hex().upper()}")
    return frame

def generate_circle_path_points(center_x, center_y, radius, interpolation_steps=60):
    """生成圆形边缘的插值路径点"""
    all_target_points = []
    for i in range(interpolation_steps + 1):
        angle = 2 * math.pi * i / interpolation_steps
        x = int(center_x + radius * math.cos(angle))
        y = int(center_y + radius * math.sin(angle))
        all_target_points.append((x, y))
    return all_target_points

def draw_circle_with_interpolation_points(img, center_x, center_y, radius, color, thickness=2):
    """绘制带插值点的圆形"""
    # 绘制圆形
    img.draw_circle(center_x, center_y, radius, color=color, thickness=thickness)

    # 生成插值路径点
    interpolation_steps = 100  # 圆形边缘100个插值点
    path_points = generate_circle_path_points(center_x, center_y, radius, interpolation_steps)

    # 绘制插值点
    for i, point in enumerate(path_points):
        if i % 3 == 0:  # 间隔绘制，避免太密集
            img.draw_circle(point[0], point[1], 2, color=(0, 255, 255), thickness=1, fill=True)

    return path_points

try:
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id)
    # 重置摄像头sensor
    sensor.reset()

    # 设置通道0的输出尺寸
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)

    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

    #构造clock
    clock = time.clock()

    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 灰度图
        img_gray = img.to_grayscale(copy = True)
        # 二制化
        img_rect = img_gray.binary(rect_binart)

        if not rect_detected:
            # 矩形识别阶段
            rects = img_rect.find_rects(threshold = 5000)
            max_rect = find_max_Rect(rects)

            if max_rect:
                corners = max_rect.corners()
                center_x = (corners[0][0] + corners[2][0]) // 2
                center_y = (corners[0][1] + corners[2][1]) // 2

                # 绘制矩形边框
                for i in range(4):
                    next_i = (i + 1) % 4
                    img.draw_line(corners[i][0], corners[i][1], corners[next_i][0], corners[next_i][1],
                                color=(0, 255, 0), thickness=3)

                # 绘制矩形中心点
                img.draw_cross(center_x, center_y, color=(255, 255, 255))

                # 发送矩形数据
                rect_corners = corners
                rect_center = (center_x, center_y)
                send_rect_data(rect_corners, rect_center)
                print("已发送矩形坐标和中心点")

                # 计算圆形半径（矩形最小边长的1/4）
                rect_width = abs(corners[1][0] - corners[0][0])
                rect_height = abs(corners[3][1] - corners[0][1])
                circle_radius = min(rect_width, rect_height) // 4

                if circle_radius > 10:
                    # 在矩形中心绘制带插值点的圆形
                    circle_path = generate_circle_path_points(center_x, center_y, circle_radius, interpolation_steps=100)
                    # 绘制带插值点的圆形
                    draw_circle_with_interpolation_points(img, center_x, center_y, circle_radius, color=(255, 0, 0), thickness=2)

                    # 绘制圆形
                    img.draw_circle(center_x, center_y, circle_radius, color=(255, 0, 0), thickness=2)

                    # 绘制圆形插值点
                    for i, point in enumerate(circle_path):
                        if i % 3 == 0:  # 间隔绘制，避免太密集
                            img.draw_circle(point[0], point[1], 2, color=(0, 255, 255), thickness=1, fill=True)

                    # 设置状态
                    rect_detected = True
                    current_target_index = 0
                    tracking_started = False

                    print("矩形识别完成，开始圆形追踪")
                    print(f"圆形中心: ({center_x}, {center_y})")
                    print(f"圆形半径: {circle_radius}")
                    print(f"追踪路径点数量: {len(circle_path)}")

        else:
            # 激光追踪阶段
            laser_pos = find_laser_point(img)

            if laser_pos:
                laser_x, laser_y = laser_pos

                if not tracking_started:
                    # 从圆形0度位置开始
                    current_target_index = 0
                    tracking_started = True

                if current_target_index < len(circle_path):
                    target_x, target_y = circle_path[current_target_index]

                    # 绘制激光点
                    img.draw_circle(laser_x, laser_y, 5, color=(255, 255, 0), thickness=2)

                    # 绘制目标点
                    img.draw_circle(target_x, target_y, 8, color=(0, 255, 0), thickness=2)
                    img.draw_cross(target_x, target_y, color=(0, 255, 0))

                    # 绘制连线
                    img.draw_line(laser_x, laser_y, target_x, target_y, color=(255, 255, 255), thickness=1)

                    # 发送追踪数据
                    send_tracking_data(laser_x, laser_y, target_x, target_y)

                    # 实时打印位置信息
                    print(f"激光点: ({laser_x}, {laser_y})  目标点: ({target_x}, {target_y})")

                    # 显示进度信息
                    img.draw_string_advanced(10, 10, 16, f"激光:({laser_x},{laser_y})", color=(255, 255, 255))
                    img.draw_string_advanced(10, 30, 16, f"目标:({target_x},{target_y})", color=(0, 255, 0))
                    img.draw_string_advanced(10, 50, 16, f"进度:{current_target_index+1}/{len(circle_path)}", color=(255, 255, 0))

                    # 检查是否到达目标点
                    dist = distance(laser_pos, (target_x, target_y))
                    if dist < 10:  # 距离阈值
                        current_target_index += 1
                        if current_target_index >= len(circle_path):
                            print("圆形追踪完成！")
                            # 重置状态
                            rect_detected = False
                            tracking_started = False
                            current_target_index = 0
                else:
                    # 追踪完成，显示完成信息
                    img.draw_string_advanced(DISPLAY_WIDTH//2-100, DISPLAY_HEIGHT//2, 24,
                                           "追踪完成！按任意键重新开始", color=(0, 255, 255))

                    # 显示圆形信息
                    center_x, center_y = rect_center
                    img.draw_string_advanced(center_x - 30, center_y - circle_radius - 30, 16,
                                           f"Circle: {circle_radius}Pin", color=(255, 255, 0))
                    img.draw_string_advanced(center_x - 40, center_y - circle_radius - 50, 16,
                                           f"Points: {len(circle_path)}", color=(0, 255, 255))
            else:
                # 未检测到激光点
                img.draw_string_advanced(10, 10, 16, "等待激光点...", color=(255, 0, 0))
        #在IDE显示FPS
        img.draw_string_advanced(192, 40, 20, "FPS: {}".format(clock.fps()), color=(255, 0, 0))

        #img = img.copy(roi = (192, 40, 464, 360))
        Display.show_image(img)

except KeyboardInterrupt as e:
    print("用户停止: ", e)
except BaseException as e:
    print(f"异常: {e}")
finally:
    # 停止传感器运行
    if isinstance(sensor, Sensor):
        sensor.stop()
    # 反初始化显示模块
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    # 释放媒体缓冲区
    MediaManager.deinit()

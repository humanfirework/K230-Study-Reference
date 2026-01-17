import time, os, sys
import math
import struct
import gc
from media.sensor import *
from media.display import *
from media.media import *
from machine import FPIOA
from machine import UART
from machine import Pin
import cv_lite
import ulab.numpy as np

picture_width = 800
picture_height = 480
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

sensor_id = 2
sensor = None

rect_binart = [(51, 80)]

# 串口配置
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart2 = UART(UART.UART2, 115200)

# 激光识别阈值 - 优化红色识别精度
RED_THRESHOLD = [(46, 100, -128, 127, -128, 127)]

# 状态变量
rect_detected = False
rect_corners = []
rect_center = (0, 0)
triangle_points = []
triangle_path = []
current_target_index = 0
tracking_started = False

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
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def send_data(x, y):
    """发送坐标数据"""
    frame = b'\xAA' + struct.pack('<BHHHH', 1, x, y) + b'\x55'
    uart2.write(frame)
    time.sleep_ms(6)
    return frame

def send_rect_data(corners, center):
    """发送矩形数据：4个角点+中心点"""
    # 发送4个角点
    for i, (x, y) in enumerate(corners):
        frame = b'\xAA' + struct.pack('<BHHHH', 10+i, x, y) + b'\x55'
        uart2.write(frame)
        time.sleep_ms(6)

    # 发送中心点
    frame = b'\xAA' + struct.pack('<BHHHH', 15, center[0], center[1]) + b'\x55'
    uart2.write(frame)
    time.sleep_ms(6)

def send_tracking_data(laser_x, laser_y, target_x, target_y):
    """发送激光点和目标点数据"""
    frame = b'\xAA' + struct.pack('<BHHHHH', 20, laser_x, laser_y, target_x, target_y) + b'\x55'
    uart2.write(frame)
    time.sleep_ms(6)
    return frame

def find_laser_point(img):
    """识别激光点 - 优化识别精度"""
    # 添加高斯模糊预处理减少噪声
    img_blur = img.copy()
    img_blur.gaussian(1)

    # 使用优化参数进行blob检测
    blobs = img_blur.find_blobs(RED_THRESHOLD,
                               pixels_threshold=3,
                               area_threshold=3,
                               x_stride=2,
                               y_stride=2,
                               merge=True)

    if blobs:
        # 优先选择圆形度较高的区域，提高激光点识别准确性
        valid_blobs = []
        for blob in blobs:
            if blob.roundness() > 0.6:  # 圆形度阈值
                valid_blobs.append(blob)

        if valid_blobs:
            # 在有效区域中选择最大的
            largest_blob = max(valid_blobs, key=lambda b: b.pixels())
            return (largest_blob.cx(), largest_blob.cy())
        elif blobs:
            # 如果没有满足圆形度的，选择最大的
            largest_blob = max(blobs, key=lambda b: b.pixels())
            return (largest_blob.cx(), largest_blob.cy())

    return None

def generate_triangle_path_points(triangle, interpolation_steps=20):
    """生成三角形边缘的插值路径点"""
    all_target_points = []
    # 对三角形的三条边进行插值
    for i in range(3):
        start = triangle[i]
        end = triangle[(i + 1) % 3]
        for j in range(interpolation_steps + 1):
            t = j / interpolation_steps
            x = int(start[0] + t * (end[0] - start[0]))
            y = int(start[1] + t * (end[1] - start[1]))
            all_target_points.append((x, y))
    return all_target_points

#根据了矩形的边长来绘制三角形
def draw_equilateral_triangle(img, center_x, center_y, side_length, color, thickness=2):
    """在指定中心点绘制等边三角形"""
    # 计算等边三角形的三个顶点
    # 顶点朝上
    height = (math.sqrt(3) / 2) * side_length

    # 三个顶点坐标
    top_x = center_x
    top_y = int(center_y - height / 2)

    left_x = int(center_x - side_length / 2)
    left_y = int(center_y + height / 2)

    right_x = int(center_x + side_length / 2)
    right_y = int(center_y + height / 2)

    # 绘制三角形的三条边
    img.draw_line(top_x, top_y, left_x, left_y, color=color, thickness=thickness)
    img.draw_line(left_x, left_y, right_x, right_y, color=color, thickness=thickness)
    img.draw_line(right_x, right_y, top_x, top_y, color=color, thickness=thickness)

    return [(top_x, top_y), (left_x, left_y), (right_x, right_y)]

def draw_triangle_with_interpolation_points(img, center_x, center_y, side_length, color, thickness=2):
    """绘制带插值点的等边三角形"""
    # 获取三角形顶点
    triangle_points = draw_equilateral_triangle(img, center_x, center_y, side_length, color, thickness)

    # 生成插值路径点
    interpolation_steps = 20  # 每条边20个插值点
    path_points = generate_triangle_path_points(triangle_points, interpolation_steps)

    # 绘制插值点
    for i, point in enumerate(path_points):
        if i % 3 == 0:  # 间隔绘制，避免太密集
            img.draw_circle(point[0], point[1], 2, color=(0, 255, 255), thickness=1, fill=True)

    return triangle_points, path_points

# 计算两点间距离
def distance(point1, point2):
    """
    计算两点间的欧几里得距离
    :param point1: 点1坐标 (x1, y1)
    :param point2: 点2坐标 (x2, y2)
    :return: 距离值
    """
    return int(math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2))

try:
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id)
    # 重置摄像头sensor
    sensor.reset()

    # 设置通道0的输出尺寸
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)

    sensor.set_pixformat(Sensor.RGB888, chn=CAM_CHN_ID_0)

    Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

    # 曝光增益因子（<1 降低亮度，>1 增加亮度）
    exposure_gain = 0.5  # 降低曝光以适应激光强度，推荐范围 0.2~3.0

    #构造clock
    clock = time.clock()

    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 曝光调整优化：仅在必要时进行RGB888格式转换
        if exposure_gain != 1.0:  # 仅当需要调整曝光时才进行转换
            # 获取RGB888图像数据并转换为numpy数组
            img_np = img.to_numpy_ref()

            # 使用cv_lite模块进行曝光调节（降低曝光以适应激光强度）
            exposed_np = cv_lite.rgb888_adjust_exposure([img.height(), img.width()],
                                                       img_np, exposure_gain)

            # 将调整后的图像重新包装为Image对象
            img = image.Image(img.width(), img.height(), image.RGB888,
                             alloc=image.ALLOC_REF, data=exposed_np)

            # 强制类型转换为RGB565以兼容后续处理
            img = img.to_rgb565()

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

                # 计算三角形边长
                rect_width = abs(corners[1][0] - corners[0][0])
                rect_height = abs(corners[3][1] - corners[0][1])
                triangle_side = min(rect_width, rect_height) // 2

                if triangle_side > 10:
                    # 绘制三角形
                    triangle_points = draw_equilateral_triangle(img, center_x, center_y,
                                                              triangle_side, color=(255, 0, 0), thickness=2)

                    # 生成三角形路径点（顺时针顺序）
                    triangle_path = generate_triangle_path_points(triangle_points, interpolation_steps=30)

                    # 设置状态
                    rect_detected = True
                    current_target_index = 0
                    tracking_started = False

                    print("矩形识别完成，开始三角形追踪")
                    print(f"三角形顶点: {triangle_points}")
                    print(f"追踪路径点数量: {len(triangle_path)}")

        else:
            # 激光追踪阶段
            laser_pos = find_laser_point(img)

            if laser_pos:
                laser_x, laser_y = laser_pos

                if not tracking_started:
                    # 从三角形左下角开始
                    current_target_index = 0
                    tracking_started = True

                if current_target_index < len(triangle_path):
                    target_x, target_y = triangle_path[current_target_index]

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
                    img.draw_string_advanced(10, 50, 16, f"进度:{current_target_index+1}/{len(triangle_path)}", color=(255, 255, 0))

                    # 检查是否到达目标点
                    dist = distance(laser_pos, (target_x, target_y))
                    if dist < 10:  # 距离阈值
                        current_target_index += 1
                        if current_target_index >= len(triangle_path):
                            print("三角形追踪完成！")
                            # 重置状态
                            rect_detected = False
                            tracking_started = False
                            current_target_index = 0
                else:
                    # 追踪完成，显示完成信息
                    img.draw_string_advanced(DISPLAY_WIDTH//2-100, DISPLAY_HEIGHT//2, 24,
                                           "追踪完成！按任意键重新开始", color=(0, 255, 255))
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
    # 优化内存管理：减少垃圾回收频率
    if clock.fps() < 10:  # 仅在帧率过低时回收内存
        gc.collect()

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

rect_binart = [(95, 158)]

# 串口配置
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart2 = UART(UART.UART2, 115200)

fpioa.set_function(53, FPIOA.GPIO53)  # 设置GPIO53功能
KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)  # GPIO53作为输入引脚，下拉模式

# 激光识别阈值
RED_THRESHOLD = [(83, 100, -19, 42, -49, 65)]

# 状态变量
rect_detected = False
rect_corners = []
rect_center = (0, 0)
bezier_path = []
current_target_index = 0
tracking_started = False
curve_type = "heart"  # 曲线类型："sine" 绘制正弦曲线，"heart" 绘制心形曲线

# 贝塞尔曲线参数
BEZIER_STEPS = 50  # 曲线离散化步数

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
    frame = b'\xAA' + struct.pack('<BHH', 0, x, y) + b'\x55'
    uart2.write(frame)
    uart2.flush()  # 等待发送完成
    print(f"[SEND_DATA] 发送坐标: ({x}, {y})")
    print(f"[SEND_DATA] 数据帧: {frame.hex().upper()}")
    return frame

def send_rect_data(corners, center):
    """发送矩形数据：4个角点+中心点（整合发送）"""
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

def find_laser_point(img):
    """识别激光点"""
    blobs = img.find_blobs(RED_THRESHOLD, pixels_threshold=5)
    if blobs:
        largest_blob = max(blobs, key=lambda b: b.pixels())
        return (largest_blob.cx(), largest_blob.cy())
    return None

def bezier_quadratic(p0, p1, p2, t):
    """二阶贝塞尔曲线计算"""
    x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
    y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
    return (int(x), int(y))

def bezier_cubic(p0, p1, p2, p3, t):
    """三阶贝塞尔曲线计算"""
    x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
    y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
    return (int(x), int(y))

def generate_heart_bezier_path(center_x, center_y, size):
    """生成倒转的爱心型贝塞尔曲线路径（尖端朝下）"""
    path_points = []
    steps = 60

    # 倒转的爱心曲线控制点
    # 上半部分（两个半圆）
    top_left_control = [
        (center_x, center_y + size//2),
        (center_x - size//2, center_y + size//2),
        (center_x - size, center_y + size//4),
        (center_x - size, center_y - size//4)
    ]
    
    top_right_control = [
        (center_x - size, center_y - size//4),
        (center_x - size, center_y - size),
        (center_x, center_y - size),
        (center_x, center_y - size//2)
    ]
    
    bottom_control = [
        (center_x, center_y - size//2),
        (center_x, center_y - size),
        (center_x + size, center_y - size),
        (center_x + size, center_y - size//4)
    ]
    
    bottom_right_control = [
        (center_x + size, center_y - size//4),
        (center_x + size, center_y + size//4),
        (center_x + size//2, center_y + size//2),
        (center_x, center_y + size//2)
    ]

    # 生成上半部分左侧曲线
    for t in range(steps + 1):
        point = bezier_cubic(*top_left_control, t/steps)
        path_points.append(point)

    # 生成上半部分右侧曲线
    for t in range(steps + 1):
        point = bezier_cubic(*top_right_control, t/steps)
        path_points.append(point)
        
    # 生成下半部分曲线
    for t in range(steps + 1):
        point = bezier_cubic(*bottom_control, t/steps)
        path_points.append(point)
        
    # 生成底部右侧曲线
    for t in range(steps + 1):
        point = bezier_cubic(*bottom_right_control, t/steps)
        path_points.append(point)

    return path_points

def generate_s_bezier_path(center_x, center_y, width, height):
    """生成S形贝塞尔曲线路径"""
    path_points = []
    steps = 50

    p0 = (center_x - width//2, center_y - height//2)
    p1 = (center_x - width//4, center_y - height//2)
    p2 = (center_x + width//4, center_y + height//2)
    p3 = (center_x + width//2, center_y + height//2)

    for t in range(steps + 1):
        point = bezier_cubic(p0, p1, p2, p3, t/steps)
        path_points.append(point)

    return path_points

def generate_sine_bezier_path(center_x, center_y, width, height, cycles=2):
    """生成正弦曲线的贝塞尔曲线路径"""
    path_points = []

    # 正弦曲线参数
    amplitude = height // 3  # 振幅
    wavelength = width / cycles  # 波长

    # 将正弦曲线分成多个贝塞尔曲线段
    segments = cycles * 4  # 每周期4个贝塞尔段
    steps_per_segment = 20

    for segment in range(segments):
        # 计算当前段的起点和终点角度
        start_angle = segment * math.pi / 2
        end_angle = (segment + 1) * math.pi / 2

        # 计算贝塞尔曲线的控制点
        x0 = center_x - width//2 + segment * width//segments
        y0 = center_y - amplitude * math.sin(start_angle)

        x3 = center_x - width//2 + (segment + 1) * width//segments
        y3 = center_y - amplitude * math.sin(end_angle)

        # 计算控制点（使用正弦曲线的导数）
        dx = width / segments
        dy = amplitude * math.cos(start_angle)

        x1 = x0 + dx/3
        y1 = y0 - dy/3

        x2 = x3 - dx/3
        y2 = y3 + amplitude * math.cos(end_angle)/3

        # 生成这一段的贝塞尔曲线点
        for step in range(steps_per_segment + 1):
            t = step / steps_per_segment
            point = bezier_cubic((int(x0), int(y0)), (int(x1), int(y1)),
                               (int(x2), int(y2)), (int(x3), int(y3)), t)
            path_points.append(point)

    return path_points

try:
    sensor = Sensor(id=sensor_id)
    sensor.reset()
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

    clock = time.clock()

    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        img_gray = img.to_grayscale(copy=True)
        img_rect = img_gray.binary(rect_binart)

        if not rect_detected:
            # 矩形识别阶段
            rects = img_rect.find_rects(threshold=5000)
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

                img.draw_cross(center_x, center_y, color=(255, 255, 255))
                rect_corners = corners
                rect_center = (center_x, center_y)
                send_rect_data(rect_corners, rect_center)

                # 生成贝塞尔曲线路径
                rect_width = abs(corners[1][0] - corners[0][0])
                rect_height = abs(corners[3][1] - corners[0][1])
                curve_size = min(rect_width, rect_height) // 2

                if curve_size > 30:
                    # 选择绘制心形或正弦曲线
                    # 可以通过修改curve_type变量切换："heart" 或 "sine"

                    if curve_type == "heart":
                        bezier_path = generate_heart_bezier_path(center_x, center_y, curve_size)
                        print("开始心形贝塞尔曲线追踪")
                    else:
                        # 绘制正弦曲线，使用2个周期
                        bezier_path = generate_sine_bezier_path(center_x, center_y,
                                                             rect_width * 0.8, rect_height * 0.8, cycles=2)
                        print("开始正弦曲线追踪")

                    rect_detected = True
                    current_target_index = 0
                    tracking_started = False
                    print(f"矩形识别完成，贝塞尔曲线路径点数量: {len(bezier_path)}")

        else:
            # 激光追踪阶段
            laser_pos = find_laser_point(img)

            if laser_pos:
                laser_x, laser_y = laser_pos

                if not tracking_started:
                    current_target_index = 0
                    tracking_started = True

                if current_target_index < len(bezier_path):
                    target_x, target_y = bezier_path[current_target_index]

                    # 绘制激光点
                    img.draw_circle(laser_x, laser_y, 5, color=(255, 255, 0), thickness=2)
                    img.draw_circle(target_x, target_y, 8, color=(0, 255, 0), thickness=2)
                    img.draw_cross(target_x, target_y, color=(0, 255, 0))
                    img.draw_line(laser_x, laser_y, target_x, target_y, color=(255, 255, 255), thickness=1)

                    # 绘制整个贝塞尔曲线
                    if len(bezier_path) > 1:
                        for i in range(1, len(bezier_path)):
                            img.draw_line(bezier_path[i-1][0], bezier_path[i-1][1],
                                        bezier_path[i][0], bezier_path[i][1],
                                        color=(100, 100, 255), thickness=1)

                    send_tracking_data(laser_x, laser_y, target_x, target_y)

                    # 检查是否到达目标点
                    dist = distance(laser_pos, (target_x, target_y))
                    if dist < 10:
                        current_target_index += 1
                        if current_target_index >= len(bezier_path):
                            print("贝塞尔曲线追踪完成！")
                            rect_detected = False
                            tracking_started = False
                            current_target_index = 0
                else:
                    curve_name = "正弦" if curve_type == "sine" else "心形"
                    img.draw_string_advanced(DISPLAY_WIDTH//2-100, DISPLAY_HEIGHT//2, 24,
                                           f"{curve_name}曲线追踪完成！", color=(0, 255, 255))
            else:
                img.draw_string_advanced(10, 10, 16, "等待激光点...", color=(255, 0, 0))

        img.draw_string_advanced(192, 40, 20, "FPS: {}".format(clock.fps()), color=(255, 0, 0))
        Display.show_image(img)

except KeyboardInterrupt as e:
    print("用户停止: ", e)
except BaseException as e:
    print(f"异常: {e}")
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()

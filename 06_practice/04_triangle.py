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
DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480 # 显示屏分辨率
picture_width, picture_height = 800, 480 # 摄像头图像分辨率


# --- 视觉识别配置 ---
RED_THRESHOLD = [(85, 100, -18, 50, -18, 51), (69, 100, -12, 58, -20, 20), (83, 100, -9, 13, -6, 22)]   # 红色目标颜色阈值 (L*, a*, b* 范围)
rect_binary_threshold = [(82, 212)]             # 矩形检测二值化阈值 (灰度值范围)
rect_area_threshold = 20000                     # 矩形最小面积阈值，用于过滤小噪声
blob_area_threshold = 5                         # 颜色块最小面积阈值，用于过滤小噪声

# --- 三角形识别参数 ---
min_line_length = 30         # 线段最小长度阈值
triangle_tolerance = 5       # 三角形判定容差

# --- 全局参数定义 ---
state = 0     #识别状态
triangle_detection_done = False  # 三角形识别完成标志
triangle_detection_time = 0      # 三角形识别完成时间
all_target_points = None         # 所有目标路径点
rect_detection_done = False      # 矩形识别完成标志
rect_detection_time = 0          # 矩形识别完成时间


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

# --- 三角形追踪处理函数 ---
def process_triangle_tracking(img):
    """
    完整的三角形识别和激光追踪处理函数
    整合了三角形检测、路径点生成、倒计时显示和激光追踪功能
    """
    global triangle_detection_done, triangle_detection_time, all_target_points
    
    # 使用整合的三角形识别函数
    if not triangle_detection_done:
        success, triangle, path_points, lines = detect_triangle_and_generate_path(
            img, min_line_length, triangle_tolerance, 10, draw=True)
        
        if success:
            all_target_points = path_points
            triangle_detection_done = True
            triangle_detection_time = time.ticks_ms()
            print("三角形识别完成！3秒后进入激光追踪")
        else:
            print("未检测到三角形")
    
    elif triangle_detection_done:
        # 优化的绘制逻辑
        elapsed_time = time.ticks_ms() - triangle_detection_time
        
        # 只在倒计时期间绘制完整信息
        if elapsed_time < 3000:
            remaining_time = 3 - (elapsed_time // 1000)
            
            # 简化路径点显示
            for i, point in enumerate(all_target_points[::4]):  # 间隔绘制
                img.draw_circle(point[0], point[1], 1, color=(255, 255, 0), thickness=2)
            
            img.draw_string_advanced(DISPLAY_WIDTH//2 - 100, DISPLAY_HEIGHT//2 + 50, 35,
                                   f"倒计时: {remaining_time}", color=(255, 255, 0))
        
        elif elapsed_time >= 3000:
            # 激光追踪阶段
            red_blobs = img.find_blobs(RED_THRESHOLD, pixels_threshold=blob_area_threshold)
            
            if red_blobs:
                laser_blob = max(red_blobs, key=lambda x: x.pixels())
                laser_x, laser_y = laser_blob.cx(), laser_blob.cy()
                
                # 使用欧氏距离计算最近点
                min_dist = float('inf')
                target_point = all_target_points[0]
                for point in all_target_points:
                    dist = math.sqrt((laser_x - point[0])**2 + (laser_y - point[1])**2)  # 欧氏距离
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
        img.draw_string_advanced(10, 50, 20, "未检测到三角形", color=(255, 255, 0))


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
        while KEY.value() == 1:
            time.sleep_ms(50)

    return state


# --- 三角形识别相关函数 ---
def distance(p1, p2):
    """计算两点间距离"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def is_triangle(p1, p2, p3, tolerance=5):
    """判断三点是否能构成三角形"""
    # 计算三边长度
    a = distance(p1, p2)
    b = distance(p2, p3)
    c = distance(p3, p1)
    
    # 检查是否三点重合
    if a < tolerance and b < tolerance and c < tolerance:
        return False
    
    # 检查是否三点共线（三角形定理）
    # 任意两边之和大于第三边
    if (a + b > c + tolerance) and (a + c > b + tolerance) and (b + c > a + tolerance):
        return True
    return False


def find_triangles(lines, min_length=30, tolerance=5):
    """从线段中查找三角形"""
    triangles = []
    
    # 过滤掉过短的线段
    valid_lines = [line for line in lines if distance((line.x1(), line.y1()), (line.x2(), line.y2())) >= min_length]
    
    # 遍历线段组合查找三角形
    for i in range(len(valid_lines)):
        for j in range(i + 1, len(valid_lines)):
            for k in range(j + 1, len(valid_lines)):
                line1 = valid_lines[i]
                line2 = valid_lines[j]
                line3 = valid_lines[k]
                
                # 获取线段端点
                p1 = (line1.x1(), line1.y1())
                p2 = (line1.x2(), line1.y2())
                p3 = (line2.x1(), line2.y1())
                p4 = (line2.x2(), line2.y2())
                p5 = (line3.x1(), line3.y1())
                p6 = (line3.x2(), line3.y2())
                
                # 检查是否有重合的点
                points = []
                for p in [p1, p2, p3, p4, p5, p6]:
                    is_new = True
                    for existing_point in points:
                        if distance(p, existing_point) < tolerance:
                            is_new = False
                            break
                    if is_new:
                        points.append(p)
                
                # 如果恰好有3个不重合的点，检查是否构成三角形
                if len(points) == 3:
                    if is_triangle(points[0], points[1], points[2], tolerance):
                        triangles.append(points)
    
    return triangles


def generate_triangle_path_points(triangle, interpolation_steps=10):
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


def detect_triangle_and_generate_path(img, min_length=30, tolerance=5, interpolation_steps=10, draw=True):
    """
    整合的三角形识别和路径生成函数
    
    参数:
    - img: 输入图像
    - min_length: 线段最小长度阈值
    - tolerance: 三角形判定容差
    - interpolation_steps: 路径点插值步数
    - draw: 是否绘制识别结果
    
    返回:
    - success: 是否成功识别三角形
    - triangle: 三角形顶点坐标列表
    - path_points: 路径点坐标列表
    - lines: 检测到的线段
    """
    # 查找线段（LSD算法）
    lines = img.find_line_segments(merge_distance=20, max_theta_diff=10)
    
    # 查找三角形
    triangles = find_triangles(lines, min_length, tolerance)
    
    if not triangles:
        if draw:
            img.draw_string_advanced(10, 50, 30, "未检测到三角形", color=(255, 255, 0))
        return False, None, None, lines
    
    # 获取第一个三角形
    triangle = triangles[0]
    
    if draw:
        # 绘制三角形的边
        for i in range(3):
            p1 = triangle[i]
            p2 = triangle[(i + 1) % 3]
            img.draw_line(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]), color=(255, 0, 0), thickness=2)
        
        # 显示顶点坐标
        for i, point in enumerate(triangle):
            x, y = int(point[0]), int(point[1])
            img.draw_circle(x, y, 5, color=(0, 255, 0), thickness=2, fill=True)
            img.draw_string_advanced(x + 5, y + 5, 20, f"({x},{y})", color=(0, 255, 0))
        
        # 显示三角形数量
        img.draw_string_advanced(10, 50, 30, f"三角形数量: {len(triangles)}", color=(255, 255, 0))
    
    # 生成路径点
    path_points = generate_triangle_path_points(triangle, interpolation_steps)
    
    # 打印三角形信息
    print("检测到三角形，顶点坐标:")
    for i, point in enumerate(triangle):
        print(f"  顶点{i+1}: ({int(point[0])}, {int(point[1])})")
    
    return True, triangle, path_points, lines




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
                    
                    # 重置三角形识别状态
                    triangle_detection_done = False
                    triangle_detection_time = 0

        # 根据当前状态执行不同任务
        if state == 0:  # 复位状态
            # 显示待机画面
            img.draw_string_advanced(10, 10, 30, "复位状态 - 等待开始", color=(0, 255, 0))

        elif state == 1:  # 运行状态
            # 执行图像识别任务
            process_triangle_tracking(img)

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

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
STATE_CURVE_DETECT = 4  # 曲线识别状态


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

# --- 曲线识别参数 ---
curve_binary_threshold = [(30, 255)]            # 降低阈值以检测更精细的曲线
curve_area_threshold = 100                       # 降低最小面积阈值
curve_edge_threshold = (20, 50)                  # 降低Canny边缘检测阈值
curve_smooth_kernel = 2                          # 减小高斯模糊核大小以减少细节丢失

# --- 全局参数定义 ---
state = 0     #识别状态
curve_points = []     # 存储检测到的曲线点
curve_detected = False     # 曲线检测完成标志
curve_detection_time = 0   # 曲线检测计时器
rect_detection_done = False  # 矩形检测完成标志
rect_detection_time = 0      # 矩形检测计时器
triangle_detection_done = False  # 三角形检测完成标志
triangle_detection_time = 0      # 三角形检测计时器



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
    """发送数据到串口"""
    try:
        # 验证输入参数
        if x is None or y is None:
            print(f"坐标值为空: x={x}, y={y}")
            x, y = 0, 0
        
        # 验证坐标类型和范围
        if not isinstance(x, int) or not isinstance(y, int):
            print(f"坐标类型错误: x={x} ({type(x)}), y={y} ({type(y)})")
            x, y = 0, 0  # 使用默认值
        elif not (0 <= x <= 65535) or not (0 <= y <= 65535):
            print(f"坐标超出范围: x={x}, y={y}")
            x, y = 0, 0  # 使用默认值
        
        # 构造数据包
        data_packet = struct.pack('<BHH', 1, x, y)  # 1表示坐标数据
        
        # 验证数据包
        if not isinstance(data_packet, bytes):
            print("数据包构造失败")
            return
        
        # 发送帧头、数据包和帧尾
        uart2.write(bytes([0xAA]))  # 帧头
        uart2.write(data_packet)    # 数据
        uart2.write(bytes([0x55]))  # 帧尾
        
    except Exception as e:
        print(f"串口发送错误: {e}")
        # 发送错误指示
        try:
            error_packet = struct.pack('<BHH', 0xFF, 0, 0)  # 错误指示
            uart2.write(bytes([0xAA]))
            uart2.write(error_packet)
            uart2.write(bytes([0x55]))
        except Exception as inner_e:
            print(f"发送错误指示失败: {inner_e}")

# --- 状态管理函数 ---
def display_state_info(state_code, duration=2):
    state_definitions = [
        (0, "复位状态", "系统初始化完成", (0, 255, 0)),
        (1, "运行状态", "正在执行识别任务", (0, 255, 255)),
        (2, "暂停状态", "等待用户操作", (255, 255, 0)),
        (3, "错误状态", "检测到异常情况", (255, 0, 0)),
        (4, "曲线识别", "正在识别曲线特征", (255, 128, 0))
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

# --- 曲线识别函数 ---
def preprocess_for_curve(img):
    """图像预处理：灰度化、去噪、边缘增强"""
    try:
        # 验证输入图像
        if img is None:
            print("输入图像为空")
            return None
        
        # 转换为灰度图
        gray_img = img.to_grayscale()
        
        # 验证灰度图像
        if gray_img is None:
            print("灰度图像转换失败")
            return None
        
        # 高斯模糊去噪
        gray_img.gaussian(curve_smooth_kernel)
        
        # Canny边缘检测
        edge_img = gray_img.copy()
        edge_img.find_edges(image.EDGE_CANNY, threshold=curve_edge_threshold)
        
        # 验证边缘图像
        if edge_img is None:
            print("边缘检测失败")
            return None
        
        return edge_img
    except Exception as e:
        print(f"图像预处理出错: {e}")
        return None

def extract_curve_points(edge_img):
    """提取曲线上的关键点"""
    points = []
    
    try:
        # 验证输入图像
        if edge_img is None:
            print("输入边缘图像为空")
            return []
        
        # 查找图像中的连通区域（blob）
        blobs = edge_img.find_blobs([
            # 黑色到深灰色范围
            (0, curve_binary_threshold[0][1], -128, 127, -128, 127)
        ], area_threshold=curve_area_threshold)
        
        # 验证blobs数据类型
        if not isinstance(blobs, list):
            print("blob检测结果数据类型错误")
            return []
        
        # 遍历每个blob
        for blob in blobs:
            # 验证blob数据类型
            if not hasattr(blob, 'y') or not hasattr(blob, 'h') or not hasattr(blob, 'x') or not hasattr(blob, 'w'):
                continue
            
            # 在blob区域内进行垂直扫描，寻找边缘点
            for y in range(blob.y(), blob.y() + blob.h(), 2):  # 每隔2个像素扫描一行
                row_points = []
                for x in range(blob.x(), blob.x() + blob.w()):
                    # 检查坐标是否在有效范围内
                    if 0 <= x < DISPLAY_WIDTH and 0 <= y < DISPLAY_HEIGHT:
                        # 检查是否为边缘点（非零像素）
                        if edge_img.get_pixel(x, y) > 0:
                            row_points.append((x, y))
                
                # 如果该行有边缘点，选择中间的点作为代表
                if row_points:
                    # 验证row_points中的点
                    valid_row_points = []
                    for p in row_points:
                        if isinstance(p, (tuple, list)) and len(p) >= 2:
                            x, y = p[0], p[1]
                            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                                valid_row_points.append((int(x), int(y)))
                    
                    if valid_row_points:
                        mid_point = valid_row_points[len(valid_row_points) // 2]
                        points.append(mid_point)
        
        # 对点进行平滑处理
        if len(points) > 3:
            # 验证points数据类型
            valid_points = []
            for p in points:
                if isinstance(p, (tuple, list)) and len(p) >= 2:
                    x, y = p[0], p[1]
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                        valid_points.append((x, y))
            
            if len(valid_points) > 3:
                # 简单的移动平均平滑
                smoothed_points = []
                window_size = 3
                for i in range(len(valid_points)):
                    if i < window_size // 2 or i >= len(valid_points) - window_size // 2:
                        smoothed_points.append(valid_points[i])
                    else:
                        # 计算窗口内的平均值
                        x_avg = sum(p[0] for p in valid_points[i-window_size//2:i+window_size//2+1]) / window_size
                        y_avg = sum(p[1] for p in valid_points[i-window_size//2:i+window_size//2+1]) / window_size
                        smoothed_points.append((int(x_avg), int(y_avg)))
                points = smoothed_points
        
        # 按y坐标排序
        # 先验证所有点的数据类型
        valid_sorted_points = []
        for p in points:
            if isinstance(p, (tuple, list)) and len(p) >= 2:
                x, y = p[0], p[1]
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    valid_sorted_points.append((int(x), int(y)))
        
        # 按y坐标排序
        valid_sorted_points.sort(key=lambda p: p[1])
        points = valid_sorted_points
        
    except Exception as e:
        print(f"提取曲线点时出错: {e}")
        points = []  # 出错时返回空列表以避免崩溃
    
    return points

def fit_curve(points):
    """曲线拟合：使用最小二乘法拟合二次曲线"""
    try:
        if len(points) < 3:
            return None
        
        # 按x坐标排序
        points.sort(key=lambda p: p[0])
        
        # 提取x, y坐标
        x_coords = []
        y_coords = []
        for p in points:
            if isinstance(p, tuple) and len(p) >= 2:
                x_coords.append(p[0])
                y_coords.append(p[1])
            elif isinstance(p, list) and len(p) >= 2:
                x_coords.append(p[0])
                y_coords.append(p[1])
        
        if len(x_coords) < 3:
            return None
        
        # 验证坐标数据类型
        if not all(isinstance(x, (int, float)) for x in x_coords) or not all(isinstance(y, (int, float)) for y in y_coords):
            print("坐标数据类型错误")
            return None
        
        # 计算二次曲线系数 y = ax² + bx + c
        n = len(points)
        sum_x = sum(x_coords)
        sum_x2 = sum(x * x for x in x_coords)
        sum_x3 = sum(x * x * x for x in x_coords)
        sum_x4 = sum(x * x * x * x for x in x_coords)
        sum_y = sum(y_coords)
        sum_xy = sum(x * y for x, y in zip(x_coords, y_coords))
        sum_x2y = sum(x * x * y for x, y in zip(x_coords, y_coords))
        
        # 解线性方程组
        denominator = n * sum_x2 * sum_x4 + sum_x * sum_x3 * sum_x2 + sum_x2 * sum_x * sum_x3 - sum_x2 * sum_x2 * sum_x2 - sum_x * sum_x * sum_x4 - n * sum_x3 * sum_x3
        
        if abs(denominator) < 1e-6:
            return None
        
        # 计算系数
        a = (n * sum_x2 * sum_x2y + sum_x * sum_x3 * sum_y + sum_x2 * sum_xy * sum_x - sum_x2 * sum_x2 * sum_y - sum_x * sum_x * sum_x2y - n * sum_x3 * sum_xy) / denominator
        b = (n * sum_xy * sum_x4 + sum_x * sum_x2y * sum_x2 + sum_x2 * sum_x * sum_x2y - sum_x2 * sum_xy * sum_x2 - sum_x * sum_x * sum_x4 - n * sum_x2y * sum_x3) / denominator
        c = (sum_x2 * sum_x2 * sum_y + sum_x * sum_x3 * sum_xy + sum_x * sum_x2 * sum_x2y - sum_x2 * sum_x2 * sum_xy - sum_x * sum_x * sum_x2y - sum_x3 * sum_x * sum_y) / denominator
        
        return (a, b, c)
    except Exception as e:
        print(f"曲线拟合时出错: {e}")
        return None

def detect_curve_lines(img):
    """使用线段检测识别曲线"""
    try:
        # 转换为灰度图
        gray_img = img.to_grayscale()
        
        # 线段检测 - 使用正确的MaixPy API
        lines = gray_img.find_lines(threshold=1000, theta_margin=25, rho_margin=25)
        
        curve_segments = []
        for line in lines:
            # 过滤短线段
            if line.length() > 20:
                # 计算线段角度
                angle = line.theta()
                # 只保留特定角度的线段作为曲线部分
                if 10 < angle < 170:  # 排除水平线段
                    # 将线段转换为点列表
                    points = [(line.x1(), line.y1()), (line.x2(), line.y2())]
                    curve_segments.append(points)
        
        return curve_segments
    except Exception as e:
        print(f"检测曲线线段时出错: {e}")
        return []

def draw_curve_info(img, points, curve_params=None, contours=None):
    """绘制曲线信息和拟合结果"""
    try:
        # 绘制连续曲线轮廓
        if contours:
            for contour in contours:
                if isinstance(contour, list) and len(contour) > 1:
                    for i in range(len(contour)-1):
                        # 增强类型检查
                        if (isinstance(contour[i], (tuple, list)) and len(contour[i]) >= 2 and 
                            isinstance(contour[i+1], (tuple, list)) and len(contour[i+1]) >= 2):
                            x1, y1 = contour[i][0], contour[i][1]
                            x2, y2 = contour[i+1][0], contour[i+1][1]
                            # 确保坐标是整数
                            if all(isinstance(coord, (int, float)) for coord in [x1, y1, x2, y2]):
                                img.draw_line(int(x1), int(y1), int(x2), int(y2), 
                                             color=(0, 255, 0), thickness=2)
        
        # 绘制检测到的点
        for point in points:
            if isinstance(point, (tuple, list)) and len(point) >= 2:
                x, y = point[0], point[1]
                # 确保坐标是整数
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    img.draw_circle(int(x), int(y), 2, color=(255, 0, 0), thickness=1)
        
        # 绘制拟合曲线
        if curve_params and len(points) > 5:
            # 验证参数类型
            if not isinstance(curve_params, (tuple, list)) or len(curve_params) < 3:
                print("曲线参数无效")
                return img
            
            a, b, c = curve_params
            # 验证参数数据类型
            if not all(isinstance(param, (int, float)) for param in [a, b, c]):
                print("曲线参数数据类型错误")
                return img
            
            # 验证点数据类型
            valid_points = []
            for p in points:
                if isinstance(p, (tuple, list)) and len(p) >= 2:
                    x, y = p[0], p[1]
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                        valid_points.append((x, y))
            
            if len(valid_points) > 0:
                # 绘制平滑的拟合曲线
                curve_points = []
                for x in range(0, DISPLAY_WIDTH, 2):
                    y = int(a * x * x + b * x + c)
                    if 0 <= y < DISPLAY_HEIGHT:
                        curve_points.append((x, y))
                
                # 绘制平滑曲线
                if len(curve_points) > 1:
                    for i in range(len(curve_points)-1):
                        x1, y1 = curve_points[i][0], curve_points[i][1]
                        x2, y2 = curve_points[i+1][0], curve_points[i+1][1]
                        # 确保坐标是整数
                        if all(isinstance(coord, (int, float)) for coord in [x1, y1, x2, y2]):
                            img.draw_line(int(x1), int(y1), int(x2), int(y2),
                                         color=(255, 255, 0), thickness=2)
        
        # 显示曲线信息
        total_points = len(points)
        if contours:
            total_points += sum(len(c) if isinstance(c, list) else 1 for c in contours)
        img.draw_string_advanced(10, 50, 20, f"曲线总点数: {total_points}", color=(255, 255, 0))
        if curve_params and len(points) > 5:
            img.draw_string_advanced(10, 80, 20, f"拟合: y={curve_params[0]:.4f}x²+{curve_params[1]:.2f}x+{curve_params[2]:.1f}", color=(255, 255, 0))
        
        return img
    except Exception as e:
        print(f"绘制曲线信息时出错: {e}")
        return img

def curve_detection_task(img):
    """完整的曲线识别任务"""
    global curve_detected, curve_points, curve_detection_time
    
    try:
        # 验证输入图像
        if img is None:
            print("输入图像为空")
            return [], None, []
        
        # 图像预处理
        edge_img = preprocess_for_curve(img)
        
        # 提取连续曲线点
        points = extract_curve_points(edge_img)
        
        # 验证points数据类型
        if not isinstance(points, list):
            print("曲线点数据类型错误")
            points = []
        
        # 过滤有效的点
        valid_points = []
        for point in points:
            if isinstance(point, (tuple, list)) and len(point) >= 2:
                x, y = point[0], point[1]
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    valid_points.append((int(x), int(y)))
        
        points = valid_points
        
        # 检测连续曲线轮廓
        contours = detect_curve_lines(img)
        
        # 验证contours数据类型
        if not isinstance(contours, list):
            print("轮廓数据类型错误")
            contours = []
        
        # 合并所有点进行曲线拟合
        all_points = points.copy()
        if contours:
            for contour in contours:
                # 增强类型检查
                if isinstance(contour, list) and len(contour) > 0:
                    # 过滤有效的点
                    valid_points = [p for p in contour if isinstance(p, (tuple, list)) and len(p) >= 2]
                    all_points.extend(valid_points)
        
        # 曲线拟合
        curve_params = None
        if len(all_points) >= 5:  # 至少需要5个点才能拟合二次曲线
            curve_params = fit_curve(all_points)
        
        # 更新检测结果
        curve_points = all_points
        curve_detected = len(all_points) > 0
        
        # 返回关键点用于串口发送
        key_points = []
        if len(all_points) >= 3:
            # 选择起始点、中间点和结束点
            key_points.append(all_points[0])  # 起始点
            key_points.append(all_points[len(all_points)//2])  # 中间点
            key_points.append(all_points[-1])  # 结束点
        
        return key_points, curve_params, contours
    
    except Exception as e:
        print(f"曲线检测任务出错: {e}")
        return [], None, []



def handle_key_state_switch():
    global state, rect_detection_done, rect_detection_time, triangle_detection_done, triangle_detection_time, curve_detected, curve_detection_time

    # 检测按键状态（GPIO53）
    if KEY.value() == 1:  # 按键按下
        state = (state + 1) % 5  # 循环切换状态 0-4
        print(f"按键触发，状态切换到: {state}")
        display_state_info(state, 1)  # 显示1秒

        # 重置矩形识别状态
        rect_detection_done = False
        rect_detection_time = 0
        
        # 重置三角形识别状态
        triangle_detection_done = False
        triangle_detection_time = 0

        # 重置曲线识别状态
        curve_detected = False
        curve_detection_time = 0

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
            if (Rxbuf[0] == 0xAA and Rxbuf[4] == 0x55):  # 检查帧头和帧尾
                new_state = Rxbuf[1]
                if 0 <= new_state <= 4 and new_state != state:
                    state = new_state
                    print(f"串口触发，状态切换到: {state}")
                    display_state_info(state, 1)
                    
                    # 重置矩形识别状态
                    rect_detection_done = False
                    rect_detection_time = 0
                    
                    # 重置三角形识别状态
                    triangle_detection_done = False
                    triangle_detection_time = 0
                    
                    # 重置曲线识别状态
                    curve_detected = False
                    curve_detection_time = 0

        # 根据当前状态执行不同任务
        if state == 0:  # 复位状态
            # 显示待机画面
            img.draw_string_advanced(10, 10, 30, "复位状态 - 等待开始", color=(0, 255, 0))

        elif state == 1:  # 运行状态
            # 执行图像识别任务
            img.draw_string_advanced(10, 10, 30, "运行状态 - 基础识别", color=(0, 255, 255))

        elif state == 2:  # 暂停状态
            # 暂停识别，显示暂停信息
            img.draw_string_advanced(10, 10, 30, "暂停状态 - 按任意键继续", color=(255, 255, 0))

        elif state == 3:  # 错误状态
            # 显示错误信息
            img.draw_string_advanced(10, 10, 30, "错误状态 - 请检查系统", color=(255, 0, 0))

        elif state == 4:  # 曲线识别状态
            # 执行曲线识别任务
            curve_detection_time += 1
            
            # 执行曲线检测
            points, curve_params, contours = curve_detection_task(img)
            
            # 绘制检测结果
            draw_curve_info(img, points, curve_params, contours)
            
            # 显示状态信息
            img.draw_string_advanced(10, 10, 30, f"曲线识别 - 第{curve_detection_time}帧", color=(255, 128, 0))
            
            # 发送检测结果到串口 - 发送曲线关键点
            if points and len(points) > 5:
                # 发送曲线的起始点、中点和结束点
                start_point = points[0]
                if isinstance(start_point, tuple) and len(start_point) >= 2:
                    start_x, start_y = start_point[0], start_point[1]
                else:
                    start_x, start_y = 0, 0
                
                mid_idx = len(points) // 2
                mid_point = points[mid_idx]
                if isinstance(mid_point, tuple) and len(mid_point) >= 2:
                    mid_x, mid_y = mid_point[0], mid_point[1]
                else:
                    mid_x, mid_y = 0, 0
                
                end_point = points[-1]
                if isinstance(end_point, tuple) and len(end_point) >= 2:
                    end_x, end_y = end_point[0], end_point[1]
                else:
                    end_x, end_y = 0, 0
                
                # 增强类型检查和数据验证
                coords = [start_x, start_y, mid_x, mid_y, end_x, end_y]
                if all(isinstance(coord, (int, float)) and 0 <= int(coord) <= 65535 for coord in coords):
                    # 发送起始点
                    send_data(int(start_x), int(start_y))
                    time.sleep_ms(10)
                    # 发送中点
                    send_data(int(mid_x), int(mid_y))
                    time.sleep_ms(10)
                    # 发送结束点
                    send_data(int(end_x), int(end_y))
                else:
                    print(f"坐标值超出范围: {coords}")
                    send_data(0, 0)
            else:
                # 无检测结果，发送特殊值
                send_data(0, 0)

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

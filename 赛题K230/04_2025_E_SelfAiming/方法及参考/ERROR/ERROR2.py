# ========================= 库导入 =========================
import gc
import os
import sys
import time
import math
import image
import struct
import cv_lite               # cv_lite 扩展模块
import ulab.numpy as np      # 轻量 NumPy（用于 ndarray 图像处理）

from media.sensor import * #导入sensor模块，使用摄像头相关接口
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
state = 0     #识别状态
STATE_RESET = 0      # 复位状态
STATE_CALIBRATE = 1  # 标定状态
STATE_AIM = 2        # 瞄准状态
STATE_SCORE = 3      # 计分状态

# --- 摄像头与显示配置 ---
sensor_id = 2
sensor = None
DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480 # 显示屏分辨率
picture_width, picture_height = 800, 480 # 摄像头图像分辨率

# --- 靶标配置 ---
target_center = None  # 靶心坐标
target_radii = [10, 20, 30, 40, 50]  # 5个圆环半径（像素）

# --- 视觉识别配置 ---
RED_THRESHOLD = [(85, 100, -18, 50, -18, 51), (69, 100, -12, 58, -20, 20), (83, 100, -9, 13, -6, 22)]   # 红色目标颜色阈值 (L*, a*, b* 范围)
rect_binary_threshold = [(82, 212)]             # 矩形检测二值化阈值 (灰度值范围)
rect_area_threshold = 20000                     # 矩形最小面积阈值，用于过滤小噪声
blob_area_threshold = 5                         # 颜色块最小面积阈值，用于过滤小噪声

# --- 全局参数定义 ---
rect_detection_done = False  # 矩形识别完成标志
rect_detection_time = 0      # 矩形识别完成时间
outer_corners = []           # 外框矩形角点
inner_corners = []           # 内框矩形角点
target_corners = []          # 目标矩形角点（外框和内框的中点）
all_target_points = []       # 目标矩形边缘的所有插值点
current_target_index = 0     # 当前追踪的目标点索引
laser_detected = False     # 激光点检测标志
laser_x = 0                # 激光点X坐标
laser_y = 0                # 激光点Y坐标

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
def send_data(laser_x, laser_y, target_x=None, target_y=None):
    global all_target_points, current_target_index
    
    # 如果未提供目标点，使用当前追踪的目标点
    if target_x is None or target_y is None:
        if all_target_points and current_target_index < len(all_target_points):
            target_x, target_y = all_target_points[current_target_index]
        else:
            target_x, target_y = 0, 0
    
    # 构建数据帧：帧头+命令字+激光坐标+目标坐标+帧尾
    frame = b'\xAA' + struct.pack('<BHHHH', 1, int(laser_x), int(laser_y), int(target_x), int(target_y)) + b'\x55'
    
    try:
        uart2.write(frame)
        uart2.flush()  # 等待发送完成
        print(f"[SEND_TRACK] 发送追踪数据:")
        print(f"[SEND_TRACK] 激光点: ({laser_x}, {laser_y})")
        print(f"[SEND_TRACK] 目标点: ({target_x}, {target_y})")
        print(f"[SEND_TRACK] 数据帧: {frame.hex().upper()}")
    except Exception as e:
        print(f"[SEND_TRACK] 串口发送失败: {e}")
    
    return frame


# --- 状态管理函数 ---
def display_state_info(state_code, duration=2):
    """
    显示当前状态信息
    状态码对应：
    0 - 复位状态
    1 - 标定状态（靶标识别）
    2 - 瞄准状态（激光追踪）
    3 - 计分状态
    """
    state_definitions = [
        (0, "复位状态", "系统初始化完成", (0, 255, 0)),
        (1, "标定状态", "正在识别靶标", (0, 255, 255)),
        (2, "瞄准状态", "激光追踪中", (255, 255, 0)),
        (3, "计分状态", "计算得分中", (255, 0, 255))
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
                                   f"数字码: {state_code}", color=(200, 200, 200))
    status_img.draw_string_advanced(DISPLAY_WIDTH//2 - 100, DISPLAY_HEIGHT//2 + 80, 25,
                                   f"时间: {time.ticks_ms()//1000}s", color=(150, 150, 150))

    Display.show_image(status_img)
    time.sleep(duration)



# --- 状态处理函数 ---
def handle_reset_state(img):
    """处理复位状态 - 重置所有参数"""
    global rect_detection_done, rect_detection_time, current_target_index, laser_detected, laser_x, laser_y
    
    # 重置矩形识别相关变量
    rect_detection_done = False
    rect_detection_time = 0
    
    # 重置激光追踪相关变量
    current_target_index = 0
    laser_detected = False
    laser_x = 0
    laser_y = 0
    
    img.draw_string_advanced(10, 10, 30, "复位状态 - 等待开始", color=(0, 255, 255))
    img.draw_string_advanced(10, 50, 25, "按按键开始矩形识别", color=(255, 255, 0))
    
    return STATE_RESET

def handle_calibrate_state(img):
    """处理标定状态 - 矩形识别和路径生成"""
    global rect_detection_done, rect_detection_time, outer_corners, inner_corners, target_corners, all_target_points
    
    img.draw_string_advanced(10, 10, 30, "标定状态 - 矩形识别", color=(0, 255, 255))
    
    if rect_detection_done:
        # 矩形识别已完成，显示倒计时
        elapsed = time.ticks_ms() - rect_detection_time
        countdown = max(0, 3 - elapsed // 1000)
        
        if countdown > 0:
            img.draw_string_advanced(DISPLAY_WIDTH//2 - 100, DISPLAY_HEIGHT//2, 40, 
                                   f"识别完成！{countdown}秒后进入激光追踪", color=(0, 255, 0))
            
        # 绘制已识别的矩形
        if outer_corners:
            for i in range(4):
                next_i = (i + 1) % 4
                img.draw_line(outer_corners[i][0], outer_corners[i][1],
                            outer_corners[next_i][0], outer_corners[next_i][1],
                            color=(255, 0, 0), thickness=2)
        
        if inner_corners:
            for i in range(4):
                next_i = (i + 1) % 4
                img.draw_line(inner_corners[i][0], inner_corners[i][1],
                            inner_corners[next_i][0], inner_corners[next_i][1],
                            color=(0, 255, 0), thickness=2)
        
        # if all_target_points:
        #     # 绘制目标路径点
        #     for point in all_target_points[::5]:  # 每5个点显示一个
        #         img.draw_circle(point[0], point[1], 2, color=(255, 255, 0), thickness=1)
        
        return STATE_CALIBRATE
    
    # 执行矩形识别
    outer_corners = []
    inner_corners = []
    target_corners = []
    all_target_points = []
    
    # 红色过滤
    red_mask = img.copy()
    # 确保图像转换为RGB565格式，然后再转换为LAB颜色空间
    if hasattr(red_mask, 'to_rgb565'):
        red_mask = red_mask.to_rgb565()
    if hasattr(red_mask, 'to_lab'):
        red_mask = red_mask.to_lab()
    red_mask = red_mask.binary(RED_THRESHOLD)
    
    # 查找矩形
    rects = red_mask.find_rects(threshold=rect_binary_threshold[0][0])
    
    if rects:
        # 按面积排序，找出最大的两个矩形
        valid_rects = []
        for rect in rects:
            if rect.area() > rect_area_threshold:
                valid_rects.append(rect)
        
        valid_rects.sort(key=lambda r: r.area(), reverse=True)
        
        if len(valid_rects) >= 2:
            # 识别外框和内框
            outer_rect = valid_rects[0]
            inner_rect = valid_rects[1]
            
            # 获取角点并排序
            outer_corners = sort_corners_clockwise(outer_rect.corners())
            inner_corners = sort_corners_clockwise(inner_rect.corners())
            
            # 计算外框中心点
            outer_center_x = sum(p[0] for p in outer_corners) // 4
            outer_center_y = sum(p[1] for p in outer_corners) // 4
            
            # 计算内框中心点
            inner_center_x = sum(p[0] for p in inner_corners) // 4
            inner_center_y = sum(p[1] for p in inner_corners) // 4
            
            # 使用外框和内框中心点的中点作为目标点
            target_x = (outer_center_x + inner_center_x) // 2
            target_y = (outer_center_y + inner_center_y) // 2
            
            # 计算目标点（外框和内框的中心点）
            outer_center_x = sum(p[0] for p in outer_corners) / 4
            outer_center_y = sum(p[1] for p in outer_corners) / 4
            inner_center_x = sum(p[0] for p in inner_corners) / 4
            inner_center_y = sum(p[1] for p in inner_corners) / 4
            
            # 计算中心点的中点作为目标点
            target_x = int((outer_center_x + inner_center_x) / 2)
            target_y = int((outer_center_y + inner_center_y) / 2)
            
            # 生成目标路径点（仅包含中心点）
            all_target_points = [(target_x, target_y)]
            
            # 保存目标角点（用于显示）
            target_corners = outer_corners
            
            # 设置矩形识别完成标志
            rect_detection_done = True
            rect_detection_time = time.ticks_ms()
            print("矩形识别完成！3秒后进入激光追踪")
            
            # 绘制识别结果
            img.draw_string_advanced(10, 50, 25, "外框识别成功", color=(255, 0, 0))
            img.draw_string_advanced(10, 80, 25, "内框识别成功", color=(0, 255, 0))
            img.draw_string_advanced(10, 110, 25, f"路径点: {len(all_target_points)}", color=(255, 255, 0))
            
            # 绘制矩形
            for i in range(4):
                next_i = (i + 1) % 4
                img.draw_line(outer_corners[i][0], outer_corners[i][1],
                            outer_corners[next_i][0], outer_corners[next_i][1],
                            color=(255, 0, 0), thickness=2)
                img.draw_line(inner_corners[i][0], inner_corners[i][1],
                            inner_corners[next_i][0], inner_corners[next_i][1],
                            color=(0, 255, 0), thickness=2)
                img.draw_line(target_corners[i][0], target_corners[i][1],
                            target_corners[next_i][0], target_corners[next_i][1],
                            color=(255, 255, 0), thickness=1)
            
            return STATE_CALIBRATE
        else:
            img.draw_string_advanced(10, 50, 25, "未找到足够的矩形", color=(255, 0, 0))
    else:
        img.draw_string_advanced(10, 50, 25, "未检测到矩形", color=(255, 0, 0))
    
    img.draw_string_advanced(10, 80, 25, "请确保靶标在视野内", color=(255, 255, 255))
    return STATE_CALIBRATE

def handle_aim_state(img):
    """处理瞄准状态 - 激光定点追踪"""
    global current_target_index, laser_detected, laser_x, laser_y

    img.draw_string_advanced(10, 10, 30, "瞄准状态 - 激光追踪", color=(255, 255, 0))

    if not rect_detection_done or not all_target_points:
        img.draw_string_advanced(10, 50, 25, "请先完成矩形识别", color=(255, 0, 0))
        return STATE_AIM

    # 激光点检测（红色检测）
    red_blobs = img.find_blobs(RED_THRESHOLD, pixels_threshold=blob_area_threshold)

    laser_detected = False
    laser_x, laser_y = 0, 0

    if red_blobs:
        # 找到最大的红色区域作为激光点
        largest_blob = max(red_blobs, key=lambda b: b.pixels())

        # 计算激光点中心
        laser_x = largest_blob.cx()
        laser_y = largest_blob.cy()

        # 验证激光点大小
        if 5 <= largest_blob.w() <= 30 and 5 <= largest_blob.h() <= 30:
            laser_detected = True

        # 获取当前目标点（中心点）
        if all_target_points:
            target_x, target_y = all_target_points[0]
            
            # 计算激光点与目标点的距离
            distance = math.sqrt((laser_x - target_x)**2 + (laser_y - target_y)**2)
            
            # 显示距离信息
            img.draw_string_advanced(10, 50, 25, f"目标: 中心点", color=(0, 255, 255))
            img.draw_string_advanced(10, 80, 25, f"距离: {int(distance)}px", color=(255, 255, 0))
            
            # 检查是否到达目标点（距离小于阈值）
            if distance < 10:  # 距离阈值设为10像素
                current_target_index = 1  # 标记为中心点已完成
                print("目标中心点已完成")
                return STATE_SCORE  # 切换到计分状态
            else:
                current_target_index = 0  # 标记为中心点未完成
        else:
            # 如果没有目标点，显示默认信息
            img.draw_string_advanced(10, 50, 25, "未识别到目标点", color=(255, 0, 0))
            target_x, target_y = DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2  # 默认中心点

        # 绘制激光点
        img.draw_circle(laser_x, laser_y, 5, color=(255, 0, 0), thickness=2)
        img.draw_cross(laser_x, laser_y, color=(255, 255, 255), size=10, thickness=1)

        # 绘制目标点
        img.draw_circle(target_x, target_y, 8, color=(0, 255, 0), thickness=2)
        img.draw_cross(target_x, target_y, color=(0, 255, 255), size=15, thickness=1)

        # 绘制连接线
        img.draw_line(laser_x, laser_y, target_x, target_y, color=(255, 255, 0), thickness=1)
    else:
        img.draw_string_advanced(10, 50, 25, "激光点尺寸异常", color=(255, 0, 0))
        img.draw_string_advanced(10, 80, 25, "请确保激光照射在视野内", color=(255, 255, 255))

    return STATE_AIM

def handle_score_state(img):
    """处理计分状态 - 显示激光追踪结果"""
    global current_target_index, rect_detection_done, all_target_points, target_corners
    
    img.draw_string_advanced(10, 10, 30, "计分状态 - 任务完成", color=(0, 255, 255))
    
    if rect_detection_done and all_target_points:
        # 显示追踪结果
        img.draw_string_advanced(10, 50, 25, "目标: 矩形中心点", color=(0, 255, 255))
        
        # 检查是否完成
        if current_target_index >= 1:
            img.draw_string_advanced(10, 80, 25, "状态: 已完成", color=(0, 255, 0))
            img.draw_string_advanced(10, 110, 25, "完成度: 100%", color=(255, 255, 0))
        else:
            img.draw_string_advanced(10, 80, 25, "状态: 未完成", color=(255, 255, 0))
            img.draw_string_advanced(10, 110, 25, "完成度: 0%", color=(255, 255, 0))
        
        # 绘制目标矩形
        if target_corners:
            for i in range(4):
                next_i = (i + 1) % 4
                img.draw_line(target_corners[i][0], target_corners[i][1],
                            target_corners[next_i][0], target_corners[next_i][1],
                            color=(0, 255, 0), thickness=2)
        
        # 绘制中心点
        if all_target_points:
            point = all_target_points[0]
            img.draw_circle(point[0], point[1], 3, color=(0, 255, 0), thickness=2)
    else:
        img.draw_string_advanced(10, 50, 25, "未完成矩形识别", color=(255, 0, 0))
    
    img.draw_string_advanced(10, 150, 25, "按按键重新开始", color=(255, 255, 0))
    
    return STATE_SCORE

# --- 几何中心排序函数 ---
def sort_corners_clockwise(corners):
    """按顺时针方向排序角点"""
    # 计算中心点
    cx = sum(p[0] for p in corners) / 4
    cy = sum(p[1] for p in corners) / 4

    # 按角度排序（从右上角开始顺时针）
    def angle_from_center(p):
        x, y = p[0] - cx, p[1] - cy
        return (math.atan2(-y, x) + 2 * math.pi) % (2 * math.pi)

    return sorted(corners, key=angle_from_center)

# --- 其他功能函数 ---
def display_help_info():
    """显示帮助信息"""
    help_img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.RGB565)
    help_img.draw_rectangle(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, color=(30, 30, 30), thickness=2, fill=True)
    
    # 绘制标题
    help_img.draw_string_advanced(DISPLAY_WIDTH//2 - 80, 30, 40, "帮助信息", color=(0, 255, 255))
    
    # 绘制帮助内容
    help_text = [
        "按键控制说明：",
        "- 按键: 循环切换状态",
        "",
        "串口控制说明：",
        "- 发送格式: 55 XX FF FF FF",
        "- XX: 状态码(0-3)",
        "",
        "状态说明：",
        "- 0: 复位状态",
        "- 1: 标定状态",
        "- 2: 瞄准状态",
        "- 3: 计分状态"
    ]
    
    for i, text in enumerate(help_text):
        help_img.draw_string_advanced(30, 100 + i*30, 25, text, color=(255, 255, 255))
    
    # 绘制返回提示
    help_img.draw_string_advanced(DISPLAY_WIDTH//2 - 100, DISPLAY_HEIGHT - 50, 25, "按任意键返回", color=(255, 255, 0))
    
    Display.show_image(help_img)
    
    # 等待按键按下
    while KEY.value() == 0:
        time.sleep_ms(100)
    
    # 等待按键释放
    while KEY.value() == 1:
        time.sleep_ms(100)

# --- 按键处理函数 ---
def handle_key_state_switch():
    """处理按键状态切换"""
    global state
    
    # 检测按键状态（GPIO53）
    if KEY.value() == 1:  # 按键按下
        time.sleep_ms(50)  # 消抖延时
        if KEY.value() == 1:  # 确认按键按下
            # 检查是否为长按（1秒以上）
            press_time = time.ticks_ms()
            while KEY.value() == 1 and (time.ticks_ms() - press_time) < 1000:
                time.sleep_ms(10)
            
            if (time.ticks_ms() - press_time) >= 1000:  # 长按1秒以上
                # 显示帮助信息
                display_help_info()
            else:  # 短按
                old_state = state
                state = (state + 1) % 4  # 循环切换状态 0-3
                print(f"按键触发，状态切换到: {state}")
                display_state_info(state, 1)  # 显示1秒
            
            # 等待按键释放
            while KEY.value() == 1:
                time.sleep_ms(10)

# --- 串口命令处理 ---
def handle_serial_command():
    """处理串口命令"""
    global state
    
    Rxbuf = bytearray(5)
    Rx_NumBytes = uart2.readinto(Rxbuf, 5)
    if Rx_NumBytes is not None and Rx_NumBytes == 5:
        if (Rxbuf[0] == 0x55 and Rxbuf[2] == 0xFF and Rxbuf[3] == 0xFF and Rxbuf[4] == 0xFF):
            new_state = Rxbuf[1]
            if 0 <= new_state <= 5 and new_state != state:
                old_state = state
                state = new_state
                print(f"串口触发，状态切换到: {state}")
                display_state_info(state, 1)

# ======================= 4. 主程序 =======================
try:
    clock = time.clock()
    sensor = Sensor(id=sensor_id)  # 构建摄像头对象
    sensor.reset()  # 复位和初始化摄像头
    sensor.set_framesize(width=picture_width, height=picture_height)  # 设置帧大小
    sensor.set_pixformat(Sensor.RGB565)  # 设置输出图像格式

    Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)  # 初始化显示
    MediaManager.init()  # 初始化media资源管理器
    sensor.run()  # 启动sensor

    # 初始化显示状态
    display_state_info(state, 2)  # 启动时显示初始状态

    print("激光瞄准打靶系统启动")
    print("状态说明：")
    print("0 - 复位状态：重置系统，清除矩形识别和激光追踪数据")
    print("1 - 标定状态：识别内外框矩形，计算矩形中心点")
    print("2 - 瞄准状态：激光定点追踪，瞄准矩形中心点")
    print("3 - 计分状态：显示激光追踪完成度和统计信息")
    print("控制方式：")
    print("- 按键：循环切换状态")
    print("- 串口：发送状态命令")


    while True:
        clock.tick()
        os.exitpoint()  # 退出点，用于调试
        img = sensor.snapshot(chn=CAM_CHN_ID_0)  # 从摄像头通道0获取一帧图像

        handle_key_state_switch()        # 处理按键状态切换
        handle_serial_command()        # 处理串口命令

        # 根据当前状态执行不同任务
        if state == STATE_RESET:  # 复位状态
            # 显示待机画面
            next_state = handle_reset_state(img)
            if next_state != state:
                state = next_state

        elif state == STATE_CALIBRATE:  # 标定状态
            next_state = handle_calibrate_state(img)
            if next_state != state:
                state = next_state

        elif state == STATE_AIM:  # 瞄准状态
            # 执行图像识别任务
            next_state = handle_aim_state(img)
            if next_state != state:
                state = next_state

        elif state == STATE_SCORE:  # 计分状态
            # 计算得分
            next_state = handle_score_state(img)
            state = next_state

        # 显示状态信息
        fps = int(clock.fps())
        img.draw_string_advanced(DISPLAY_WIDTH-150, 10, 20, f"状态:{state} FPS:{fps}", color=(255, 255, 255))

        Display.show_image(img)        # 显示摄像头画面

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
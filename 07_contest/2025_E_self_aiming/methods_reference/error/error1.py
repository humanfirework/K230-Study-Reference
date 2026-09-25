# ========================= 激光瞄准打靶装置 =========================
# 功能：识别A4幅面紫外感光纸上的靶标
# 特征：红色靶心(直径≤0.1cm) + 5个同心圆(半径2-10cm，间隔2cm)


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

from machine import Timer
from machine import FPIOA
from machine import Pin
from machine import UART
from machine import PWM


# ======================= 1. 全局配置 =======================

# --- 状态定义 ---
STATE_RESET = 0      # 初始复位状态
STATE_CALIBRATE = 1  # 标定状态
STATE_AIM = 2        # 瞄准状态
STATE_SCORE = 3      # 计分状态

# --- 摄像头与显示配置 ---
sensor_id = 2
sensor = None
DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480
picture_width, picture_height = 800, 480

# --- 颜色阈值配置 ---
RED_THRESHOLD = [(0, 100, 15, 127, -128, 127)]    # 红色标记检测
TARGET_THRESHOLD = [(0, 100, 15, 127, -128, 127)] # 靶标检测

# --- 靶标参数 ---
TARGET_CENTER = None          # 靶心坐标
TARGET_CIRCLES = []           # 检测到的圆环
CIRCLE_RADII = [20, 40, 60, 80, 100]  # 像素单位的圆半径(对应2-10cm)
SCORE_ZONES = [10, 8, 6, 4, 2]         # 对应圆环的分数
AIM_TOLERANCE = 5            # 瞄准容差像素

# --- 系统状态 ---
state = STATE_RESET
is_calibrated = False
laser_detected = False
last_shot_time = 0

# ======================= 2. 初始化 =======================

# 初始化串口通信
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart2 = UART(UART.UART2, 115200)

# 初始化按键
fpioa.set_function(53, FPIOA.GPIO53)
KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)

# 初始化激光检测
fpioa.set_function(54, FPIOA.GPIO54)
LASER_SENSOR = Pin(54, Pin.IN)

# ======================= 3. 核心功能函数 =======================

def send_data(x, y, score=0, hit_type=0):
    """发送瞄准数据到控制系统"""
    frame = b'\xAA' + struct.pack('<BHHHB', 1, x, y, score, hit_type) + b'\x55'
    uart2.write(frame)
    uart2.flush()  # 等待发送完成
    return frame

def calculate_distance(p1, p2):
    """计算两点间距离"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def find_target_circles(img):
    """
    识别靶标上的红色圆形
    
    功能描述：
    1. 在输入图像中检测所有圆形
    2. 过滤掉半径不在合理范围内的圆形（半径<10或>110像素）
    3. 验证圆形区域内的红色像素比例，确保识别的是红色靶标
    4. 返回符合要求的圆形列表
    
    参数：
    - img: 输入的图像对象，需要支持find_circles和get_pixel方法
    
    返回：
    - valid_circles: 符合条件的圆形对象列表，每个圆形包含x,y,r属性
    
    算法说明：
    - 使用find_circles检测圆形，设置阈值3000控制检测灵敏度
    - 设置x_margin,y_margin,r_margin=10避免重复检测
    - 半径范围15-120像素，步长2像素
    - 红色判定标准：R>200且G<100且B<100
    - 要求红色像素占比>30%才认为是有效靶标圆形
    """
    
    # 步骤1：检测所有圆形
    # threshold=3000: 圆形检测的阈值，值越大检测到的圆形越少但越精确
    # x_margin/y_margin/r_margin=10: 圆形之间的最小间距，避免重复检测
    # r_min=15, r_max=120: 最小和最大半径范围，对应靶标实际尺寸
    # r_step=2: 半径搜索步长，平衡精度和效率
    circles = img.find_circles(threshold=3000, x_margin=10, y_margin=10, r_margin=10,
                               r_min=15, r_max=120, r_step=2)
    
    valid_circles = []
    
    # 步骤2：遍历检测到的每个圆形
    for circle in circles:
        # 步骤2.1：半径过滤 - 排除过小或过大的圆形
        # 靶标圆形半径应在10-110像素范围内
        if circle.r() < 10 or circle.r() > 110:
            continue
            
        # 步骤2.2：颜色验证 - 检查圆形区域内红色像素比例
        # 定义圆形感兴趣区域(ROI)
        roi = (circle.x()-circle.r(), circle.y()-circle.r(), 
               circle.r()*2, circle.r()*2)
        
        # 初始化计数器
        red_pixels = 0    # 红色像素计数
        total_pixels = 0  # 总像素计数
        
        # 遍历ROI内每个像素
        for x in range(max(0, roi[0]), min(img.width(), roi[0]+roi[2])):
            for y in range(max(0, roi[1]), min(img.height(), roi[1]+roi[3])):
                # 获取像素RGB值
                pixel = img.get_pixel(x, y)
                
                # 红色判定条件：R通道值>200且G、B通道值<100
                # 这样可以有效区分红色与其他颜色
                if pixel[0] > 200 and pixel[1] < 100 and pixel[2] < 100:
                    red_pixels += 1
                total_pixels += 1
        
        # 步骤2.3：红色像素比例验证
        # 要求红色像素占比>30%，确保圆形确实是红色靶标的一部分
        if total_pixels > 0 and (red_pixels/total_pixels) > 0.3:
            valid_circles.append(circle)
    
    # 返回所有符合要求的红色圆形
    return valid_circles

def calibrate_target(img):
    """标定靶标位置和圆环"""
    global TARGET_CENTER, TARGET_CIRCLES, is_calibrated
    
    # 查找所有圆形
    circles = find_target_circles(img)
    
    if len(circles) >= 5:
        # 按半径排序
        circles.sort(key=lambda c: c.r())
        
        # 找到最接近中心的圆作为靶心
        center_x = img.width() // 2
        center_y = img.height() // 2
        
        min_dist = float('inf')
        center_circle = None
        
        for circle in circles:
            dist = calculate_distance((circle.x(), circle.y()), (center_x, center_y))
            if dist < min_dist:
                min_dist = dist
                center_circle = circle
        
        if center_circle:
            TARGET_CENTER = (center_circle.x(), center_circle.y())
            TARGET_CIRCLES = circles
            is_calibrated = True
            
            # 绘制标定结果
            img.draw_circle(center_circle.x(), center_circle.y(), 3, 
                          color=(0, 255, 0), thickness=2, fill=True)
            
            for circle in circles:
                img.draw_circle(circle.x(), circle.y(), circle.r(), 
                              color=(255, 0, 0), thickness=1)
            
            return True
    
    return False

def detect_laser_point(img):
    """检测激光点位置"""
    # 查找红色激光点
    red_blobs = img.find_blobs(RED_THRESHOLD, pixels_threshold=5)
    
    if red_blobs:
        # 找到最亮的红色区域
        laser_blob = max(red_blobs, key=lambda x: x.pixels())
        return (laser_blob.cx(), laser_blob.cy())
    
    return None

def calculate_score(laser_pos):
    """计算击中分数"""
    if not TARGET_CENTER:
        return 0
    
    distance = calculate_distance(laser_pos, TARGET_CENTER)
    
    # 根据距离计算分数
    for i, radius in enumerate(CIRCLE_RADII):
        if distance <= radius:
            return SCORE_ZONES[i]
    
    return 0

def display_aiming_interface(img, laser_pos=None, score=0):
    """显示瞄准界面"""
    
    # 绘制靶标
    if TARGET_CENTER and is_calibrated:
        # 绘制同心圆
        for i, radius in enumerate(CIRCLE_RADII):
            color = (255, 0, 0) if i % 2 == 0 else (255, 255, 255)
            img.draw_circle(TARGET_CENTER[0], TARGET_CENTER[1], radius, 
                          color=color, thickness=1)
        
        # 绘制靶心
        img.draw_circle(TARGET_CENTER[0], TARGET_CENTER[1], 3, 
                      color=(0, 255, 0), thickness=2, fill=True)
    
    # 绘制激光点
    if laser_pos:
        img.draw_circle(laser_pos[0], laser_pos[1], 5, 
                      color=(255, 255, 0), thickness=2)
        img.draw_line(laser_pos[0]-10, laser_pos[1], laser_pos[0]+10, laser_pos[1], 
                    color=(255, 255, 0), thickness=1)
        img.draw_line(laser_pos[0], laser_pos[1]-10, laser_pos[0], laser_pos[1]+10, 
                    color=(255, 255, 0), thickness=1)
    
    # 显示状态信息
    status_text = ["复位", "标定", "瞄准", "计分"][state]
    img.draw_string_advanced(10, 10, 25, f"状态: {status_text}", color=(255, 255, 255))
    
    if is_calibrated:
        img.draw_string_advanced(10, 40, 20, f"靶心: {TARGET_CENTER}", color=(0, 255, 0))
    
    if score > 0:
        img.draw_string_advanced(10, 70, 30, f"得分: {score}", color=(255, 255, 0))

def handle_key_input():
    """处理按键输入"""
    global state, is_calibrated
    
    if KEY.value() == 1:
        state = (state + 1) % 4
        
        if state == STATE_RESET:
            is_calibrated = False
            print("系统复位")
        elif state == STATE_CALIBRATE:
            print("开始标定靶标")
        elif state == STATE_AIM:
            print("开始瞄准")
        elif state == STATE_SCORE:
            print("显示得分")
        
        # 防抖
        while KEY.value() == 1:
            time.sleep_ms(50)

def handle_serial_command():
    """处理串口命令"""
    global state
    
    Rxbuf = bytearray(5)
    Rx_NumBytes = uart2.readinto(Rxbuf, 5)
    
    if Rx_NumBytes == 5 and Rxbuf[0] == 0x55 and Rxbuf[4] == 0xFF:
        cmd = Rxbuf[1]
        if 0 <= cmd <= 3:
            state = cmd
            print(f"串口命令: 切换到状态{cmd}")

# ======================= 4. 主程序 =======================

try:
    clock = time.clock()
    sensor = Sensor(id=sensor_id)
    sensor.reset()
    sensor.set_framesize(width=picture_width, height=picture_height)
    sensor.set_pixformat(Sensor.RGB565)
    
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
    MediaManager.init()
    sensor.run()
    
    print("激光瞄准系统启动...")
    
    while True:
        clock.tick()
        os.exitpoint()
        
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        
        # 处理输入
        handle_key_input()
        handle_serial_command()
        
        # 根据状态执行对应功能
        if state == STATE_RESET:
            img.draw_string_advanced(DISPLAY_WIDTH//2-100, DISPLAY_HEIGHT//2-20, 30, 
                                   "按按键开始标定", color=(255, 255, 255))
            
        elif state == STATE_CALIBRATE:
            success = calibrate_target(img)
            if success:
                img.draw_string_advanced(DISPLAY_WIDTH//2-100, DISPLAY_HEIGHT//2+50, 25, 
                                       "标定完成！按按键继续", color=(0, 255, 0))
            else:
                img.draw_string_advanced(DISPLAY_WIDTH//2-100, DISPLAY_HEIGHT//2+50, 25, 
                                       "未找到靶标，请调整位置", color=(255, 0, 0))
        
        elif state == STATE_AIM:
            laser_pos = detect_laser_point(img)
            
            if laser_pos:
                score = calculate_score(laser_pos)
                send_data(laser_pos[0], laser_pos[1], score, 1)
                
                # 检查是否击中
                if calculate_distance(laser_pos, TARGET_CENTER) <= AIM_TOLERANCE:
                    img.draw_string_advanced(DISPLAY_WIDTH//2-50, DISPLAY_HEIGHT//2+50, 30, 
                                           "击中！", color=(0, 255, 0))
            
            display_aiming_interface(img, laser_pos)
        
        elif state == STATE_SCORE:
            laser_pos = detect_laser_point(img)
            if laser_pos:
                score = calculate_score(laser_pos)
                display_aiming_interface(img, laser_pos, score)
                send_data(laser_pos[0], laser_pos[1], score, 2)
            
            img.draw_string_advanced(DISPLAY_WIDTH//2-100, DISPLAY_HEIGHT-50, 25, 
                                   "按按键重新开始", color=(255, 255, 255))
        
        # 显示帧率
        fps = int(clock.fps())
        img.draw_string_advanced(DISPLAY_WIDTH-80, 10, 20, f"FPS: {fps}", color=(255, 255, 255))
        
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

# ======================= 5. 使用说明 =======================
"""
使用说明：
1. 将A4靶标放置在摄像头视野中央
2. 按按键进入标定模式，系统会自动识别靶标
3. 标定完成后，激光点会被自动追踪
4. 击中靶标后系统会显示得分
5. 按按键可以循环切换不同模式

靶标规格：
- A4纸大小
- 红色靶心点(直径≤1mm)
- 5个同心圆，半径分别为2cm、4cm、6cm、8cm、10cm
- 圆环宽度≤1mm
"""
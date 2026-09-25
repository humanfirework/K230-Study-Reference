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
STATE_RESET = 0  # 初始复位状态

# --- 摄像头与显示配置 ---
sensor_id = 2
sensor = None
DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480 # 显示屏分辨率
picture_width, picture_height = 800, 480 # 摄像头图像分辨率

# --- 视觉识别配置 ---
RED_THRESHOLD = [(85, 100, -18, 50, -18, 51)]   # 红色目标颜色阈值 (L*, a*, b* 范围)
rect_binary_threshold = [(82, 212)]             # 矩形检测二值化阈值 (灰度值范围)
rect_area_threshold = 20000                     # 矩形最小面积阈值，用于过滤小噪声
blob_area_threshold = 5                         # 颜色块最小面积阈值，用于过滤小噪声

# --- 全局参数定义 ---



# ======================= 2. 初始化 =======================

# 初始化串口
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart2 = UART(UART.UART2, 115200)

# 按键初始化
fpioa.set_function(53, FPIOA.GPIO53)  # 设置GPIO53功能
KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)  # GPIO53作为输入引脚，下拉模式


# ======================= 3. 函数定义 =======================

# --- 串口发送数据包 ---
def send_data(x, y):
    # 使用struct.pack构建数据包
    frame = b'\xAA' + struct.pack('<BHHHH', 1, x, y) + b'\x55'
    uart2.write(frame)
    uart2.flush()  # 单次发送完成后，清空缓存
    return frame  # 返回构建的frame

# --- 状态管理函数 ---
def display_state_info(state_code, duration=2):
    state_definitions = [
        (0, "复位状态", "系统初始化完成", (0, 255, 0)),
        (1, "运行状态", "正在执行识别任务1", (0, 255, 255)),
        (2, "运行状态", "正在执行识别任务2", (255, 255, 0)),
        (8, "调整状态", "阈值调整", (255, 0, 255))
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
    status_img.draw_string_advanced(DISPLAY_WIDTH//2 - 140, DISPLAY_HEIGHT//2 - 80, 35,
                                   f"状态: {current_state_info[1]}", color=border_color)
    status_img.draw_string_advanced(DISPLAY_WIDTH//2 - 150, DISPLAY_HEIGHT//2 - 20, 30,
                                   f"描述: {current_state_info[2]}", color=(255, 255, 255))
    status_img.draw_string_advanced(DISPLAY_WIDTH//2 - 140, DISPLAY_HEIGHT//2 + 30, 35,
                                   f"状态码: {state_code}", color=(200, 200, 200))
    status_img.draw_string_advanced(DISPLAY_WIDTH//2 + 210, DISPLAY_HEIGHT//2 + 150, 25,
                                   f"时间: {time.ticks_ms()//1000}s", color=(150, 150, 150))

    Display.show_image(status_img)
    time.sleep(duration)

def handle_key_press():
    global state  # 声明使用全局变量state

    # 处理按键状态切换
    if KEY.value() == 1:  # 按键按下（上拉模式，按下为高电平）
        time.sleep_ms(50)  # 消抖延时
        if KEY.value() == 1:  # 确认按键确实按下
            # 状态切换逻辑：状态0→8→0循环
            old_state = state
            if state == 0:
                state = 8  # 直接跳到状态8（阈值调节）
            elif state == 8:
                state = 0  # 从状态8返回状态0
            else:
                state = (state + 1) % 10  # 其他状态正常循环

            print(f"按键切换：状态从 {old_state} 切换到 {state}")
            display_state_info(state, 1)  # 显示新状态1秒

            # 等待按键释放，避免重复触发
            while KEY.value() == 1:
                time.sleep_ms(10)

# 触摸屏阈值调节函数
def handle_threshold_adjustment():
    """
    触摸屏阈值调节功能

    功能说明：
    1. 支持红点识别(LAB颜色空间)和矩形识别(灰度)两种阈值调节模式
    2. 通过触摸屏实时调节阈值参数，并支持保存到全局变量
    3. 提供返回、模式切换、保存三个功能按钮

    返回：0 - 返回复位状态
    """
    tp = TOUCH(0)  # 初始化触摸屏对象

    # 阈值模式配置：映射到全局变量
    threshold_dict = {'red_point': RED_THRESHOLD, 'gray_rect': rect_binary_threshold}

    # 界面颜色配置
    button_color = (150, 150, 150)  # 按钮背景色
    text_color = (0, 0, 0)        # 文字颜色

    # 支持的阈值模式列表
    threshold_mode_lst = list(threshold_dict.keys())
    current_mode = 'red_point'  # 初始模式：LAB颜色空间阈值调节

    # 初始化滑块值：根据模式返回对应的默认阈值
    def init_slider_values(mode):
        """根据模式返回对应的默认阈值参数"""
        if mode == 'red_point':
            return [85, 100, -18, 50, -18, 51]  # LAB颜色空间的L,A,B阈值(6个参数)
        else:
            return [82, 212]  # 灰度阈值(2个参数：最小值、最大值)

    slider_values = init_slider_values(current_mode)

    def draw_threshold_ui():
        """
        绘制左右分屏的阈值调节界面
        左侧：实时摄像头画面（二值化处理后）
        右侧：阈值调节面板（标题、按钮、滑块）
        """
        # 创建一个新的图像对象用于绘制
        img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.RGB565)
        img.clear()  # 清空图像内容

        # 定义分屏参数
        left_width = DISPLAY_WIDTH // 2
        right_width = DISPLAY_WIDTH - left_width

        # 1. 绘制左侧实时画面 (二值化处理后)
        # 获取当前摄像头画面并进行二值化处理
        raw_img = sensor.snapshot(chn=CAM_CHN_ID_0)
        processed_img = raw_img.copy()  # 复制图像以避免修改原始图像
        
        if current_mode == 'red_point':
            # 红点模式：LAB颜色空间二值化
            processed_img = processed_img.binary([[i - 128 for i in slider_values]])
            processed_img = processed_img.to_rgb565()
        else:
            # 矩形模式：灰度二值化
            processed_img = processed_img.to_grayscale()
            processed_img = processed_img.binary([slider_values[:2]])
            processed_img = processed_img.to_rgb565()
        
        # 将处理后的图像绘制到左侧
        img.draw_image(processed_img, 0, 0, alpha=255, roi=(0, 0, left_width, DISPLAY_HEIGHT))

        # 2. 绘制右侧阈值调节面板
        # 绘制半透明遮罩（可选，如果需要的话）
        # img.draw_rectangle(left_width, 0, right_width, DISPLAY_HEIGHT, color=(0, 0, 0), thickness=1, fill=True)
        # img.draw_rectangle(left_width, 0, right_width, DISPLAY_HEIGHT, color=(255, 255, 255), thickness=1, fill=True, alpha=128)

        # 绘制标题
        title = f"阈值调节 - {current_mode}模式"
        title_x = left_width + (right_width - len(title) * 15) // 2  # 简单计算居中位置
        img.draw_string_advanced(title_x, 10, 30, title, color=(0, 255, 0))

        # 绘制按钮
        button_width = 80
        button_height = 35
        button_spacing = 10
        button_start_x = left_width + (right_width - 3*button_width - 2*button_spacing) // 2
        button_y = 60

        # 返回按钮
        img.draw_rectangle(button_start_x, button_y, button_width, button_height, color=(100, 100, 100), thickness=1, fill=True)
        img.draw_string_advanced(button_start_x + 15, button_y + 5, 25, "返回", color=(255, 255, 255))

        # 切换模式按钮
        switch_x = button_start_x + button_width + button_spacing
        img.draw_rectangle(switch_x, button_y, button_width, button_height, color=(100, 100, 100), thickness=1, fill=True)
        img.draw_string_advanced(switch_x + 15, button_y + 5, 25, "切换", color=(255, 255, 255))

        # 保存按钮
        save_x = switch_x + button_width + button_spacing
        img.draw_rectangle(save_x, button_y, button_width, button_height, color=(100, 100, 100), thickness=1, fill=True)
        img.draw_string_advanced(save_x + 15, button_y + 5, 25, "保存", color=(255, 255, 255))

        # 绘制滑块
        slider_width = right_width - 60
        slider_height = 35
        slider_x = left_width + 30
        slider_y_start = 125
        
        # 根据当前模式动态生成滑块
        param_names = []
        if current_mode == 'red_point':
            param_names = ["L-Min", "L-Max", "A-Min", "A-Max", "B-Min", "B-Max"]
        else:  # rect模式
            param_names = ["Gray-Min", "Gray-Max"]
            
        for i, value in enumerate(slider_values):
            y_pos = slider_y_start + i * 60
            
            # 绘制参数名称
            img.draw_string_advanced(left_width + 5, y_pos, 20, param_names[i], color=(200, 200, 200))
            
            # 绘制滑块轨道
            img.draw_rectangle(slider_x, y_pos + 15, slider_width, slider_height, color=(150, 150, 150), thickness=1, fill=True)
            
            # 绘制滑块值
            img.draw_string_advanced(slider_x + slider_width + 5, y_pos + 20, 20, str(value), color=(255, 255, 0))
            
            # 计算滑块位置
            if current_mode == 'red_point':
                # LAB模式：值范围-128~127
                slider_pos = int((value + 128) * slider_width / 256)
            else:
                # 灰度模式：值范围0~255
                slider_pos = int(value * slider_width / 255)
            
            # 绘制滑块按钮
            img.draw_rectangle(slider_x + slider_pos - 5, y_pos + 10, 10, slider_height + 10, color=(255, 0, 0), thickness=1, fill=True)

        return img  # 返回绘制完成的图像

    def get_button_action(x, y):
        """
        根据触摸坐标判断按钮动作（适应左右分屏布局）

        参数：
        x, y - 触摸点的屏幕坐标

        返回：
        "return" - 返回复位状态
        "switch_mode" - 切换阈值模式
        "save" - 保存当前阈值
        None - 无按钮点击

        按钮区域定义（右侧面板内）：
        左侧分界线：DISPLAY_WIDTH//2
        返回按钮：x在[panel_x+offset, panel_x+offset+80]范围内
        切换按钮：x在[panel_x+offset+90, panel_x+offset+170]范围内
        保存按钮：x在[panel_x+offset+180, panel_x+offset+260]范围内
        """
        # 定义分屏参数
        left_width = DISPLAY_WIDTH // 2
        right_width = DISPLAY_WIDTH - left_width
        panel_x = left_width

        # 检查是否在右侧面板内
        if x < panel_x:
            return None

        # 计算相对右侧面板的坐标
        relative_x = x - panel_x
        relative_y = y

        # 按钮区域定义
        button_width = 80
        button_height = 35
        button_spacing = 10
        button_start_x = (right_width - 3*button_width - 2*button_spacing) // 2
        button_y = 60

        # 返回按钮区域
        return_x = button_start_x
        if button_y <= relative_y <= button_y + button_height and return_x <= relative_x <= return_x + button_width:
            return "return"

        # 切换按钮区域
        switch_x = button_start_x + button_width + button_spacing
        if button_y <= relative_y <= button_y + button_height and switch_x <= relative_x <= switch_x + button_width:
            return "switch_mode"

        # 保存按钮区域
        save_x = button_start_x + 2*(button_width + button_spacing)
        if button_y <= relative_y <= button_y + button_height and save_x <= relative_x <= save_x + button_width:
            return "save"

        return None  # 点击区域不在任何按钮上

    def update_slider_value(x, y, index):
        """更新滑块值（适应左右分屏布局）"""
        # 定义分屏参数
        left_width = DISPLAY_WIDTH // 2
        right_width = DISPLAY_WIDTH - left_width
        panel_x = left_width

        # 检查是否在右侧面板内
        if x < panel_x:
            return

        # 计算相对右侧面板的坐标
        relative_x = x - panel_x
        relative_y = y

        # 滑块参数
        slider_width = right_width - 60
        slider_height = 35
        slider_x = 30
        slider_y_start = 125
        y_pos = slider_y_start + index * 60

        # 检查是否在滑块区域内
        if y_pos + 15 <= relative_y <= y_pos + 15 + slider_height and slider_x <= relative_x <= slider_x + slider_width:
            # 计算相对滑块位置
            slider_pos = relative_x - slider_x
            slider_pos = max(0, min(slider_width, slider_pos))  # 限制在滑块范围内

            if current_mode == 'red_point':
                # LAB模式：值范围-128~127，映射到0~slider_width像素
                new_value = int(slider_pos * 256 / slider_width - 128)
                slider_values[index] = max(-128, min(127, new_value))
            else:
                # 灰度模式：值范围0~255，映射到0~slider_width像素
                new_value = int(slider_pos * 255 / slider_width)
                slider_values[index] = max(0, min(255, new_value))

    def save_thresholds():
        """
        将当前调整的阈值保存到全局变量

        保存逻辑：
        1. 红点模式：保存6个LAB参数到RED_THRESHOLD全局变量
        2. 矩形模式：保存2个灰度参数到rect_binary_threshold全局变量

        注意：
        - 使用clear()清空原列表，避免旧数据残留
        - 红点模式使用tuple包装，便于后续图像处理使用
        - 矩形模式直接保存为列表，与图像处理函数兼容
        """
        if current_mode == 'red_point':
            RED_THRESHOLD.clear()  # 清空原阈值
            RED_THRESHOLD.extend([tuple(slider_values)])  # 保存为tuple格式
        else:
            rect_binary_threshold.clear()  # 清空原阈值
            rect_binary_threshold.extend([tuple(slider_values)])   # 保存为tuple格式

    # 主循环：处理触摸交互
    while True:
        # 1. 绘制界面并显示
        img = draw_threshold_ui()
        Display.show_image(img)

        # 2. 获取触摸输入
        points = tp.read()
        if len(points) > 0:
            x, y = points[0].x, points[0].y  # 获取第一个触摸点坐标
            action = get_button_action(x, y)   # 判断按钮动作

            # 3. 处理按钮动作
            if action == "return":
                # 返回按钮：回到复位状态(状态0)
                display_state_info(0, 1)
                return 0  # 返回复位状态
            elif action == "switch_mode":
                # 切换模式：在LAB和灰度模式间循环切换
                current_mode = threshold_mode_lst[(threshold_mode_lst.index(current_mode) + 1) % len(threshold_mode_lst)]
                slider_values = init_slider_values(current_mode)  # 重新加载对应模式的默认值
            elif action == "save":
                # 保存按钮：保存当前阈值并显示成功提示
                save_thresholds()
                img.draw_string_advanced(DISPLAY_WIDTH//2-50, DISPLAY_HEIGHT//2, 30, "保存成功!", color=(0, 255, 0))
                Display.show_image(img)
                time.sleep(1)  # 显示1秒提示信息

            # 4. 处理滑块调节（适应左右分屏布局）
            slider_count = len(slider_values)
            # 定义分屏参数
            left_width = DISPLAY_WIDTH // 2
            right_width = DISPLAY_WIDTH - left_width
            panel_x = left_width
            
            # 滑块参数
            slider_width = right_width - 60
            slider_height = 35
            slider_x = panel_x + 30
            slider_y_start = 125

            for i in range(slider_count):
                y_pos = slider_y_start + i * 60  # 垂直间隔60像素
                # 检查触摸点是否在右侧面板内且在滑块区域内
                if (x >= panel_x and 
                    y_pos + 15 <= y <= y_pos + 15 + slider_height and 
                    slider_x <= x <= slider_x + slider_width):
                    update_slider_value(x, y, i)  # 更新对应滑块的值
                    break  # 一次只处理一个滑块

        time.sleep_ms(100)  # 100ms刷新间隔，避免CPU占用过高


# ======================= 4. 主程序 =======================
try:

    clock = time.clock()
    sensor = Sensor(id = sensor_id) #构建摄像头对象
    sensor.reset() #复位和初始化摄像头
    sensor.set_framesize(width = picture_width, height = picture_height) #设置帧大小为LCD分辨率()，默认通道0    （显示画面的大小）一般小
    sensor.set_pixformat(Sensor.RGB565) #设置输出图像格式，默认通道0

    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init() #初始化media资源管理器
    sensor.run() #启动sensor




    # 初始化显示状态
    display_state_info(state, 2)  # 启动时显示初始状态

    # print("按键使用说明：")
    # print("- 按下GPIO53按键可在状态间切换")
    # print("- 状态0：复位状态，按一次按键进入阈值调节")
    # print("- 状态8：阈值调节，在此界面可调节识别参数")
    # print("- 在阈值调节界面按"返回"按钮或再次按键可退出")

    while True:
        clock.tick()
        os.exitpoint()  # 退出点，用于调试
        img = sensor.snapshot(chn = CAM_CHN_ID_0)  # 从摄像头通道0获取一帧图像

        # 矩形图像处理
        img_gray = img.to_grayscale(copy=True)        # 转换为灰度图
        img_binary = img_gray.binary(rect_binary_threshold)  # 二值化处理
        rects = img_binary.find_rects()              # 查找矩形轮廓

        # 处理串口状态切换（格式：55 XX FF FF FF）
        Rxbuf = bytearray(5)
        Rx_NumBytes = uart2.readinto(Rxbuf, 5)
        if Rx_NumBytes is not None and Rx_NumBytes == 5:
            if (Rxbuf[0] == 0x55 and Rxbuf[2] == 0xFF and Rxbuf[3] == 0xFF and Rxbuf[4] == 0xFF):
                new_state = Rxbuf[1]
                if 0 <= new_state <= 9 and new_state != state:
                    old_state = state
                    state = new_state
                    print(f"串口命令：状态从 {old_state} 切换到 {state}")
                    display_state_info(state, 1)  # 显示新状态1秒

        handle_key_press()

        # 根据当前状态执行不同任务
        if state == 0:  # 复位状态
            # 显示待机画面
            img.draw_string_advanced(10, 10, 30, "复位状态 - 等待开始", color=(0, 255, 0))
            img.draw_string_advanced(10, 50, 25, "按按键切换到阈值调节", color=(255, 255, 0))

        elif state == 1:  # 运行状态
            # 执行图像识别任务
            img.draw_string_advanced(10, 10, 30, "运行状态 - 任务1", color=(0, 255, 255))

            # 这里可以添加具体的识别逻辑

        elif state == 2:  # 运行状态
            # 执行图像识别任务
            img.draw_string_advanced(10, 10, 30, "运行状态 - 任务2", color=(0, 255, 255))

            # 这里可以添加具体的识别逻辑

        elif state == 3:  # 运行状态
            # 执行图像识别任务
            img.draw_string_advanced(10, 10, 30, "运行状态 - 任务3", color=(0, 255, 255))

            # 这里可以添加具体的识别逻辑

        elif state == 8:  # 屏幕改变阈值
            state = handle_threshold_adjustment()


        elif state == 9:  # 暂停状态
            # 暂停识别，显示暂停信息
            img.draw_string_advanced(10, 10, 30, "暂停状态 - 等待串口命令继续", color=(255, 255, 0))




        # 显示当前状态码
        img.draw_string_advanced(DISPLAY_WIDTH-100, 10, 25, f"状态:{state}", color=(255, 255, 255))
        # 显示当前阈值参数
        if RED_THRESHOLD:
            red_thresh_str = f"红点:{RED_THRESHOLD[0]}"
            img.draw_string_advanced(10, DISPLAY_HEIGHT-80, 20, red_thresh_str, color=(255, 0, 0))
        
        if rect_binary_threshold:
            rect_thresh_str = f"矩形:{rect_binary_threshold}"
            img.draw_string_advanced(10, DISPLAY_HEIGHT-50, 20, rect_thresh_str, color=(0, 255, 0))
            
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

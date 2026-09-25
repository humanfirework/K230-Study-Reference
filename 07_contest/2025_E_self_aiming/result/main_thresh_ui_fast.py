import time, os, sys
import math
import struct
from media.sensor import *
from media.display import *
from media.media import *

from machine import FPIOA
from machine import UART
from machine import Pin
from machine import TOUCH

picture_width = 400
picture_height = 240
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

sensor_id = 2
sensor = None

# 可调参数
rect_binary_default = [(103, 255)]  # 默认二值化阈值
rect_binary_small = [(127, 216)]    # 面积小于5000像素时的二值化阈值
rect_binary_large = [(85, 200)]   # 面积大于20000像素时的二值化阈值

# 根据面积确定二值化阈值的函数
def get_binary_threshold(area):
    if area < 5000:
        return rect_binary_small
    elif area > 5000 and area < 20000:
        return rect_binary_default
    else:
        return rect_binary_large

# 串口配置
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
fpioa.set_function(48, FPIOA.GPIO48)

# 按键初始化
fpioa.set_function(53, FPIOA.GPIO53)  # 设置GPIO53功能
KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)  # GPIO53作为输入引脚，下拉模式

uart2 = UART(UART.UART2, 115200)
LED = Pin(48, Pin.OUT, pull=Pin.PULL_NONE, drive=15)

# 屏幕中心坐标
SCREEN_CENTER_X = 200
SCREEN_CENTER_Y = 120

# 矩形数据变量
rect_corners = []
rect_center = (0, 0)
is_first_frame = True  # 标记是否为第一帧
last_frame_center = (0, 0)  # 上一帧的矩形中心点

# 目标点稳定性优化变量
last_valid_target = (0, 0)  # 上一次的有效目标坐标
current_target_count = 0     # 当前目标的连续识别计数
TARGET_STABILITY_THRESHOLD = 3  # 目标稳定阈值（连续识别次数）

# 预测提前量变量
previous_target = (0, 0)  # 上一帧的目标位置
predicted_target = (0, 0)  # 预测的目标位置

# 矩形识别参数
MIN_RECT_AREA = 500      # 最小矩形面积
MAX_RECT_AREA = 50000     # 最大矩形面积
MIN_ASPECT_RATIO = 0.5    # 最小长宽比
MAX_ASPECT_RATIO = 2.5    # 最大长宽比


def handle_threshold_adjustment():
    """
    触摸屏阈值调节功能

    功能说明：
    1. 支持矩形识别(灰度)阈值调节模式
    2. 通过触摸屏实时调节阈值参数，并支持保存到全局变量
    3. 提供返回、模式切换、保存三个功能按钮

    返回：0 - 返回复位状态
    """
    tp = TOUCH(0)  # 初始化触摸屏对象

    # 界面颜色配置
    button_color = (150, 150, 150)  # 按钮背景色
    text_color = (0, 0, 0)        # 文字颜色

    # 初始模式：灰度阈值调节
    current_mode = 'gray_rect'

    # 初始化滑块值：根据threshold_mode返回对应的默认阈值
    def init_slider_values(mode):
        """根据threshold_mode返回对应的默认阈值参数"""
        # 根据threshold_mode选择不同的矩形阈值
        if threshold_mode == 0:  # 默认阈值
            return [82, 212]
        elif threshold_mode == 1:  # 小面积阈值
            return [85, 220]
        else:  # 大面积阈值
            return [75, 200]

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
        mode_names = ["默认", "小面积", "大面积"]
        title = f"阈值调节 - {mode_names[threshold_mode]}模式"
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

        # 灰度模式参数名称
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

            # 灰度模式：值范围0~255，映射到0~slider_width像素
            new_value = int(slider_pos * 255 / slider_width)
            slider_values[index] = max(0, min(255, new_value))

    def save_thresholds():
        """
        将当前调整的阈值保存到全局变量

        保存逻辑：
        根据threshold_mode保存2个灰度参数到对应的全局变量

        注意：
        - 使用clear()清空原列表，避免旧数据残留
        - 直接保存为列表，与图像处理函数兼容
        """
        # 根据threshold_mode保存到不同的全局变量
        if threshold_mode == 0:  # 默认阈值
            rect_binary_default.clear()
            rect_binary_default.extend([tuple(slider_values)])
        elif threshold_mode == 1:  # 小面积阈值
            rect_binary_small.clear()
            rect_binary_small.extend([tuple(slider_values)])
        else:  # 大面积阈值
            rect_binary_large.clear()
            rect_binary_large.extend([tuple(slider_values)])

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
                return 0  # 返回复位状态
            elif action == "switch_mode":
                # 切换模式：在三种矩形阈值模式间循环切换
                global threshold_mode
                threshold_mode = (threshold_mode + 1) % 3
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

def find_best_rect(img_binary, is_first=False, last_center=(0, 0)):
    """根据帧数选择最佳矩形：第一帧选面积最大，后续帧优先选距离上一帧中心最近的矩形"""
    # 查找所有白色连通域
    blobs = img_binary.find_blobs([(255, 255)], x_stride=2, y_stride=2, area_threshold=100)
    if not blobs:
        return None

    valid_rects = []
    for blob in blobs:
        # 获取轮廓点
        points = blob.min_corners()
        if len(points) < 4:
            continue

        # 计算面积和长宽比
        x, y, w, h = blob.rect()
        area = w * h
        aspect_ratio = w / h if h > 0 else 0

        # 几何指标过滤
        if area < MIN_RECT_AREA or area > MAX_RECT_AREA:
            continue
        if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
            continue

        # 计算中心点
        center_x = (points[0][0] + points[2][0]) // 2
        center_y = (points[0][1] + points[2][1]) // 2

        # 创建一个类似 rect 的对象
        class RectLike:
            def __init__(self, corners, rect, center, area):
                self._corners = corners
                self._rect = rect
                self._center = center
                self._area = area

            def corners(self):
                return self._corners

            def rect(self):
                return self._rect

            def center(self):
                return self._center

            def area(self):
                return self._area

        valid_rects.append(RectLike(points, (x, y, w, h), (center_x, center_y), area))

    if not valid_rects:
        return None

    if is_first or last_center == (0, 0):
        # 第一帧或没有上一帧中心：选面积最大的
        best_rect = max(valid_rects, key=lambda r: r.area())
    else:
        # 后续帧：优先选距离上一帧中心50像素内的矩形
        nearby_rects = []
        for rect in valid_rects:
            dist = distance(rect.center(), last_center)
            if dist <= 50:  # 50像素内
                nearby_rects.append((rect, dist))

        if nearby_rects:
            # 在50像素内的矩形中选面积最大的
            best_rect = max(nearby_rects, key=lambda x: x[0].area())[0]
        else:
            # 没有50像素内的矩形，选面积最大的
            best_rect = max(valid_rects, key=lambda r: r.area())

    return best_rect


def send_combined_data(target_x, target_y):
    """发送整合的数据包（矩形坐标和目标点矩形中心）"""
    if target_x == 0 and target_y == 0:
        frame = b'\xAA' + struct.pack('<BHH', 0, target_x, target_y) + b'\x55'
        uart2.write(frame)
        uart2.flush()
        print(f"[COMBINED] 未检测到矩形，发送数据0")
        print(f"[COMBINED] 数据帧: {frame.hex().upper()}")
    else:
        frame = b'\xAA' + struct.pack('<BHH', 1, target_x, target_y) + b'\x55'
        uart2.write(frame)
        uart2.flush()
        print(f"[COMBINED] 发送整合数据:")
        print(f"[COMBINED] 目标点矩形中心: ({target_x}, {target_y})")
        print(f"[COMBINED] 数据帧: {frame.hex().upper()}")
    return frame

# 计算两点间距离
def distance(point1, point2):
    return int(math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2))

try:
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id)
    sensor.reset()
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.GRAYSCALE, chn=CAM_CHN_ID_0)

    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

    #构造clock
    clock = time.clock()

    # 初始化Situation变量
    Situation = 0  # 0:未初始化, 1:开始识别, 2:停止识别, 3:阈值调节
    threshold_mode = 0  # 0:默认阈值, 1:小面积阈值, 2:大面积阈值

    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 检查按钮状态，如果按下则进入阈值调节界面
        if KEY.value() == 1:  # 按钮被按下
            threshold_mode = (threshold_mode + 1) % 3  # 在三种模式间循环切换
            Situation = 3
            print(f"通过按钮进入阈值调节界面，当前模式: {threshold_mode}")
            # 等待按钮释放，避免重复触发
            while KEY.value() == 1:
                time.sleep_ms(10)

        #接收数据包0X"55 XX FF FF"
        Rxbuf = bytearray(4)
        Rx_NumBytes = uart2.readinto(Rxbuf, 4)
        if Rx_NumBytes is not None and Rx_NumBytes == 4:
            if (Rxbuf[0] == 0x55 and Rxbuf[2] == 0xFF and Rxbuf[3] == 0xFF):
                if(Rxbuf[1] == 0x01):
                    Situation = 1
                    print("识别矩形，校准激光")
                elif(Rxbuf[1] == 0x02):
                    Situation = 2
                    print("停止识别")
                elif(Rxbuf[1] == 0x03):  # 新增情况，用于进入阈值调节界面
                    Situation = 3
                    print("进入阈值调节界面")

        # 根据Situation状态决定是否进行图像处理
        if Situation == 0:
            # 图像预处理 - 减少复制操作以提高性能
            img_gray = img.to_grayscale(copy=False)  # 直接转换，不创建副本

            # 根据上一帧矩形面积确定二值化阈值
            if last_frame_center != (0, 0) and 'max_rect' in locals() and max_rect is not None and hasattr(max_rect, 'area'):
                binary_threshold = get_binary_threshold(max_rect.area())
            else:
                binary_threshold = rect_binary_default

            # 二值化处理
            img_binary = img_gray.binary(binary_threshold)

            # 简化形态学操作 - 减少计算量以提高帧率
            # 使用开运算替代单独的腐蚀和膨胀操作
            img_binary.open(1)

            # 移除梯度运算以提高性能，如需要可重新启用
            # img_gradient = img_binary.copy()
            # img_gradient.erode(1)  # 腐蚀图像
            # img_dilated = img_binary.copy()
            # img_dilated.dilate(1)  # 膨胀图像
            # 梯度 = 膨胀 - 腐蚀
            # img_gradient = img_dilated.sub(img_gradient)
            # img_binary = img_gradient  # 使用梯度图像进行后续处理

            # 使用新的矩形识别方法（根据帧数选择策略）
            max_rect = find_best_rect(img_binary, is_first_frame, last_frame_center)

            # 调试：显示梯度运算结果
            # img.draw_image(img_binary, 0, 0, x_scale=0.3, y_scale=0.3)  # 显示梯度图像

            # 调试信息
            print(f"检测到矩形: 1个" if max_rect else "检测到矩形: 0个")

            if max_rect:
                corners = max_rect.corners()
                center_x = (corners[0][0] + corners[2][0]) // 2
                center_y = (corners[0][1] + corners[2][1]) // 2

                # 更新上一帧中心点（仅在成功检测到矩形时）
                last_frame_center = (center_x, center_y)
                if is_first_frame:
                    is_first_frame = False

                # 计算速度向量并预测下一帧位置
                velocity_x = center_x - previous_target[0]
                velocity_y = center_y - previous_target[1]
                predicted_x = center_x + velocity_x
                predicted_y = center_y + velocity_y
                predicted_target = (predicted_x, predicted_y)
                previous_target = (center_x, center_y)

                # 目标点稳定性优化
                # 检查当前目标是否与上一次目标接近（例如距离小于50像素）
                dist_to_last = distance((center_x, center_y), last_valid_target)
                if dist_to_last < 50:
                    current_target_count += 1
                else:
                    # 新目标出现，但需要进一步验证是否为有效目标
                    # 如果距离过大（例如超过100像素），则认为是异常检测，不更新目标
                    if dist_to_last > 100:
                        # 距离过大，可能是错误检测，不更新计数和目标
                        current_target_count = max(0, current_target_count - 1)  # 减少计数但不低于0
                    else:
                        # 距离适中，可能是有效的新目标，重置计数
                        current_target_count = 1
                        last_valid_target = (center_x, center_y)

                # 只有当连续识别次数达到阈值时才更新并发送新目标数据
                if current_target_count >= TARGET_STABILITY_THRESHOLD:
                    # 更新有效目标
                    last_valid_target = (center_x, center_y)

                    # 简化绘图操作以提高帧率
                    # 只绘制必要的图形元素

                    # 绘制矩形边框（简化线条粗细）
                    for i in range(4):
                        next_i = (i + 1) % 4
                        img.draw_line(corners[i][0], corners[i][1], corners[next_i][0], corners[next_i][1],
                                    color=(0, 255, 0), thickness=1)  # 减小线条粗细

                    # 绘制中心点
                    img.draw_cross(center_x, center_y, color=(255, 255, 255))

                    # 更新矩形数据
                    rect_corners = corners
                    rect_center = (center_x, center_y)

                    # 将target_x和target_y改为预测的目标点矩形中心坐标
                    target_x = predicted_target[0]
                    target_y = predicted_target[1]

                    # 发送整合数据包（发送预测位置）
                    send_combined_data(target_x, target_y)
                else:
                    # 未达到稳定阈值，继续使用预测位置
                    target_x, target_y = predicted_target
                    send_combined_data(target_x, target_y)

                # 绘制屏幕中心点和误差向量
                img.draw_cross(SCREEN_CENTER_X, SCREEN_CENTER_Y, color=(255, 255, 255))
                img.draw_line(SCREEN_CENTER_X, SCREEN_CENTER_Y, center_x, center_y,
                             color=(255, 255, 0), thickness=1)  # 减小线条粗细

                # 检查是否对准目标（距离小于阈值）
                # 使用预测位置进行对准判断
                dist_to_target = distance((SCREEN_CENTER_X, SCREEN_CENTER_Y), predicted_target)
                if dist_to_target < 30:  # 阈值可调
                    LED.value(1)  # 打开激光
                    print("激光已打开")
                else:
                    LED.value(0)  # 关闭激光

                # 精简显示信息以提高性能
                img.draw_string_advanced(10, 10, 16, f"FPS: {clock.fps():.1f}", color=(255, 0, 0))
                img.draw_string_advanced(10, 30, 16, f"中心:({center_x},{center_y})", color=(0, 255, 0))
                img.draw_string_advanced(10, 50, 16, f"距离:{dist_to_target}", color=(0, 0, 255))
                img.draw_string_advanced(10, 70, 16, f"阈值:{binary_threshold}", color=(255, 255, 255))
            else:
                # 没有检测到矩形，重置计数器并发送预测位置
                current_target_count = 0
                target_x, target_y = predicted_target
                send_combined_data(target_x, target_y)
        elif Situation == 2:
            # 当Situation为2时，停止识别，不进行图像处理，不发送数据
            pass
        elif Situation == 3:  # 新增情况，用于进入阈值调节界面
            # 调用阈值调节函数
            result = handle_threshold_adjustment()
            if result == 0:  # 如果返回0，表示用户点击了返回按钮
                Situation = 0  # 回到初始状态
        else:
            # 当Situation为0或其他值时，不发送数据
            pass

        # 显示图像
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

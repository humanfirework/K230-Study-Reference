import gc
import os
import sys
import time
import math
import struct

from math import *
from media.sensor import * #导入sensor模块，使用摄像头相关接口
from media.display import * #导入display模块，使用display相关接口
from media.media import * #导入media模块，使用meida相关接口

from machine import FPIOA
from machine import Pin
from machine import UART
from machine import PWM

# ======================= 1. 全局配置 =======================
sensor_id = 2
picture_width = 800
picture_height = 480
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

# --- 视觉识别配置 ---
RED_THRESHOLD = [(96, 100, -25, 34, -30, 18)] # 红色阈值
Green_thresholds = (30, 100, -64, -8, 50, 70)  # 绿色阈值（移除多余逗号）
rect_binart = (87, 183)

# --- 摄像头与显示配置 ---
state = 0     #识别状态
Situation = 0
pencil_points = []  # 空列表初始化5个点  #记入铅笔矩形坐标5个点
TRACKING_THRESHOLD = 10  # 像素
CONFIRMATION_DURATION_S = 1  # 目标确认持续时间(秒)
# 定义激光位置
laser_x = 0
laser_y = 0
frame = 0
frame1 = 0

fpioa = FPIOA()
fpioa.help()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart2 = UART(UART.UART2, 115200)


# 创建按键对象，用于触发图像采集
fpioa.set_function(53, FPIOA.GPIO53)  # 设置GPIO53功能
KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)  # GPIO53作为输入引脚，下拉模式

# 发送目标位置数据的函数
# 参数x,y: 目标位置的x和y坐标值


def send_data(x, y):
    # 使用struct.pack构建数据包
    frame = b'\xAA' + struct.pack('<BHHHH', 1, x, y) + b'\x55'
    uart2.write(frame)
    time.sleep_ms(6)  # 单次发送
    return frame  # 返回构建的frame

def send_target_data(x, y):
    # 发送追踪目标数据
    frame = b'\xAA' + struct.pack('<BHHHH', 2, x, y) + b'\x55'
    uart2.write(frame)
    time.sleep_ms(6)
    return frame


def send_five_points(points):
    """
    points: 列表，包含5个[x, y]，如 [[x1, y1], [x2, y2], ..., [x5, y5]]
    """
    if len(points) != 5:
        print("点数量不足5个，无法发送")
        return
    # 展开所有点
    data = []
    for pt in points:
        data.extend(pt)  # [x1, y1, x2, y2, ...]
    # '<'表示小端，B表示1字节标志位，10H表示10个unsigned short坐标值
    frame = b'\xAA' + struct.pack('<B10H', 0, *data) + b'\x55'
    for i in range(4):
        uart2.write(frame)
        time.sleep_ms(6)
    return frame


# 寻找面积最大的N个矩形
def find_largest_rects(rects, count=2):
    if not rects or count <= 0:
        return []
    # 按面积排序矩形
    rects_with_area = []
    for rect in rects:
        x, y, w, h = rect.rect()
        area = w * h
        rects_with_area.append((area, rect))
    # 降序排序并取前count个
    rects_with_area.sort(reverse=True, key=lambda x: x[0])
    return [rect for (area, rect) in rects_with_area[:count]]

def sort_rect_corners(corners):
    # 对矩形角点进行排序，返回[左上, 右上, 右下, 左下]
    if len(corners) != 4:
        print(f"警告: 矩形角点数量异常 ({len(corners)})，返回原始顺序")
        return corners

    # 按y坐标排序区分上下两组
    sorted_by_y = sorted(corners, key=lambda p: p[1])
    y_values = [p[1] for p in sorted_by_y]
    y_diff = y_values[-1] - y_values[0]
    threshold = max(10, int(y_diff * 0.2))

    # 处理上下分组
    if sorted_by_y[1][1] - sorted_by_y[0][1] <= threshold:
        top_points = sorted_by_y[:2]
        bottom_points = sorted_by_y[2:]
    elif y_values[-1] - y_values[-2] <= threshold:
        top_points = sorted_by_y[:2]
        bottom_points = sorted_by_y[2:]
    else:
        # 特殊情况处理：取中间两个点为一组
        top_points = sorted_by_y[1:3]
        bottom_points = [sorted_by_y[0]] + sorted_by_y[3:]

    # 按x坐标排序区分左右
    top_points.sort(key=lambda p: p[0])
    bottom_points.sort(key=lambda p: p[0], reverse=True)

    # 组合结果并验证
    sorted_corners = [top_points[0], top_points[1], bottom_points[0], bottom_points[1]]

    # 二次验证左上角点
    if sorted_corners[0][1] > sorted_corners[1][1] + 5:
        sorted_corners[0], sorted_corners[1] = sorted_corners[1], sorted_corners[0]

    return sorted_corners


try:

    sensor = Sensor(id = sensor_id) #构建摄像头对象
    sensor.reset() #复位和初始化摄像头
    sensor.set_framesize(width = picture_width, height = picture_height) #设置帧大小为LCD分辨率()，默认通道0    （显示画面的大小）一般小
    sensor.set_pixformat(Sensor.RGB565) #设置输出图像格式，默认通道0

    Display.init(Display.VIRT, width = DISPLAY_WIDTH, height = DISPLAY_HEIGHT) #只使用IDE缓冲区显示图像      （画面大小）一般大

    MediaManager.init() #初始化media资源管理器

    sensor.run() #启动sensor

    clock = time.clock()

    while True:
        os.exitpoint()  # 退出点，用于调试
        img = sensor.snapshot(chn = CAM_CHN_ID_0)  # 从摄像头通道0获取一帧图像
        # img_rect = img.to_grayscale(copy = True)    #灰度图
        # img_rect = img_rect.binary([rect_binart])   #二制化

        #接收数据包0X“55 XX FF FF FF”
        Rxbuf = bytearray(5)
        Rx_NumBytes = uart2.readinto(Rxbuf, 5)
        if Rx_NumBytes is not None and Rx_NumBytes == 5:
            if (Rxbuf[0] == 0x55 and Rxbuf[2] == 0xFF and Rxbuf[3] == 0xFF):
                if(Rxbuf[1] == 0x01):
                    Situation = 1
                    print("校准激光")
                elif(Rxbuf[1] == 0x02):
                    Situation = 2
                    print("识别矩形")

        # --- 状态定义 ---
        STATE_INITIAL_RESET = 1 # 初始复位状态
        STATE_DETECT_TARGET = 0 # 检测目标状态
        STATE_CONFIRM_TARGET = 2 # 确认目标状态
        #TATE_TRACING = 3        # 追踪目标状态
        #STATE_FINISH = 4         # 完成状态

        """2.定位5个铅笔矩形坐标点"""
        if Situation == 0:
            if state == STATE_INITIAL_RESET:
                img.draw_string_advanced(0, 0, 20,"TAST:1", color=(0, 0, 0))
                blobs = img.find_blobs(RED_THRESHOLD)
                if blobs:
                    pixel = []
                    for B in blobs:
                        pixel.append(B.pixels())
                    max_index = pixel.index(max(pixel))
                    B = blobs[max_index]
                    img.draw_rectangle(B[0:4])
                    img.draw_cross(B[5], B[6])
                #定义按键，通过按键计入激光点的坐标
                    if KEY.value() == 1:
                        time.sleep_ms(100)
                        if KEY.value() == 1 and len(pencil_points) < 5:
                            blobs = img.find_blobs(RED_THRESHOLD)
                            if blobs:
                                pixel = []
                                for B in blobs:
                                    pixel.append(B.pixels())
                                max_index = pixel.index(max(pixel))
                                B = blobs[max_index]
                                img.draw_rectangle(B[0:4])
                                img.draw_cross(B[5], B[6])
                                pencil_points.append([B[5], B[6]])
                                print(f"已记录第{len(pencil_points)}个点坐标:", B[5], B[6])
                                # 显示已记录的点
                            else:
                                print("未检测到激光点")
                        elif len(pencil_points) >= 5:
                            print("已记录5个点，切换到追踪模式")
                            send_five_points(pencil_points)  # 发送5个点
                            state = STATE_DETECT_TARGET  # 切换到检测目标状态
                            frame1 = send_five_points(pencil_points)  # 发送5个点
                            print("串口数据:", ' '.join(f'{byte:02X}' for byte in frame1))
                    for i in range(len(pencil_points)):
                        img.draw_cross(pencil_points[i][0], pencil_points[i][1])

            elif state == STATE_DETECT_TARGET:
                img.draw_string_advanced(0, 0, 20,"TAST:2", color=(0, 0, 0))
                # 清除之前的轨迹
                if 'prev_laser_pos' not in locals():
                    prev_laser_pos = None
                # 获取新帧
                img = sensor.snapshot(chn = CAM_CHN_ID_0)
                # 绘制已记录的参考点
                for i, (x, y) in enumerate(pencil_points):
                    img.draw_cross(x, y, color=(0, 255, 0))
                    img.draw_string_advanced(x+10, y, 12, f"P{i+1}", color=(0, 255, 0))
                blobs = img.find_blobs(RED_THRESHOLD)  # 重新检测色块
                if blobs:
                    pixel = []
                    for B in blobs:
                        pixel.append(B.pixels())
                    max_index = pixel.index(max(pixel))
                    B = blobs[max_index]
                    img.draw_rectangle(B[0:4])
                    img.draw_cross(B[5], B[6])

                    time.sleep_ms(10)
                    laser_x = B.x() + round(B.w()/2)
                    laser_y = B.y() + round(B.h()/2)
                    frame = send_data(laser_x, laser_y)
                    print("发送坐标:", laser_x, laser_y)
                    print("串口数据:", ' '.join(f'{byte:02X}' for byte in frame))

        #矩形识别
        if Situation == 2:
            # 查找线段并绘制
            img_rect = img.to_grayscale(copy=True)
            img_rect.gaussian(1)  # 添加高斯模糊降噪
            img_rect.binary([(60, 192)])
            rects = img_rect.find_rects()
            count = 0  # 初始化线段计数器

            # 计算矩形面积的辅助函数
            def get_rect_area(rect):
                corners = rect.corners()
                min_x = min(p[0] for p in corners)
                max_x = max(p[0] for p in corners)
                min_y = min(p[1] for p in corners)
                max_y = max(p[1] for p in corners)
                return (max_x - min_x) * (max_y - min_y)

            # 按面积排序并取前两个最大矩形
            sorted_rects = sorted(rects, key=get_rect_area, reverse=True)[:2]
            print("------矩形检测结果------")

            if len(sorted_rects) >= 2:
                # 确定外框和内框
                rect1, rect2 = sorted_rects
                area1, area2 = get_rect_area(rect1), get_rect_area(rect2)
                outer_rect = rect1 if area1 > area2 else rect2
                inner_rect = rect2 if area1 > area2 else rect1

                # 判断内框是否在外框内部的辅助函数
                def is_inside(inner, outer):
                    inner_corners = inner.corners()
                    outer_corners = outer.corners()
                    o_min_x, o_max_x = min(p[0] for p in outer_corners), max(p[0] for p in outer_corners)
                    o_min_y, o_max_y = min(p[1] for p in outer_corners), max(p[1] for p in outer_corners)
                    return all(o_min_x <= x <= o_max_x and o_min_y <= y <= o_max_y for x, y in inner_corners)

                # 对矩形顶点进行排序的函数（顺时针方向，从左上角开始）
                def sort_corners(corners):
                    # 计算中心点
                    center = (sum(p[0] for p in corners)/4, sum(p[1] for p in corners)/4)
                    # 根据与中心点的角度排序
                    corners_with_angle = []
                    for (x, y) in corners:
                        angle = math.atan2(y - center[1], x - center[0])
                        corners_with_angle.append((x, y, angle))
                    # 按角度排序（顺时针）
                    corners_with_angle.sort(key=lambda c: c[2])
                    # 返回排序后的顶点坐标
                    return [(c[0], c[1]) for c in corners_with_angle]

                # 检查内框是否在外框内部
                if is_inside(inner_rect, outer_rect):
                    # 获取并排序外框顶点
                    outer_corners = outer_rect.corners()
                    outer_corners = sort_corners(outer_corners)
                    # 绘制外框（红色）
                    for i in range(4):
                        img.draw_line(outer_corners[i][0], outer_corners[i][1], outer_corners[(i+1)%4][0], outer_corners[(i+1)%4][1], color=(255,0,0), thickness=2)

                    # 打印外框四个端点坐标
                    print("外框顶点坐标:")
                    for i, (x, y) in enumerate(outer_corners):
                        print(f"顶点{i+1}: ({x}, {y})")

                    # 绘制内框（绿色）
                    inner_corners = inner_rect.corners()
                    inner_corners = sort_corners(inner_corners)
                    # 绘制内框（绿色）
                    for i in range(4):
                        img.draw_line(inner_corners[i][0], inner_corners[i][1], inner_corners[(i+1)%4][0], inner_corners[(i+1)%4][1], color=(0,255,0), thickness=2)
                    print(f"外框面积: {get_rect_area(outer_rect)}, 内框面积: {get_rect_area(inner_rect)}")

                    # 打印内框四个端点坐标
                    print("内框顶点坐标:")
                    for i, (x, y) in enumerate(inner_corners):
                        print(f"顶点{i+1}: ({x}, {y})")

                    # 计算中间矩形四个顶点（内外框对应端点的中点）
                        # 计算对应顶点的中点坐标
                        middle_corners = [
                            [int((oc[0] + ic[0])/2), int((oc[1] + ic[1])/2)]
                            for oc, ic in zip(outer_corners, inner_corners)
                        ]

                        # 绘制中间矩形（蓝色）
                        for i in range(4):
                            img.draw_line(*middle_corners[i], *middle_corners[(i+1)%4],
                                        color=(0, 0, 255), thickness=2)

                    # 打印中间矩形四个端点坐标
                    print("中间矩形顶点坐标:")
                    for i, (x, y) in enumerate(middle_corners):
                        print(f"顶点{i+1}: ({x}, {y})")
                else:
                    print("警告: 小矩形不在大矩形内部，不绘制矩形")
            print("---------END---------")

        """4.激光追踪"""
        if state == 4:
            img.draw_string_advanced(0, 0, 20,"TAST:4", color=(0, 0, 0))
            tracking_complete = False
            start_time = time.time()

            while time.time() - start_time < 2 and not tracking_complete:
                img = sensor.snapshot(chn=CAM_CHN_ID_0)

                # 检测红色光斑
                red_blobs = img.find_blobs(Red_thresholds)
                red_blob = max(red_blobs, key=lambda b: b.pixels()) if red_blobs else None

                # 检测绿色光斑
                green_blobs = img.find_blobs(Green_thresholds)
                green_blob = max(green_blobs, key=lambda b: b.pixels()) if green_blobs else None

                if red_blob and green_blob:
                    # 确保光斑面积足够大，过滤噪声
                    if red_blob.pixels() < 5 or green_blob.pixels() < 5:
                        print("光斑面积过小，可能为噪声")
                        continue
                    # 获取中心坐标
                    red_x, red_y = red_blob.cx(), red_blob.cy()
                    green_x, green_y = green_blob.cx(), green_blob.cy()

                    # 计算距离 (像素)
                    distance = math.sqrt((red_x - green_x)**2 + (red_y - green_y)** 2)

                    # 像素转厘米 (根据实际校准，此处为示例值)
                    # 校准方法: 测量实际10cm距离对应的像素数，更新以下比例
                    PIXEL_PER_CM = 10.0  # 校准值：1cm = 10像素 (根据实际情况调整)
                    distance_cm = distance / PIXEL_PER_CM       #（我觉得并不标准）

                    # 绘制光斑和距离
                    img.draw_cross(red_x, red_y, color=(255, 0, 0))
                    img.draw_cross(green_x, green_y, color=(0, 255, 0))
                    img.draw_line(red_x, red_y, green_x, green_y, color=(255, 255, 0))
                    img.draw_string_advanced(10, 30, 16, f"距离:{distance_cm:.1f}cm", color=(0,0,0))

                    if distance_cm > 3:
                        # 简单比例控制
                        move_x = int((red_x - green_x) * 0.5)
                        move_y = int((red_y - green_y) * 0.5)
                        new_green_x = green_x + move_x
                        new_green_y = green_y + move_y
                        # 限制最大移动速度，避免超调
                        max_step = 20  # 最大单步移动像素
                        move_x = max(-max_step, min(max_step, move_x))
                        move_y = max(-max_step, min(max_step, move_y))
                        new_green_x = green_x + move_x
                        new_green_y = green_y + move_y
                        # 使用uart2发送数据（修复端口错误）
                        send_target_data(new_green_x, new_green_y)
                    else:
                        tracking_complete = True

                Display.show_image(img, x=int((DISPLAY_WIDTH - picture_width)/2), y=int((DISPLAY_HEIGHT - picture_height)/2))
                time.sleep_ms(50)

            if tracking_complete:
                print("追踪完成: 距离≤3cm")
                beep_pwm.freq(1000)
                beep_pwm.enable(True)
                time.sleep_ms(100)
                beep_pwm.enable(False)
            else:
                print("追踪超时")

        # """串口发送"""
        # if (state == 1 or state == 2 or state == 3):
        #     # 发送数据
        #     if state == 1:
        #         # 发送所有点数据，使用统一的二进制格式
        #         for p in pencil_points:
        #             send_data(p[0], p[1])
        #         print(f"已发送数据: 状态={state}, 点数量={len(pencil_points)}")

        #     elif state == 2:
        #         # 使用统一的二进制格式发送激光点坐标
        #         send_data(laser_x, laser_y)
        #         print(f"发送数据: 状态={state}, X={laser_x}, Y={laser_y}")

        #     elif state == 3:
        #         # 使用统一的二进制格式发送矩形角点坐标
        #         for corner in target_rect_corners:
        #             send_data(corner[0], corner[1])
        #         print(f"发送数据: 状态={state}, 角点数量={len(target_rect_corners)}")

        #img = img.copy(roi = (200, 56, 432, 336))
        Display.show_image(img, x = int((DISPLAY_WIDTH - picture_width) / 2), y = int((DISPLAY_HEIGHT - picture_height) / 2))


###################
# IDE中断释放资源代码
###################
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






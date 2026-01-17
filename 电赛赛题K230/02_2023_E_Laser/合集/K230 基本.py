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

sensor_id = 2
picture_width = 800
picture_height = 480
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

# 颜色识别阈值 (L Min, L Max, A Min, A Max, B Min, B Max) LAB模型
# 下面的阈值元组是用来识别 红、绿、蓝三种颜色，当然你也可以调整让识别变得更好。
RED_THRESHOLD = [(71, 100, 3, 49, -10, 18), (64, 94, 11, 55, -26, 46), (56, 85, 21, 55, -2, 28)] # 红色阈值
Green_thresholds = (30, 100, -64, -8, 50, 70)  # 绿色阈值（移除多余逗号）
laser_threshold = (73, 100, -21, 58, -18, 25) # 激光阈值
rect_binart = (87, 183)

state = 0     #识别状态
pencil_points = []  # 空列表  # 初始化5个点  #记入铅笔矩形坐标5个点
# 设置追踪阈值
TRACKING_THRESHOLD = 10  # 像素
# 定义激光位置
laser_x = 0
laser_y = 0
frame = 0

fpioa = FPIOA()
fpioa.help()
# 初始化UART2
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart2 = UART(UART.UART2, 115200)

# 配置蜂鸣器IO口功能
fpioa.set_function(43, FPIOA.PWM1)
# 初始化蜂鸣器PWM通道
beep_pwm = PWM(1, 4000, 50, enable=False)  # 默认频率4kHz,占空比50%

# 创建按键对象，用于触发图像采集
fpioa.set_function(53, FPIOA.GPIO53)  # 设置GPIO53功能
KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)  # GPIO53作为输入引脚，下拉模式

# 发送目标位置数据的函数
# 参数x,y: 目标位置的x和y坐标值


def send_data(x, y, x1, y1):
    # 使用struct.pack构建数据包
    frame = b'\xAA' + struct.pack('<BHHHH', 0, x, y, x1, y1) + b'\x55'
    n = 0  # 计数器，用于记录发送次数
    for i in range(4):
        uart2.write(frame)
        time.sleep_ms(6)  # 合并延时，保持总时长不变
        n += 1  # 更新发送计数器
    return frame  # 返回构建的frame


def send_five_points(points):
    """
    points: 列表，包含5个[x, y]，如 [[x1, y1], [x2, y2], ..., [x5, y5]]
    """
    import struct
    if len(points) != 5:
        print("点数量不足5个，无法发送")
        return
    # 展开所有点
    data = []
    for pt in points:
        data.extend(pt)  # [x1, y1, x2, y2, ...]
    # '<'表示小端，10H表示10个unsigned short
    frame = b'\xAA' + struct.pack('<10H', *data) + b'\x55'
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
        img_rect = img.to_grayscale(copy = True)    #灰度图
        img_rect = img_rect.binary([rect_binart])   #二制化

        # --- 状态定义 ---
        STATE_INITIAL_RESET = 0  # 初始复位状态
        STATE_DETECT_TARGET = 1  # 检测目标状态
        # STATE_CONFIRM_TARGET = 2 # 确认目标状态
        # STATE_TRACING = 3        # 追踪目标状态
        # STATE_FINISH = 4         # 完成状态

        """2.定位5个铅笔矩形坐标点"""
        if state == 0:
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
                    elif len(pencil_points) >= 1:
                        print("已记录5个点，切换到追踪模式")
                        send_five_points(pencil_points)  # 发送5个点
                        state = STATE_DETECT_TARGET  # 切换到检测目标状态
            for i in range(len(pencil_points)):
                img.draw_cross(pencil_points[i][0], pencil_points[i][1])


        elif state == 1:
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
            blobs = img.find_blobs(RED_THRESHOLD)  # 重新检测色块 （可添加阈值，识别不同颜色）
            if blobs:
                pixel = []
                for B in blobs:
                    pixel.append(B.pixels())
                max_index = pixel.index(max(pixel))
                B = blobs[max_index]
                img.draw_rectangle(B[0:4])
                img.draw_cross(B[5], B[6])
                #C=img.get_pixel(B[5], B[6])  # 获取中心点像素颜色值

                time.sleep_ms(10)  # 添加短暂延迟避免连续发送
                laser_x = B.x() + round(B.w()/2)
                laser_y = B.y() + round(B.h()/2)
                frame = send_data(pencil_points[0][0], pencil_points[0][1], laser_x, laser_y)
                print("发送坐标:", pencil_points[0][0], pencil_points[0][1], laser_x, laser_y)
                print("串口数据:", ' '.join(f'{byte:02X}' for byte in frame))


        target_rect_corners = []
        """3.寻找矩形"""
        if state == 3:
            img.draw_string_advanced(0, 0, 20,"TAST:3", color=(0, 0, 0))
            count = 0  # 初始化矩形计数器
            rects = img_rect.find_rects(threshold = 10000)
            # 筛选面积最大的两个矩形
            largest_rects = find_largest_rects(rects, count=2)
            detected_rects = []
            rect1_corners = []
            rect2_corners = []
            print("------矩形统计开始------")

            # 处理第一个矩形
            if len(largest_rects) >= 1:
                rect1 = largest_rects[0]
                rect1_corners = sort_rect_corners(rect1.corners())
                detected_rects.append(rect1_corners)
                print(f"矩形1角点(已排序): {rect1_corners}")
                # 绘制第一个矩形
                img.draw_line(rect1_corners[0][0], rect1_corners[0][1], rect1_corners[1][0], rect1_corners[1][1], color=(255, 0, 0), thickness=2)
                img.draw_line(rect1_corners[1][0], rect1_corners[1][1], rect1_corners[2][0], rect1_corners[2][1], color=(255, 0, 0), thickness=2)
                img.draw_line(rect1_corners[2][0], rect1_corners[2][1], rect1_corners[3][0], rect1_corners[3][1], color=(255, 0, 0), thickness=2)
                img.draw_line(rect1_corners[3][0], rect1_corners[3][1], rect1_corners[0][0], rect1_corners[0][1], color=(255, 0, 0), thickness=2)

            # 处理第二个矩形
            if len(largest_rects) >= 2:
                rect2 = largest_rects[1]
                rect2_corners = sort_rect_corners(rect2.corners())
                detected_rects.append(rect2_corners)
                print(f"矩形2角点(已排序): {rect2_corners}")
                # 绘制第二个矩形
                img.draw_line(rect2_corners[0][0], rect2_corners[0][1], rect2_corners[1][0], rect2_corners[1][1], color=(0, 0, 255), thickness=2)
                img.draw_line(rect2_corners[1][0], rect2_corners[1][1], rect2_corners[2][0], rect2_corners[2][1], color=(0, 0, 255), thickness=2)
                img.draw_line(rect2_corners[2][0], rect2_corners[2][1], rect2_corners[3][0], rect2_corners[3][1], color=(0, 0, 255), thickness=2)
                img.draw_line(rect2_corners[3][0], rect2_corners[3][1], rect2_corners[0][0], rect2_corners[0][1], color=(0, 0, 255), thickness=2)

            count = len(detected_rects)
            print(f"共检测到{count}个有效矩形")

            if count >= 2 and len(rect1_corners) == 4 and len(rect2_corners) == 4:
                    # 计算两个矩形对应角点的中点作为目标矩形角点
                    target_rect_corners = []
                    for i in range(4):
                        # 计算x坐标中点
                        mid_x = int((rect1_corners[i][0] + rect2_corners[i][0]) / 2)
                        # 计算y坐标中点
                        mid_y = int((rect1_corners[i][1] + rect2_corners[i][1]) / 2)
                        target_rect_corners.append([mid_x, mid_y])

                    #计算目标矩形4个点
                    # 计算目标矩形四个角点（取两个矩形对应角点的中点）
                    target_rect_corners[0][0] = int((rect1_corners[0][0] + rect2_corners[0][0]) / 2)
                    target_rect_corners[0][1] = int((rect1_corners[0][1] + rect2_corners[0][1]) / 2)

                    target_rect_corners[1][0] = int((rect1_corners[1][0] + rect2_corners[1][0]) / 2)
                    target_rect_corners[1][1] = int((rect1_corners[1][1] + rect2_corners[1][1]) / 2)

                    target_rect_corners[2][0] = int((rect1_corners[2][0] + rect2_corners[2][0]) / 2)
                    target_rect_corners[2][1] = int((rect1_corners[2][1] + rect2_corners[2][1]) / 2)

                    target_rect_corners[3][0] = int((rect1_corners[3][0] + rect2_corners[3][0]) / 2)
                    target_rect_corners[3][1] = int((rect1_corners[3][1] + rect2_corners[3][1]) / 2)
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
                    PIXEL_PER_CM = 12.5  # 示例值：1cm = 12.5像素
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






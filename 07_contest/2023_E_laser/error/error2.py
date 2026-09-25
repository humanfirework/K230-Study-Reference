import gc
import os
import sys
import time
import math

# 原代码使用通配符导入 math 库所有内容，现根据需求按需导入
from math import *
from media.sensor import * #导入sensor模块，使用摄像头相关接口
from media.display import * #导入display模块，使用display相关接口
from media.media import * #导入media模块，使用meida相关接口

from machine import FPIOA
from machine import Pin
from machine import UART
from machine import PWM

# 颜色识别阈值 (L Min, L Max, A Min, A Max, B Min, B Max) LAB模型
# 下面的阈值元组是用来识别 红、绿、蓝三种颜色，当然你也可以调整让识别变得更好。
Red_thresholds = (29, 45, 4, 31, -5, 17), # 红色阈值
Green_thresholds = (30, 100, -64, -8, 50, 70), # 绿色阈值
Blue_thresholds = (0, 40, 0, 90, -128, -20) # 蓝色阈值
laser_threshold = (29, 45, 4, 31, -5, 17) # 激光阈值

state = 0     #识别状态
pencil_points = []  # 空列表  # 初始化5个点  #记入铅笔矩形坐标5个点
# 设置追踪阈值
TRACKING_THRESHOLD = 10  # 像素
# 定义激光位置
laser_x = 0
laser_y = 0
# 在检测到激光点后记录
red_history = []
green_history = []


# 定义激光状态
laser_detected = False
# 定义追踪状态
tracking = False

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

#可以写在32上来解析数据包，发送可以按照这个格式写（问题：还不熟悉将数据填入列表，数组或元组之中）
def Receive_date():
    data = uart2.read()
    if data:
        print(data)
        # 解析数据
        if data.startswith("P"):
            # 解析点的索引
            point_index = int(data[1])
            # 解析X坐标
            x_start = data.index("X") + 1           #在 data 列表中查找"X"的位置索引并加1
            x_end = data.index("Y")                 #在 data 列表中查找"Y"的位置索引这通常用于从类似"X123Y456"这样的字符串中提取"X"和"Y"之间的内容(123)
            x_value = int(data[x_start:x_end])      #显示x坐标
            # 解析Y坐标
            y_start = data.index("Y") + 1           #在 data 列表中查找"Y"的位置索引并加1
            y_end = data.index("\r")                #“\r“的位置为结束符”
            y_value = int(data[y_start:y_end])
            # 更新点的位置

# 发送目标位置数据的函数
# 参数x,y: 目标位置的x和y坐标值
def send_target_data(x,y):
    n = 0  # 计数器，用于记录发送次数
    # 循环4次发送数据，提高传输可靠性
    for i in range(4):
        # 将x坐标分解为高8位和低8位
        x_h = (x>>8)&0xFF  # 取x的高8位
        x_l = x&0xFF       # 取x的低8位

        # 将y坐标分解为高8位和低8位
        y_h = (y>>8)&0xFF  # 取y的高8位
        y_l = y&0xFF       # 取y的低8位

        # 发送x坐标数据包
        # 数据包格式: [0x55, 0xaa, 0x00, x_h, x_l, 0xfa]
        # 0x55 0xaa: 数据包头
        # 0xff: 表示这是x坐标数据
        # x_h, x_l: x坐标的高低位
        # 0xfa: 数据包尾
        uart2.write(bytearray([0x55, 0xaa, 0x00, int(x_h)&0xFF, int(x_l)&0xFF, 0xfa]))

        time.sleep_ms(5)  # 短暂延时，防止数据冲突
        n += 1  # 计数器递增

        # 发送y坐标数据包
        # 数据包格式: [0x55, 0xaa, 0xff, y_h, y_l, 0xfa]
        # 0x00: 表示这是y坐标数据
        uart2.write(bytearray([0x55, 0xaa, 0xff, int(y_h)&0xFF, int(y_l)&0xFF, 0xfa]))

        time.sleep_ms(5)  # 短暂延时
        n += 1  # 计数器递增

#最大矩形
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

# 寻找最大色块面积的函数
def find_max_blob(blobs):
    # 对色块列表按照周长进行降序排序
    # 使用lambda函数获取每个色块的周长作为排序依据
    blobs.sort(key=lambda x:x.perimeter(),reverse=True);
    # # 初始化一个空字典用于存储最大色块信息
    max_value={}
    # # 获取排序后的第一个色块(周长最大的色块)
    max_value=blobs[0];
    # # 返回最大色块
    return max_value;


try:

    sensor = Sensor(width=640, height=480) #构建摄像头对象
    sensor.reset() #复位和初始化摄像头
    sensor.set_framesize(width=640, height=480) #设置帧大小为LCD分辨率(640x480)，默认通道0
    sensor.set_pixformat(Sensor.RGB565) #设置输出图像格式，默认通道0

    Display.init(Display.VIRT, sensor.width(), sensor.height()) #只使用IDE缓冲区显示图像

    MediaManager.init() #初始化media资源管理器

    sensor.run() #启动sensor

    clock = time.clock()

    rect_binart = (0, 20, -11, 5, -4, 10)
    while True:
        os.exitpoint()  # 退出点，用于调试
        img = sensor.snapshot(chn = CAM_CHN_ID_0)  # 从摄像头通道0获取一帧图像

        """
        1.串口接收（可以直接写uart2.read()接收消息）
        例如：
        data = uart2.read()
        if data == b'1':  # 接收到'1'时持续发送
        """
        #接收数据包0X“55 XX FF FF FF”
        Rxbuf = bytearray(5)
        Rx_NumBytes = uart2.readinto(Rxbuf, 5);
        if Rx_NumBytes is not None and Rx_NumBytes == 5:
            if (Rxbuf[0] == 0x55 and Rxbuf[2] == 0xFF and Rxbuf[3] == 0xFF and Rxbuf[4] == 0xFF):
                if(Rxbuf[1] == 0x01):
                    state = 1
                    print("任务1.寻找单点")
                elif(Rxbuf[1] == 0x02):
                    state = 2
                    print("任务2.四点顺序追踪")
                elif(Rxbuf[1] == 0x03):
                    state = 3
                    print("任务3.矩形轮廓追踪")
                elif(Rxbuf[1] == 0x04):
                    state = 4
                    print("任务4.识别激光")

                elif(Rxbuf[1] == 0x08):
                    state = 5
                    print("任务8.定位5个铅笔矩形坐标点")
                elif(Rxbuf[1] == 0x00):
                    state = 0
                    print("停止")

        img = sensor.snapshot(chn = CAM_CHN_ID_0)
        #灰度图
        img_rect = img.to_grayscale(copy = True)
        #二制化
        img_rect = img_rect.binary([rect_binart])
        B = []
        cx = 0
        cy = 0
        err_dx = 0
        err_dy = 0
        # 在图像中寻找红色阈值范围内的色块
        blobs = img.find_blobs(Red_thresholds)
        if blobs:
            pixel = []
            for B in blobs:
                pixel.append(B.pixels())
            max_index = pixel.index(max(pixel))
            B = blobs[max_index]
            img.draw_rectangle(B[0:4])
            img.draw_cross(B[5], B[6])
            cx = B[0] + int(B[2] / 2)
            cy = B[1] + int(B[3] / 2)

        """任务1.寻找单点"""
        if state == 1:
            img.draw_string_advanced(0, 0, "TASK:1")
            for i in range(len(pencil_points)):
                img.draw_cross(pencil_points[i][0], pencil_points[i][1], size = 5, color = (255,255,255))
            if B:
                err_dx = cx - pencil_points[0][0]
                err_dy = cy - pencil_points[0][1]
                if abs(err_dx) < 1 and abs(err_dy) < 1:
                    print("定位成功")


        # """任务2.四点顺序追踪"""
        # if state == 2:
        #     img.draw_string_advanced(0, 0, "TASK:2")
        #     for i in range(len(pencil_points)):
        #         img.draw_cross(pencil_points[i][0], pencil_points[i][1], size = 5, color = (255,255,255))
        #     points = (pencil_points[1], pencil_points[2], pencil_points[3], pencil_points[4], pencil_points[0])


        """任务3.矩形轮廓追踪"""
        # 在全局作用域声明变量
        flag_find_first_rect = False
        flag_find_second_rect = False
        first_rect_corners = [[0,0] for _ in range(4)]
        second_rect_corners =[[0,0] for _ in range(4)]
        target_rect_corners = [[0,0] for _ in range(4)]
        show_first_rect = False
        show_second_rect = False
        show_target_rect = True
        found_rect = 0
        send_state = 0

        if state == 3:
            img.draw_string_advanced(0, 0, "TASK:3", size = 3, color=(0, 0, 0), scale=2)
            # 配置黑色矩形检测参数
            rect_threshold = 50000  # 调整阈值以匹配黑色矩形大小
            x_gradient = 5
            y_gradient = 5
            min_area = 10000       # 最小面积过滤
            max_area = 100000      # 最大面积过滤
            found_black_rect = False
            target_rect_corners = []

            # 预处理：转换为灰度图并增强对比度以突出黑色矩形
            img_gray = img.to_grayscale()
            img_gray = img_gray.contrast(2.0)
            # 二值化处理，只保留黑色区域
            img_binary = img_gray.binary([(0, 50)])  # 黑色阈值 (0-50)

            # 寻找矩形轮廓
            for rect in img_binary.find_rects(threshold=rect_threshold, x_gradient=x_gradient, y_gradient=y_gradient):
                area = rect.magnitude()
                # 面积过滤，排除过小或过大的矩形
                if min_area < area < max_area:
                    # 获取矩形四个角点
                    target_rect_corners = rect.corners()
                    found_black_rect = True
                    print(f"找到黑色矩形，面积: {area}")
                    print(f"矩形顶点: {target_rect_corners}")
                    break  # 找到一个合适的矩形后停止搜索

            # 如果找到矩形，绘制并发送顶点坐标
            if found_black_rect and len(target_rect_corners) == 4:
                # 绘制矩形边框
                img.draw_line(target_rect_corners[0][0], target_rect_corners[0][1], target_rect_corners[1][0], target_rect_corners[1][1], color=(0, 255, 0))
                img.draw_line(target_rect_corners[1][0], target_rect_corners[1][1], target_rect_corners[2][0], target_rect_corners[2][1], color=(0, 255, 0))
                img.draw_line(target_rect_corners[2][0], target_rect_corners[2][1], target_rect_corners[3][0], target_rect_corners[3][1], color=(0, 255, 0))
                img.draw_line(target_rect_corners[3][0], target_rect_corners[3][1], target_rect_corners[0][0], target_rect_corners[0][1], color=(0, 255, 0))

                # 绘制四个顶点（不同颜色标记顺序）
                colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]  # 红、绿、蓝、黄
                for i, p in enumerate(target_rect_corners):
                    img.draw_circle(p[0], p[1], 5, color=colors[i], fill=True)
                    img.draw_string_advanced(p[0]+10, p[1], f"P{i+1}", color=colors[i])

                # 顶点排序：确保按顺时针顺序排列（左上→右上→右下→左下）
                # 计算中心点
                cx = sum(p[0] for p in target_rect_corners) / 4
                cy = sum(p[1] for p in target_rect_corners) / 4
                # 计算各点与中心点的角度并排序
                def sort_corners(points, cx, cy):
                    return sorted(points, key=lambda p: math.atan2(p[1]-cy, p[0]-cx))
                target_rect_corners = sort_corners(target_rect_corners, cx, cy)
                # 按顺序存储四个顶点坐标
                pencil_points = target_rect_corners
                
                # 串口发送四个顶点坐标
                data = "!4"
                for i, (x, y) in enumerate(target_rect_corners):
                    data += f"X{x}Y{y}"
                data += "@"
                uart2.write(data)
                print(f"发送矩形顶点数据: {data}")
            else:
                img.draw_string_advanced(10, 30, "未检测到黑色矩形", color=(255, 0, 0))

                    # 控制数据发送频率，每10帧发送一次目标矩形数据


        #识别激光
        if state == 4:   # 接收到‘4’时持续发送
            img = sensor.snapshot(chn = CAM_CHN_ID_0)  # 每次循环都获取新帧
            blobs = img.find_blobs(Red_thresholds)  # 重新检测色块 （可添加阈值，识别不同颜色）
            if blobs:
                pixel = []
                for B in blobs:
                    pixel.append(B.pixels())
                max_index = pixel.index(max(pixel))
                B = blobs[max_index]
                img.draw_rectangle(B[0:4])
                img.draw_cross(B[5], B[6])
                #C=img.get_pixel(B[5], B[6])  # 获取中心点像素颜色值

                Display.show_image(img)
                time.sleep_ms(10)  # 添加短暂延迟避免连续发送
                laser_x = B.x() + round(B.w()/2)
                laser_y = B.y() + round(B.h()/2)

        """任务8.定位5个铅笔矩形坐标点"""
        if state == 8:
            img.draw_string_advanced(0, 0, "TASK:8", size = 3, color=(0, 0, 0), scale=2)
            blobs = img.find_blobs([laser_threshold])
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
                time.sleep_ms(100)  #庐山派没有消抖按键，后面可根据需要调整
                if KEY.value() == 1 and len(pencil_points) < 5:
                    blobs = img.find_blobs([laser_threshold])
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
                        # 发送标记点位置

                    else:
                        print("未检测到激光点")
                elif len(pencil_points) >= 5:
                    print("已记录5个点，请停止采集")
            #在图像上绘制5个点并存入pencil_points
            for i in range(len(pencil_points)):
                img.draw_cross(pencil_points[i][0], pencil_points[i][1], size = 5, color = (255,255,255))

        """串口发送"""
        if (state == 1 or state == 2 or state == 3, state == 8):
            # 发送数据
            if state == 1:
                uart2.write('!' + 'X' + str(err_dx) + 'Y' + str(err_dy) + '@')
                print(f"发送数据: 状态={state}, X={err_dx}, Y={err_dy}")
            elif state == 2:
                uart2.write('!' + str() + ',' + str() + '@')
                print(f"发送数据: 状态={}, X={}, Y={}")

            elif state == 3:
                data = "!" + str(len(target_rect_corners))
                for corner in target_rect_corners:
                    data += "X" + str(corner[0]) + "Y" + str(corner[1])
                data += "@"
                uart2.write(data)
                print(f"发送数据: 状态={state}, 数据={data}")

            elif state == 8:
                # 发送所有点数据，格式为: !数量X1Y1X2Y2...XnYn@
                data = "!" + str(len(pencil_points))
                for point in pencil_points:
                    data += "X" + str(point[0]) + "Y" + str(point[1])
                data += "@"
                uart2.write(data)
                print(f"发送数据: 状态={state}, 数据={data}")

        Display.show_image(img)


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



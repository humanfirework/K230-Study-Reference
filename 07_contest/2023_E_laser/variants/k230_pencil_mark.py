import gc
import os
import sys
import time
import math

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
Red_thresholds = (72, 99, -6, 46, -40, 25) # 红色阈值
Green_thresholds = (30, 100, -64, -8, 50, 70)  # 绿色阈值（移除多余逗号）
Blue_thresholds = (0, 40, 0, 90, -128, -20) # 蓝色阈值
laser_threshold = (73, 100, -21, 58, -18, 25) # 激光阈值

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
        # 数据包格式: [0x55, 0xaa, 0xff, x_h, x_l, 0xfa]
        # 0x55 0xaa: 数据包头
        # 0xff: 表示这是x坐标数据
        # x_h, x_l: x坐标的高低位
        # 0xfa: 数据包尾
        uart.write(bytearray([0x55, 0xaa, 0xff, int(x_h)&0xFF, int(x_l)&0xFF, 0xfa]))

        time.sleep_ms(3)  # 短暂延时，防止数据冲突
        n += 1  # 计数器递增

        # 发送y坐标数据包
        # 数据包格式: [0x55, 0xaa, 0x00, y_h, y_l, 0xfa]
        # 0x00: 表示这是y坐标数据
        uart.write(bytearray([0x55, 0xaa, 0x00, int(y_h)&0xFF, int(y_l)&0xFF, 0xfa]))

        time.sleep_ms(3)  # 短暂延时
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
# 参数blobs: 检测到的所有色块列表
def find_max_blob(blobs):
    # 对色块列表按照周长进行降序排序
    # 使用lambda函数获取每个色块的周长作为排序依据
    blobs.sort(key=lambda x:x.perimeter(),reverse=True);

    # 初始化一个空字典用于存储最大色块信息
    max_value={}

    # 获取排序后的第一个色块(周长最大的色块)
    max_value=blobs[0];

    # 返回最大色块
    return max_value;

#使用激光在铅笔方框的4个顶点和中心点
def laser_calibration():
    loop = True
    while loop:
        img = sensor.snapshot()
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
            if len(pencil_points) < 5:
                if KEY.value() == 1:
                    if KEY.value() == 1:
                        time.sleep_ms(100)  # 消抖
                        if KEY.value() == 1:  # 确认按钮按下
                            pencil_points.append([blobs[0].x(), blobs[0].y()])
                            print("激光点坐标：", blobs[0].x(), blobs[0].y())


            else:   #等待5个数据输入完成
                loop = False
        #在图像上画出5个点的位置
            for n in range(len(pencil_points)):
                img.draw_cross(pencil_points[n][0], pencil_points[n][1], color=(255, 255, 255))
                img.draw_string_advanced(pencil_points[n][0], pencil_points[n][1], str(n), color=(255, 255, 255))
                # 发送数据
                uart2.write("P" + str(n) + "X" + str(pencil_points[n][0]) + "Y" + str(pencil_points[n][1]) + "\r\n")
        Display.show_image(img)


try:

    sensor = Sensor() #构建摄像头对象
    sensor.reset() #复位和初始化摄像头
    sensor.set_framesize(width=800, height=480) #设置帧大小为LCD分辨率(800x480)，默认通道0
    sensor.set_pixformat(Sensor.RGB565) #设置输出图像格式，默认通道0

    Display.init(Display.VIRT, sensor.width(), sensor.height()) #只使用IDE缓冲区显示图像

    MediaManager.init() #初始化media资源管理器

    sensor.run() #启动sensor

    clock = time.clock()

    rect_binart = (101, 183)
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
                if(Rxbuf[1] == 0x01): #定位激光点
                    state = 1
                    print("开始依次定位铅笔矩形框5个坐标点")
                elif(Rxbuf[1] == 0x02): #开始寻找矩形
                    state = 2
                    print("开始识别矩形")
                elif(Rxbuf[1] == 0x03):
                    state = 3
                    print("开始校准激光")
                elif(Rxbuf[1] == 0x04):
                    state = 4
                    print("开始激光追踪")
                elif(Rxbuf[1] == 0x00):
                    state = 0
                    print("停止")

        img = sensor.snapshot(chn = CAM_CHN_ID_0)
         #灰度图
        img_rect = img.to_grayscale(copy = True)
        #二制化
        img_rect = img_rect.binary([rect_binart])

        """2.定位5个铅笔矩形坐标点"""
        if state == 1:
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
                    time.sleep_ms(20)
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
                            # 显示已记录的点
                            for point in pencil_points:
                                img.draw_cross(pencil_points[len(pencil_points)-1][0], pencil_points[len(pencil_points)-1][1])
                                uart2.write("P" + str(len(pencil_points)) + "X" + str(pencil_points[len(pencil_points)-1][0]) + "Y" + str(pencil_points[len(pencil_points)-1][1]) + "\r\n")
                        else:
                            print("未检测到激光点")
                    elif len(pencil_points) >= 5:
                        print("已记录5个点，请停止采集")
                # 发送数据
                for i in range(len(pencil_points)):
                    img.draw_cross(pencil_points[i][0], pencil_points[i][1])



        """2.寻找矩形"""
        # 在全局作用域声明变量
        center_x = 0
        center_y = 0

        if state == 2:
            rects = img_rect.find_rects(threshold = 5000)

            # """识别画面中大于threshold的矩形"""
            # for rect in rects:
            #     corners = rect.corners()
            #     center_x = (corners[0][0] + corners[1][0]) // 2
            #     center_y = (corners[0][1] + corners[3][1]) // 2
            #     img.draw_rectangle(rect.rect(), color=(1, 147, 230), thickness=3)  # 绘制线段
            #     img.draw_cross(center_x, center_y, color=(255, 255, 255))

            """识别最大矩形"""
            max_rect = find_max_Rect(rects)
            if max_rect:
                corners = max_rect.corners()
                center_x = (corners[0][0] + corners[2][0]) // 2
                center_y = (corners[0][1] + corners[2][1]) // 2
                for p in corners:
                    img.draw_circle(p[0], p[1], 3, color=(0,255,0), fill = True, thickness = 3)

                # """3.矩形坐标转换"""
                # for i in range(4):
                #     Corners[i*2] = corners[i][0] - center_x
                #     Corners[i*2+1] = center_y - corners[i][1]
                img.draw_rectangle(max_rect.rect(), color = (0,0,255), thickness = 3)
                img.draw_cross(center_x, center_y, color = (255,255,255))

        #识别激光
        if state == 6:   # 接收到‘6’时持续发送
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

        """串口发送
        if (state == 1 or state == 6):
            # 发送数据
            if state == 1:
                uart2.write('！' + str(center_x) + ',' + str(center_y) + '@')
                print(f"发送数据: 状态={state}, X={center_x}, Y={center_y}")
            if state == 6:
                uart2.write('！' + str(laser_x) + ',' + str(laser_y) + '@')
                print(f"发送数据: 状态={state}, X={laser_x}, Y={laser_y}")
        """

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






# 激光沿矩形边框运动
def laser_rect():
    if state == 6 and max_rect:
        # 获取外矩形坐标
        outer_rect_x, outer_rect_y, outer_rect_w, outer_rect_h = max_rect.rect()

        # 计算内矩形坐标（假设黑带宽1.8cm，约68像素）
        inner_rect_x = outer_rect_x + 34  # 半宽
        inner_rect_y = outer_rect_y + 34
        inner_rect_w = outer_rect_w - 68
        inner_rect_h = outer_rect_h - 68

        # 计算黑带区域的四个顶点（内外矩形之间的中点）
        black_band_vertices = [
            ((outer_rect_x + inner_rect_x) // 2, (outer_rect_y + inner_rect_y) // 2),  # 左上
            ((outer_rect_x + outer_rect_w + inner_rect_x + inner_rect_w) // 2, (outer_rect_y + inner_rect_y) // 2),  # 右上
            ((outer_rect_x + outer_rect_w + inner_rect_x + inner_rect_w) // 2, (outer_rect_y + outer_rect_h + inner_rect_y + inner_rect_h) // 2),  # 右下
            ((outer_rect_x + inner_rect_x) // 2, (outer_rect_y + outer_rect_h + inner_rect_y + inner_rect_h) // 2)  # 左下
        ]

        # 计算激光是否在黑带区域内
        in_black_band = (
            (outer_rect_x <= laser_x <= outer_rect_x + outer_rect_w and outer_rect_y <= laser_y <= outer_rect_y + outer_rect_h) and
            not (inner_rect_x <= laser_x <= inner_rect_x + inner_rect_w and
                 inner_rect_y <= laser_y <= inner_rect_y + inner_rect_h)
        )

        if not in_black_band:
            # 如果激光不在黑带区域，计算最近的黑带顶点
            closest_vertex = None
            min_dist = float('inf')

            for vertex in black_band_vertices:
                dist = (vertex[0] - laser_x)**2 + (vertex[1] - laser_y)**2
                if dist < min_dist:
                    min_dist = dist
                    closest_vertex = vertex

            # 计算移动方向
            move_x = closest_vertex[0] - laser_x
            move_y = closest_vertex[1] - laser_y

            # 发送移动指令
            uart2.write(f'MOVE {move_x} {move_y}\n')
        else:
            # 沿黑带运动逻辑
            # 找到最近的黑带顶点
            min_dist = float('inf')
            target_vertex = None

            for vertex in black_band_vertices:
                dist = (vertex[0] - laser_x)**2 + (vertex[1] - laser_y)**2
                if dist < min_dist:
                    min_dist = dist
                    target_vertex = vertex

            # 计算移动方向
            move_x = target_vertex[0] - laser_x
            move_y = target_vertex[1] - laser_y

            # 发送移动指令
            uart2.write(f'MOVE {move_x} {move_y}\n')



# 激光追踪函数
# 持续检测红色激光和绿色激光的位置，并计算两者之间的距离和方向
def laser_track():
    loop = True
    while loop:  # 持续循环检测
        img = sensor.snapshot(chn = CAM_CHN_ID_0)  # 从摄像头通道0获取一帧图像

        # 检测红色激光
        red_blobs = img.find_blobs(Red_thresholds)  # 使用红色阈值检测红色激光点
        if red_blobs:  # 如果检测到红色激光
            red_pixels = [b.pixels() for b in red_blobs]  # 获取每个红色区域的像素数量
            max_red = red_blobs[red_pixels.index(max(red_pixels))]  # 找到像素最多的红色区域
            red_x = max_red.x() + round(max_red.w()/2)  # 计算红色激光中心点x坐标
            red_y = max_red.y() + round(max_red.h()/2)  # 计算红色激光中心点y坐标
            img.draw_cross(red_x, red_y, color=(255,0,0))  # 在图像上绘制红色十字标记

        # 检测绿色激光
        green_blobs = img.find_blobs(Green_thresholds)  # 使用绿色阈值检测绿色激光点
        if green_blobs:  # 如果检测到绿色激光
            green_pixels = [b.pixels() for b in green_blobs]  # 获取每个绿色区域的像素数量
            max_green = green_blobs[green_pixels.index(max(green_pixels))]  # 找到像素最多的绿色区域
            green_x = max_green.x() + round(max_green.w()/2)  # 计算绿色激光中心点x坐标
            green_y = max_green.y() + round(max_green.h()/2)  # 计算绿色激光中心点y坐标
            img.draw_cross(green_x, green_y, color=(0,255,0))  # 在图像上绘制绿色十字标记

        # 计算距离和方向
        dx = green_x - red_x  # x方向距离差
        dy = green_y - red_y  # y方向距离差
        distance = (dx**2 + dy**2)**0.5  # 计算两点之间的欧几里得距离

        # 绘制追踪线
        img.draw_line(red_x, red_y, green_x, green_y, color=(255,255,0))  # 用黄色线条连接两点
        # 计算角度
        angle = math.atan2(dy, dx)  # 计算角度（弧度）
        angle_deg = math.degrees(angle)  # 将弧度转换为角度
        # 显示距离和角度
        img.draw_string(red_x, red_y, "Dist: {:.2f}mm".format(distance), color=(255, 255, 0))
        img.draw_string(red_x, red_y + 20, "Angle: {:.2f}deg".format(angle_deg), color=(255, 255, 0))

        # 更新激光位置
        laser_x = red_x  # 更新全局变量laser_x
        laser_y = red_y  # 更新全局变量laser_y

        # 在检测到激光点后记录
        red_history.append((red_x, red_y))
        green_history.append((green_x, green_y))

        # 保持最近100个点
        if len(red_history) > 100:
            red_history.pop(0)
            green_history.pop(0)

        # 计算绿色激光的平均移动向量
        if len(green_history) > 1:
            last_green = green_history[-2]
            green_move_x = green_x - last_green[0]
            green_move_y = green_y - last_green[1]
            # 预测下一个位置
            predicted_x = green_x + green_move_x
            predicted_y = green_y + green_move_y

        # 绘制历史轨迹
        for i in range(1, len(red_history)):
            img.draw_line(red_history[i-1][0], red_history[i-1][1],
                        red_history[i][0], red_history[i][1],
                        color=(255,0,0))
            img.draw_line(green_history[i-1][0], green_history[i-1][1],
                        green_history[i][0], green_history[i][1],
                        color=(0,255,0))

        if distance > TRACKING_THRESHOLD:
            # 需要移动红色激光
            move_x = dx * 0.5  # 移动比例为距离的一半
            move_y = dy * 0.5
            # 发送移动指令
            uart2.write(f'MOVE {move_x} {move_y}\n')
        # 发送数据
        uart2.write("L" + str(laser_x) + "Y" + str(laser_y) + "A" + str(angle_deg) + "\r\n")  # 发送激光位置数据









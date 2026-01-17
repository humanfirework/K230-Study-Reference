import gc
import time
import os
import sys

from media.sensor import * #导入sensor模块，使用摄像头相关接口
from media.display import * #导入display模块，使用display相关接口
from media.media import * #导入media模块，使用meida相关接口

from machine import FPIOA
from machine import Pin
from machine import UART

# 颜色识别阈值 (L Min, L Max, A Min, A Max, B Min, B Max) LAB模型
# 下面的阈值元组是用来识别 红、绿、蓝三种颜色，当然你也可以调整让识别变得更好。
Red_thresholds = (29, 45, 4, 31, -5, 17), # 红色阈值
Green_thresholds = (30, 100, -64, -8, 50, 70), # 绿色阈值
Blue_thresholds = (0, 40, 0, 90, -128, -20) # 蓝色阈值

try:

    fpioa = FPIOA()
    fpioa.help()
    fpioa.set_function(11, FPIOA.UART2_TXD)
    fpioa.set_function(12, FPIOA.UART2_RXD)
    uart2 = UART(UART.UART2, 115200)

    sensor = Sensor() #构建摄像头对象
    sensor.reset() #复位和初始化摄像头
    sensor.set_framesize(width=800, height=480) #设置帧大小为LCD分辨率(800x480)，默认通道0
    sensor.set_pixformat(Sensor.RGB565) #设置输出图像格式，默认通道0

    Display.init(Display.VIRT, sensor.width(), sensor.height()) #只使用IDE缓冲区显示图像

    MediaManager.init() #初始化media资源管理器

    sensor.run() #启动sensor

    clock = time.clock()

    while True:

        ################
        ## 这里编写代码 ##
        ################
        #clock.tick()

        #img = sensor.snapshot() #拍摄一张图片

        #blobs = img.find_blobs(Red_thresholds) # 0,1,2分别表示红，绿，蓝色。

        #if blobs:

        #    for b in blobs: #画矩形和箭头表示
        #        tmp=img.draw_circle(b[5],b[6],int(b[2]/2),color = (255, 255, 255),thickness = 2,fill = False)
        #        tmp=img.draw_cross(b[5], b[6], thickness = 2)

        #img.draw_string_advanced(0, 0, 30, 'FPS: '+str("%.3f"%(clock.fps())), color = (255, 255, 255))

        #Display.show_image(img) #显示图片

        #print(clock.fps()) #打印FPS

        os.exitpoint()  # 退出点，用于调试
        img = sensor.snapshot(chn = CAM_CHN_ID_0)  # 从摄像头通道0获取一帧图像
#        blobs = img.find_blobs(Red_thresholds)  # 重新检测色块
#        if blobs:
#            pixel = []
#            for B in blobs:
#                pixel.append(B.pixels())
#            max_index = pixel.index(max(pixel))
#            B = blobs[max_index]
#            img.draw_rectangle(B[0:4])
#            img.draw_cross(B[5], B[6])
#            #C=img.get_pixel(B[5], B[6])  # 获取中心点像素颜色值
             #在检测前没有识别颜色追踪

        data = uart2.read()  # 非阻塞读取串口数据
        if data == b'1':  # 接收到'1'时持续发送
            while True:
                img = sensor.snapshot(chn = CAM_CHN_ID_0)  # 每次循环都获取新帧
                blobs = img.find_blobs(Red_thresholds)  # 重新检测色块
                if blobs:
                    pixel = []
                    for B in blobs:
                        pixel.append(B.pixels())
                    max_index = pixel.index(max(pixel))
                    B = blobs[max_index]
                    img.draw_rectangle(B[0:4])
                    img.draw_cross(B[5], B[6])
                    #C=img.get_pixel(B[5], B[6])  # 获取中心点像素颜色值

                    print(B.x(), B.y(), B.w(), B.h())  # 调试打印色块位置和大小
                    uart2.write('!' + str(B.x() + round(B.w()/2)) + ',' + str(B.y() + round(B.h()/2)) + '@')

                data = uart2.read()
                if data == b'2':  # 接收到'2'时停止发送
                    break
                Display.show_image(img)
                time.sleep_ms(10)  # 添加短暂延迟避免连续发送
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

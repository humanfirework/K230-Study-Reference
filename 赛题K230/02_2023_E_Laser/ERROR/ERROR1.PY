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

picture_width = 480
picture_height = 320

sensor_id = 2
sensor = None

# 显示模式选择：可以是 "VIRT"、"LCD" 或 "HDMI"
DISPLAY_MODE = "LCD"

# 根据模式设置显示宽高
if DISPLAY_MODE == "VIRT":
    # 虚拟显示器模式
    DISPLAY_WIDTH = ALIGN_UP(1920, 16)
    DISPLAY_HEIGHT = 1080
elif DISPLAY_MODE == "LCD":
    # 3.1寸屏幕模式
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
elif DISPLAY_MODE == "HDMI":
    # HDMI扩展板模式
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
else:
    raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

state = 0
laser_x = 0
laser_y = 0
Corners = [0,0,0,0,0,0,0,0]

red_thresholds = (29, 45, 4, 31, -5, 17)
green_thresholds = (29, 45, 4, 31, -5, 17)


"""函数：寻找最大色块"""
def find_max_Blob(blobs):
    if not blobs:
        return None

    pixel = []
    for B in blobs:
        pixel.append(B.pixels())
    max_index = pixel.index(max(pixel))
    B = blobs[max_index]
    return B

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


try:

    fpioa = FPIOA()
    fpioa.help()
    fpioa.set_function(11, FPIOA.UART2_TXD)
    fpioa.set_function(12, FPIOA.UART2_RXD)
    uart2 = UART(UART.UART2, 115200)

    sensor = Sensor() #构建摄像头对象
    sensor.reset() #复位和初始化摄像头
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    # 设置通道0的输出像素格式为RGB888
    sensor.set_pixformat(Sensor.RGB888, chn=CAM_CHN_ID_0)

    # 使用IDE的帧缓冲区作为显示输出
    Display.init(Display.VIRT, width=800, height=480, to_ide=True)

    MediaManager.init() #初始化media资源管理器

    sensor.run() #启动sensor

    clock = time.clock()
    rect_binart = (101, 183)

    while True:
        os.exitpoint() #检测IDE中断
        clock.tick()

        """1.串口接收"""
        Rxbuf = bytearray(5)
        Rx_NumBytes = uart2.readinto(Rxbuf, 5);
        if Rx_NumBytes is not None and Rx_NumBytes == 5:
            if (Rxbuf[0] == 0x55 and Rxbuf[2] == 0xFF and Rxbuf[3] == 0xFF and Rxbuf[4] == 0xFF):
                if(Rxbuf[1] == 0x01): #开始识别矩形
                    state = 1
                    print("开始识别矩形")
                elif(Rxbuf[1] == 0x02): #停止识别矩形
                    state = 0
                    print("停止识别矩形")
                elif(Rxbuf[1] == 0x06):
                    state = 6
                    print("开始追踪激光")

        """获取图像"""
        img = sensor.snapshot(chn = CAM_CHN_ID_0)

        #灰度图
        img_rect = img.to_grayscale(copy = True)
        #二制化
        img_rect = img_rect.binary([rect_binart])

        """2.寻找矩形"""
        # 在全局作用域声明变量
        center_x = 0
        center_y = 0

        if state == 1:
            rects = img_rect.find_rects(threshold = 5000)
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

        if state == 6:
            blobs = img.find_blobs([red_thresholds])  # 重新检测色块
            if blobs:
                pixel = []
                for B in blobs:
                    pixel.append(B.pixels())
                max_index = pixel.index(max(pixel))
                B = blobs[max_index]
                img.draw_rectangle(B[0:4])
                img.draw_cross(B[5], B[6])
                laser_x = B[5]
                laser_y = B[6]


        if(state == 1 or state == 6):  # 当状态为1(矩形识别)或6(激光追踪)时执行
            # 发送数据
            if state == 1:
                uart2.write('矩形坐标:' + str(center_x) + ',' + str(center_y) + '@')
                print(f"发送数据: 状态={state}, X={center_x}, Y={center_y}")
            if state == 6:
                uart2.write('激光坐标:' + str(laser_x) + ',' + str(laser_y) + '@')
                print(f"发送数据: 状态={state}, X={laser_x}, Y={laser_y}")


        Display.show_image(img, x=int((DISPLAY_WIDTH - picture_width) / 2), y=int((DISPLAY_HEIGHT - picture_height) / 2))

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


    
import time, os, sys

import utime
from media.sensor import *
from media.display import *
from media.media import *

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
    DISPLAY_WIDTH = 480
    DISPLAY_HEIGHT = 320
elif DISPLAY_MODE == "HDMI":
    # HDMI扩展板模式
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
else:
    raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

try:
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id)
    # 重置摄像头sensor
    sensor.reset()

    # 无需进行镜像翻转
    # 设置水平镜像
    # sensor.set_hmirror(False)
    # 设置垂直翻转
    # sensor.set_vflip(False)

    # 设置通道0的输出尺寸为
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    # 设置通道0的输出像素格式为RGB888
    sensor.set_pixformat(Sensor.RGB888, chn=CAM_CHN_ID_0)

    # 使用IDE的帧缓冲区作为显示输出
    Display.init(Display.VIRT, width=1920, height=1080, to_ide=True)
    # 初始化媒体管理器
    MediaManager.init()
    # 启动传感器
    sensor.run()

    #构造clock
    clock = utime.clock()

    rect_binart = (101, 183)

    while True:
        os.exitpoint()

        #更新当前时间（毫秒）
        clock.tick()

        # 捕获通道0的图像
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        #灰度图
        img_rect = img.to_grayscale(copy = True)
        #二制化
        img_rect = img_rect.binary([rect_binart])

        #找一个目标的矩形大小
        #image.find_rects([roi=Auto, threshold=10000])
        #（roi 是用于指定感兴趣区域的矩形元组 (x, y, w, h)）
        rects = img_rect.find_rects(threshold = 5000)

        # 找到面积最大的矩形
        max_rect = None
        max_area = 0

        count = 0  # 初始化线段计数器

        print("------矩形统计开始------")
        for rect in rects:
            x, y, w, h = rect.rect()
            area = w * h
            if area > max_area:
                max_area = area
                max_rect = rect

        if max_rect:
            corners = max_rect.corners()
            center_x = (corners[0][0] + corners[2][0]) // 2
            center_y = (corners[0][1] + corners[2][1]) // 2

            #([x0, y0], [x1, y1], [x2, y2], [x3, y3])
            #元组嵌套，如X0是corners[0][0],y0是corners[0][1]

            img.draw_line(corners[0][0], corners[0][1], corners[1][0], corners[1][1], color = (0, 255, 0), thickness = 5)
            img.draw_line(corners[2][0], corners[2][1], corners[1][0], corners[1][1], color = (0, 255, 0), thickness = 5)
            img.draw_line(corners[2][0], corners[2][1], corners[3][0], corners[3][1], color = (0, 255, 0), thickness = 5)
            img.draw_line(corners[0][0], corners[0][1], corners[3][0], corners[3][1], color = (0, 255, 0), thickness = 5)

            #img.draw_rectangle(max_rect.rect(), color=(1, 147, 230), thickness=3)  # 绘制线段
            img.draw_cross(center_x, center_y, color=(255, 255, 255))

            print(f"矩形{count}: {corners}")        #返回矩形4个点坐标
            count += 1
        print("---------END---------")
        #在IDE显示FPS
        img.draw_string_advanced(0, 0, 20, "FPS: {}".format(clock.fps()), color =  (255, 0, 0))

        #压缩
        img.compressed_for_ide()

        # 显示捕获的图像
        Display.show_image(img, x=int((DISPLAY_WIDTH - picture_width) / 2), y=int((DISPLAY_HEIGHT - picture_height) / 2))



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

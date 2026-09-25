# bilibili搜索学不会电磁场看教程
# 第五课，电赛经常出现电磁炮标靶、小车车道线等需要识别的简单物体，这节课我们来学习一下如何识别色块和线段

import time
import os
import sys

from media.sensor import *
from media.display import *
from media.media import *
from time import ticks_ms

sensor = None

try:
    print("camera_test")

    sensor = Sensor(width=1024, height=768)
    sensor.reset()

    # 鼠标悬停在函数上可以查看允许接收的参数
    sensor.set_framesize(width=1024, height=768)
    sensor.set_pixformat(Sensor.RGB565)

    Display.init(Display.LT9611, to_ide=True)
    # 初始化媒体管理器
    MediaManager.init()
    # 启动 sensor
    sensor.run()
    clock = time.clock()

    while True:
        clock.tick()
        os.exitpoint()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
#        # 绘制字符串，参数依次为：x, y, 字符高度，字符串，字符颜色（RGB三元组）
#        img.draw_string_advanced(50, 50, 80, "hello k230\n学不会电磁场", color=(255, 0, 0))

#        # 绘制直线，参数依次为：x1, y1, x2, y2, 颜色，线宽
#        img.draw_line(50, 50, 300, 130, color=(0, 255, 0), thickness=2)

#        # 绘制方框，参数依次为：x, y, w, h, 颜色，线宽，是否填充
#        img.draw_rectangle(1000, 50, 300, 200, color=(0, 0, 255), thickness=4, fill=False)

#        # 绘制关键点, 列表[(x, y, 旋转角度)]
#        img.draw_keypoints([[960, 540, 200]], color=(255, 255, 0), size=30, thickness=2, fill=False)

#        # 绘制圆, x, y, r
#        img.draw_circle(640, 640, 50, color=(255, 0, 255), thickness=2, fill=True)
#        # 精细的像素级操作，虽然说其实一般用不上，这里利用像素填充的方式绘制一个非常奇怪的方块吧
#        for i in range(1200, 1250):
#            for j in range(700, 750):
#                color =((i + j)%256, (i*j)%256, abs(i-j)%256)
#                img.set_pixel(i, j, color)

        # 寻找线段，参数依次为roi, 合并线段的距离阈值，合并线段的角度阈值
        img_line = img.to_rgb565(copy=True)
        img_line.midpoint_pool(2, 2)
        lines = img_line.find_line_segments((0, 0, 1024//2, 768//2), 15, 15)
        for line in lines:
            if line.length() > 100:
                img.draw_line(line.x1()*2, line.y1()*2, line.x2()*2, line.y2()*2, color=(0, 255, 0), thickness=5)

        # 寻找色块，参数依次为颜色阈值（在上一节二值化时讲过）, 是否反转，roi, x_stride, y_stride, pixels_threshold, margin(是否合并)
        blobs = img.find_blobs([(41, 57, 31, 83, 13, 71)], False,\
                               (0, 0, 640, 640), x_stride=5, y_stride=5, \
                               pixels_threshold=3000, margin=True)
        for blob in blobs:
            img.draw_rectangle(blob.x(), blob.y(), blob.w(), blob.h(), color=(0, 255, 0), thickness=6, fill=False)

        img.draw_string_advanced(50, 50, 80, "fps: {}".format(clock.fps()), color=(255, 0, 0))
        img.compressed_for_ide()
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

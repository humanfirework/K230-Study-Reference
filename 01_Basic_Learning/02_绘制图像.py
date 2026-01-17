import time
import os
import sys

from media.sensor import *
from media.display import *
from media.media import *

sensor = None
sensor_id = 2

try:
    sensor = Sensor()
    sensor.reset()

    sensor.set_framesize(sensor.FHD, chn = CAM_CHN_ID_0)
    sensor.set_pixformat(sensor.RGB565, chn = CAM_CHN_ID_0)

    Display.init(Display.VIRT, width=1920, height=1080, to_ide=True)

    MediaManager.init()

    sensor.run()

    while True:
        os.exitpoint()

        # 捕获通道0的图像
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        img.draw_string_advanced(50, 50, 80, " HelloWorld\n\r何为人生", color = (255, 0, 0))
        img.draw_line(50, 50, 300, 130, color = (0, 0, 255), thickness = 4)
        img.draw_rectangle(1000, 50, 300, 200, color = (0, 0, 255), thickness = 10)
        keypoints = [(960, 540, 270), (640, 360, 0)]
        img.draw_keypoints(keypoints, color = (0, 0, 0), thickness = 4, fill = False, size = 30)
        img.draw_circle(640, 540, 100, color = (255, 0, 255), thickness = 10, fill = True)
        #img.set.pixel(x, y, color)设置像素点

        img.draw_rectangle(50, 50, 1000, 960, color = (0, 0, 0), thickness = 20)
        #img = image.Image(640, 480, image.RGB565)
        # 显示捕获的图像
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

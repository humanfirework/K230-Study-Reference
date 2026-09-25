import time, os, sys

import utime
from media.sensor import *
from media.display import *
from media.media import *

#用CSI0接口的摄像头
sensor_id = 2
sensor = None

try:
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id, width = 1024, height = 768)
    # 重置摄像头sensor
    sensor.reset()

    # 无需进行镜像翻转
    # 设置水平镜像
    # sensor.set_hmirror(False)
    # 设置垂直翻转
    # sensor.set_vflip(False)

    # 设置通道0的输出尺寸为640x640
    sensor.set_framesize(width = 1024, height = 768, chn=CAM_CHN_ID_0)
    # 设置通道0的输出像素格式为RGB888
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    # 使用IDE的帧缓冲区作为显示输出
    Display.init(Display.VIRT, width=1920, height=1080, to_ide=True)
    # 初始化媒体管理器
    MediaManager.init()
    # 启动传感器
    sensor.run()

    #构造clock
    clock = utime.clock()

    # 指定颜色阈值
    # 格式：[min_L, max_L, min_A, max_A, min_B, max_B]
    color_threshold = [(29, 42, -10, 34, -16, 39)]
    while True:
        os.exitpoint()

        #更新当前时间（毫秒）
        clock.tick()

        # 捕获通道0的图像
        img = sensor.snapshot(chn=CAM_CHN_ID_0)


        #查找斑点 （stride:步幅）
        blobs = img.find_blobs(color_threshold, False, (0, 0, 1024, 768),\
                               x_stride = 5, y_stride = 5, \
                               pixels_threshold = 3000)
    #参数：
        #color_threshold 是要寻找的颜色的阈值，area_threshold 表示过滤掉小于此面积的色块。
        #invert = Flash 参数用于反转阈值操作
        #roi = (0, 0, 1024, 768)参数为感兴趣区域的矩形元组 (x, y, w, h)。若未指定，ROI 将默认为整个图像的矩形。操作仅限于该区域内的像素。
        #x_stride 为查找色块时需要跳过的 x 像素数量。在找到色块后，直线填充算法将精确处理该区域。如果已知色块较大，可以增加 x_stride 以提高查找速度。
        #y_stride 为查找色块时需要跳过的 y 像素数量。在找到色块后，直线填充算法将精确处理该区域。如果已知色块较大，可以增加 y_stride 以提高查找速度。
        #area_threshold 用于过滤掉边界框区域小于此值的色块。
        #pixels_threshold 用于过滤掉像素数量少于此值的色块。
        #blobs = img.find_blobs(color_threshold,area_threshold = 2000)
        #merge 若为 True，则合并所有未被过滤的色块，这些色块的边界矩形互相重叠



        #绘制矩形
        for blob in blobs:
            img.draw_rectangle(blob[0:4], color = (255, 0, 0), thickness = 5)
            img.draw_cross(blob[5], blob[6], size = 10, color = (255, 255, 255))
            img.draw_string_advanced(blob[0], blob[1]-35, 30, "red",color = (255, 0, 0))



        #在IDE显示FPS
        img.draw_string_advanced(50, 50, 40, "FPS: {}".format(clock.fps()), color =  (255, 0, 0))

        #压缩
        #img.compressed_for_ide()

        # 显示捕获的图像
        Display.show_image(img)

        #打印当前fps
        print("fps = ", clock.fps())



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

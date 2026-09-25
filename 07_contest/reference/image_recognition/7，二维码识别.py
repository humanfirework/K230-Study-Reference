import time, math, os, gc

from media.sensor import * #导入sensor模块，使用摄像头相关接口
from media.display import * #导入display模块，使用display相关接口
from media.media import * #导入media模块，使用meida相关接口

try:

    sensor = Sensor() #构建摄像头对象
    sensor.reset() #复位和初始化摄像头
    sensor.set_framesize(width=800, height=480) #设置帧大小为LCD分辨率(800x480)，默认通道0
    sensor.set_pixformat(Sensor.RGB565) #设置输出图像格式，默认通道0

    Display.init(Display.VIRT, sensor.width(), sensor.height()) #只使用IDE缓冲区显示图像

    MediaManager.init() #初始化media资源管理器

    sensor.run() #启动sensor

    clock = time.clock()

    while True:

        os.exitpoint() #检测IDE中断
        clock.tick()

        img = sensor.snapshot() #拍摄图片

        res = img.find_qrcodes() #寻找二维码

        if len(res) > 0: #在图片和终端显示二维码信息

            tmp = img.draw_rectangle(res[0].rect(), thickness=2, color = (255, 0, 255))
            img.draw_string_advanced(0, 0, 30, res[0].payload(), color = (255, 255, 255))

            print(res[0].payload()) #串口终端打印

        Display.show_image(img) #显示图片

        print(clock.fps()) #打印帧率

###################
# IDE中断释放资源代码
###################
except KeyboardInterrupt as e:
    print(f"user stop")
except BaseException as e:
    print(f"Exception '{e}'")
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

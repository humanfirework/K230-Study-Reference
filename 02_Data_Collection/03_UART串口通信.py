import time
import os
import sys

from media.sensor import *
from media.display import *
from media.media import *
from time import ticks_ms
from machine import FPIOA
from machine import Pin
from machine import PWM
from machine import Timer
from machine import UART
import time

picture_width = 800
picture_height = 480

sensor_id = 2
sensor = None

try:
    print("camera_test")
    fpioa = FPIOA()
    fpioa.help()
    fpioa.set_function(53, FPIOA.GPIO53)
    fpioa.set_function(11, FPIOA.UART2_TXD)
    fpioa.set_function(12, FPIOA.UART2_RXD)

    KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)
    uart2 = UART(UART.UART2, 115200)

    sensor = Sensor(wihth = picture_width, height = picture_height, id = sensor_id)
    sensor.reset()

    sensor.set_framesize(width = 800, height = 480)
    sensor.set_pixformat(sensor.RGB565)

    Display.init(Display.ST7701, width = 800, height = 480, to_ide = True)

    MediaManager.init()

    sensor.run()
    clock = time.clock()

    while True:
        clock.tick()
        os.exitpoint()

        img = sensor.snapshot(chn = CAM_CHN_ID_0)
        if KEY.value() == 1:
            uart2.write("Hello World\n")

        infor = uart2.read()
        if not infor == None:
            print(infor)




except KeyboardInterrupt as e:
    print("用户手动停止程序: ", e)

# 2. 其他所有异常捕获
except BaseException as e:
    print(f"程序运行异常: {e}")

# 最终清理工作(无论是否发生异常都会执行)
finally:
    # 安全停止传感器
    if isinstance(sensor, Sensor):  # 检查传感器对象是否存在
        sensor.stop()  # 停止传感器采集

    # 反初始化显示设备
    Display.deinit()

    # 系统清理
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)  # 启用睡眠退出点
    time.sleep_ms(100)  # 短暂延时确保资源释放














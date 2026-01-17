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
import time


sensor = None

try:

    print("camera_test")
    fpioa = FPIOA()
    fpioa.help()
    fpioa.set_function(53, FPIOA.GPIO53)

    key = Pin(53, Pin.IN, Pin.PULL_DOWN)


    sensor = Sensor(width=1024, height=768)
    sensor.reset()

    # 鼠标悬停在函数上可以查看允许接收的参数
    sensor.set_framesize(width=1024, height=768)
    sensor.set_pixformat(Sensor.RGB565)

    Display.init(Display.ST7701, width=800, height=480, to_ide=True)
    # 初始化媒体管理器
    MediaManager.init()
    # 启动 sensor
    sensor.run()
    clock = time.clock()

    counter = 0
    save_folder = "/data/data/images/"
    class_lst = ["one", "two", "three", "four", "five", \
                 "six", "seven", "eight", "nine", "zero"]
    class_id = -1
    prefix = "batch_1_"
    while True:
        clock.tick()
        os.exitpoint()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        if key.value() == 1:
            class_id = (class_id + 1) % len(class_lst)
            os.mkdir(save_folder+class_lst[class_id])
            for i in range(3):
                print("will collect {} class in {} s".format(class_lst[class_id], 3-i))
                time.sleep_ms(1000)
            counter = 100
        if not counter == 0:
            time.sleep_ms(50)
            file_name = "{}_{}_{}.jpg".format(prefix, class_lst[class_id], str(counter))
            save_img = img.compress(95)
            file_path = save_folder + class_lst[class_id] + "/" + file_name
            with open(file_path, 'wb') as f:
                f.write(save_img)
            print("img saved to \"{}\"".format(file_path))
            counter -= 1

        #img.draw_string_advanced(50, 50, 80, "fps: {}".format(clock.fps()), color=(255, 0, 0))
        img.midpoint_pool(2, 2)
        #img.compressed_for_ide()
        Display.show_image(img, x=(800-480)//2, y=(480-400)//2)

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

# 导入必要的库和模块
import time, os, sys
import utime
from machine import FPIOA  # 用于GPIO配置
from machine import Pin    # 用于引脚控制

# 导入媒体处理相关模块
from media.sensor import *  # 摄像头传感器接口
from media.display import *  # 显示设备接口
from media.media import *    # 媒体处理核心接口

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


try:
    print("camera_test")  # 打印测试开始信息

    # GPIO53配置为下拉输入模式
    fpioa = FPIOA()  # 创建FPIOA对象
    fpioa.help()     # 打印FPIOA帮助信息(调试用)
    fpioa.set_function(53, FPIOA.GPIO53)  # 设置GPIO53功能

    # 创建按键对象，用于触发图像采集
    KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)  # GPIO53作为输入引脚，下拉模式

    # 初始化摄像头传感器
    sensor = Sensor(width=480, height=320, id=sensor_id)  # 创建传感器对象
    sensor.reset()  # 重置传感器

    # 设置传感器参数
    sensor.set_framesize(width=480, height=320)  # 设置帧尺寸
    sensor.set_pixformat(sensor.RGB888)           # 设置像素格式为RGB888

    # 初始化显示设备(ST7701屏幕)
    Display.init(Display.ST7701, width=800, height=480, to_ide=True)

    # 初始化媒体管理器
    MediaManager.init()

    # 启动传感器
    sensor.run()
    clock = time.clock()  # 创建时钟对象用于帧率计算

    # 图像采集相关变量
    counter = 0                     # 图像计数器
    save_folder = "/data/data/images/"  # 图像保存目录
    # 分类标签列表
    class_lst = ["one", "two", "three", "four", "five",
                 "six", "seven", "eight", "nine", "zero"]
    class_id = -1                   # 当前分类ID
    prefix = "batch_1_"             # 文件名前缀

    fps = time.clock()

    while True:
        fps.tick()

        os.exitpoint()
        img = sensor.snapshot(chn = CAM_CHN_ID_0)

        # 按键检测：当按键按下时切换分类并开始采集
        if KEY.value() == 1:  # 检测按键按下
            # 循环切换分类ID
            class_id = (class_id + 1) % len(class_lst)
            # 创建分类目录
            os.mkdir(save_folder + class_lst[class_id])

            # 倒计时3秒提示
            for i in range(3):
                print("将采集 {} 类图像，倒计时 {} 秒".format(class_lst[class_id], 3-i))
                time.sleep_ms(1000)

            counter = 100  # 设置采集数量为100张

        # 图像采集与保存逻辑
        if not counter == 0:  # 如果还有图像需要采集
            time.sleep_ms(50)  # 短暂延时，控制采集速率

            # 生成文件名：前缀_分类名_序号.jpg
            file_name = "{}_{}_{}.jpg".format(prefix, class_lst[class_id], str(counter))

            # 图像压缩(质量95%)
            save_img = img.compress(95)

            # 拼接完整保存路径
            file_path = save_folder + class_lst[class_id] + "/" + file_name

            # 保存图像文件
            with open(file_path, 'wb') as f:
                f.write(save_img)

            print("图像已保存到：\"{}\"".format(file_path))
            counter -= 1  # 计数器减1

        img.draw_string_advanced(0, 0, 32, str(counter), color=(255, 0, 0))
        img.draw_string_advanced(0, 768, 32, "FPS: ".format(fps.fps()), color=(255, 0, 0))

        # 在屏幕上实时显示图像
        Display.show_image(img)


# 异常处理部分
# 1. 用户主动中断(Ctrl+C)
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
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)  # 启用睡眠退出点
    time.sleep_ms(100)  # 短暂延时确保资源释放

    # 释放媒体缓冲区(自动处理)

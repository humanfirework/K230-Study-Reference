import time, os, sys

from media.sensor import *
from media.display import *
from media.media import *
import time, math, os, gc, sys

picture_width = 640
picture_height = 480

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
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id)
    # 重置摄像头sensor
    sensor.reset()

    # 无需进行镜像翻转
    # 设置水平镜像
    # sensor.set_hmirror(False)
    # 设置垂直翻转
    # sensor.set_vflip(False)

    # 设置通道0的输出尺寸
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    # 设置通道0的输出像素格式为GRAYSCALE(灰度)
    sensor.set_pixformat(Sensor.GRAYSCALE, chn=CAM_CHN_ID_0)
    #sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    # 根据模式初始化显示器
    if DISPLAY_MODE == "VIRT":
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)
    elif DISPLAY_MODE == "LCD":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "HDMI":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)

    BINARY_VISIBLE = True # 使用二值化图像你可以看到什么是线性回归。
                          # 这可能降低 FPS（每秒帧数）.

    THRESHOLD = D(90, 23)  # 黑白图像的灰度阈值
    Display.init(Display.ST7701,  width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    BINARY_VISIBLE = True
    # 初始化媒体管理器
    MediaManager.init()
    # 启动传感器
    sensor.run()

    # 创建一个FPS计时器，用于实时计算每秒帧数
    fps = time.clock()

    while True:
        os.exitpoint()
        # 更新FPS计时
        fps.tick()

        #image.binary([THRESHOLD])将灰度值在THRESHOLD范围变成了白色
        img = sensor.snapshot().binary([THRESHOLD]) if BINARY_VISIBLE else sensor.snapshot()

            # 返回一个类似 find_lines() 和find_line_segments()的对象.
            # 有以下函数使用方法： x1(), y1(), x2(), y2(), length(),
            # theta() (rotation in degrees), rho(), and magnitude().
            #
            # magnitude() 代表线性回归的指令，其值为(0, INF]。
            # 0表示一个圆，INF数值越大，表示线性拟合的效果越好。

        line = img.get_regression([(255,255) if BINARY_VISIBLE else THRESHOLD])

        if (line):

            img.draw_line(line.line(), color = 127,thickness=4)

            print(line) #打印结果

        #显示图片，仅用于LCD居中方式显示

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

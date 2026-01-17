import time, os, sys
from media.sensor import *
from media.display import *
from media.media import *

# 显示参数 / Display parameters
DISPLAY_WIDTH = 640    # LCD显示宽度 / LCD display width
DISPLAY_HEIGHT = 480   # LCD显示高度 / LCD display height

# 颜色阈值(LAB色彩空间) / Color thresholds (LAB color space)
# (L Min, L Max, A Min, A Max, B Min, B Max)
COLOR_THRESHOLDS = [
    (0, 66, 7, 127, 3, 127),    # 红色阈值 / Red threshold
    (42, 100, -128, -17, 6, 66),     # 绿色阈值 / Green threshold
    (43, 99, -43, -4, -56, -7),       # 蓝色阈值 / Blue threshold
]

# 显示颜色定义 / Display color definitions
DRAW_COLORS = [(255,0,0), (0,255,0), (0,0,255)]  # RGB颜色 / RGB colors
COLOR_LABELS = ['RED', 'GREEN', 'BLUE']           # 颜色标签 / Color labels

def init_sensor():
    """初始化摄像头 / Initialize camera sensor"""
    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
    sensor.set_pixformat(Sensor.RGB565)
    return sensor

def init_display():
    """初始化显示 / Initialize display"""
    Display.init(Display.ST7701, to_ide=True)
    MediaManager.init()

def process_blobs(img, threshold_idx):
    """处理颜色区块检测 / Process color blob detection"""
    blobs = img.find_blobs([COLOR_THRESHOLDS[threshold_idx]])
    if blobs:
        for blob in blobs:
            # 绘制检测框和标记 / Draw detection box and markers
            img.draw_rectangle(blob[0:4], thickness=4, color=DRAW_COLORS[threshold_idx])
            img.draw_cross(blob[5], blob[6], thickness=2)
            img.draw_string_advanced(blob[0], blob[1]-35, 30,
                                   COLOR_LABELS[threshold_idx],
                                   color=DRAW_COLORS[threshold_idx])

def main():
    try:
        # 初始化设备 / Initialize devices
        sensor = init_sensor()
        init_display()
        sensor.run()

        clock = time.clock()

        while True:
            clock.tick()

            # 捕获图像 / Capture image
            img = sensor.snapshot()

            # 检测三种颜色 / Detect three colors
            for i in range(3):
                process_blobs(img, i)

            # 显示FPS / Display FPS
            fps_text = f'FPS: {clock.fps():.3f}'
            img.draw_string_advanced(0, 0, 30, fps_text, color=(255, 255, 255))

            # 显示图像并打印FPS / Display image and print FPS
            Display.show_image(img)
            print(clock.fps())

    except KeyboardInterrupt as e:
        print("用户中断 / User interrupted: ", e)
    except Exception as e:
        print(f"发生错误 / Error occurred: {e}")
    finally:
        # 清理资源 / Cleanup resources
        if 'sensor' in locals() and isinstance(sensor, Sensor):
            sensor.stop()
        Display.deinit()
        MediaManager.deinit()

if __name__ == "__main__":
    main()

import time
import os
import sys

from media.sensor import *
from media.display import *
from media.media import *
from time import ticks_ms

# ------------------- 配置部分 -------------------

# 显示模式选择：可以是 "VIRT"、"LCD" 或 "HDMI"
# "VIRT": 虚拟显示器模式 (通常用于PC上的IDE调试)
# "LCD": 3.1寸屏幕模式 (例如 ST7701 驱动的屏幕)
# "HDMI": HDMI扩展板模式 (例如 LT9611 驱动的HDMI输出)
DISPLAY_MODE = "LCD"

# 摄像头ID，通常为 2
SENSOR_ID = 2

# 这是一个为 rgb(254, 150, 200) 设定的、更宽泛的红色阈值
# 对应的中心LAB值约为: L=75, a=40, b=-5
# L(亮度)范围设得很宽，以适应不同光照。a(红/绿)通道集中在红色区域。b(黄/蓝)通道允许一些偏黄或偏蓝的色差。
RED_THRESHOLD = [(30, 95, 20, 70, -25, 25)]

# 这是一个为 rgb(138, 242, 133) 设定的、更宽泛的绿色阈值
# 对应的中心LAB值约为: L=85, a=-45, b=40
# L(亮度)范围同样很宽。a(红/绿)通道集中在绿色区域。b(黄/蓝)通道则倾向于黄绿色区域。
GREEN_THRESHOLD = [(40, 98, -80, -30, 20, 80)]

# 查找色块 (Blob) 时过滤掉的最小像素面积。
# 小于此面积的色块将被忽略，有助于去除噪声。
BLOB_AREA_THRESHOLD = 2

# 查找矩形时，对灰度图进行二值化处理的阈值。
# 图像像素值在此范围内将被视为前景（例如白色），否则为背景（例如黑色）。
RECT_BINARY_THRESHOLD = [(82, 212)]

# 查找矩形时的最小面积阈值。
# 小于此面积的矩形将被忽略，有助于过滤掉小的干扰。
RECT_AREA_THRESHOLD = 100000

# ------------------- 程序主体 -------------------

# 初始化 sensor 变量为 None，以便在 finally 块中进行安全检查
sensor = None

try:
    print("开始执行图像识别程序...")

    # --- 1. 初始化摄像头 ---
    sensor = Sensor(id=SENSOR_ID)
    sensor.reset() # 重置摄像头到默认设置
    # sensor.set_hmirror(False) # 根据实际安装情况设置水平镜像，False为不镜像
    # sensor.set_vflip(False)   # 根据实际安装情况设置垂直翻转，False为不翻转

    # --- 2. 初始化显示设备 ---
    # 根据 DISPLAY_MODE 配置常量来初始化不同的显示设备
    if DISPLAY_MODE == "VIRT":
        # 虚拟显示器模式：分辨率设置为1920x1080，帧率为60fps
        DISPLAY_WIDTH, DISPLAY_HEIGHT = ALIGN_UP(1920, 16), 1080
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)
    elif DISPLAY_MODE == "LCD":
        # LCD屏幕模式：分辨率设置为800x480，输出到IDE (to_ide=True)
        DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "HDMI":
        # HDMI扩展板模式：分辨率设置为1920x1080，输出到IDE (to_ide=True)
        DISPLAY_WIDTH, DISPLAY_HEIGHT = 1920, 1080
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    else:
        # 如果配置了未知的显示模式，则抛出错误
        raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

    # 设置摄像头输出尺寸以匹配显示设备的屏幕尺寸
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0) # 设置像素格式为RGB565

    # --- 3. 初始化媒体管理器和时钟 ---
    MediaManager.init() # 初始化媒体管理器，管理摄像头和显示资源
    sensor.run()        # 启动摄像头图像捕获
    clock = time.clock() # 初始化时钟对象，用于计算帧率

    print("初始化完成，进入主循环...")
    # --- 4. 主循环 ---
    # 程序的核心逻辑在此循环中持续运行，直到被中断
    while True:
        clock.tick() # 更新时钟，用于帧率计算
        os.exitpoint() # 允许操作系统进行上下文切换，防止程序阻塞

        # a. 捕获图像
        img = sensor.snapshot(chn=CAM_CHN_ID_0) # 从摄像头捕获一帧图像

        # b. 矩形识别和绘制
        # 为了不影响原始彩色图像的操作，复制一份图像进行灰度处理和二值化
        img_rect_gray = img.to_grayscale(copy=True)
        # 将灰度图像进行二值化，以便 find_rects 函数能够识别轮廓
        img_rect_gray = img_rect_gray.binary(RECT_BINARY_THRESHOLD)
        # 在二值化图像中查找矩形，并应用最小面积阈值
        rects = img_rect_gray.find_rects(threshold=RECT_AREA_THRESHOLD)

        if rects:
            # 如果检测到矩形
            for rect in rects:
                corner = rect.corners() # 获取矩形的四个角点坐标
                # 使用循环绘制矩形的四条边，颜色为绿色，厚度为3像素
                for i in range(4):
                    p1 = corner[i]
                    p2 = corner[(i + 1) % 4] # 连接当前角点和下一个角点（最后一个点连接回第一个点）
                    img.draw_line(p1[0], p1[1], p2[0], p2[1], color=(0, 255, 0), thickness=3)

        # c. 查找并标记最大的红色色块
        # 在彩色图像中查找符合红色阈值的色块，并应用最小面积阈值
        red_blobs = img.find_blobs(RED_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
        if red_blobs:
            # find_blobs 返回的列表是按面积从大到小排序的，所以第一个就是最大的
            largest_red_blob = red_blobs[0]
            # 在最大红色色块的中心绘制一个红色的十字，用于标记
            # largest_red_blob[5] 是中心X坐标 (cx)，largest_red_blob[6] 是中心Y坐标 (cy)
            img.draw_cross(largest_red_blob[5], largest_red_blob[6], color=(255, 0, 0), size=15, thickness=2)
            # 在控制台输出最大红色色块的中心坐标
            # print("Largest Red Blob Center: X={}, Y={}".format(largest_red_blob[5], largest_red_blob[6]))


        # d. 查找并标记最大的绿色色块
        # 在彩色图像中查找符合绿色阈值的色块，并应用最小面积阈值
        green_blobs = img.find_blobs(GREEN_THRESHOLD, area_threshold=BLOB_AREA_THRESHOLD)
        if green_blobs:
            largest_green_blob = green_blobs[0] # 获取最大的绿色色块
            # 在最大绿色色块的中心绘制一个绿色的十字，用于标记
            img.draw_cross(largest_green_blob[5], largest_green_blob[6], color=(0, 255, 0), size=15, thickness=2)
            # 在控制台输出最大绿色色块的中心坐标
            # print("Largest Green Blob Center: X={}, Y={}".format(largest_green_blob[5], largest_green_blob[6]))


        # e. 显示FPS并在屏幕上显示图像
        # 在图像左上角显示当前帧率 (FPS)
        img.draw_string_advanced(10, 10, 30, "fps: {:.2f}".format(clock.fps()), color=(255, 255, 0))
        # img.compressed_for_ide() # 如果在IDE中显示图像卡顿，可以取消此行注释以启用图像压缩
        Display.show_image(img) # 将处理后的图像显示到屏幕上

except KeyboardInterrupt as e:
    # 捕获用户中断异常 (例如，通过Ctrl+C)
    print(f"用户停止: {e}")
except BaseException as e:
    # 捕获所有其他运行时异常
    print(f"程序出现异常: {e}")
finally:
    # --- 5. 退出和清理 ---
    # 无论程序是正常结束还是因异常终止，都将执行此处的清理代码
    print("正在停止程序并释放资源...")
    if isinstance(sensor, Sensor):
        sensor.stop() # 停止摄像头
    Display.deinit() # 释放显示器资源
    # 启用退出点睡眠模式，可能有助于在退出后降低功耗或稳定系统
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100) # 短暂延时，确保资源完全释放
    MediaManager.deinit() # 释放媒体管理器资源
    print("程序已退出。")
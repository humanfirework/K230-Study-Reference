# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任

import time, os, sys , math

from media.sensor import *
from media.display import *
from media.media import *
from machine import FPIOA,UART,Pin

picture_width = 400
picture_height = 240

sensor_id = 2
sensor = None
fps=time.clock()
count=0
first_rect_corners = [[0,0] for _ in range(4)]
second_rect_corners =[[0,0] for _ in range(4)]

fpioa=FPIOA()
fpioa.set_function(11,FPIOA.UART2_TXD)
fpioa.set_function(12,FPIOA.UART2_RXD)

uart = UART(UART.UART2, baudrate=115200, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)
button = Pin(53,Pin.IN,Pin.PULL_DOWN)

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

    # 设置通道0的输出尺寸为1920x1080
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    # 设置通道0的输出像素格式为RGB565
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    # 根据模式初始化显示器
    if DISPLAY_MODE == "VIRT":
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)
    elif DISPLAY_MODE == "LCD":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "HDMI":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)

    # 初始化媒体管理器
    MediaManager.init()
    # 启动传感器
    sensor.run()

    while True:
        fps.tick()
        os.exitpoint()

        # 捕获通道0的图像
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 查找线段并绘制
        img_rect = img.to_grayscale(copy=True)
        img_rect.gaussian(1)  # 添加高斯模糊降噪
        img_rect.binary([(80, 154)])
        rects = img_rect.find_rects()
        count = 0  # 初始化线段计数器

        # 计算矩形面积的辅助函数
        def get_rect_area(rect):
            corners = rect.corners()
            min_x = min(p[0] for p in corners)
            max_x = max(p[0] for p in corners)
            min_y = min(p[1] for p in corners)
            max_y = max(p[1] for p in corners)
            return (max_x - min_x) * (max_y - min_y)

        # 按面积排序并取前两个最大矩形
        sorted_rects = sorted(rects, key=get_rect_area, reverse=True)[:2]
        print("------矩形检测结果------")

        if len(sorted_rects) >= 2:
            # 确定外框和内框
            rect1, rect2 = sorted_rects
            area1, area2 = get_rect_area(rect1), get_rect_area(rect2)
            outer_rect = rect1 if area1 > area2 else rect2
            inner_rect = rect2 if area1 > area2 else rect1

            # 判断内框是否在外框内部的辅助函数
            def is_inside(inner, outer):
                inner_corners = inner.corners()
                outer_corners = outer.corners()
                o_min_x, o_max_x = min(p[0] for p in outer_corners), max(p[0] for p in outer_corners)
                o_min_y, o_max_y = min(p[1] for p in outer_corners), max(p[1] for p in outer_corners)
                return all(o_min_x <= x <= o_max_x and o_min_y <= y <= o_max_y for x, y in inner_corners)

            # 对矩形顶点进行排序的函数（顺时针方向，从左上角开始）
            def sort_corners(corners):
                # 计算中心点
                center = (sum(p[0] for p in corners)/4, sum(p[1] for p in corners)/4)
                # 根据与中心点的角度排序
                corners_with_angle = []
                for (x, y) in corners:
                    angle = math.atan2(y - center[1], x - center[0])
                    corners_with_angle.append((x, y, angle))
                # 按角度排序（顺时针）
                corners_with_angle.sort(key=lambda c: c[2])
                # 返回排序后的顶点坐标
                return [(c[0], c[1]) for c in corners_with_angle]

            # 检查内框是否在外框内部
            if is_inside(inner_rect, outer_rect):
                # 获取并排序外框顶点
                outer_corners = outer_rect.corners()
                outer_corners = sort_corners(outer_corners)
                # 绘制外框（红色）
                for i in range(4):
                    img.draw_line(outer_corners[i][0], outer_corners[i][1], outer_corners[(i+1)%4][0], outer_corners[(i+1)%4][1], color=(255,0,0), thickness=2)

                # 打印外框四个端点坐标
                print("外框顶点坐标:")
                for i, (x, y) in enumerate(outer_corners):
                    print(f"顶点{i+1}: ({x}, {y})")

                # 绘制内框（绿色）
                inner_corners = inner_rect.corners()
                inner_corners = sort_corners(inner_corners)
                # 绘制内框（绿色）
                for i in range(4):
                    img.draw_line(inner_corners[i][0], inner_corners[i][1], inner_corners[(i+1)%4][0], inner_corners[(i+1)%4][1], color=(0,255,0), thickness=2)
                print(f"外框面积: {get_rect_area(outer_rect)}, 内框面积: {get_rect_area(inner_rect)}")

                # 打印内框四个端点坐标
                print("内框顶点坐标:")
                for i, (x, y) in enumerate(inner_corners):
                    print(f"顶点{i+1}: ({x}, {y})")

                # 计算中间矩形四个顶点（内外框对应端点的中点）
                    # 计算对应顶点的中点坐标
                    middle_corners = [
                        [int((oc[0] + ic[0])/2), int((oc[1] + ic[1])/2)]
                        for oc, ic in zip(outer_corners, inner_corners)
                    ]

                    # 绘制中间矩形（蓝色）
                    for i in range(4):
                        img.draw_line(*middle_corners[i], *middle_corners[(i+1)%4],
                                     color=(0, 0, 255), thickness=2)

                # 打印中间矩形四个端点坐标
                print("中间矩形顶点坐标:")
                for i, (x, y) in enumerate(middle_corners):
                    print(f"顶点{i+1}: ({x}, {y})")
            else:
                print("警告: 小矩形不在大矩形内部，不绘制矩形")
        print("---------END---------")

        img.draw_string_advanced(0,0,20,"FPS:{}".format(fps.fps()))
        #img.compressed_for_ide()

        # 显示捕获的图像，中心对齐，居中显示
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

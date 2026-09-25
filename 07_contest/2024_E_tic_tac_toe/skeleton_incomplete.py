import gc
import os
import sys
import time
import math
import struct

from math import *
from media.sensor import * #导入sensor模块，使用摄像头相关接口
from media.display import * #导入display模块，使用display相关接口
from media.media import * #导入media模块，使用meida相关接口

from machine import FPIOA
from machine import Pin
from machine import UART
from machine import PWM

# ======================= 1. 全局配置 =======================
#=======摄像头基本配置========
sensor_id = 2
picture_width = 480
picture_height = 240

DISPLAY_MODE = "LCD"

# 根据模式设置显示宽高
if DISPLAY_MODE == "VIRT":
    # 虚拟显示器模式
    DISPLAY_WIDTH = ALIGN_UP(1920, 16)
    DISPLAY_HEIGHT = 1080
elif DISPLAY_MODE == "LCD":
    # 3.1寸屏幕模式
    DISPLAY_WIDTH = 480
    DISPLAY_HEIGHT = 240
elif DISPLAY_MODE == "HDMI":
    # HDMI扩展板模式
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
else:
    raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

#=======串口配置========
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart = UART(UART.UART2, 115200)

# ======按键配置========
fpioa.set_function(53, FPIOA.GPIO53)  # 设置GPIO53功能
KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)  # GPIO53作为输入引脚，下拉模式

# ======================= 2. 全局变量 =======================
# 自定义帧头帧尾
FRAME_HEADER = bytes([0xAA])  # 1字节帧头
FRAME_FOOTER = bytes([0x55])  # 1字节帧尾

roi_qipan=(30,0,100,120)    # 棋盘点ROI
roi_heiqi=(0,0,30,120)      # 黑棋ROI
roi_baiqi=(130,0,30,120)    # 白棋ROI

# 游戏棋盘
board = [[' ' for _ in range(3)] for _ in range(3)]
# 玩家和电脑的标记
PLAYER = 'X'
COMPUTER = 'O'

# 棋盘点坐标
boardlines = [[0, 0], [0, 0], [0, 0],
            [0, 0], [0, 0], [0, 0],
            [0, 0], [0, 0]]
# 三子棋九点坐标
ninepoints = [[0, 0], [0, 0], [0, 0],
              [0, 0], [0, 0], [0, 0],
              [0, 0], [0, 0], [0, 0]]
# ROI 区域
detectrois = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0],
            [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0],
            [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
# 黑白色块阈值
white_threshold = [(53, 100, -35, 38, -30, 33)]
black_threshold = [(0, 21, -36, 17, -15, 30)]













# ======================= 3. 定义基本函数 =======================
def float_to_bytes(f):
    """将浮点数转为4字节（小端序）"""
    return struct.pack('<f', f)

def build_frame(data):
    """构建完整数据帧"""
    return FRAME_HEADER + data + FRAME_FOOTER

def get_chess_presence_status(board):
    presence_status = 0
    for row in range(3):
        for col in range(3):
            index = row * 3 + col
            if board[row][col] != ' ':  # 有棋子
                presence_status |= (1 << (8 - index))  # 设置对应位（共9位：index 0~8，对应位8~0）
    return presence_status & 0x1FF  # 保留低9位（0b111111111，即511）

def get_chess_color_status(board):
    color_status = 0
    for row in range(3):
        for col in range(3):
            index = row * 3 + col
            if board[row][col] == COMPUTER:  # 黑棋（原代码为 PLAYER，现改为 COMPUTER）
                color_status |= (1 << (8 - index))  # 设置对应位（共9位）
    return color_status & 0x1FF      # 保留低9位

#寻找面积最大并且宽度高度限制的矩形
def max_rect(img, w=0, h=0):
    rects = img.find_rects(roi=roi_qipan, threshold=8000)
    max_area = 0
    max_rect = None

    # 如果识别到矩形
    if rects:
        # 开始遍历矩形是否>=w*h
        for rect in rects:
            if rect.w() * rect.h() > max_area and rect.w() > w and rect.h() > h:
                max_area = rect.w() * rect.h()
                max_rect = rect
    return max_rect

def send_data_frame(*coordinates):
    data = bytes([0x02]) +b''.join(struct.pack('<f', coord) for coord in coordinates)
    frame = build_frame(data)
    uart.write(frame)

def send_data(task_id, x=None, y=None, qipanzhuangtai=None, qizizhuangtai=None):
    # 根据任务ID发送不同类型的数据
    if task_id == 0x02:
        if x is not None and y is not None:
            x_bytes = struct.pack('<f', x)
            y_bytes = struct.pack('<f', y)
            data = bytes([task_id]) + x_bytes + y_bytes
            frame = build_frame(data)
            uart.write(frame)
            print(f"发送坐标：任务ID=0x{task_id:02X}, x={x}, y={y}")
        else:
            print("发送数据时，x和y不能为None")
    elif task_id == 0x03:
        if qipanzhuangtai is not None and qizizhuangtai is not None:
            # 打包9位状态值为2字节无符号整数（小端序）
            presence_bytes = struct.pack('<H', qipanzhuangtai)   # 2字节，保留9位
            color_bytes = struct.pack('<H', qizizhuangtai)       # 2字节，保留9位
            data = bytes([task_id]) + presence_bytes + color_bytes
            frame = build_frame(data)
            uart.write(frame)
            print(f"发送状态：任务ID=0x{task_id:02X}, 棋盘状态={bin(qipanzhuangtai)}, 棋子状态={bin(qizizhuangtai)}")
        else:
            print("发送数据时，棋盘状态和棋子状态不能为None")
    elif task_id == 0x05:
        data = bytes([task_id]) + bytes([0xAA])
        frame = build_frame(data)
        uart.write(frame)
        print(f"发送复位指令：任务ID=0x{task_id:02X}")
    else:
        print(f"未知的任务ID：0x{task_id:02X}")

def receive_and_unpack():
    






##########################################################

# ======================= 4. 主函数 =======================
frame_counter = 0
draw_interval = 15  # 每10帧绘制一次

try:
    sensor = Sensor(id=sensor_id, width=picture_width, height=picture_height)
    sensor.reset()    # 重置摄像头sensor
    # 无需进行镜像和翻转
    sensor.set_hmirror(False)
    sensor.set_vflip(False)
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    # 根据模式初始化显示器
    if DISPLAY_MODE == "VIRT":
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)
    elif DISPLAY_MODE == "LCD":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "HDMI":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)

    MediaManager.init()
    sensor.run()

    while True:
        os.exitpoint()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)        # 捕获通道0的图像



















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
    MediaManager.deinit()

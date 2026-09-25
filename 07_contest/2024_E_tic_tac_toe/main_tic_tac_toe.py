import math  # 添加这一行
import struct  # 新增的导入语句
from media.sensor import *
from media.display import *
from media.media import *
from machine import UART
from machine import Pin
from machine import FPIOA
import time

fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
fpioa.set_function(62,FPIOA.GPIO62)
fpioa.set_function(20,FPIOA.GPIO20)
fpioa.set_function(63,FPIOA.GPIO63)
LED_R = Pin(62, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 红灯
LED_G = Pin(20, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 绿灯
LED_B = Pin(63, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 蓝灯
LED_R.high()  # 关闭红灯
LED_G.high()  # 关闭绿灯
LED_B.high()  # 关闭蓝灯
LED = LED_R  # 当前控制的LED为红色LED
##################变量初始化####################
sensor_id = 2
sensor = None
picture_width = 160
picture_height = 120
move_flag = 0
move_flaga = 0
move_flagb = 0
choice = 0
roi_qipan=(30,0,100,120)
roi_heiqi=(0,0,30,120)
roi_baiqi=(130,0,30,120)
uart = UART(UART.UART2, baudrate=115200, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)
qizi_status = {
    0x00: False, 0x01: False, 0x02: False, 0x03: False, 0x04: False,
    0x05: False, 0x06: False, 0x07: False, 0x08: False, 0x09: False
}
# 自定义帧头帧尾
FRAME_HEADER = bytes([0xFF])  # 1字节帧头
FRAME_FOOTER = bytes([0xFE])  # 1字节帧尾
# 在全局作用域中添加计数器
reset_count = 0  # 用于记录接收到 sub_id == 0x02 的次数
# AI 使用黑棋（0x00-0x04），按顺序选取未被取出的棋子（0号→1号→2号→3号→4号）
AI_CHESS_ORDER = [0x00, 0x01, 0x02, 0x03, 0x04]
AI_CHESS_ORDERa = [0x05, 0x06, 0x07, 0x08, 0x09]
used_chess_pieces = set()
task4_start = False
task5_start= False
task6_start= False
nineqihe = [[0, 0] for _ in range(10)]  # 10个位置，前5个黑棋，后5个白棋
qihe_status = 0x000001FF
waiting_for_number = False  # 标记是否在等待第二个指令
received_color = False      # 标记是否已经处理了第一个指令
closest_blob_coords = None  # 存储最近的棋子坐标
grid_5_coords = None        # 存储格子5的坐标
task2_running = False       # 标记是否正在执行任务2
coordinates_acquired = False
qihe_coordinates = {
    0x00: (roi_heiqi[0] + 0 * (roi_heiqi[2] / 5), roi_heiqi[1]),  # 黑棋0
    0x01: (roi_heiqi[0] + 1 * (roi_heiqi[2] / 5), roi_heiqi[1]),  # 黑棋1
    0x02: (roi_heiqi[0] + 2 * (roi_heiqi[2] / 5), roi_heiqi[1]),  # 黑棋2
    0x03: (roi_heiqi[0] + 3 * (roi_heiqi[2] / 5), roi_heiqi[1]),  # 黑棋3
    0x04: (roi_heiqi[0] + 4 * (roi_heiqi[2] / 5), roi_heiqi[1]),  # 黑棋4
    0x05: (roi_baiqi[0] + 0 * (roi_baiqi[2] / 5), roi_baiqi[1]),  # 白棋0
    0x06: (roi_baiqi[0] + 1 * (roi_baiqi[2] / 5), roi_baiqi[1]),  # 白棋1
    0x07: (roi_baiqi[0] + 2 * (roi_baiqi[2] / 5), roi_baiqi[1]),  # 白棋2
    0x08: (roi_baiqi[0] + 3 * (roi_baiqi[2] / 5), roi_baiqi[1]),  # 白棋3
    0x09: (roi_baiqi[0] + 4 * (roi_baiqi[2] / 5), roi_baiqi[1]),   # 白棋4
}
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
# 游戏棋盘
board = [[' ' for _ in range(3)] for _ in range(3)]

# 玩家和电脑的标记
PLAYER = 'X'
COMPUTER = 'O'
# 新增：记录每个棋格连续检测到棋子的帧数
stable_frames = [[0 for _ in range(3)] for _ in range(3)]
# 新增：判定棋子稳定所需的帧数
STABLE_FRAME_THRESHOLD = 10
clock = time.clock()
ANGLE_SENT = False
task = True
initialized = False
task4_executed = False
task5_executed = False
last_piece_count = 0  # 用于记录上一帧棋盘上的棋子数量
last_board_state = None  # 用于记录上一帧的棋盘状态
game_over = False
task5_executed = False       # 标记任务5是否已初始化
player_move_executed = False  # 标记玩家是否已落子
computer_need_to_move = False # 标记电脑是否需要回应落子

##############################################

##################基本函数#####################
# 显示模式选择：可以是 "VIRT"、"LCD" 或 "HDMI"
DISPLAY_MODE = "LCD"

# 根据模式设置显示宽高
if DISPLAY_MODE == "VIRT":
    # 虚拟显示器模式
    DISPLAY_WIDTH = ALIGN_UP(160, 2)
    DISPLAY_HEIGHT = 120
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
##############################################

##################底层函数#####################
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


# 只有当计数值>=xxx时才会识别棋盘状态
#   接收到"AI方下棋-电机RST数据包"的解析函数中，清零
ret_first_cnt = 0
hand_second_cnt = 0
#寻找面积最大并且宽度高度限制的矩形
def max_rect(img, w=0, h=0):
    global ret_first_cnt, hand_second_cnt
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
                # AI下好了电机RST数据包 + 4/5题
                ret_first_cnt += 1    # 电机复位完成，第一次识别棋盘状态
                hand_second_cnt = 0     # 手遮挡后完成作弊，第二次识别棋盘状态
#                print("ret_first_cnt:") #                print(ret_first_cnt)
                # 等到灯亮
            else:
                # AI下好了电机RST数据包 + 4/5题
#                print("null")
                ret_first_cnt = 0
                hand_second_cnt += 1
#                print(hand_second_cnt)
    return max_rect

#计算棋盘九点坐标
def cal_ninepoints(rect):
    points = [[0, 0], [0, 0], [0, 0],
              [0, 0], [0, 0], [0, 0],
              [0, 0], [0, 0], [0, 0]]
    points[4][0] = int((rect.corners()[3][0] + rect.corners()[1][0]) / 2)
    points[4][1] = int((rect.corners()[3][1] + rect.corners()[1][1]) / 2)
    points[0][0] = int(rect.corners()[3][0] + (rect.corners()[1][0] - rect.corners()[3][0]) / 6)
    points[0][1] = int(rect.corners()[3][1] + (rect.corners()[1][1] - rect.corners()[3][1]) / 6)
    points[8][0] = int(rect.corners()[3][0] + (rect.corners()[1][0] - rect.corners()[3][0]) / 6 * 5)
    points[8][1] = int(rect.corners()[3][1] + (rect.corners()[1][1] - rect.corners()[3][1]) / 6 * 5)
    points[6][0] = int(rect.corners()[0][0] + (rect.corners()[2][0] - rect.corners()[0][0]) / 6)
    points[6][1] = int(rect.corners()[0][1] - (rect.corners()[0][1] - rect.corners()[2][1]) / 6)
    points[2][0] = int(rect.corners()[0][0] + (rect.corners()[2][0] - rect.corners()[0][0]) / 6 * 5)
    points[2][1] = int(rect.corners()[0][1] - (rect.corners()[0][1] - rect.corners()[2][1]) / 6 * 5)
    points[1][0] = points[0][0] + int((points[2][0] - points[0][0]) / 2)
    points[1][1] = points[0][1] + int((points[2][1] - points[0][1]) / 2)
    points[3][0] = points[0][0] + int((points[6][0] - points[0][0]) / 2)
    points[3][1] = points[0][1] + int((points[6][1] - points[0][1]) / 2)
    points[5][0] = points[2][0] + int((points[8][0] - points[2][0]) / 2)
    points[5][1] = points[2][1] + int((points[8][1] - points[2][1]) / 2)
    points[7][0] = points[6][0] + int((points[8][0] - points[6][0]) / 2)
    points[7][1] = points[6][1] + int((points[8][1] - points[6][1]) / 2)
    return points
#计算棋盘直线坐标
def cal_boardlines(rect):
    lines = [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]
    lines[0][0] = int(rect.corners()[3][0] + (rect.corners()[2][0] - rect.corners()[3][0]) / 3)
    lines[0][1] = int(rect.corners()[3][1] + (rect.corners()[2][1] - rect.corners()[3][1]) / 3)
    lines[1][0] = int(rect.corners()[3][0] + (rect.corners()[2][0] - rect.corners()[3][0]) / 3 * 2)
    lines[1][1] = int(rect.corners()[3][1] + (rect.corners()[2][1] - rect.corners()[3][1]) / 3 * 2)
    lines[2][0] = int(rect.corners()[3][0] + (rect.corners()[0][0] - rect.corners()[3][0]) / 3)
    lines[2][1] = int(rect.corners()[3][1] + (rect.corners()[0][1] - rect.corners()[3][1]) / 3)
    lines[3][0] = int(rect.corners()[2][0] + (rect.corners()[1][0] - rect.corners()[2][0]) / 3)
    lines[3][1] = int(rect.corners()[2][1] + (rect.corners()[1][1] - rect.corners()[2][1]) / 3)
    lines[4][0] = int(rect.corners()[3][0] + (rect.corners()[0][0] - rect.corners()[3][0]) / 3 * 2)
    lines[4][1] = int(rect.corners()[3][1] + (rect.corners()[0][1] - rect.corners()[3][1]) / 3 * 2)
    lines[5][0] = int(rect.corners()[2][0] + (rect.corners()[1][0] - rect.corners()[2][0]) / 3 * 2)
    lines[5][1] = int(rect.corners()[2][1] + (rect.corners()[1][1] - rect.corners()[2][1]) / 3 * 2)
    lines[6][0] = int(rect.corners()[0][0] + (rect.corners()[1][0] - rect.corners()[0][0]) / 3)
    lines[6][1] = int(rect.corners()[0][1] + (rect.corners()[1][1] - rect.corners()[0][1]) / 3)
    lines[7][0] = int(rect.corners()[0][0] + (rect.corners()[1][0] - rect.corners()[0][0]) / 3 * 2)
    lines[7][1] = int(rect.corners()[0][1] + (rect.corners()[1][1] - rect.corners()[0][1]) / 3 * 2)
    return lines
#画出棋盘九点坐标
def draw_ninepoints(img, points, board):
    for i in range(0, 9):
        row = i // 3
        col = i % 3
        x = points[i][0]
        y = points[i][1]

        if board[row][col] == PLAYER:  # 白棋
            img.draw_line(x - 10, y - 10, x + 10, y + 10, color=(0, 0, 0), thickness=2)
            img.draw_line(x + 10, y - 10, x - 10, y + 10, color=(0, 0, 0), thickness=2)

        elif board[row][col] == COMPUTER:  # 黑棋
            img.draw_circle(x, y, 10, color=(255, 255, 255), thickness=2)
#画出棋盘
def draw_board(img, maxrect, lines):
    img.draw_line(maxrect.corners()[0][0], maxrect.corners()[0][1], maxrect.corners()[1][0], maxrect.corners()[1][1],
                  color=(0, 0, 255), thickness=2)
    img.draw_line(maxrect.corners()[1][0], maxrect.corners()[1][1], maxrect.corners()[2][0], maxrect.corners()[2][1],
                  color=(0, 0, 255), thickness=2)
    img.draw_line(maxrect.corners()[2][0], maxrect.corners()[2][1], maxrect.corners()[3][0], maxrect.corners()[3][1],
                  color=(0, 0, 255), thickness=2)
    img.draw_line(maxrect.corners()[3][0], maxrect.corners()[3][1], maxrect.corners()[0][0], maxrect.corners()[0][1],
                  color=(0, 0, 255), thickness=2)
    img.draw_line(boardlines[0][0], boardlines[0][1], boardlines[6][0], boardlines[6][1], color=(0, 0, 255), thickness=2)
    img.draw_line(boardlines[1][0], boardlines[1][1], boardlines[7][0], boardlines[7][1], color=(0, 0, 255), thickness=2)
    img.draw_line(boardlines[2][0], boardlines[2][1], boardlines[3][0], boardlines[3][1], color=(0, 0, 255), thickness=2)
    img.draw_line(boardlines[4][0], boardlines[4][1], boardlines[5][0], boardlines[5][1], color=(0, 0, 255), thickness=2)

def cal_roi(maxrect):
    global ninepoints
    rois = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0],
            [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0],
            [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    for i in range(0, 9):
        rois[i][0] = ninepoints[i][0] - 2
        rois[i][1] = ninepoints[i][1] - 2
        rois[i][2] = 4
        rois[i][3] = 4
    return rois

def send_data_frame(*coordinates):
    data = bytes([0x02]) +b''.join(struct.pack('<f', coord) for coord in coordinates)
    frame = build_frame(data)
    uart.write(frame)
##############################################

##################基本函数#####################
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
    global uart, task_id, naqi_qizixuhao,ret_first_cnt, hand_second_cnt,move_flaga,move_flagb,task4_start,task6_start,task5_start,computer_thought_once,computer_thought_oncea,naqi_geziweizhi_flag, sub_task_id, move_flag, qihe_status, reset_count
    frame_start = False    # 标记是否找到帧头
    frame_end = False      # 标记是否找到帧尾
    frame_data = bytearray()  # 存储完整的帧数据
    time.sleep(0.05)
    while True:
        byte = uart.read(1)  # 从串口读取一个字节
        if byte is None:
            break  # 如果没有数据，退出循环

        byte = byte[0]  # 提取字节值

        # 打印接收到的字节值
        print(f"接收到字节：0x{byte:02X}")

        # 检测帧头
        if byte == 0xFF:
            frame_start = True
            frame_data = bytearray([byte])  # 存储帧头
            continue  # 继续读取后续数据

        # 检测帧尾
        if byte == 0xFE:
            if frame_start:
                frame_end = True
                frame_start = False
                frame_data.append(byte)  # 存储帧尾
                # 处理完整的帧数据
                if len(frame_data) >= 4:  # 确保数据长度至少为4字节（帧头、任务ID、子任务ID、帧尾）
                    task_id = frame_data[1]
                    sub_task_id = frame_data[2] if len(frame_data) > 2 else 0
                    print(f"接收到任务ID：0x{task_id:02X}")
                    # 根据任务ID和子任务ID执行不同的任务
                    if task_id == 0x00:
                        print("执行选题")
                        reset_count = 0
                        if sub_task_id == 0x01:
                            print("执行任务1")
                        elif sub_task_id == 0x02:
                            print("执行任务2")
                        elif sub_task_id == 0x03:
                            print("执行任务3")
                            task3_send_angle(board_angle)
                        elif sub_task_id == 0x04:
                            print("执行任务4")
                            task4_start = True
                        elif sub_task_id == 0x05:
                            print("执行任务5")
                            task5_start = True
                        elif sub_task_id == 0x06:
                            print("执行任务6")
                            task6_start = True
                        else:
                            print(f"未知的子任务ID：0x{sub_task_id:02X}")
                    elif task_id == 0x01:
                        #move_flag = 2
#                        move_flaga = 2
                        print("用户拿棋")
                        #computer_thought_once = False
                        naqi_qizixuhao = frame_data[2] if len(frame_data) > 2 else 0
                        naqi_geziweizhi_flag = frame_data[3] if len(frame_data) > 3 else 0
                        findqiziqipan()
                        task1(naqi_qizixuhao, naqi_geziweizhi_flag)
                        # 检查棋子是否已经被取出
                        if naqi_qizixuhao in qizi_status and qizi_status[naqi_qizixuhao]:
                            continue  # 不执行后续操作

                        if naqi_qizixuhao == 0x00:
                            print("0号黑棋")
                            # 更新棋盒状态：取出0号黑棋
                            qihe_status &= ~(1 << 8)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        elif naqi_qizixuhao == 0x01:
                            print("1号黑棋")
                            # 更新棋盒状态：取出1号黑棋
                            qihe_status &= ~(1 << 7)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        elif naqi_qizixuhao == 0x02:
                            print("2号黑棋")
                            # 更新棋盒状态：取出2号黑棋
                            qihe_status &= ~(1 << 6)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        elif naqi_qizixuhao == 0x03:
                            print("3号黑棋")
                            # 更新棋盒状态：取出3号黑棋
                            qihe_status &= ~(1 << 5)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        elif naqi_qizixuhao == 0x04:
                            print("4号黑棋")
                            # 更新棋盒状态：取出4号黑棋
                            qihe_status &= ~(1 << 4)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        elif naqi_qizixuhao == 0x05:
                            print("0号白棋")
                            # 更新棋盒状态：取出0号白棋
                            qihe_status &= ~(1 << 3)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        elif naqi_qizixuhao == 0x06:
                            print("1号白棋")
                            # 更新棋盒状态：取出1号白棋
                            qihe_status &= ~(1 << 2)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        elif naqi_qizixuhao == 0x07:
                            print("2号白棋")
                            # 更新棋盒状态：取出2号白棋
                            qihe_status &= ~(1 << 1)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        elif naqi_qizixuhao == 0x08:
                            print("3号白棋")
                            # 更新棋盒状态：取出3号白棋
                            qihe_status &= ~(1 << 0)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        elif naqi_qizixuhao == 0x09:
                            print("4号白棋")
                            # 更新棋盒状态：取出4号白棋
                            qihe_status &= ~(1 << 8)
                            qizi_status[naqi_qizixuhao] = True  # 标记棋子已被取出
                            naqi_geziweizhi_flag = True
                        else:
                            print(f"未知的棋子序号：0x{naqi_qizixuhao:02X}")

                        if naqi_geziweizhi_flag:
                            if naqi_geziweizhi_flag == 0x00:
                                print("0号格")
                            elif naqi_geziweizhi_flag == 0x01:
                                print("1号格")
                            elif naqi_geziweizhi_flag == 0x02:
                                print("2号格")
                            elif naqi_geziweizhi_flag == 0x03:
                                print("3号格")
                            elif naqi_geziweizhi_flag == 0x04:
                                print("4号格")
                            elif naqi_geziweizhi_flag == 0x05:
                                print("5号格")
                            elif naqi_geziweizhi_flag == 0x06:
                                print("6号格")
                            elif naqi_geziweizhi_flag == 0x07:
                                print("7号格")
                            elif naqi_geziweizhi_flag == 0x08:
                                print("8号格")
                            else:
                                print(f"未知的格子位置：0x{naqi_geziweizhi_flag:02X}")
                            naqi_geziweizhi_flag = False
                    elif task_id == 0x04:
                        sub_id = frame_data[2]
                        print("已复位")
                        if sub_id == 0x01 :
                            send_data(0x03, 0x01,0x01,presence_status, color_status)
                            print("当前棋盘状态1:")
                            for col in board:
                                print(col)
                            print(f"存在状态: {bin(presence_status)}")
                            print(f"颜色状态: {bin(color_status)}")
                            send_data(0x05, 0xaa, 0x03, presence_status, color_status)
                            print("发送复位指令")
                            sub_id = 0x00
                        elif sub_id == 0x02 :
#                            print("当前棋盘状态1:")
#                            for col in board:
#                                print(col)
#                            print(f"存在状态: {bin(presence_status)}")
#                            print(f"颜色状态: {bin(color_status)}")
                            # 增加计数器
                            if reset_count < 8:
                                print("当前棋盘状态1:")
                                for col in board:
                                    print(col)
                                print(f"存在状态: {bin(presence_status)}")
                                print(f"颜色状态: {bin(color_status)}")
                                send_data(0x03, 0x01, 0x01, presence_status, color_status)
                                print("发送复位指令")
                                reset_count += 1
                            else:
                                send_data(0x05, 0xaa, 0x01, presence_status, color_status)
                            sub_id = 0x00
                        elif sub_id == 0x04:
                            print(f"进入 sub_id == 0x04 分支，当前 sub_id: {sub_id:02X}")
                            print("开始检测胜负")
                            move_flag = 4
                            move_flaga = 4
                            move_flagb =4
                            ret_first_cnt = 0
                            hand_second_cnt = 0
                            print(f"设置 move_flag 为: {move_flag}")
                            send_data(0x03, 0x01, 0x01, presence_status, color_status)
                            print("当前棋盘状态2:")
                            for col in board:
                                print(col)
                            print(f"存在状态: {bin(presence_status)}")
                            print(f"颜色状态: {bin(color_status)}")
                            print("发送复位指令")
                            sub_id = 0x00
                        elif sub_id == 0x05 :
                            computer_thought_once = False
                            computer_thought_oncea = False
                            move_flag = 5
                            move_flaga = 5
                            move_flagb= 5
                            send_data(0x03, 0x01,0x01,presence_status, color_status)
                            print("当前棋盘状态3:")
                            for col in board:
                                print(col)
                            print(f"存在状态: {bin(presence_status)}")
                            print(f"颜色状态: {bin(color_status)}")
                            print("发送复位指令")
                            sub_id = 0x00
                        elif sub_id == 0x07 :
                            move_flaga = 2
                            move_flagb = 2
                            send_data(0x03, 0x01,0x01,presence_status, color_status)
                            print("当前棋盘状态3:")
                            for col in board:
                                print(col)
                            print(f"存在状态: {bin(presence_status)}")
                            print(f"颜色状态: {bin(color_status)}")
                            print("发送复位指令")
                            sub_id = 0x00
                        elif sub_id == 0x08 :
                            move_flaga = 1
                            move_flagb = 1
                            sub_id = 0x00
                    else:
                        print(f"未知的任务ID：0x{task_id:02X}")
                else:
                    print("帧数据长度不足")
                frame_data = bytearray()  # 清空帧数据
                frame_end = False
            break  # 找到帧尾，退出循环

        # 如果在帧头和帧尾之间，存储数据
        if frame_start and not frame_end:
            frame_data.append(byte)
            
def send_coordinates(x, y, target_x=None, target_y=None):
    data = bytes([0x01])+float_to_bytes(x) + float_to_bytes(y)
    if target_x is not None and target_y is not None:
        data += float_to_bytes(target_x) + float_to_bytes(target_y)
    frame = build_frame(data)
    uart.write(frame)
    print(f"发送坐标：棋子({x:.2f}, {y:.2f}) {'-> 目标格子({:.2f}, {:.2f})'.format(target_x, target_y) if target_x else ''}")
def update_nineqihe(status):
    global nineqihe, roi_heiqi, roi_baiqi

    # 清空nineqihe
    nineqihe = [[0, 0] for _ in range(10)]

    # 获取黑棋坐标（前5位）
    for i in range(5):
        if (status & (1 << (8 - i))) == 0:  # 如果对应位为0，表示棋子已被取出
            nineqihe[i] = [0, 0]  # 标记为取出
        else:
            # 计算黑棋坐标
            x = roi_heiqi[0] + (i % 5) * (roi_heiqi[2] // 5)
            y = roi_heiqi[1] + (i // 5) * (roi_heiqi[3] // 1)
            nineqihe[i] = [x, y]

    # 获取白棋坐标（后5位）
    for i in range(5, 10):
        if (status & (1 << (13 - i))) == 0:  # 如果对应位为0，表示棋子已被取出
            nineqihe[i] = [0, 0]  # 标记为取出
        else:
            # 计算白棋坐标
            x = roi_baiqi[0] + ((i - 5) % 5) * (roi_baiqi[2] // 5)
            y = roi_baiqi[1] + ((i - 5) // 5) * (roi_baiqi[3] // 1)
            nineqihe[i] = [x, y]
def findqiziqipan():
    global naqi_qizixuhao, naqi_geziweizhi_flag, closest_blob_coords, grid_5_coords, task2_running

    task2_running = True  # 开始执行时设为True

    # 确定棋子类型（黑棋/白棋）及对应的子区域列表
    if 0x00 <= naqi_qizixuhao <= 0x04:  # 黑棋（0-4号）
        is_black = True
        sub_roi_index = naqi_qizixuhao  # 直接使用序号作为子区域索引（0-4）
        sub_rois = roi_heiqi_sub  # 黑棋的5个子区域
        threshold = black_threshold
    elif 0x05 <= naqi_qizixuhao <= 0x09:  # 白棋（5-9号，对应子区域0-4）
        is_black = False
        sub_roi_index = naqi_qizixuhao - 0x05  # 转换为0-4索引
        sub_rois = roi_baiqi_sub  # 白棋的5个子区域
        threshold = white_threshold
    else:
        print(f"无效的棋子序号: 0x{naqi_qizixuhao:02X}")
        task2_running = False
        return

    # 检查子区域索引是否有效（0-4）
    if sub_roi_index < 0 or sub_roi_index >= len(sub_rois):
        print(f"子区域索引越界: {sub_roi_index}")
        task2_running = False
        return

    # 获取当前序号对应的子区域
    target_sub_roi = sub_rois[sub_roi_index]
    x, y, w, h = target_sub_roi

    # 在目标子区域内检测色块
    img = sensor.snapshot(chn=CAM_CHN_ID_0)
    blobs = img.find_blobs(threshold, roi=target_sub_roi, merge=True)

    if blobs:
        # 取第一个检测到的色块（假设每个子区域只有一个棋子）
        blob = blobs[0]
        closest_blob_coords = (blob.cx(), blob.cy())
        print(f"在序号 {naqi_qizixuhao} 对应的子区域找到棋子，坐标: ({closest_blob_coords[0]}, {closest_blob_coords[1]})")

        # 处理目标格子位置（若有）
        if 0x00 <= naqi_geziweizhi_flag <= 0x08:  # 格子0-8
            grid_index = naqi_geziweizhi_flag
            if 0 <= grid_index < 9:
                grid_5_coords = (ninepoints[grid_index][0], ninepoints[grid_index][1])
                # 发送棋子坐标和目标格子坐标
                send_coordinates(closest_blob_coords[0], closest_blob_coords[1], grid_5_coords[0], grid_5_coords[1])
            else:
                print(f"无效的格子索引: {grid_index}")
        else:
            # 仅发送棋子坐标（无目标格子时）
            send_coordinates(closest_blob_coords[0], closest_blob_coords[1])
    else:
        print(f"序号 {naqi_qizixuhao} 对应的子区域未找到棋子")

    task2_running = False  # 执行结束设为False
def select_forerunner(choice):
    global CURRENT_PLAYER, GAME_STARTED, board, ninepoints  # 显式声明使用全局变量
    CURRENT_PLAYER = COMPUTER if choice == 0 else PLAYER
    GAME_STARTED = False
    print("先手已设置为:", "电脑" if choice == 0 else "玩家")

    max_attempts = 50  # 最大尝试次数（可根据实际情况调整）
    attempt = 0

    while attempt < max_attempts:
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        maxrect = max_rect(img, 54, 54)  # 保持原有检测逻辑
        if maxrect:
            ninepoints = cal_ninepoints(maxrect)  # 计算九点坐标
            break  # 检测到棋盘后退出循环
        else:
            print("未检测到棋盘，重试中...")
            time.sleep_ms(100)  # 修正为毫秒级延迟（MicroPython 支持）
            attempt += 1
    else:
        print("超时：无法检测到棋盘！")
        # 可在此处添加错误处理逻辑，例如重启检测或退出程序

    if choice == 0 and maxrect:  # 仅在检测到棋盘后让电脑落子
        computer_move(board)
def update_board_state(img):
    global board, stable_frames, ninepoints, detectrois, choice  # 显式声明使用全局变量
    player_move = None

    # 检测棋盘区域
    maxrect = max_rect(img, 54, 54)
    if maxrect is not None:
        ninepoints = cal_ninepoints(maxrect)
        detectrois = cal_roi(maxrect)

    # 初始化一个临时棋盘状态，用于存储当前检测结果
    current_board = [[' ' for _ in range(3)] for _ in range(3)]

    # 检测每个格子
    for i in range(9):
        row = i // 3
        col = i % 3
        roi = detectrois[i]

        if (roi[0] < 160 and roi[1] < 120
                and roi[0] + roi[2] < 160 and roi[1] + roi[3] < 120
                and roi[0] > 0 and roi[1] > 0 and roi[2] > 0 and roi[3] > 0):
            # 检测黑色棋子
            if choice == 1:  # 电脑先手，玩家是白色
                blobs = img.find_blobs(black_threshold, roi=roi, merge=True)
            else:  # 玩家先手，玩家是黑色
                blobs = img.find_blobs(white_threshold, roi=roi, merge=True)

            if blobs:
                current_board[row][col] = 'X' if choice == 1 else 'O'  # 更新临时棋盘状态
                stable_frames[row][col] += 1
                if stable_frames[row][col] >= STABLE_FRAME_THRESHOLD and board[row][col] == ' ':
                    player_move = (row, col)
            else:
                stable_frames[row][col] = 0

            # 检测白色棋子
            if choice == 1:  # 电脑先手，玩家是白色
                blobs = img.find_blobs(white_threshold, roi=roi, merge=True)
            else:  # 玩家先手，玩家是黑色
                blobs = img.find_blobs(black_threshold, roi=roi, merge=True)

            if blobs:
                current_board[row][col] = 'O' if choice == 1 else 'X'  # 更新临时棋盘状态
                stable_frames[row][col] += 1
                if stable_frames[row][col] >= STABLE_FRAME_THRESHOLD and board[row][col] == ' ':
                    player_move = (row, col)
            else:
                stable_frames[row][col] = 0

    # 检测棋子是否消失
    for i in range(9):
        row = i // 3
        col = i % 3
        if stable_frames[row][col] <= 0 and board[row][col] != ' ':
            # 如果棋子消失超过一定帧数，重置棋盘状态
            if stable_frames[row][col] <= -STABLE_FRAME_THRESHOLD:
                current_board[row][col] = ' '
                stable_frames[row][col] = 0  # 重置计数器

    # 更新全局棋盘状态
    board = current_board

    return player_move
# 检查是否有玩家获胜
def check_winner(board, player):
    # 检查行
    for row in board:
        if row[0] == row[1] == row[2] == player:
            return True
    # 检查列
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] == player:
            return True
    # 检查对角线
    if board[0][0] == board[1][1] == board[2][2] == player:
        return True
    if board[0][2] == board[1][1] == board[2][0] == player:
        return True
    return False

# 检查是否平局
def is_full(board):
    return all([cell != ' ' for row in board for cell in row])

# Alpha - Beta 剪枝算法，限制搜索深度
def minimax(board, depth, is_maximizing, alpha, beta, max_depth=4):
    if depth >= max_depth or check_winner(board, COMPUTER) or check_winner(board, PLAYER) or is_full(board):
        if check_winner(board, COMPUTER):
            return 1
        elif check_winner(board, PLAYER):
            return -1
        elif is_full(board):
            return 0
        return 0

    if is_maximizing:
        best_score = float('-inf')
        for i in range(3):

            for j in range(3):
                if board[i][j] == ' ':
                    board[i][j] = COMPUTER
                    score = minimax(board, depth + 1, False, alpha, beta, max_depth)
                    board[i][j] = ' '
                    best_score = max(score, best_score)
                    alpha = max(alpha, best_score)
                    if beta <= alpha:
                        break
        return best_score
    else:
        best_score = float('inf')
        for i in range(3):
            for j in range(3):
                if board[i][j] == ' ':
                    board[i][j] = PLAYER
                    score = minimax(board, depth + 1, True, alpha, beta, max_depth)
                    board[i][j] = ' '
                    best_score = min(score, best_score)
                    beta = min(beta, best_score)
                    if beta <= alpha:
                        break
        return best_score
# 电脑选择最佳移动
def find_best_move(board):
    best_score = float('-inf')
    best_move = None
    alpha = float('-inf')
    beta = float('inf')
    for i in range(3):
        for j in range(3):
            if board[i][j] == ' ':
                board[i][j] = COMPUTER
                score = minimax(board, 0, False, alpha, beta)
                board[i][j] = ' '
                if score > best_score:
                    best_score = score
                    best_move = (i, j)
    return best_move
def computer_move(board):
    move = find_best_move(board)
    if move:
        row, col = move
        board[row][col] = COMPUTER  # 使用 X 表示黑棋

        # 获取对应棋盘点坐标
        index = row * 3 + col
        x = ninepoints[index][0]
        y = ninepoints[index][1]

def change_choice(new_choice):
    global choice
    choice = new_choice
    #print(f"choice 的值已更新为: {choice}")
    # 任务1：发送棋盘状态数据
status_sent = False  # 标记是否已发送状态数据
def change_qipanzhuangtai():
    global status_sent

    if status_sent:
        return  # 如果已经发送过状态数据，则直接返回

    # 如果未发送状态数据，则发送状态数据
    if not status_sent:
        send_data(0x03, 0x01,0x01,presence_status, color_status)
        print("当前棋盘状态:")
        for col in board:
            print(col)
        print(f"存在状态: {bin(presence_status)}")
        print(f"颜色状态: {bin(color_status)}")
#
        print("发送复位指令")
        status_sent = True  # 标记状态数据已发送
def find_and_sort_blobs(roi, threshold):
    img = sensor.snapshot(chn=CAM_CHN_ID_0)
    blobs = img.find_blobs(threshold, roi=roi, merge=True)

    if blobs:
        # 提取每个blob的y坐标
        blobs_with_y = [(blob, blob.cy()) for blob in blobs]
        # 按照y坐标从小到大排序
        sorted_blobs = sorted(blobs_with_y, key=lambda x: x[1])
        return [blob[0] for blob in sorted_blobs]
    return []
def find_and_sort_blobsa(roi, threshold):
    img = sensor.snapshot(chn=CAM_CHN_ID_0)
    blobs = img.find_blobs(threshold, roi=roi, merge=True)

    if blobs:
        # 提取每个blob的y坐标
        blobs_with_y = [(blob, blob.cy()) for blob in blobs]
        print(blobs_with_y)
        # 按照y坐标从小到大排序
        sorted_blobs = sorted(blobs_with_y, key=lambda x: x[1])
        return [blob[0] for blob in sorted_blobs]
    return []
def get_sub_rois(roi, num_sub_rois=5):
    """
    将给定的 ROI 分成指定数量的子区域（从上到下平均分割）。
    :param roi: 原始 ROI，格式为 (x, y, width, height)
    :param num_sub_rois: 子区域的数量（默认为 5）
    :return: 子区域列表，每个子区域的格式为 (x, y, width, height)
    """
    x, y, w, h = roi
    sub_rois = []
    for i in range(num_sub_rois):
        sub_roi_h = h // num_sub_rois
        sub_y = y + i * sub_roi_h
        sub_rois.append((x, sub_y, w, sub_roi_h))
    return sub_rois

def draw_sub_rois(img, sub_rois, color=(255, 0, 0), thickness=2):
    """
    在图像上绘制子区域的边界框。
    :param img: 要绘制的图像对象
    :param sub_rois: 子区域列表，每个子区域的格式为 (x, y, width, height)
    :param color: 边界框颜色，默认为蓝色 (255, 0, 0)
    :param thickness: 边界框线宽，默认为 2
    """
    for i, sub_roi in enumerate(sub_rois):
        x, y, w, h = sub_roi
        img.draw_rectangle(x, y, w, h, color=color, thickness=thickness)
        img.draw_string(x + 5, y + 15, f"{i}", color=color, scale=2)  # 在子区域
def find_blobs_in_sub_rois(sub_rois, threshold):
    img = sensor.snapshot(chn=CAM_CHN_ID_0)
    blobs_list = []
    for i, sub_roi in enumerate(sub_rois):
        blobs = img.find_blobs(threshold, roi=sub_roi, merge=True)
        if blobs:
            # 获取第一个blob的中心坐标
            blob = blobs[0]
            cx = blob.cx()
            cy = blob.cy()
            blobs_list.append((i, cx, cy))  # 存储索引和坐标
    return blobs_list
def get_qipan_coordinates(grid_index):
    """根据格子索引（0-8）获取棋盘坐标"""
    if 0 <= grid_index < 9:
        return ninepoints[grid_index]
    else:
        print(f"错误：无效的格子索引 {grid_index}，应在 0-8 之间")
        return (0, 0)
def get_qihe_status(board):
    """根据 qizi_status 计算棋盒状态（存在的棋子对应位设为1）"""
    status = 0x000001FF  # 初始状态，假设所有棋子存在（需根据实际逻辑调整）
    # 遍历每个棋子状态，存在的棋子对应的位设为1
    for key, exists in qizi_status.items():
        if not exists:  # exists为False表示棋子存在（未被取出）
            # 假设棋子序号对应位的位置（0x00到0x09对应位0到9）
            status |= 1 << key
    return status & 0x000003FF  # 确保只保留低10位（假设棋盒有10个棋子）
def calculate_board_angle(rect):
    corners = rect.corners()
    # 选择相邻两个角点计算角度
    x1, y1 = corners[0]
    x2, y2 = corners[1]
    dx = x2 - x1
    dy = y2 - y1
    angle = math.atan2(dy, dx) * 180 / math.pi
    return angle

# 新增一个全局标志，用于记录send_data是否已经被调用
sent_flag = False

def evaluate_game_status(board, presence_status, color_status):
    global game_over, task4_start, task5_executed, sent_flag  # 使用全局标志

    if game_over:  # 已结束则不再处理
        return 0

    # 判断玩家获胜
    if check_winner(board, PLAYER):
        if not sent_flag:
            print("电脑获胜！")
            send_data(0x05, 0xaa, 0x03, presence_status, color_status)
            sent_flag = True
        return 1  # 玩家获胜

    # 判断电脑获胜
    elif check_winner(board, COMPUTER):
        if not sent_flag:
            print("玩家获胜！")
            send_data(0x05, 0xaa, 0x03, presence_status, color_status)
            sent_flag = True
        return 2  # 电脑获胜

    # 判断平局
    if is_full(board):
        if not sent_flag:
            print("平局！")
            send_data(0x05, 0xaa, 0x03, presence_status, color_status)
            sent_flag = True
        return 3  # 平局

    return 0  # 游戏继续
sent_flaga = False
def evaluate_game_statusa(board, presence_status, color_status):
    global game_over, task4_start, task5_executed, sent_flaga  # 使用全局标志

    if game_over:  # 已结束则不再处理
        return 0

    # 判断玩家获胜
    if check_winner(board, PLAYER):
        if not sent_flaga:
            print("玩家获胜！")
            send_data(0x05, 0xaa, 0x03, presence_status, color_status)
            sent_flaga = True
        return 1  # 玩家获胜

    # 判断电脑获胜
    elif check_winner(board, COMPUTER):
        if not sent_flaga:
            print("电脑获胜！")
            send_data(0x05, 0xaa, 0x03, presence_status, color_status)
            sent_flaga = True
        return 2  # 电脑获胜

    # 判断平局
    if is_full(board):
        if not sent_flaga:
            print("平局！")
            send_data(0x05, 0xaa, 0x03, presence_status, color_status)
            sent_flaga = True
        return 3  # 平局

    return 0  # 游戏继续

##############################################

##################任务函数#####################

def task1(qizixuhao, geziweizhi):
    global qihe_status, nineqihe, coordinates_acquired, presence_status, color_status

    if not coordinates_acquired:
        qihe_status = get_qihe_status(board)
        update_nineqihe(qihe_status)

        # 获取棋盒坐标
        if qizixuhao not in qihe_coordinates:
            print(f"错误：未知棋子序号 0x{qizixuhao:02X}")
            return
        qh_x, qh_y = qihe_coordinates[qizixuhao]

        # 获取棋盘坐标
        grid_coords = get_qipan_coordinates(geziweizhi)
        if not grid_coords:
            return
        qp_x, qp_y = grid_coords

#        # 发送坐标数据
#        data = (
#            float_to_bytes(qh_x) + float_to_bytes(qh_y) +
#            float_to_bytes(qp_x) + float_to_bytes(qp_y)
#        )
#        frame = build_frame(data)
#        uart.write(frame)
#        print(f"发送坐标：棋盒({qh_x:.2f}, {qh_y:.2f}) -> 棋盘({qp_x:.2f}, {qp_y:.2f})")
        coordinates_acquired = True

    # 更新棋盒状态（保持原有逻辑）
    if 0x00 <= qizixuhao <= 0x04:
        position = qizixuhao
        qihe_status &= ~(1 << (8 - position))
    elif 0x05 <= qizixuhao <= 0x09:
        position = qizixuhao - 5
        qihe_status &= ~(1 << (13 - position))
    qizi_status[qizixuhao] = True
def task3_send_angle(angle):
    global ANGLE_SENT
    if not ANGLE_SENT:
        angle_bytes = float_to_bytes(angle)
        frame = build_frame(bytes([0x07])+angle_bytes)
        uart.write(frame)
        print(f"棋盘与水平的夹角为：{angle:.2f}度")
        ANGLE_SENT = True
zuobi_flag = 0





def task5_player_fore(img):
    global move_flaga, choice,task, abcd_flag, zuobi_flag,abcde_flag, sen_flag, computer_need_to_move, qizi_status, AI_CHESS_ORDER, board, ninepoints, qihe_coordinates, game_overmove_flag, zuobi_flag, task, choice, task2_running, task4_executed, computer_move_executed, presence_status, color_status, last_board_state, last_piece_count, last_piece_positions, game_over, first_send_black_coords, first_move_flag_1_send, first_move_flag_7_send,  computer_thought_once, cheat_detected, ret_first_cnt, hand_second_cnt,move_flagb, zuobi_flag, task, abcd_flag, abcde_flag, sen_flag, sub_task_id, task_id, choice, task2_running, task4_executed, computer_move_executed, presence_status, color_status, last_board_state, last_piece_count, last_piece_positions, game_over, first_send_black_coords, first_move_flag_1_send, first_move_flag_7_send, computer_thought_once, cheat_detected, first_piece_positions, first_piece_count, second_piece_positions, second_piece_count, first_record_done, second_record_done, cheat_reported
    # 初始化新的标志变量
    if 'computer_thought_oncea' not in globals():
        global computer_thought_oncea
        computer_thought_oncea = False
    if 'first_piece_positions' not in globals():
        first_piece_positions = {}
        first_piece_count = 0
        second_piece_positions = {}
        second_piece_count = 0
        computer_thought_once = False
        cheat_detected = False
        first_record_done = False  # 标记第一次记录是否完成
        second_record_done = False  # 标记第二次记录是否完成
        cheat_reported = False  # 标记是否已经报告过作弊（但此处改为每次检测独立处理）

    if not task5_executed:
        if not initialized:
            change_choice(1)      # 设置玩家为先手
#            print("任务5启动：玩家先手")
#        task = True
#        task5_executed = True

    if move_flaga == 4 and abcd_flag:
        abcde_flag = 1
        sen_flag = 1
        update_board_state(img)
        presence_status = get_chess_presence_status(board)
        color_status = get_chess_color_status(board)
        change_qipanzhuangtai()
        # 评估游戏状态，若已结束则设置 game_over 并返回
        game_status = evaluate_game_statusa(board, presence_status, color_status)
        first_piece_positions.clear()
        for i in range(3):
            for j in range(3):
                if board[i][j] != ' ':
                    grid_index = i * 3 + j
                    first_piece_positions[grid_index] = (ninepoints[grid_index][0], ninepoints[grid_index][1])  # 记录格子索引对应的坐标
        first_piece_count = sum(1 for row in board for cell in row if cell != ' ')
        # 打印棋子坐标
        first_piece_coords = ", ".join([f"({x:.2f}, {y:.2f})" for x, y in first_piece_positions.values()])
        print(f"第一次棋子位置记录完成，当前棋子数: {first_piece_count}，坐标分别为：{first_piece_coords}")
        first_record_done = True  # 标记第一次记录完成
        abcd_flag = 0

    if move_flaga == 1 and not computer_thought_oncea:  # 电脑落子逻辑
        move = find_best_move(board)
        if move:
            row, col = move
            # 任务5中电脑拿白棋，使用PLAYER标记（原COMPUTER是黑棋，此处改为PLAYER）
            board[row][col] = PLAYER
            index = row * 3 + col
            x_computer, y_computer = ninepoints[index]
            blobs = find_and_sort_blobsa(roi_baiqi, white_threshold)  # 白棋检测阈值和区域
            if blobs:
                x, y = blobs[0].cx(), blobs[0].cy()
                print(f"发送白棋坐标（y最小）: ({x}, {y})")
                print(f"电脑在位置 ({row}, {col}) 落子，坐标({x_computer}, {y_computer})")
                send_data_frame(x, y, x_computer, y_computer)
            computer_thought_oncea = True  # 标记电脑已思考过。



    if move_flaga == 5 :
        abcd_flag = 1

    if move_flaga == 2:
        if abcde_flag:
            abcd_flag = 1
            # 仅在棋子总数不变时检测位置变化
            second_piece_positions.clear()
            for i in range(3):
                for j in range(3):
                    if board[i][j] != ' ':
                        grid_index = i * 3 + j
                        second_piece_positions[grid_index] = (ninepoints[grid_index][0], ninepoints[grid_index][1])
            second_piece_count = sum(1 for row in board for cell in row if cell != ' ')
            # 打印棋子坐标
            second_piece_coords = ", ".join([f"({x:.2f}, {y:.2f})" for x, y in second_piece_positions.values()])
            print(f"第二次棋子位置记录完成，当前棋子数: {second_piece_count}，坐标分别为：{second_piece_coords}")
            second_record_done = True  # 标记第二次记录完成
            abcde_flag = 0
        if first_piece_count == second_piece_count and first_piece_count > 0:
            moved_pieces = []
            # 查找第一次存在但位置变化或消失后出现在新位置的棋子
            for grid_idx, (x1, y1) in first_piece_positions.items():
                if grid_idx in second_piece_positions:
                    x2, y2 = second_piece_positions[grid_idx]
                    if (x1 != x2) or (y1 != y2):  # 坐标不同则视为移动
                        moved_pieces.append(((x1, y1), (x2, y2)))
                else:
                    # 第一次存在但第二次消失，检查是否出现在新格子
                    for new_grid_idx, (x2, y2) in second_piece_positions.items():
                        if new_grid_idx not in first_piece_positions:
                            moved_pieces.append(((x1, y1), (x2, y2)))
                            break  # 每个消失的棋子只对应一个新增的棋子（总数不变）

            # 处理检测结果（移除cheat_reported限制，每次有移动就执行）
            if len(moved_pieces) > 0:  # 关键修改：删除 and not cheat_reported
                cheat_detected = True
                # 取第一个检测到的移动（避免重复检测，但允许每次检测都触发）
                from_coord, to_coord = moved_pieces[0]
                if sen_flag:
                    print(f"棋子从 ({from_coord[0]:.2f}, {from_coord[1]:.2f}) 移动到 ({to_coord[0]:.2f}, {to_coord[1]:.2f})")
                    send_data_frame(to_coord[0], to_coord[1], from_coord[0], from_coord[1])
                    # 移动棋子回去
                    for i in range(3):
                        for j in range(3):
                            grid_index = i * 3 + j
                            if second_piece_positions.get(grid_index) == to_coord:
                                board[i][j] = ' '  # 清空当前位置
                    for grid_idx, coord in first_piece_positions.items():
                        if coord == from_coord:
                            row = grid_idx // 3
                            col = grid_idx % 3
                            # 假设棋子是 COMPUTER 类型，你可以根据实际情况修改
                            board[row][col] = COMPUTER
                    sen_flag = 0
                # 不需要标记cheat_reported，下次检测会重新计算
            elif len(moved_pieces) == 0:
                cheat_detected = False
                move_flaga = 5  # 无作弊，恢复正常流程
        else:
            # 棋子总数变化（正常落子或取子）
            cheat_detected = False
            move_flaga = 5
            first_piece_positions.clear()  # 清空记录，准备下次检测
            second_piece_positions.clear()
zuobi_flag = 0
# 在文件开头部分添加
first_send_black_coords = False
abcd_flag = 1
abcde_flag = 1
sen_flag = 1
def task6_computer_fore(img):
    global move_flagb, zuobi_flag, task, abcd_flag, abcde_flag, sen_flag, sub_task_id, task_id, choice, task2_running, task4_executed, computer_move_executed, presence_status, color_status, last_board_state, last_piece_count, last_piece_positions, game_over, first_send_black_coords, first_move_flag_1_send, first_move_flag_7_send, computer_thought_once, cheat_detected, first_piece_positions, first_piece_count, second_piece_positions, second_piece_count, first_record_done, second_record_done, cheat_reported  # 显式声明所有使用的全局变量

    # 初始化标志变量（仅在首次运行时执行）
    if 'first_piece_positions' not in globals():
        first_piece_positions = {}
        first_piece_count = 0
        second_piece_positions = {}
        second_piece_count = 0
        computer_thought_once = False
        cheat_detected = False
        first_record_done = False  # 标记第一次记录是否完成
        second_record_done = False  # 标记第二次记录是否完成
        cheat_reported = False  # 标记是否已经报告过作弊（但此处改为每次检测独立处理）

    # 游戏已结束则直接返回
    if game_over:
        return

    # 记录第一次棋子位置（sub_task_id=0x04 对应 FF 04 04 FE）
    if move_flagb == 4 and abcd_flag:
        abcde_flag = 1
        sen_flag = 1
        update_board_state(img)
        presence_status = get_chess_presence_status(board)
        color_status = get_chess_color_status(board)
        change_qipanzhuangtai()
        game_status = evaluate_game_status(board, presence_status, color_status)
        first_piece_positions.clear()
        for i in range(3):
            for j in range(3):
                if board[i][j] != ' ':
                    grid_index = i * 3 + j
                    first_piece_positions[grid_index] = (ninepoints[grid_index][0], ninepoints[grid_index][1])  # 记录格子索引对应的坐标
        first_piece_count = sum(1 for row in board for cell in row if cell != ' ')
        # 打印棋子坐标
        first_piece_coords = ", ".join([f"({x:.2f}, {y:.2f})" for x, y in first_piece_positions.values()])
        print(f"第一次棋子位置记录完成，当前棋子数: {first_piece_count}，坐标分别为：{first_piece_coords}")
        first_record_done = True  # 标记第一次记录完成
        abcd_flag = 0

    # 任务初始化逻辑（保持原有逻辑）
    if not task4_executed:
        if not initialized:
            change_choice(0)  # 电脑先手
            move = find_best_move(board)
            row, col = move
            # 任务5中电脑拿白棋，使用PLAYER标记（原COMPUTER是黑棋，此处改为PLAYER）
            board[1][1] = COMPUTER  # 第五格对应的行和列索引是1和1
            index = 1 * 3 + 1  # 第五格的索引是4
            x_computer, y_computer = ninepoints[index]
            print(f"电脑初始落子：({row}, {col})，坐标({x_computer}, {y_computer})")
            blobs = find_and_sort_blobs(roi_heiqi, black_threshold)
            if blobs and not first_send_black_coords:
                x, y = blobs[0].cx(), blobs[0].cy()
                print(f"发送黑棋坐标（y最小）: ({x}, {y})")
                print(f"电脑在位置 ({row}, {col}) 落子，坐标({x_computer}, {y_computer})")
                send_data_frame(x, y, x_computer, y_computer)
                first_send_black_coords = True
        task4_executed = True

    # 电脑落子逻辑（保持原有逻辑）
    if move_flagb == 1 and not computer_thought_once:
        move = find_best_move(board)
        if move:
            if board == [
                ['X', ' ', ' '],
                [' ', 'X', ' '],
                [' ', 'O', 'O']
            ]:
                # 这里可能是想给 row 和 col 赋值
                row, col = 2, 0
            elif board == [
               ['X', ' ', 'O'],
               [' ', 'X', ' '],
               ['X', 'O', 'O']
            ]:
               # 这里可能是想给 row 和 col 赋值
                row, col = 1, 0
            elif board == [
              ['X', 'O', ' '],
              [' ', 'X', ' '],
              [' ', ' ', 'O']
            ]:
              # 这里可能是想给 row 和 col 赋值
                row, col = 2, 0
            elif board == [
              ['X', 'O', 'O'],
              [' ', 'X', ' '],
              ['X', ' ', 'O']
            ]:
             # 这里可能是想给 row 和 col 赋值
                row, col = 1, 0
            elif board == [
               ['X', ' ', 'X'],
               [' ', 'X', 'O'],
               ['O', ' ', 'O']
            ]:
               # 这里可能是想给 row 和 col 赋值
                row, col = 0, 1
            elif board == [
               ['X', 'X', 'O'],
              ['O', 'X', ' '],
              [' ', ' ', 'O']
             ]:
              # 这里可能是想给 row 和 col 赋值
                row, col = 2, 1
            elif board == [
               ['X', ' ', 'O'],
              [' ', 'X', 'X'],
              [' ', 'O', 'O']
             ]:
              # 这里可能是想给 row 和 col 赋值
                row, col = 1, 1
            elif board == [
               ['X', ' ', ' '],
              [' ', 'X', ' '],
              ['O', ' ', 'O']
             ]:
              # 这里可能是想给 row 和 col 赋值
                row, col = 2, 1
            elif board == [
               ['X', ' ', ' '],
              [' ', 'X', 'O'],
              ['O', 'X', 'O']
             ]:
              # 这里可能是想给 row 和 col 赋值
                row, col = 0, 1
            elif board == [
               ['O', 'X', ' '],
              ['O', 'X', ' '],
              [' ', ' ', ' ']
             ]:
              # 这里可能是想给 row 和 col 赋值
                row, col = 2, 1
            else:
                row, col = move
            board[row][col] = COMPUTER
            index = row * 3 + col
            x_computer, y_computer = ninepoints[index]
            blobs = find_and_sort_blobs(roi_heiqi, black_threshold)
            if blobs:
                x, y = blobs[0].cx(), blobs[0].cy()
                send_data_frame(x, y, x_computer, y_computer)
            computer_thought_once = True

    # 作弊检测核心逻辑（关键修改：移除cheat_reported限制，每次满足条件都执行）
    if move_flagb == 2:
        if abcde_flag:
            abcd_flag = 1
            # 仅在棋子总数不变时检测位置变化
            second_piece_positions.clear()
            for i in range(3):
                for j in range(3):
                    if board[i][j] != ' ':
                        grid_index = i * 3 + j
                        second_piece_positions[grid_index] = (ninepoints[grid_index][0], ninepoints[grid_index][1])
            second_piece_count = sum(1 for row in board for cell in row if cell != ' ')
            # 打印棋子坐标
            second_piece_coords = ", ".join([f"({x:.2f}, {y:.2f})" for x, y in second_piece_positions.values()])
            print(f"第二次棋子位置记录完成，当前棋子数: {second_piece_count}，坐标分别为：{second_piece_coords}")
            second_record_done = True  # 标记第二次记录完成
            abcde_flag = 0
        if first_piece_count == second_piece_count and first_piece_count > 0:
            moved_pieces = []
            # 查找第一次存在但位置变化或消失后出现在新位置的棋子
            for grid_idx, (x1, y1) in first_piece_positions.items():
                if grid_idx in second_piece_positions:
                    x2, y2 = second_piece_positions[grid_idx]
                    if (x1 != x2) or (y1 != y2):  # 坐标不同则视为移动
                        moved_pieces.append(((x1, y1), (x2, y2)))
                else:
                    # 第一次存在但第二次消失，检查是否出现在新格子
                    for new_grid_idx, (x2, y2) in second_piece_positions.items():
                        if new_grid_idx not in first_piece_positions:
                            moved_pieces.append(((x1, y1), (x2, y2)))
                            break  # 每个消失的棋子只对应一个新增的棋子（总数不变）

            # 处理检测结果（移除cheat_reported限制，每次有移动就执行）
            if len(moved_pieces) > 0:  # 关键修改：删除 and not cheat_reported
                cheat_detected = True
                # 取第一个检测到的移动（避免重复检测，但允许每次检测都触发）
                from_coord, to_coord = moved_pieces[0]
                if sen_flag:
                    print(f"棋子从 ({from_coord[0]:.2f}, {from_coord[1]:.2f}) 移动到 ({to_coord[0]:.2f}, {to_coord[1]:.2f})")
                    send_data_frame(to_coord[0], to_coord[1], from_coord[0], from_coord[1])
                    # 移动棋子回去
                    for i in range(3):
                        for j in range(3):
                            grid_index = i * 3 + j
                            if second_piece_positions.get(grid_index) == to_coord:
                                board[i][j] = ' '  # 清空当前位置
                    for grid_idx, coord in first_piece_positions.items():
                        if coord == from_coord:
                            row = grid_idx // 3
                            col = grid_idx % 3
                            # 假设棋子是 COMPUTER 类型，你可以根据实际情况修改
                            board[row][col] = COMPUTER
                    sen_flag = 0
                # 不需要标记cheat_reported，下次检测会重新计算
            elif len(moved_pieces) == 0:
                cheat_detected = False
                move_flagb = 5  # 无作弊，恢复正常流程
        else:
            # 棋子总数变化（正常落子或取子）
            cheat_detected = False
            move_flagb = 5
            first_piece_positions.clear()  # 清空记录，准备下次检测
            second_piece_positions.clear()

    # 其他状态处理（保持原有逻辑）
    if move_flagb == 5:
        abcd_flag = 1


##############################################

##################主函数#####################
frame_counter = 0
draw_interval = 15  # 每10帧绘制一次

try:
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id, width=160, height=120)
    # 重置摄像头sensor
    sensor.reset()

    # 无需进行镜像和翻转
    # 设置不要水平镜像
    sensor.set_hmirror(True)
    # 设置不要垂直翻转
    sensor.set_vflip(True)

    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    # 设置通道0的输出像素格式为RGB565，要注意有些案例只支持GRAYSCALE格式
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

    fps = time.clock()
    roi_heiqi_sub = get_sub_rois(roi_heiqi)
    roi_baiqi_sub = get_sub_rois(roi_baiqi)
    # send_data_frame(160, 0, 0,120)
    while True:
        os.exitpoint()
        fps.tick()
        current_time = time.ticks_ms()  # 获取当前时间（单位：毫秒）
        presence_status = get_chess_presence_status(board)
        color_status = get_chess_color_status(board)
        receive_and_unpack()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        update_board_state(img)  # 更新棋盘状态
        img.draw_rectangle(roi_qipan, color=(120, 0, 120), thickness=2)
        img.draw_rectangle(roi_heiqi, color=(120, 0, 120), thickness=2)
        img.draw_rectangle(roi_baiqi, color=(120, 0, 120), thickness=2)
#        board1 = [
#                    ['O', ' ', 'X'],
#                    [' ', 'O', ' '],
#                    ['O', 'X', 'X']
#                ]
#        best_move1 = find_best_move(board1)
#        print(f"情境1：电脑的最佳落子位置：{best_move1}")  # 应该是 (0, 2)
#        print("当前棋盘状态1:")
#        for col in board:
#            print(col)
#        print(f"存在状态: {bin(presence_status)}")
#        print(f"颜色状态: {bin(color_status)}")
        if task4_start:
            task6_computer_fore(img)
        if task5_start:
            task5_player_fore(img)
        if task6_start:
            task6_computer_fore(img)

        maxrect = max_rect(img, 54, 54)
        if maxrect is not None:
            ninepoints = cal_ninepoints(maxrect)
            draw_ninepoints(img, ninepoints, board)
            boardlines = cal_boardlines(maxrect)
            draw_board(img, maxrect, boardlines)
            detectrois = cal_roi(maxrect)
            board_angle = calculate_board_angle(maxrect)
#        if frame_counter % draw_interval == 0:
#            send_data_frame(0, 0, 160,120)
        frame_counter += 1
        Display.show_image(img, x=0, y=0, layer=Display.LAYER_OSD0)
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
uart.deinit()


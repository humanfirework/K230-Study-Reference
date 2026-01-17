# 导入必要的库和模块
import time, os, sys
import math
import cv_lite  # 导入cv_lite扩展模块，用于图像处理
import ulab.numpy as np  # 导入numpy库，用于数值计算
from media.sensor import *  # 导入传感器相关模块
from media.display import *  # 导入显示相关模块
from media.media import *  # 导入媒体管理模块
from machine import UART, FPIOA  # 导入UART和FPIOA模块，用于串口通信

# --------------------------- 硬件初始化 ---------------------------
# 串口初始化
# 创建FPIOA对象并配置引脚功能
fpioa = FPIOA()
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)  # 将引脚11映射为UART2发送端
fpioa.set_function(12, FPIOA.UART2_RXD)  # 将引脚12映射为UART2接收端

# UART串口初始化
# 参数说明：UART2, 波特率115200, 8位数据位, 无校验位, 1位停止位
uart2 = UART(UART.UART2, baudrate=115200, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)

# 屏幕分辨率设置
lcd_width = 800   # LCD屏幕宽度
lcd_height = 480  # LCD屏幕高度

# 摄像头初始化（修改为与其他文件一致的方式）
sensor_id = 2  # 传感器ID
sensor = Sensor(id=sensor_id)  # 创建传感器对象
sensor.reset()  # 重置传感器
# 设置图像帧大小为320x240，使用通道CAM_CHN_ID_0
sensor.set_framesize(width=320, height=240, chn=CAM_CHN_ID_0)
# 设置像素格式为灰度图，用于矩形检测；保留彩色用于紫色色块检测
sensor.set_pixformat(Sensor.GRAYSCALE, chn=CAM_CHN_ID_0)

# 显示初始化
Display.init(Display.ST7701, width=lcd_width, height=lcd_height, to_ide=False)  # 初始化ST7701显示屏
MediaManager.init()  # 初始化媒体管理器
sensor.run()  # 启动传感器

# --------------------------- 配置参数 ---------------------------
# 矩形检测核心参数（基于cv_lite）
canny_thresh1      = 50        # Canny边缘检测低阈值
canny_thresh2      = 150       # Canny边缘检测高阈值
approx_epsilon     = 0.04      # 多边形拟合精度（越小越精确）
area_min_ratio     = 0.005     # 最小面积比例（相对于图像总面积）
max_angle_cos      = 0.3       # 角度余弦阈值（越小越接近矩形）
gaussian_blur_size = 3         # 高斯模糊核尺寸（奇数）

# 原有筛选参数
MIN_AREA = 100               # 最小面积阈值
MAX_AREA = 50000             # 最大面积阈值（增大以识别大矩形）
MIN_ASPECT_RATIO = 0.3        # 最小宽高比
MAX_ASPECT_RATIO = 3.0        # 最大宽高比

# 虚拟坐标与圆形参数
BASE_RADIUS = 30              # 基础半径（虚拟坐标单位）
POINTS_PER_CIRCLE = 24        # 圆形采样点数量

# 基础矩形参数（固定方向，不再自动切换）
RECT_WIDTH = 210    # 固定矩形宽度
RECT_HEIGHT = 95    # 固定矩形高度
# 移除自动切换方向的逻辑，始终使用固定宽高的虚拟矩形

# 坐标差值变量
diff_x = 0  # X轴坐标差值
diff_y = 0  # Y轴坐标差值

# 激光点坐标（紫色色块中心点）
laser_x, laser_y = 197, 109

# 添加用于存储上一帧差值的变量
prev_diff_x, prev_diff_y = 0, 0  # 上一帧的X、Y轴坐标差值

# 二值化参数
binary_value = [(24, 101)]  # 二值化阈值范围

# --------------------------- 工具函数 ---------------------------
def calculate_distance(p1, p2):
    """计算两点之间的欧几里得距离

    Args:
        p1 (tuple): 第一个点的坐标 (x, y)
        p2 (tuple): 第二个点的坐标 (x, y)

    Returns:
        float: 两点之间的距离
    """
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])** 2)

def calculate_center(points):
    """计算点集的中心点坐标

    Args:
        points (list): 点坐标列表，每个点为 (x, y) 元组

    Returns:
        tuple: 中心点坐标 (x, y)，如果输入为空则返回 (0, 0)
    """
    if not points:
        return (0, 0)
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    return (sum_x / len(points), sum_y / len(points))

def is_valid_rect(corners):
    """验证矩形是否有效

    通过以下条件验证矩形有效性：
    1. 对边比例校验：检查相对边长度比例是否在合理范围内
    2. 面积校验：检查矩形面积是否在设定的阈值范围内
    3. 宽高比校验：检查矩形宽高比是否在合理范围内

    Args:
        corners (list): 矩形四个角点的坐标列表

    Returns:
        bool: 如果矩形有效返回True，否则返回False
    """
    # 计算四条边的长度
    edges = [calculate_distance(corners[i], corners[(i+1)%4]) for i in range(4)]

    # 对边比例校验：检查相对边长度比例是否在合理范围内
    ratio1 = edges[0] / max(edges[2], 0.1)
    ratio2 = edges[1] / max(edges[3], 0.1)
    valid_ratio = 0.5 < ratio1 < 1.5 and 0.5 < ratio2 < 1.5

    # 面积校验：使用向量叉积计算面积，并检查是否在阈值范围内
    area = 0
    for i in range(4):
        x1, y1 = corners[i]
        x2, y2 = corners[(i+1) % 4]
        area += (x1 * y2 - x2 * y1)
    area = abs(area) / 2
    valid_area = MIN_AREA < area < MAX_AREA

    # 宽高比校验：计算矩形的宽高比并检查是否在合理范围内
    width = max(p[0] for p in corners) - min(p[0] for p in corners)
    height = max(p[1] for p in corners) - min(p[1] for p in corners)
    aspect_ratio = width / max(height, 0.1)
    valid_aspect = MIN_ASPECT_RATIO < aspect_ratio < MAX_ASPECT_RATIO

    # 返回所有验证条件的结果
    return valid_ratio and valid_area and valid_aspect


def send_target_data(x, y):
    """通过UART发送目标坐标数据

    将坐标数据打包成特定格式并通过UART发送，
    根据坐标的正负值设置不同的标志位。

    数据格式：
    [0x55, 0xaa, x_sign, x_h, x_l, y_sign, y_h, y_l, 0xfa]

    Args:
        x (int): X轴坐标差值
        y (int): Y轴坐标差值
    """
    # 将坐标值分解为高低字节
    x_h = (x >> 8) & 0xFF  # X坐标高8位
    x_l = x & 0xFF         # X坐标低8位
    y_h = (y >> 8) & 0xFF  # Y坐标高8位
    y_l = y & 0xFF         # Y坐标低8位

    # 根据坐标正负值设置标志位并发送数据
    if x > 0 and y > 0:
        # 第一象限：X正，Y正
        uart2.write(bytearray([0x55, 0xaa, 0x00, int(x_h) & 0xFF, int(x_l) & 0xFF, 0x00, int(y_h) & 0xFF, int(y_l) & 0xFF, 0xfa]))
    elif x < 0 and y < 0:
        # 第三象限：X负，Y负
        uart2.write(bytearray([0x55, 0xaa, 0x01, int(x_h) & 0xFF, int(x_l) & 0xFF, 0x01, int(y_h) & 0xFF, int(y_l) & 0xFF, 0xfa]))
    elif x > 0 and y < 0:
        # 第四象限：X正，Y负
        uart2.write(bytearray([0x55, 0xaa, 0x00, int(x_h) & 0xFF, int(x_l) & 0xFF, 0x01, int(y_h) & 0xFF, int(y_l) & 0xFF, 0xfa]))
    elif x < 0 and y > 0:
        # 第二象限：X负，Y正
        uart2.write(bytearray([0x55, 0xaa, 0x01, int(x_h) & 0xFF, int(x_l) & 0xFF, 0x00, int(y_h) & 0xFF, int(y_l) & 0xFF, 0xfa]))

    # 刷新UART缓冲区
    uart2.flush()

def get_perspective_matrix(src_pts, dst_pts):
    """计算透视变换矩阵

    使用四对对应点计算3x3透视变换矩阵，用于将虚拟坐标映射到图像坐标。
    通过求解线性方程组来获得变换矩阵参数。

    Args:
        src_pts (list): 源点坐标列表，每个点为 (x, y) 元组
        dst_pts (list): 目标点坐标列表，每个点为 (x, y) 元组

    Returns:
        list: 3x3透视变换矩阵，如果计算失败则返回None
    """
    # 构建线性方程组的系数矩阵A和常数向量B
    A = []
    B = []
    for i in range(4):
        x, y = src_pts[i]
        u, v = dst_pts[i]
        # 根据透视变换的数学原理构建方程组
        A.append([x, y, 1, 0, 0, 0, -u*x, -u*y])
        A.append([0, 0, 0, x, y, 1, -v*x, -v*y])
        B.append(u)
        B.append(v)

    # 使用高斯消元法求解线性方程组
    n = 8
    for i in range(n):
        # 选择主元以提高数值稳定性
        max_row = i
        for j in range(i, len(A)):
            if abs(A[j][i]) > abs(A[max_row][i]):
                max_row = j
        A[i], A[max_row] = A[max_row], A[i]
        B[i], B[max_row] = B[max_row], B[i]

        # 检查主元是否接近零
        pivot = A[i][i]
        if abs(pivot) < 1e-8:
            return None

        # 归一化主行
        for j in range(i, n):
            A[i][j] /= pivot
        B[i] /= pivot

        # 消元
        for j in range(len(A)):
            if j != i and A[j][i] != 0:
                factor = A[j][i]
                for k in range(i, n):
                    A[j][k] -= factor * A[i][k]
                B[j] -= factor * B[i]

    # 构造并返回3x3变换矩阵
    return [
        [B[0], B[1], B[2]],
        [B[3], B[4], B[5]],
        [B[6], B[7], 1.0]
    ]

def transform_points(points, matrix):
    """应用透视变换将虚拟坐标映射到原始图像坐标

    使用给定的透视变换矩阵将一组虚拟坐标点转换为图像坐标点。

    Args:
        points (list): 虚拟坐标点列表，每个点为 (x, y) 元组
        matrix (list): 3x3透视变换矩阵

    Returns:
        list: 映射后的图像坐标点列表，每个点为 (x, y) 元组
    """
    transformed = []
    for (x, y) in points:
        # 应用透视变换公式
        x_hom = x * matrix[0][0] + y * matrix[0][1] + matrix[0][2]
        y_hom = x * matrix[1][0] + y * matrix[1][1] + matrix[1][2]
        w_hom = x * matrix[2][0] + y * matrix[2][1] + matrix[2][2]

        # 检查齐次坐标的分母是否接近零
        if abs(w_hom) > 1e-8:
            # 转换为笛卡尔坐标
            transformed.append((x_hom / w_hom, y_hom / w_hom))
    return transformed

def sort_corners(corners):
    """将矩形角点按左上、右上、右下、左下顺序排序

    对检测到的矩形角点进行排序，确保它们按照标准顺序排列：
    左上 -> 右上 -> 右下 -> 左下

    Args:
        corners (list): 矩形角点坐标列表，每个点为 (x, y) 元组

    Returns:
        list: 按标准顺序排列的角点坐标列表
    """
    # 计算角点的中心位置
    center = calculate_center(corners)

    # 根据相对于中心的角度对角点进行初步排序
    sorted_corners = sorted(corners, key=lambda p: math.atan2(p[1]-center[1], p[0]-center[0]))

    # 调整顺序为左上、右上、右下、左下
    if len(sorted_corners) == 4:
        # 找到左上角点（x+y最小的点）
        left_top = min(sorted_corners, key=lambda p: p[0]+p[1])
        index = sorted_corners.index(left_top)
        # 重新排列角点顺序
        sorted_corners = sorted_corners[index:] + sorted_corners[:index]
    return sorted_corners

def get_rectangle_orientation(corners):
    """计算矩形的主方向角（水平边与x轴的夹角）

    通过计算矩形相邻边的向量，确定矩形的主要方向角。

    Args:
        corners (list): 矩形角点坐标列表，每个点为 (x, y) 元组

    Returns:
        float: 矩形主方向角（弧度），如果角点数量不为4则返回0
    """
    if len(corners) != 4:
        return 0

    # 计算上边和右边的向量
    top_edge = (corners[1][0] - corners[0][0], corners[1][1] - corners[0][1])
    right_edge = (corners[2][0] - corners[1][0], corners[2][1] - corners[1][1])

    # 选择较长的边作为主方向
    if calculate_distance(corners[0], corners[1]) > calculate_distance(corners[1], corners[2]):
        main_edge = top_edge
    else:
        main_edge = right_edge

    # 计算主方向角（弧度）
    angle = math.atan2(main_edge[1], main_edge[0])
    return angle

# --------------------------- 主循环 ---------------------------
# 初始化时钟对象用于计算FPS
clock = time.clock()
# 获取图像形状信息 [高, 宽]，用于cv_lite相关处理
image_shape = [sensor.height(), sensor.width()]

# 主循环：持续捕获图像并处理
while True:
    # 开始计时
    clock.tick()
    # 获取当前图像帧
    img = sensor.snapshot()

    # 1. 绘制固定位置的紫色中心点（激光点位置）
    # 用于视觉参考，显示目标点位置
    img.draw_circle(laser_x, laser_y, 1, color=(255, 0, 255), thickness=1)

    # 2. 矩形检测（使用内置方法替换cv_lite）
    # 2.1 将RGB图像转为灰度图（用于矩形检测）
    gray_img = img.to_grayscale()
    # 对灰度图进行二值化处理，突出矩形特征
    gray_img.binary(binary_value)

    # 2.2 使用内置方法检测矩形
    # threshold参数用于控制矩形检测的敏感度，值越小检测越敏感
    detected_rects = gray_img.find_rects(threshold=10000)  # 调整threshold参数以更好地检测大矩形  # pyright: ignore[reportUnreachable]

    # 2.3 将检测到的矩形转换为与cv_lite兼容的格式
    # 便于后续处理和筛选
    rects = []
    for r in detected_rects:
        # 提取矩形的四个角点坐标
        corners = r.corners()
        if len(corners) == 4:  # 确保检测到的矩形有4个角点
            # 将矩形数据转换为统一格式：[x, y, w, h, c1.x, c1.y, c2.x, c2.y, c3.x, c3.y, c4.x, c4.y]
            rect_data = [
                r.x(), r.y(), r.w(), r.h(),  # 矩形的x坐标、y坐标、宽度、高度
                corners[0][0], corners[0][1],  # 第一个角点坐标
                corners[1][0], corners[1][1],  # 第二个角点坐标
                corners[2][0], corners[2][1],  # 第三个角点坐标
                corners[3][0], corners[3][1]   # 第四个角点坐标
            ]
            rects.append(rect_data)

    # 3. 筛选最小矩形（保留原有逻辑）
    # 初始化最小面积为无穷大，用于寻找面积最小的有效矩形
    min_area = float('inf')
    # 存储找到的最小矩形信息和角点坐标
    smallest_rect = None
    smallest_rect_corners = None  # 存储最小矩形的角点

    # 遍历所有检测到的矩形
    for rect in rects:
        # rect格式: [x, y, w, h, c1.x, c1.y, c2.x, c2.y, c3.x, c3.y, c4.x, c4.y]
        x, y, w, h = rect[0], rect[1], rect[2], rect[3]
        # 提取四个角点坐标
        corners = [
            (rect[4], rect[5]),   # 角点1
            (rect[6], rect[7]),   # 角点2
            (rect[8], rect[9]),   # 角点3
            (rect[10], rect[11])  # 角点4
        ]

        # 验证矩形有效性（通过面积、宽高比等条件筛选）
        if is_valid_rect(corners):
            # 计算矩形面积
            area = w * h  # 直接使用矩形宽高计算面积（更高效）
            # 更新最小矩形：如果当前矩形面积更小，则更新记录
            if area < min_area:
                min_area = area
                smallest_rect = (x, y, w, h)
                smallest_rect_corners = corners

    # 4. 处理最小矩形（修改后：固定虚拟矩形方向）
    # 如果找到了有效的最小矩形，则进行后续处理
    if smallest_rect and smallest_rect_corners:
        x, y, w, h = smallest_rect
        corners = smallest_rect_corners

        # 对矩形角点进行排序，确保按标准顺序排列
        sorted_corners = sort_corners(corners)

        # 计算矩形中心点坐标
        rect_center = calculate_center(sorted_corners)
        # 将中心点坐标转换为整数
        rect_center_int = (int(round(rect_center[0])), int(round(rect_center[1])))

        # 绘制从矩形中心点到紫色色块中心点(158, 91)的黄色连线
        # 用于视觉参考，显示两点之间的连接
        img.draw_line(rect_center_int[0], rect_center_int[1], 158, 91, color=(255, 255, 0), thickness=2)

        # 计算矩形中心点与激光点之间的差值
        diff_x = laser_x - rect_center_int[0]
        diff_y = laser_y - rect_center_int[1]

        # 添加差值突变检测和舍去逻辑
        # 如果当前帧与上一帧的差值突变超过阈值，则舍去当前帧数据
        THRESHOLD = 50  # 差值突变阈值，可根据实际情况调整
        if abs(diff_x - prev_diff_x) > THRESHOLD or abs(diff_y - prev_diff_y) > THRESHOLD:
            # 差值突变过大，舍去当前帧数据，不进行后续处理
            continue

        # 更新上一帧差值，用于下一帧的突变检测
        prev_diff_x, prev_diff_y = diff_x, diff_y

        # 在图像上显示两点间的差值
        img.draw_string_advanced(10, 30, 16, f"diff_x: {diff_x}, diff_y: {diff_y}", color=(255, 255, 255))

        # 计算矩形主方向角（仅用于参考，不再影响虚拟矩形方向）
        angle = get_rectangle_orientation(sorted_corners)

        # 【核心修改】移除自动切换方向逻辑，固定使用预设的虚拟矩形尺寸和方向
        # 定义固定尺寸的虚拟矩形（用于透视变换的源坐标）
        virtual_rect = [
            (0, 0),                 # 左上角
            (RECT_WIDTH, 0),        # 右上角
            (RECT_WIDTH, RECT_HEIGHT),  # 右下角
            (0, RECT_HEIGHT)        # 左下角
        ]

        # 【核心修改】固定圆形半径参数（不再根据实际宽高比调整）
        radius_x = BASE_RADIUS  # X轴半径
        radius_y = BASE_RADIUS  # Y轴半径

        # 【核心修改】固定虚拟中心（基于固定的宽高）
        virtual_center = (RECT_WIDTH / 2, RECT_HEIGHT / 2)  # 虚拟矩形的中心点

        # 在虚拟矩形中生成椭圆点集（映射后为正圆）
        # 用于创建圆形轨迹的参考点
        virtual_circle_points = []
        for i in range(POINTS_PER_CIRCLE):
            # 计算每个点的角度
            angle_rad = 2 * math.pi * i / POINTS_PER_CIRCLE
            # 计算点在虚拟矩形中的坐标
            x_virt = virtual_center[0] + radius_x * math.cos(angle_rad)
            y_virt = virtual_center[1] + radius_y * math.sin(angle_rad)
            virtual_circle_points.append((x_virt, y_virt))

        # 计算透视变换矩阵并映射坐标
        # 将虚拟坐标映射到实际图像坐标
        matrix = get_perspective_matrix(virtual_rect, sorted_corners)
        if matrix:
            # 应用透视变换将虚拟圆点映射到图像坐标
            mapped_points = transform_points(virtual_circle_points, matrix)
            # 将坐标转换为整数
            int_points = [(int(round(x)), int(round(y))) for x, y in mapped_points]

            # 绘制映射后的圆形轨迹点
            for (px, py) in int_points:
                img.draw_circle(px, py, 2, color=(255, 0, 255), thickness=2)

            # 绘制映射后的圆心
            mapped_center = transform_points([virtual_center], matrix)
            if mapped_center:
                cx, cy = map(int, map(round, mapped_center[0]))
                img.draw_circle(cx, cy, 3, color=(0, 0, 255), thickness=1)

            # 发送坐标差值数据
            send_target_data(diff_x, diff_y)

    # 5. 显示与性能统计
    # 计算并获取当前帧率
    fps = clock.fps()
    # 在图像上显示帧率信息
    img.draw_string_advanced(10, 10, 20, f"FPS: {fps:.1f}", color=(255, 255, 255))  # 显示FPS

    # 压缩图像以便在IDE中显示
    img.compressed_for_ide()

    # 在LCD屏幕上显示图像
    # 居中显示图像
    Display.show_image(img,
                      x=round((lcd_width-sensor.width())/2),
                      y=round((lcd_height-sensor.height())/2))

    # 在控制台打印帧率信息
    print(f"FPS: {fps:.1f}")  # 打印FPS

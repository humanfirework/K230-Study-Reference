from pyb import UART
import gc
import sensor, image, time

# ==================================================
# ### 调试参数区（所有可调参数集中在此，方便修改） ###
# ==================================================
## ---------------------- 图像配置 ----------------------
RESOLUTION = sensor.QQVGA  # 分辨率：sensor.QQVGA(160x120) / sensor.QVGA(320x240)
V_FLIP = True              # 垂直翻转（True/False，根据安装方向调整）
H_MIRROR = True            # 水平翻转（True/False，根据安装方向调整）
FILTER_TYPE = 'median'     # 滤波类型：'gaussian'（高斯）/'median'（中值，抗抖动更强）
FILTER_KERNEL = 3          # 滤波核大小（奇数，3=3x3，越大去噪越强但越慢）

## ---------------------- 矩形识别 ----------------------
RECT_THRESHOLD = 12000     # 矩形检测阈值（越小越灵敏，推荐10000~20000）
RECT_GRADIENT = 10         # 边缘梯度（越小检测越灵敏，推荐8~15）
MAX_HISTORY = 3            # 矩形历史记录帧数（越多跟踪越稳，推荐2~5）
INIT_CONFIRM_THRESH = 3    # 初始识别确认帧数（连续N帧才确认，推荐2~5）
RECT_INIT_DIST = 20        # 初始识别允许的中心距离（像素，推荐15~30）
RECT_TRACK_DIST = 30       # 跟踪阶段允许的中心距离（像素，推荐25~40）

## ---------------------- 激光识别 ----------------------
LASER_LAB = (91, 100, -128, 127, -128, 127)  # 激光LAB阈值（用OpenMV IDE校准）
LASER_STABLE_THRESH = 2    # 激光稳定帧数（连续N帧才确认，推荐2~4）
LASER_CIRCULARITY = 0.5    # 激光圆形度阈值（越小允许形状越不规则，推荐0.5~0.7）
BLOB_PIXEL_THRESH = 5      # 激光色块像素阈值（过滤小噪点，推荐3~10）
BLOB_AREA_THRESH = 5       # 激光色块面积阈值（过滤小区域，推荐3~10）

## ---------------------- 通信配置 ----------------------
UART_PORT_NUM = 3          # 串口号（UART3）
BAUD_RATE = 115200         # 波特率（需与STM32一致）
PROTOCOL_HEADER = "DATA"   # 串口协议头（方便STM32解析）

# ==================================================
# ### 初始化（引用调试参数区变量） ###
# ==================================================
# 摄像头初始化
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(RESOLUTION)
sensor.skip_frames(time=2000)
sensor.set_vflip(V_FLIP)
sensor.set_hmirror(H_MIRROR)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

# 串口初始化
uart = UART(UART_PORT_NUM, BAUD_RATE)
uart.init(BAUD_RATE, bits=8, parity=None, stop=1, timeout_char=1000)

# 全局变量（基于调试参数初始化）
first_rect_corners = [[0, 0] for _ in range(4)]  # 矩形顶点
history_corners = []                             # 矩形历史顶点
last_laser_x, last_laser_y = 0, 0                # 激光历史坐标
stable_count = 0                                 # 激光稳定计数器

# ==================================================
# ### 辅助函数 ###
# ==================================================
def get_rect_center(corners):
    """计算矩形中心坐标"""
    cx = sum(p[0] for p in corners) // 4
    cy = sum(p[1] for p in corners) // 4
    return (cx, cy)

def rect_distance(corners1, corners2):
    """计算两个矩形的中心距离"""
    cx1, cy1 = get_rect_center(corners1)
    cx2, cy2 = get_rect_center(corners2)
    return ((cx1 - cx2)**2 + (cy1 - cy2)**2)**0.5

# ==================================================
# ### 主逻辑 ###
# ==================================================
clock = time.clock()
while True:
    clock.tick()
    img = sensor.snapshot()

    # ---------- 1. 图像预处理（滤波） ----------
    if FILTER_TYPE == 'gaussian':
        img = img.gaussian(FILTER_KERNEL)
    elif FILTER_TYPE == 'median':
        img = img.median(FILTER_KERNEL)

    # ---------- 2. 矩形识别与跟踪 ----------
    current_rect = None
    for rect in img.find_rects(threshold=RECT_THRESHOLD,
                               x_gradient=RECT_GRADIENT,
                               y_gradient=RECT_GRADIENT):
        current_rect = rect
        break

    if current_rect:
        new_corners = current_rect.corners()
        # 初始识别验证
        if first_rect_corners == [[0, 0] for _ in range(4)]:
            if not history_corners:
                history_corners.append(new_corners)
                init_confirm_count = 1
            else:
                if rect_distance(new_corners, history_corners[-1]) < RECT_INIT_DIST:
                    init_confirm_count += 1
                    history_corners.append(new_corners)
                    if init_confirm_count >= INIT_CONFIRM_THRESH:
                        first_rect_corners = new_corners  # 确认跟踪
                else:
                    init_confirm_count = 1
                    history_corners = [new_corners]
        # 已确认，跟踪更新
        else:
            if rect_distance(new_corners, first_rect_corners) < RECT_TRACK_DIST:
                first_rect_corners = new_corners
                history_corners.append(new_corners)
                if len(history_corners) > MAX_HISTORY:
                    history_corners.pop(0)

    # ---------- 3. 激光识别与跟踪 ----------
    laser_detected = False
    laser_x, laser_y = 0, 0
    blobs = img.find_blobs(
        [LASER_LAB],
        pixels_threshold=BLOB_PIXEL_THRESH,
        area_threshold=BLOB_AREA_THRESH,
        merge=True,
        margin=2
    )

    target_blob = None
    max_brightness = 0
    for blob in blobs:
        # 圆形度筛选
        perimeter = blob.perimeter()
        circularity = 4 * 3.14159 * blob.area() / (perimeter ** 2) if perimeter > 0 else 0
        if circularity > LASER_CIRCULARITY:
            # 亮度筛选（保留最亮目标）
            stats = img.get_statistics(roi=blob.rect())
            brightness = stats.l_mean()
            if brightness > max_brightness:
                max_brightness = brightness
                target_blob = blob

    if target_blob:
        curr_x, curr_y = target_blob.cx(), target_blob.cy()
        # 坐标稳定性判断
        if abs(curr_x - last_laser_x) < 5 and abs(curr_y - last_laser_y) < 5:
            stable_count += 1
        else:
            stable_count = 1
        last_laser_x, last_laser_y = curr_x, curr_y
        if stable_count >= LASER_STABLE_THRESH:
            laser_detected = True
            laser_x, laser_y = curr_x, curr_y
            img.draw_cross(laser_x, laser_y, color=(0, 255, 0), size=8)  # 绿色十字

    # ---------- 4. 可视化绘制 ----------
    # ▶ 矩形（若检测到）
    if first_rect_corners != [[0, 0] for _ in range(4)]:
        # 白色边框
        for i in range(4):
            img.draw_line(
                first_rect_corners[i][0], first_rect_corners[i][1],
                first_rect_corners[(i+1)%4][0], first_rect_corners[(i+1)%4][1],
                color=(255, 255, 255)
            )
        # 绿色顶点
        for p in first_rect_corners:
            img.draw_circle(p[0], p[1], 3, color=(0, 255, 0))
        # 蓝色中心
        rect_center = get_rect_center(first_rect_corners)
        img.draw_circle(rect_center[0], rect_center[1], 5, color=(0, 0, 255), fill=True)

    # ▶ 画面中心（红色原点，QQVGA中心为(80,60)）
    img.draw_circle(80, 60, 3, color=(255, 0, 0), fill=True)

    # ---------- 5. 串口通信 ----------
    rect_center = get_rect_center(first_rect_corners) if first_rect_corners != [[0, 0] for _ in range(4)] else (-1, -1)
    if laser_detected and rect_center != (-1, -1):
        data = f"{PROTOCOL_HEADER},{laser_x},{laser_y},{rect_center[0]},{rect_center[1]}\r\n"
        uart.write(data.encode())
        print(f"发送: 激光({laser_x},{laser_y}) | 矩形({rect_center[0]},{rect_center[1]})")
    elif rect_center != (-1, -1):
        uart.write(f"{PROTOCOL_HEADER},-1,-1,{rect_center[0]},{rect_center[1]}\r\n".encode())
        print(f"未检测到激光 | 矩形({rect_center[0]},{rect_center[1]})")
    elif laser_detected:
        uart.write(f"{PROTOCOL_HEADER},{laser_x},{laser_y},-1,-1\r\n".encode())
        print(f"激光({laser_x},{laser_y}) | 未检测到矩形")
    else:
        uart.write(f"{PROTOCOL_HEADER},-1,-1,-1,-1\r\n".encode())
        print("未检测到矩形和激光")

    # ---------- 6. 性能与内存管理 ----------
    print(f"帧率: {clock.fps():.1f}fps")
    gc.collect()  # 强制回收内存

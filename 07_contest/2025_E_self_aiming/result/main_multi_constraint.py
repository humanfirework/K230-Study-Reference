import time, os, sys
import math
import struct
from media.sensor import *
from media.display import *
from media.media import *
from machine import FPIOA
from machine import UART
from machine import Pin

picture_width = 400
picture_height = 240
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

sensor_id = 2
sensor = None

# 可调参数
rect_binary_default = [(100, 255)]  # 默认二值化阈值
rect_binary_small = [(127, 216)]    # 面积小于500像素时的二值化阈值
rect_binary_large = [(81, 200)]   # 面积大于10000像素时的二值化阈值

# 根据面积确定二值化阈值的函数
def get_binary_threshold(area):
    if area < 5000:
        return rect_binary_small
    elif area > 5000 and area < 20000:
        return rect_binary_default
    else:
        return rect_binary_large

# 串口配置
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
fpioa.set_function(48, FPIOA.GPIO48)

uart2 = UART(UART.UART2, 115200)
LED = Pin(48, Pin.OUT, pull=Pin.PULL_NONE, drive=15)

# 屏幕中心坐标
SCREEN_CENTER_X = 200
SCREEN_CENTER_Y = 120

# 矩形数据变量
rect_corners = []
rect_center = (0, 0)
is_first_frame = True  # 标记是否为第一帧
last_frame_center = (0, 0)  # 上一帧的矩形中心点

# 目标点稳定性优化变量
last_valid_target = (0, 0)  # 上一次的有效目标坐标
current_target_count = 0     # 当前目标的连续识别计数
TARGET_STABILITY_THRESHOLD = 3  # 目标稳定阈值（连续识别次数）

# 预测提前量变量
previous_target = (0, 0)  # 上一帧的目标位置
predicted_target = (0, 0)  # 预测的目标位置

# 矩形识别参数
MIN_RECT_AREA = 500      # 最小矩形面积
MAX_RECT_AREA = 50000     # 最大矩形面积
MIN_ASPECT_RATIO = 0.5    # 最小长宽比
MAX_ASPECT_RATIO = 2.5    # 最大长宽比

# 新增：查找具有嵌套关系的矩形对
def find_nested_rects(img_binary):
    """查找具有嵌套关系的矩形对（外框+内框）"""
    # 查找所有白色连通域及其层次结构
    blobs = img_binary.find_blobs([(255, 255)], x_stride=2, y_stride=2, area_threshold=100, merge=False, margin=0)
    if not blobs:
        return None

    # 按面积排序，便于后续处理
    blobs.sort(key=lambda b: b.area(), reverse=True)
    
    # 查找嵌套的矩形对
    for i, outer_blob in enumerate(blobs):
        # 检查是否为有效外框
        outer_points = outer_blob.min_corners()
        if len(outer_points) < 4:
            continue
        
        # 新增：检查轮廓近似多边形顶点数，只有8个顶点才是目标矩形
        if len(outer_points) != 8:
            continue
        
        # 计算外框几何属性
        outer_x, outer_y, outer_w, outer_h = outer_blob.rect()
        outer_area = outer_w * outer_h
        outer_aspect_ratio = outer_w / outer_h if outer_h > 0 else 0
        
        # 新增：检查外接矩形面积与实际像素面积的比值
        # 对于双层框，这个比值应该显著大于1（接近2或更高）
        # 对于单层实心矩形，这个比值接近1
        area_ratio = outer_area / outer_blob.area() if outer_blob.area() > 0 else 0
        if area_ratio < 1.5:  # 阈值设为1.5，可区分单层和双层框
            continue
        
        # 外框几何指标过滤
        if outer_area < MIN_RECT_AREA or outer_area > MAX_RECT_AREA:
            continue
        if outer_aspect_ratio < MIN_ASPECT_RATIO or outer_aspect_ratio > MAX_ASPECT_RATIO:
            continue
        
        # 查找内框（面积较小且位于外框内部）
        for inner_blob in blobs[i+1:]:
            # 检查是否为有效内框
            inner_points = inner_blob.min_corners()
            if len(inner_points) < 4:
                continue
            
            # 计算内框几何属性
            inner_x, inner_y, inner_w, inner_h = inner_blob.rect()
            inner_area = inner_w * inner_h
            inner_aspect_ratio = inner_w / inner_h if inner_h > 0 else 0
            
            # 内框几何指标过滤
            if inner_area < MIN_RECT_AREA/4 or inner_area > outer_area/2:  # 内框面积应在合理范围
                continue
            if inner_aspect_ratio < MIN_ASPECT_RATIO or inner_aspect_ratio > MAX_ASPECT_RATIO:
                continue
            
            # 检查内框是否在外框内部
            if (inner_x > outer_x and inner_y > outer_y and 
                inner_x + inner_w < outer_x + outer_w and 
                inner_y + inner_h < outer_y + outer_h):
                # 计算外框中心点
                outer_center_x = (outer_points[0][0] + outer_points[2][0]) // 2
                outer_center_y = (outer_points[0][1] + outer_points[2][1]) // 2
                
                # 创建类似 rect 的对象
                class RectLike:
                    def __init__(self, corners, rect, center, area):
                        self._corners = corners
                        self._rect = rect
                        self._center = center
                        self._area = area

                    def corners(self):
                        return self._corners

                    def rect(self):
                        return self._rect

                    def center(self):
                        return self._center

                    def area(self):
                        return self._area
                
                return RectLike(outer_points, (outer_x, outer_y, outer_w, outer_h), (outer_center_x, outer_center_y), outer_area)
    
    return None

def find_best_rect(img_binary, is_first=False, last_center=(0, 0)):
    """根据帧数选择最佳矩形：第一帧选面积最大，后续帧优先选距离上一帧中心最近的矩形"""
    # 查找所有白色连通域
    blobs = img_binary.find_blobs([(255, 255)], x_stride=2, y_stride=2, area_threshold=100)
    if not blobs:
        return None

    valid_rects = []
    for blob in blobs:
        # 获取轮廓点
        points = blob.min_corners()
        if len(points) < 4:
            continue

        # 计算面积和长宽比
        x, y, w, h = blob.rect()
        area = w * h
        aspect_ratio = w / h if h > 0 else 0

        # 几何指标过滤
        if area < MIN_RECT_AREA or area > MAX_RECT_AREA:
            continue
        if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
            continue

        # 计算中心点
        center_x = (points[0][0] + points[2][0]) // 2
        center_y = (points[0][1] + points[2][1]) // 2

        # 创建一个类似 rect 的对象
        class RectLike:
            def __init__(self, corners, rect, center, area):
                self._corners = corners
                self._rect = rect
                self._center = center
                self._area = area

            def corners(self):
                return self._corners

            def rect(self):
                return self._rect

            def center(self):
                return self._center

            def area(self):
                return self._area

        valid_rects.append(RectLike(points, (x, y, w, h), (center_x, center_y), area))

    if not valid_rects:
        return None

    if is_first or last_center == (0, 0):
        # 第一帧或没有上一帧中心：选面积最大的
        best_rect = max(valid_rects, key=lambda r: r.area())
    else:
        # 后续帧：优先选距离上一帧中心50像素内的矩形
        nearby_rects = []
        for rect in valid_rects:
            dist = distance(rect.center(), last_center)
            if dist <= 50:  # 50像素内
                nearby_rects.append((rect, dist))

        if nearby_rects:
            # 在50像素内的矩形中选面积最大的
            best_rect = max(nearby_rects, key=lambda x: x[0].area())[0]
        else:
            # 没有50像素内的矩形，选面积最大的
            best_rect = max(valid_rects, key=lambda r: r.area())

    return best_rect


def send_combined_data(target_x, target_y):
    """发送整合的数据包（矩形坐标和目标点矩形中心）"""
    if target_x == 0 and target_y == 0:
        frame = b'\xAA' + struct.pack('<BHH', 0, target_x, target_y) + b'\x55'
        uart2.write(frame)
        uart2.flush()
        print(f"[COMBINED] 未检测到矩形，发送数据0")
        print(f"[COMBINED] 数据帧: {frame.hex().upper()}")
    else:
        frame = b'\xAA' + struct.pack('<BHH', 1, target_x, target_y) + b'\x55'
        uart2.write(frame)
        uart2.flush()
        print(f"[COMBINED] 发送整合数据:")
        print(f"[COMBINED] 目标点矩形中心: ({target_x}, {target_y})")
        print(f"[COMBINED] 数据帧: {frame.hex().upper()}")
    return frame

# 计算两点间距离
def distance(point1, point2):
    return int(math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2))


# 一维卡尔曼滤波器类
class KalmanFilter1D:
    def __init__(self, process_variance=1e-3, measurement_variance=0.1, estimated_error=1.0, initial_value=0.0):
        """
        初始化一维卡尔曼滤波器
        :param process_variance: 过程噪声方差(Q)
        :param measurement_variance: 测量噪声方差(R)
        :param estimated_error: 估计误差协方差(P)
        :param initial_value: 初始值
        """
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.estimated_error = estimated_error
        self.value = initial_value

    def update(self, measurement):
        """
        更新卡尔曼滤波器状态
        :param measurement: 测量值
        :return: 滤波后的值
        """
        # 预测步骤
        # predicted_value = self.value  # 状态预测（这里简化为恒定模型）
        predicted_error = self.estimated_error + self.process_variance  # 误差协方差预测

        # 更新步骤
        kalman_gain = predicted_error / (predicted_error + self.measurement_variance)  # 卡尔曼增益
        self.value = self.value + kalman_gain * (measurement - self.value)  # 状态更新
        self.estimated_error = (1 - kalman_gain) * predicted_error  # 误差协方差更新

        return self.value

try:
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id)
    sensor.reset()
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.GRAYSCALE, chn=CAM_CHN_ID_0)

    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

    #构造clock
    clock = time.clock()

    # 初始化卡尔曼滤波器用于平滑目标位置
    kalman_x = KalmanFilter1D(process_variance=1e-3, measurement_variance=0.1)
    kalman_y = KalmanFilter1D(process_variance=1e-3, measurement_variance=0.1)

    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 图像预处理 - 减少复制操作以提高性能
        img_gray = img.to_grayscale(copy=False)  # 直接转换，不创建副本

        # 根据上一帧矩形面积确定二值化阈值
        if last_frame_center != (0, 0) and 'max_rect' in locals() and max_rect is not None and hasattr(max_rect, 'area'):
            binary_threshold = get_binary_threshold(max_rect.area())
        else:
            binary_threshold = rect_binary_default
        
        # 二值化处理
        img_binary = img_gray.binary(binary_threshold)

        # 简化形态学操作 - 减少计算量以提高帧率
        # 使用开运算替代单独的腐蚀和膨胀操作
        # 级联操作：先闭运算（填补空洞），再开运算（去噪）
        #img_binary.close(2)  # 结构元素大小可调（2~3像素）
        img_binary.open(1)

        # 移除梯度运算以提高性能，如需要可重新启用
        # img_gradient = img_binary.copy()
        # img_gradient.erode(1)  # 腐蚀图像
        # img_dilated = img_binary.copy()
        # img_dilated.dilate(1)  # 膨胀图像
        # 梯度 = 膨胀 - 腐蚀
        # img_gradient = img_dilated.sub(img_gradient)
        # img_binary = img_gradient  # 使用梯度图像进行后续处理

        # 使用新的矩形识别方法（根据帧数选择策略）
        # 修改这里，优先使用嵌套矩形检测
        max_rect = find_nested_rects(img_binary)
        if max_rect is None:
            max_rect = find_best_rect(img_binary, is_first_frame, last_frame_center)

        # 调试：显示梯度运算结果
        # img.draw_image(img_binary, 0, 0, x_scale=0.3, y_scale=0.3)  # 显示梯度图像

        # 调试信息
        print(f"检测到矩形: 1个" if max_rect else "检测到矩形: 0个")

        if max_rect:
            corners = max_rect.corners()
            center_x = (corners[0][0] + corners[2][0]) // 2
            center_y = (corners[0][1] + corners[2][1]) // 2

            # 使用卡尔曼滤波器平滑中心点坐标
            filtered_center_x = int(kalman_x.update(center_x))
            filtered_center_y = int(kalman_y.update(center_y))
            
            # 更新上一帧中心点（仅在成功检测到矩形时）
            last_frame_center = (filtered_center_x, filtered_center_y)
            if is_first_frame:
                is_first_frame = False

            # 计算速度向量并预测下一帧位置
            velocity_x = filtered_center_x - previous_target[0]
            velocity_y = filtered_center_y - previous_target[1]
            predicted_x = filtered_center_x + velocity_x
            predicted_y = filtered_center_y + velocity_y
            predicted_target = (predicted_x, predicted_y)
            previous_target = (filtered_center_x, filtered_center_y)

            # 目标点稳定性优化
            # 检查当前目标是否与上一次目标接近（例如距离小于50像素）
            if distance((center_x, center_y), last_valid_target) < 50:
                current_target_count += 1
            else:
                # 新目标出现，重置计数
                current_target_count = 1
                last_valid_target = (center_x, center_y)

            # 只有当连续识别次数达到阈值时才更新并发送新目标数据
            if current_target_count >= TARGET_STABILITY_THRESHOLD:
                # 更新有效目标
                last_valid_target = (center_x, center_y)

                # 简化绘图操作以提高帧率
                # 只绘制必要的图形元素

                # 绘制矩形边框（简化线条粗细）
                for i in range(4):
                    next_i = (i + 1) % 4
                    img.draw_line(corners[i][0], corners[i][1], corners[next_i][0], corners[next_i][1],
                                color=(0, 255, 0), thickness=1)  # 减小线条粗细

                # 绘制中心点
                img.draw_cross(center_x, center_y, color=(255, 255, 255))

                # 更新矩形数据
                rect_corners = corners
                rect_center = (filtered_center_x, filtered_center_y)

                # 将target_x和target_y改为预测的目标点矩形中心坐标
                target_x = predicted_target[0]
                target_y = predicted_target[1]

                # 发送整合数据包（发送预测位置）
                send_combined_data(target_x, target_y)
            else:
                # 未达到稳定阈值，继续使用预测位置
                target_x, target_y = predicted_target
                send_combined_data(target_x, target_y)

            # 绘制屏幕中心点和误差向量
            img.draw_cross(SCREEN_CENTER_X, SCREEN_CENTER_Y, color=(255, 255, 255))
            img.draw_line(SCREEN_CENTER_X, SCREEN_CENTER_Y, center_x, center_y,
                         color=(255, 255, 0), thickness=1)  # 减小线条粗细

            # 检查是否对准目标（距离小于阈值）
            # 使用预测位置进行对准判断
            dist_to_target = distance((SCREEN_CENTER_X, SCREEN_CENTER_Y), predicted_target)
            if dist_to_target < 30:  # 阈值可调
                LED.value(1)  # 打开激光
                print("激光已打开")
            else:
                LED.value(0)  # 关闭激光

            # 精简显示信息以提高性能
            img.draw_string_advanced(10, 10, 16, f"FPS: {clock.fps():.1f}", color=(255, 0, 0))
            img.draw_string_advanced(10, 30, 16, f"中心:({filtered_center_x},{filtered_center_y})", color=(0, 255, 0))
            img.draw_string_advanced(10, 50, 16, f"距离:{dist_to_target}", color=(0, 0, 255))
        else:
            # 没有检测到矩形，重置计数器并发送预测位置
            current_target_count = 0
            target_x, target_y = predicted_target
            send_combined_data(target_x, target_y)

        # 显示图像
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

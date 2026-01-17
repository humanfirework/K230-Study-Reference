# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任

import time, os, sys, math
from media.sensor import *
from media.display import *
from media.media import *

picture_width = 800
picture_height = 480

sensor_id = 2
sensor = None

# 显示模式选择：可以是 "VIRT"、"LCD" 或 "HDMI"
DISPLAY_MODE = "LCD"

# 根据模式设置显示宽高
if DISPLAY_MODE == "VIRT":
    DISPLAY_WIDTH = ALIGN_UP(1920, 16)
    DISPLAY_HEIGHT = 1080
elif DISPLAY_MODE == "LCD":
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
elif DISPLAY_MODE == "HDMI":
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
else:
    raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

def calculate_distance(point1, point2):
    """计算两点之间的欧氏距离"""
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def calculate_line_angle(line):
    """计算线段的角度（弧度）"""
    x1, y1, x2, y2 = line.line()
    return math.atan2(y2 - y1, x2 - x1)

def extend_line(line, extend_length=10):
    """延长线段两端"""
    x1, y1, x2, y2 = line.line()
    angle = calculate_line_angle(line)
    
    # 延长起点
    new_x1 = x1 - extend_length * math.cos(angle)
    new_y1 = y1 - extend_length * math.sin(angle)
    
    # 延长终点
    new_x2 = x2 + extend_length * math.cos(angle)
    new_y2 = y2 + extend_length * math.sin(angle)
    
    return (new_x1, new_y1, new_x2, new_y2)

def find_polygon_vertices(lines, tolerance=15):
    """
    从线段中查找多边形顶点
    tolerance: 顶点容差（像素）
    """
    if len(lines) < 3:
        return []
    
    vertices = []
    
    # 收集所有线段的端点
    endpoints = []
    for line in lines:
        x1, y1, x2, y2 = line.line()
        endpoints.append((x1, y1))
        endpoints.append((x2, y2))
    
    # 合并相近的端点
    merged_points = []
    for point in endpoints:
        merged = False
        for existing in merged_points:
            if calculate_distance(point, existing) < tolerance:
                merged = True
                break
        if not merged:
            merged_points.append(point)
    
    return merged_points

def find_polygons_from_lines(lines, min_sides=3, max_sides=8, tolerance=20):
    """
    从线段中识别多边形
    min_sides: 最小边数
    max_sides: 最大边数
    tolerance: 顶点容差（像素）
    """
    if len(lines) < min_sides:
        return []
    
    polygons = []
    vertices = find_polygon_vertices(lines, tolerance)
    
    if len(vertices) < min_sides:
        return []
    
    # 计算凸包
    if len(vertices) >= 3:
        # 简单实现：按角度排序并连接
        center_x = sum(p[0] for p in vertices) / len(vertices)
        center_y = sum(p[1] for p in vertices) / len(vertices)
        center = (center_x, center_y)
        
        # 按相对于中心的角度排序
        vertices_sorted = sorted(vertices, key=lambda p: math.atan2(p[1] - center_y, p[0] - center_x))
        
        # 检查是否能形成合理的多边形
        if len(vertices_sorted) >= min_sides and len(vertices_sorted) <= max_sides:
            # 计算周长
            perimeter = 0
            for i in range(len(vertices_sorted)):
                next_i = (i + 1) % len(vertices_sorted)
                perimeter += calculate_distance(vertices_sorted[i], vertices_sorted[next_i])
            
            # 计算面积（使用鞋带公式）
            area = 0
            n = len(vertices_sorted)
            for i in range(n):
                j = (i + 1) % n
                area += vertices_sorted[i][0] * vertices_sorted[j][1]
                area -= vertices_sorted[j][0] * vertices_sorted[i][1]
            area = abs(area) / 2
            
            # 过滤掉面积过小的多边形
            if area > 100:  # 最小面积阈值
                polygons.append({
                    'vertices': vertices_sorted,
                    'sides': len(vertices_sorted),
                    'area': area,
                    'perimeter': perimeter,
                    'center': center
                })
    
    return polygons

def classify_polygon_type(vertices):
    """根据顶点数量分类多边形类型"""
    sides = len(vertices)
    polygon_names = {
        3: "三角形",
        4: "四边形",
        5: "五边形",
        6: "六边形",
        7: "七边形",
        8: "八边形"
    }
    return polygon_names.get(sides, f"{sides}边形")

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
        os.exitpoint()

        # 捕获通道0的图像
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 查找线段（LSD算法）
        lines = img.find_line_segments(merge_distance=20, max_theta_diff=10)
        
        # 绘制所有检测到的线段
        for line in lines:
            img.draw_line(line.line(), color=(0, 255, 0), thickness=2)
        
        # 从线段中识别多边形
        polygons = find_polygons_from_lines(lines, min_sides=3, max_sides=8, tolerance=25)
        
        # 绘制和标记识别到的多边形
        for idx, polygon in enumerate(polygons):
            vertices = polygon['vertices']
            polygon_type = classify_polygon_type(vertices)
            
            # 绘制多边形轮廓
            for i in range(len(vertices)):
                start_point = vertices[i]
                end_point = vertices[(i + 1) % len(vertices)]
                img.draw_line(int(start_point[0]), int(start_point[1]), 
                            int(end_point[0]), int(end_point[1]), 
                            color=(255, 0, 0), thickness=3)
            
            # 标记顶点
            for vertex in vertices:
                img.draw_circle(int(vertex[0]), int(vertex[1]), 5, color=(0, 0, 255), thickness=-1)
            
            # 显示多边形信息
            center_x, center_y = polygon['center']
            info_text = f"{polygon_type} 边数:{polygon['sides']} 面积:{int(polygon['area'])}"
            img.draw_string_advanced(int(center_x) - 30, int(center_y) - 10, 20, info_text, 
                          color=(255, 255, 255), scale=1.2)
        
        # 显示统计信息
        stats_text = f"线段数: {len(lines)} 多边形: {len(polygons)}"
        img.draw_string_advanced(10, 10, 20, stats_text, color=(255, 255, 255), scale=1.5)

        # 显示捕获的图像，中心对齐，居中显示
        Display.show_image(img, x=int((DISPLAY_WIDTH - picture_width) / 2), 
                         y=int((DISPLAY_HEIGHT - picture_height) / 2))

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
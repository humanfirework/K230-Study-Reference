import time, os, sys
from media.sensor import *
from media.display import *
from media.media import *
from machine import FPIOA
from machine import UART
from machine import Pin
import struct

# 串口配置 - 使用5.贝塞尔曲线.py的配置
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart = UART(UART.UART2, 115200)

# 显示参数
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

# LAB颜色空间阈值 - 基于亚博移植参考
THRESHOLDS = [
    ((21, 33, -15, 9, -9, 6)),    # 黑线
    ((40, 86, -44, -20, -24, 25)), # 绿色
    ((0, 100, 15, 127, 15, 127)),  # 红色
    ((0, 100, -128, -10, -128, 127)),  # 蓝色
]

# PID参数
KP = 1.2
KI = 0.1
KD = 0.3

# 基础速度
BASE_SPEED = 400

# 屏幕中心点坐标
SCREEN_CENTER = DISPLAY_WIDTH // 2

# 全局变量
prev_error = 0
integral = 0
current_color_index = 0  # 当前检测的颜色索引

# 按键配置 - 用于切换颜色
fpioa.set_function(53, FPIOA.GPIO53)
KEY = Pin(53, Pin.IN, Pin.PULL_DOWN)

last_key_state = 0
key_debounce_time = 0

def init_sensor():
    """初始化摄像头"""
    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
    sensor.set_pixformat(Sensor.RGB565)
    return sensor

def init_display():
    """初始化显示"""
    Display.init(Display.ST7701, to_ide=True)
    MediaManager.init()

def send_motor_data(left_speed, right_speed):
    """发送电机速度数据 - 使用5.贝塞尔曲线.py的格式"""
    # 限制速度范围
    left_speed = max(-1000, min(1000, left_speed))
    right_speed = max(-1000, min(1000, right_speed))
    
    # 发送数据格式: 0xAA + 数据类型 + 左右速度 + 0x55
    frame = b'\xAA' + struct.pack('<BHH', 1, int(left_speed), int(right_speed)) + b'\x55'
    uart.write(frame)
    uart.flush()  # 等待发送完成
    print(f"[MOTOR] 发送速度: 左={left_speed}, 右={right_speed}")
    print(f"[MOTOR] 数据帧: {frame.hex().upper()}")

def calculate_pid(target, current):
    """计算PID输出"""
    global prev_error, integral

    error = target - current
    integral += error
    derivative = error - prev_error

    # 限制积分项防止积分饱和
    integral = max(-50, min(50, integral))

    output = KP * error + KI * integral + KD * derivative

    # 计算左右电机速度
    left_speed = BASE_SPEED - output
    right_speed = BASE_SPEED + output

    # 保存当前误差用于下次计算
    prev_error = error

    return int(left_speed), int(right_speed)

def handle_key():
    """处理按键切换颜色"""
    global current_color_index, key_debounce_time, last_key_state
    
    current_time = time.ticks_ms()
    key_state = KEY.value()
    
    if key_state == 1 and last_key_state == 0 and (current_time - key_debounce_time) > 200:
        current_color_index = (current_color_index + 1) % len(THRESHOLDS)
        key_debounce_time = current_time
        print(f"[KEY] 切换到颜色: {current_color_index}")
        
    last_key_state = key_state
    return key_state

def process_color_line(img, blobs):
    """处理颜色巡线"""
    if not blobs:
        # 如果没有检测到色块，发送停车命令
        send_motor_data(0, 0)
        return False

    # 找出面积最大的色块
    largest_blob = max(blobs, key=lambda b: b[4])
    
    # 计算色块中心X坐标
    blob_center_x = largest_blob[0] + largest_blob[2] // 2
    blob_center_y = largest_blob[1] + largest_blob[3] // 2
    
    # 计算PID输出
    left_speed, right_speed = calculate_pid(SCREEN_CENTER, blob_center_x)
    
    # 发送电机控制数据
    send_motor_data(left_speed, right_speed)
    
    # 绘制调试信息
    color = get_threshold_color(current_color_index)
    img.draw_rectangle(largest_blob[0:4], color=color, thickness=3)
    img.draw_cross(blob_center_x, blob_center_y, color=color, thickness=2)
    
    # 绘制目标线和当前位置（来自亚博移植参考）
    img.draw_line(SCREEN_CENTER, 0, SCREEN_CENTER, DISPLAY_HEIGHT, color=(0, 255, 0), thickness=1)
    img.draw_line(blob_center_x, largest_blob[1], blob_center_x, largest_blob[1] + largest_blob[3], color=(255, 0, 0), thickness=2)
    
    return True

def get_threshold_color(index):
    """根据阈值索引返回对应颜色"""
    colors = [
        (255, 255, 255),  # 黑色
        (0, 255, 0),      # 绿色
        (255, 0, 0),      # 红色
        (0, 0, 255),      # 蓝色
    ]
    return colors[index % len(colors)]

def draw_ui(img):
    """绘制UI界面"""
    # 绘制中心参考线
    img.draw_line(SCREEN_CENTER, 0, SCREEN_CENTER, DISPLAY_HEIGHT, 
                  color=(0, 255, 0), thickness=1)
    
    # 绘制当前颜色信息
    color_names = ["黑色", "绿色", "红色", "蓝色"]
    current_name = color_names[current_color_index]
    img.draw_string_advanced(10, 10, 24, f"颜色: {current_name}", 
                           color=get_threshold_color(current_color_index))
    
    # 绘制按键提示
    img.draw_string_advanced(10, 50, 20, "按键: 切换颜色", color=(255, 255, 255))
    
    # 绘制阈值信息
    threshold = THRESHOLDS[current_color_index]
    img.draw_string_advanced(10, 80, 16, 
                           f"L:{threshold[0]}-{threshold[1]} ",
                           color=(255, 255, 255))
    img.draw_string_advanced(10, 100, 16,
                           f"A:{threshold[2]}-{threshold[3]} ",
                           color=(255, 255, 255))
    img.draw_string_advanced(10, 120, 16,
                           f"B:{threshold[4]}-{threshold[5]} ",
                           color=(255, 255, 255))

def main():
    """主函数"""
    global last_key_state
    
    try:
        # 初始化设备
        sensor = init_sensor()
        init_display()
        sensor.run()

        clock = time.clock()
        
        print("[INFO] 颜色巡线系统启动")
        print("[INFO] 按键切换颜色，按Ctrl+C退出")

        while True:
            clock.tick()
            img = sensor.snapshot()

            # 处理按键
            handle_key()
            
            # 获取当前颜色阈值
            current_threshold = THRESHOLDS[current_color_index]
            
            # 在图像下半部分检测色块
            roi = (0, DISPLAY_HEIGHT//2, DISPLAY_WIDTH, DISPLAY_HEIGHT//2)
            blobs = img.find_blobs([current_threshold], roi=roi, 
                                 pixels_threshold=100, area_threshold=100)
            
            # 处理巡线
            line_detected = process_color_line(img, blobs)
            
            # 绘制调试信息
            draw_ui(img)
            
            # 显示FPS
            fps = clock.fps()
            img.draw_string_advanced(DISPLAY_WIDTH-150, 10, 20, f"FPS: {fps:.1f}", 
                                   color=(255, 255, 255))
            
            # 显示状态
            status = "检测到" if line_detected else "未检测"
            img.draw_string_advanced(DISPLAY_WIDTH-150, 40, 20, status, 
                                   color=(0, 255, 0) if line_detected else (255, 0, 0))

            Display.show_image(img)

    except KeyboardInterrupt as e:
        print("用户中断: ", e)
        send_motor_data(0, 0)  # 停止电机
    except Exception as e:
        print(f"发生错误: {e}")
        send_motor_data(0, 0)  # 停止电机
    finally:
        # 清理资源
        send_motor_data(0, 0)
        if 'sensor' in locals() and isinstance(sensor, Sensor):
            sensor.stop()
        Display.deinit()
        MediaManager.deinit()

if __name__ == "__main__":
    main()
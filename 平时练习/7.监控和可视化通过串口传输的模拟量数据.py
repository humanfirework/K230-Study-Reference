import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time
 
# --- 配置 ---
# SERIAL_PORT = '/dev/ttyUSB0'  # 根据你的系统修改串口号 (Windows: 'COM3', Linux: '/dev/ttyUSB0' or '/dev/ttyACM0', macOS: '/dev/cu.usbserial-xxxx')
SERIAL_PORT = 'COM4'
BAUD_RATE = 115200          # 波特率，通常与 MicroPython 默认 REPL 波特率一致
MAX_DATA_POINTS = 200       # 图上显示的最大数据点数量
 
# --- 初始化 ---
data_buffer = deque(maxlen=MAX_DATA_POINTS)
time_buffer = deque(maxlen=MAX_DATA_POINTS) # 用于存储时间或样本序号
 
# --- 创建图形 ---
fig, ax = plt.subplots()
line, = ax.plot([], [], 'r-') # 初始化一条红色的线
 
# 设置图形外观
ax.set_title('Real-time ADC Voltage')
ax.set_xlabel('Sample Index') # 或者 'Time (s)' 如果你使用时间戳
ax.set_ylabel('Voltage (V)')
ax.grid(True)
 
# 设置初始坐标轴范围 (可以根据需要调整)
ax.set_ylim(0, 4.0) # 假设最大电压不超过4V
ax.set_xlim(0, MAX_DATA_POINTS)
 
# --- 打开串口 ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) # timeout=1秒，避免无数据时卡死
    print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
except serial.SerialException as e:
    print(f"Error opening serial port {SERIAL_PORT}: {e}")
    print("Please check the port name, permissions, and if the device is connected.")
    exit()
 
# --- 更新函数 (由动画调用) ---
def update(frame):
    """读取串口数据并更新图形"""
    try:
        if ser.in_waiting > 0:
            line_bytes = ser.readline()
            line_str = line_bytes.decode('utf-8').strip()
 
            # 尝试将接收到的字符串转换为浮点数
            try:
                voltage = float(line_str)
                data_buffer.append(voltage)
                time_buffer.append(len(data_buffer) - 1) # 使用样本索引作为X轴
 
                # 更新绘图数据
                line.set_data(time_buffer, data_buffer)
 
                # 动态调整坐标轴范围 (如果需要)
                ax.relim()          # 重新计算限制
                ax.autoscale_view(True,True,True) # 自动缩放视图
 
                # 保持X轴窗口滑动 (可选)
                if len(time_buffer) >= MAX_DATA_POINTS:
                     ax.set_xlim(time_buffer[0], time_buffer[-1])
 
 
            except ValueError:
                # 忽略无法转换的数据行 (可能是 MicroPython 打印的错误信息等)
                print(f"Warning: Could not parse value: {line_str}")
 
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        # 可以选择在这里尝试重新连接或退出
        plt.close(fig) # 关闭图形窗口
        return line, # 返回当前线条对象
 
    except Exception as e:
         print(f"An error occurred in update: {e}")
 
    return line, # 返回更新后的线条对象
 
# --- 创建并启动动画 ---
# interval: 更新图形的间隔（毫秒）
# blit=True: 优化绘图性能 (只重绘变化的部分)，但在某些后端或动态调整坐标轴时可能出问题，False 更稳定
ani = animation.FuncAnimation(fig, update, interval=50, blit=False)
 
# --- 显示图形 ---
try:
    plt.show()
except Exception as e:
    print(f"Error displaying plot: {e}")
 
# --- 清理 ---
ser.close()
print("Serial port closed.")
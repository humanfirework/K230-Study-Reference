from machine import UART
from machine import FPIOA

# 配置引脚
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)

# 初始化UART2，波特率115200，8位数据位，无校验，1位停止位
uart = UART(UART.UART2, baudrate=115200, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)


# 要发送的字符串
message = "Hello,LuShan-Pi!\n"

# 通过UART发送数据
uart.write(message)


# 发送字节数组
#data = bytes([0x01, 0x02, 0x03, 0x04])
#uart.write(data)


# 释放UART资源
uart.deinit()



#连续发送数据

"""
import time
from machine import UART
from machine import FPIOA

# 配置引脚
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)

# 初始化UART2，波特率115200，8位数据位，无校验，1位停止位
uart = UART(UART.UART2, baudrate=115200, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)

# 获取传感器数据（假设为变量sensor_value）
sensor_value = 0  # 示例数据

while True:
    message = "Sensor Value: {}\n".format(sensor_value)
    uart.write(message)
    sensor_value = sensor_value+1
    time.sleep(0.1)
"""


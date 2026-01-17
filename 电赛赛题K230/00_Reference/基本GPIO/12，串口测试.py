import time
from machine import UART
from machine import FPIOA

# 配置引脚
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)

# 初始化UART2，波特率115200，8位数据位，无校验，1位停止位
uart = UART(UART.UART2, baudrate=115200, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)

# 要测试的消息
test_message = b'UART Loopback Test!'

# 发送数据
uart.write(test_message)

# 等待数据发送和接收（根据波特率和数据长度，调整延时）
time.sleep(0.1)

# 如果接收不到数据就一直尝试读取
received_data = b''

received_data = uart.read()

received_message = None  # 初始化变量

if received_data:
    received_message = received_data
    print("Received:", received_message)
    if received_message == test_message:
        print("Loopback Test Passed!")
    else:
        print("Loopback Test Failed: Data Mismatch")
else:
    print("Loopback Test Failed: No Data Received")

print("test_message is {}".format(test_message))
if received_message is not None:
    print("received_message is {}".format(received_message))

# 释放UART资源
uart.deinit()

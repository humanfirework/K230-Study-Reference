# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任

from machine import Pin
from machine import FPIOA
import time

# 创建FPIOA对象，用于初始化引脚功能配置
fpioa = FPIOA()

# 设置引脚功能，将指定的引脚配置为普通GPIO功能,
fpioa.set_function(62,FPIOA.GPIO62)
fpioa.set_function(20,FPIOA.GPIO20)
fpioa.set_function(63,FPIOA.GPIO63)

# 实例化Pin62, Pin20, Pin63为输出，分别用于控制红、绿、蓝三个LED灯
LED_R = Pin(62, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 红灯
LED_G = Pin(20, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 绿灯
LED_B = Pin(63, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 蓝灯

# 板载RGB灯是共阳结构，设置引脚为高电平时关闭灯，低电平时点亮灯
# 初始化时先关闭所有LED灯
LED_R.high()  # 关闭红灯
LED_G.high()  # 关闭绿灯
LED_B.high()  # 关闭蓝灯

# 基础点灯试验：选择一个LED灯并让其闪烁
# 默认选择红色LED灯，后续可以通过变量改变需要控制的灯
LED = LED_R  # 当前控制的LED为红色LED

while True:
    LED.low()   # 点亮当前选择的LED
    time.sleep(0.5)  # 等待0.5秒
    LED.high()  # 熄灭当前选择的LED
    time.sleep(0.5)  # 等待0.5秒from machine import Pin

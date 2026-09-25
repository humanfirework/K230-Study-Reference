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

# 实例化Pin62, Pin20, Pin63为输出，分别控制红、绿、蓝灯
LED_R = Pin(62, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
LED_G = Pin(20, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
LED_B = Pin(63, Pin.OUT, pull=Pin.PULL_NONE, drive=7)

def set_color(r, g, b):
    """设置RGB灯的颜色，使用Pin.high()和Pin.low()控制"""
    if r == 0:
        LED_R.low()  # 红灯亮
    else:
        LED_R.high()  # 红灯灭

    if g == 0:
        LED_G.low()  # 绿灯亮
    else:
        LED_G.high()  # 绿灯灭

    if b == 0:
        LED_B.low()  # 蓝灯亮
    else:
        LED_B.high()  # 蓝灯灭

def blink_color(r, g, b, delay):
    """设置颜色并让灯亮一段时间后熄灭"""
    set_color(r, g, b)  # 设置颜色
    time.sleep(delay)   # 保持该颜色一段时间
    set_color(1, 1, 1)  # 熄灭所有灯（共阳：1为熄灭）
    time.sleep(delay)   # 熄灭后等待一段时间

while True:
    # 红色
    blink_color(0, 1, 1, 0.5)
    # 绿色
    blink_color(1, 0, 1, 0.5)
    # 蓝色
    blink_color(1, 1, 0, 0.5)
    # 黄色（红+绿）
    blink_color(0, 0, 1, 0.5)
    # 紫色（红+蓝）
    blink_color(0, 1, 0, 0.5)
    # 青色（绿+蓝）
    blink_color(1, 0, 0, 0.5)
    # 白色（红+绿+蓝）
    blink_color(0, 0, 0, 0.5)

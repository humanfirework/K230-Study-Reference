# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任

from machine import RTC
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

# 默认选择红色LED灯，后续可以通过变量改变需要控制的灯
LED = LED_G  # 当前控制的LED为绿色LED

# 实例化 RTC 对象
rtc = RTC()

# 设置当前时间
# 假设要设置时间为 2024 年 12 月 11 日，星期三(值为3表示星期三)，时间为 17:07:50
# rtc.init((年, 月, 日, 星期, 时, 分, 秒, 微秒))
rtc.init((2024, 12, 11, 3, 17, 7, 50, 0))
print("RTC 初始化完成，当前时间：", rtc.datetime())

# 定义目标时间点，假设定时任务为每天 17:08 触发，在这个例程中会在10秒后触发。
target_hour = 17
target_minute = 8

def check_and_trigger_event():
    """
    检查当前时间是否达到了指定的时间点，并触发事件。
    """
    current_time = rtc.datetime()
    print("当前时间：", current_time)

    # 提取当前时间的小时和分钟
    current_hour = current_time[4]
    current_minute = current_time[5]

    # 判断是否达到目标时间点
    if current_hour == target_hour and current_minute == target_minute:
        # 触发事件
        trigger_event()

def trigger_event():
    """
    触发特定的事件逻辑。
    """
    LED.low()   # 点亮当前选择的LED
    print("触发定时事件：绿灯亮啦！当前时间达到了目标时间点！")

# 主循环，持续运行程序逻辑
while True:
    check_and_trigger_event()

    # 延时 1 秒，避免主循环运行速度过快
    time.sleep(1)

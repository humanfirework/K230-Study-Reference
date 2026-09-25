# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任

from machine import RTC
from machine import Pin
from machine import FPIOA
from machine import Timer
import time

fpioa = FPIOA()

# 将62、20、63号引脚映射为GPIO，用于控制RGB灯的三个颜色通道
fpioa.set_function(62, FPIOA.GPIO62)
fpioa.set_function(20, FPIOA.GPIO20)
fpioa.set_function(63, FPIOA.GPIO63)

LED_R = Pin(62, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 红色LED
LED_G = Pin(20, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 绿色LED
LED_B = Pin(63, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 蓝色LED

# 板载RGB灯是共阳结构，高电平=关闭灯，低电平=点亮灯
# 初始化时先关闭所有LED灯
LED_R.high()
LED_G.high()
LED_B.high()

# 定义一个变量记录当前点亮的是哪一种LED
color_state = 0  # 0:红, 1:绿, 2:蓝

# 回调函数，用于定期切换LED状态
def led_toggle(timer):
    global color_state
    # 首先关闭所有LED
    LED_R.high()
    LED_G.high()
    LED_B.high()

    # 根据当前状态点亮对应的LED
    if color_state == 0:
        LED_R.low()  # 点亮红灯
    elif color_state == 1:
        LED_G.low()  # 点亮绿灯
    elif color_state == 2:
        LED_B.low()  # 点亮蓝灯

    # 切换到下一个颜色状态
    color_state = (color_state + 1) % 3

# 创建软件定时器，index=-1表示软件定时器
tim = Timer(-1)

# 初始化定时器为周期模式，每隔500ms调用一次led_toggle回调函数
tim.init(period=500, mode=Timer.PERIODIC, callback=led_toggle)

# 主循环：此处无需手动控制LED，定时器会定期触发回调函数
while True:
    # 主循环空转，保持程序运行
    time.sleep(1)

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
fpioa.set_function(53,FPIOA.GPIO53)

# 实例化Pin62, Pin20, Pin63为输出，分别控制红、绿、蓝三个LED灯
LED_R = Pin(62, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 红灯
LED_G = Pin(20, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 绿灯
LED_B = Pin(63, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 蓝灯

# 按键引脚为53，按下时高电平，设置为输入模式
button = Pin(53, Pin.IN, Pin.PULL_DOWN)  # 使用下拉电阻

# 初始选择控制红灯
LED = LED_R  # 默认控制红灯

# 初始化时关闭所有LED灯（共阳：高电平时为灭灯）
LED_R.high()
LED_G.high()
LED_B.high()

# 消抖时间设置为20毫秒
debounce_delay = 20  # 毫秒
last_press_time = 0  # 上次按键按下的时间，单位为毫秒

# 记录LED当前状态，True表示亮，False表示灭
led_on = False

# 记录按键状态，用于检测按下和松开的状态变化
button_last_state = 0  # 上次按键状态

# 主循环
while True:
    button_state = button.value()  # 获取当前按键状态
    current_time = time.ticks_ms()  # 获取当前时间（单位：毫秒）

    # 检测按键从未按下(0)到按下(1)的变化（上升沿）
    if button_state == 1 and button_last_state == 0:
        # 检查按键是否在消抖时间外
        if current_time - last_press_time > debounce_delay:
            # 切换LED的状态
            if led_on:
                LED.high()  # 熄灭LED
            else:
                LED.low()   # 点亮LED

            led_on = not led_on  # 反转LED状态
            last_press_time = current_time  # 更新按键按下时间

    # 更新上次按键状态
    button_last_state = button_state

    # 简单延时，防止主循环过于频繁
    time.sleep_ms(10)

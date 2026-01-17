import time
from machine import PWM, FPIOA

# 配置蜂鸣器IO口功能
beep_io = FPIOA()
beep_io.set_function(43, FPIOA.PWM1)

# 初始化蜂鸣器PWM通道
beep_pwm = PWM(1, 4000, 50, enable=False)  # 默认频率4kHz,占空比50%

# 使能PWM通道输出
beep_pwm.enable(1)
# 延时50ms
time.sleep_ms(50)
# 关闭PWM输出 防止蜂鸣器吵闹
beep_pwm.enable(0)
# 叫完了就释放PWM
beep_pwm.deinit()

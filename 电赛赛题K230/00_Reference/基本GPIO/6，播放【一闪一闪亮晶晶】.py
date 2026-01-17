import time
from machine import PWM, FPIOA

# 配置蜂鸣器IO口功能
beep_io = FPIOA()
beep_io.set_function(43, FPIOA.PWM1)

# 初始化蜂鸣器
beep = PWM(1, 1000, 50, enable=False)  # 默认频率1kHz,占空比50%

# 定义音符频率（以Hz为单位）
notes = {
    'C4': 261,
    'D4': 293,
    'E4': 329,
    'F4': 349,
    'G4': 392,
    'A4': 440,
    'B4': 493,
    'C5': 523
}

# 定义《一闪一闪亮晶晶》旋律和节奏 (音符, 时长ms)
melody = [
    ('C4', 500), ('C4', 500), ('G4', 500), ('G4', 500),
    ('A4', 500), ('A4', 500), ('G4', 1000),
    ('F4', 500), ('F4', 500), ('E4', 500), ('E4', 500),
    ('D4', 500), ('D4', 500), ('C4', 1000)
]

def play_tone(note, duration):
    """播放指定音符"""
    frequency = notes.get(note, 0)  # 获取音符对应的频率
    if frequency > 0:
        beep.freq(frequency)        # 设置频率
        beep.enable(True)           # 启用蜂鸣器
        time.sleep_ms(duration)     # 持续播放指定时间
        beep.enable(False)          # 停止蜂鸣器
        time.sleep_ms(50)           # 音符之间的短暂停顿

# 播放旋律
for note, duration in melody:
    play_tone(note, duration)

# 释放PWM资源
beep.deinit()

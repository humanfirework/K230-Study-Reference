# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任
from machine import ADC
import time

# 实例化 ADC 通道 0，用于读取模拟信号的数字值
adc = ADC(0)

# 主循环，持续运行程序逻辑
while True:
    # 获取 ADC 通道 0 的采样值
    # ADC 采样值是一个无符号 16 位整数，范围为 0 到 65535
    adc_value = adc.read_u16()

    # 获取 ADC 通道 0 的电压值，单位为微伏（uV）
    adc_voltage_uv = adc.read_uv()

    # 将电压值从微伏转换为伏特（V）
    # 1 伏特 = 1,000,000 微伏
    adc_voltage_v = adc_voltage_uv / (1000 * 1000)

    # 打印采样值和电压值
    # 输出格式为 "ADC Value: <采样值>, Voltage: <微伏值> uV, <伏特值> V"
    print("ADC Value: %d, Voltage: %d uV, %.6f V" % (adc_value, adc_voltage_uv, adc_voltage_v))

    # 简单延时 100 毫秒，防止主循环运行速度过快
    time.sleep_ms(100)

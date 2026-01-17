import time
from machine import PWM, FPIOA

# ======================= 参数配置 =======================
# 定义舵机控制相关的GPIO、PWM ID、频率、脉宽等参数。

# --- X轴舵机 (左右/Pan) 配置 ---
X_SERVO_GPIO = 42      # X轴舵机连接的GPIO引脚
X_SERVO_PWM_ID = 0     # X轴舵机使用的PWM控制器ID

# --- Y轴舵机 (上下/Tilt) 配置 ---
Y_SERVO_GPIO = 52      # Y轴舵机连接的GPIO引脚
Y_SERVO_PWM_ID = 4     # Y轴舵机使用的PWM控制器ID

# --- 通用舵机规格 (假设均为TBS-K20型舵机) ---
SERVO_FREQ_HZ = 50     # 舵机PWM信号的频率，单位赫兹 (Hz)
PULSE_MIN_MS = 0.5     # 舵机能够接受的最小脉宽，单位毫秒 (ms)
PULSE_MAX_MS = 2.5     # 舵机能够接受的最大脉宽，单位毫秒 (ms)

# --- 运动轨迹定义 (所有脉宽值均以毫秒 (ms) 为单位) ---
PULSE_CENTER_MS = 1.6  # 舵机居中时的脉宽
SQUARE_OFFSET_MS = 0.1 # 正方形边长的一半，即从中心点到任意角点的X或Y轴脉宽偏移量
STEP_DELAY_S = 1.5     # 移动到每个轨迹点后的停留时间，单位秒 (s)

# 1. 定义初始位置 (云台中心) 的X和Y轴舵机脉宽
INITIAL_POS = (PULSE_CENTER_MS, PULSE_CENTER_MS)

# 2. 定义正方形四个角的位置 (X轴脉宽, Y轴脉宽)
# 运动方向说明：Y轴脉宽增大通常使云台向上移动；X轴脉宽减小通常使云台向左移动。
TOP_LEFT     = (PULSE_CENTER_MS - SQUARE_OFFSET_MS, PULSE_CENTER_MS + SQUARE_OFFSET_MS) # 左上角位置
TOP_RIGHT    = (PULSE_CENTER_MS + SQUARE_OFFSET_MS, PULSE_CENTER_MS + SQUARE_OFFSET_MS) # 右上角位置
BOTTOM_RIGHT = (PULSE_CENTER_MS + SQUARE_OFFSET_MS, PULSE_CENTER_MS - SQUARE_OFFSET_MS) # 右下角位置
BOTTOM_LEFT  = (PULSE_CENTER_MS - SQUARE_OFFSET_MS, PULSE_CENTER_MS - SQUARE_OFFSET_MS) # 左下角位置
# =======================================================


def move_servos(pwm_x, pwm_y, target_pos):
    """
    同时移动两个舵机到指定的目标脉宽位置。

    参数:
        pwm_x: X轴舵机的PWM对象实例。
        pwm_y: Y轴舵机的PWM对象实例。
        target_pos: 一个元组，包含目标X轴脉宽 (ms) 和目标Y轴脉宽 (ms)。
    """
    pos_x_ms, pos_y_ms = target_pos
    period_ms = 1000 / SERVO_FREQ_HZ # 计算PWM信号的周期，单位毫秒

    # 计算并设置X轴舵机的占空比
    # 占空比 = (目标脉宽 / PWM周期) * 100%
    duty_x = (pos_x_ms / period_ms) * 100
    pwm_x.duty(duty_x)

    # 计算并设置Y轴舵机的占空比
    duty_y = (pos_y_ms / period_ms) * 100
    pwm_y.duty(duty_y)

    print(f"--> 移动到 X: {pos_x_ms:.1f}ms, Y: {pos_y_ms:.1f}ms")


# --- 主程序入口 ---
# 初始化舵机PWM对象为None，以便在异常处理的finally块中安全地进行资源释放。
servo_x = None
servo_y = None
try:
    # 1. 初始化FPIOA (Flexible Pin IO Array) 和 PWM (脉冲宽度调制)
    # FPIOA用于将GPIO引脚映射到特定的功能（例如PWM）。
    fpioa = FPIOA()
    fpioa.set_function(X_SERVO_GPIO, getattr(FPIOA, f'PWM{X_SERVO_PWM_ID}'))
    fpioa.set_function(Y_SERVO_GPIO, getattr(FPIOA, f'PWM{Y_SERVO_PWM_ID}'))

    # 根据PWM ID和频率创建PWM对象
    servo_x = PWM(X_SERVO_PWM_ID, SERVO_FREQ_HZ)
    servo_y = PWM(Y_SERVO_PWM_ID, SERVO_FREQ_HZ)

    # 启用PWM输出，开始控制舵机
    servo_x.enable(True)
    servo_y.enable(True)

    print("双轴舵机运动控制程序启动...")

    # 2. 循环执行预定义的运动序列，使舵机绘制正方形
    while True:
        print("\n======== 开始新一轮运动序列 ========")

        # 第1步: 移动到初始位置 (中心点)
        print("步骤 1: 移动到初始位置...")
        move_servos(servo_x, servo_y, INITIAL_POS)
        time.sleep(3) # 在初始位置停留较长时间

        # 第2步: 从中心移动到正方形的左上角 (准备开始绘制)
        print("步骤 2: 移动到正方形左上角...")
        move_servos(servo_x, servo_y, TOP_LEFT)
        time.sleep(STEP_DELAY_S) # 停留一段时间

        # 第3步: 绘制正方形的四条边
        print("步骤 3: 开始绘制正方形...")
        move_servos(servo_x, servo_y, TOP_RIGHT)    # 从左上角移动到右上角
        time.sleep(STEP_DELAY_S)
        move_servos(servo_x, servo_y, BOTTOM_RIGHT) # 从右上角移动到右下角
        time.sleep(STEP_DELAY_S)
        move_servos(servo_x, servo_y, BOTTOM_LEFT)  # 从右下角移动到左下角
        time.sleep(STEP_DELAY_S)
        move_servos(servo_x, servo_y, TOP_LEFT)     # 从左下角移动回左上角 (完成一个闭环)
        time.sleep(STEP_DELAY_S)
        print("正方形绘制完成。")

        # 第4步: 从当前位置 (左上角) 返回初始中心位置
        print("步骤 4: 返回初始位置...")
        move_servos(servo_x, servo_y, INITIAL_POS)
        time.sleep(3) # 回到初始位置后再次停留较长时间，以便观察

except KeyboardInterrupt:
    # 捕获用户中断异常 (例如，通过Ctrl+C)
    print("\n程序被用户停止。")
except Exception as e:
    # 捕获所有其他运行时异常，并打印错误信息
    print(f"\n发生错误: {e}")
finally:
    # 5. 释放资源
    # 确保在程序退出前，禁用并释放所有已启用的PWM资源，防止资源泄露或硬件异常。
    if servo_x:
        servo_x.deinit() # 禁用并释放X轴舵机PWM
    if servo_y:
        servo_y.deinit() # 禁用并释放Y轴舵机PWM
    print("PWM资源已全部释放。")
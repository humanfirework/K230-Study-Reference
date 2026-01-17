# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任

import time, os, sys

#使用默认摄像头，可选参数:0,1,2.
sensor_id = 2

# ========== 多媒体/图像相关模块 ==========
from media.sensor import Sensor, CAM_CHN_ID_0
from media.display import Display
from media.media import MediaManager
import image

# ========== GPIO/按键/LED相关模块 ==========
from machine import Pin
from machine import FPIOA

# ========== 创建FPIOA对象并为引脚功能分配 ==========
fpioa = FPIOA()
fpioa.set_function(62, FPIOA.GPIO62)   # 红灯
fpioa.set_function(20, FPIOA.GPIO20)   # 绿灯
fpioa.set_function(63, FPIOA.GPIO63)   # 蓝灯
fpioa.set_function(53, FPIOA.GPIO53)   # 按键

# ========== 初始化LED (共阳：高电平熄灭，低电平亮) ==========
LED_R = Pin(62, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 红灯
LED_G = Pin(20, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 绿灯
LED_B = Pin(63, Pin.OUT, pull=Pin.PULL_NONE, drive=7)  # 蓝灯

# 默认熄灭所有LED
LED_R.high()
LED_G.high()
LED_B.high()

# 选一个LED用来拍照提示
PHOTO_LED = LED_B

# ========== 初始化按键：按下时高电平 ==========
button = Pin(53, Pin.IN, Pin.PULL_DOWN)
debounce_delay = 200  # 按键消抖时长(ms)
last_press_time = 0
button_last_state = 0

# ========== 显示配置 ==========
DISPLAY_MODE = "LCD"   # 可选："VIRT","LCD","HDMI"
if DISPLAY_MODE == "VIRT":
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
    FPS = 30
elif DISPLAY_MODE == "LCD":
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
    FPS = 60
elif DISPLAY_MODE == "HDMI":
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
    FPS = 30
else:
    raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

def lckfb_save_jpg(img, filename, quality=95):
    """
    将图像压缩成JPEG后写入文件 (不依赖第一段 save_jpg/MediaManager.convert_to_jpeg 的写法)
    :param img:    传入的图像对象 (Sensor.snapshot() 得到)
    :param filename: 保存的目标文件名 (含路径)
    :param quality:  压缩质量 (1-100)
    """
    compressed_data = img.compress(quality=quality)

    with open(filename, "wb") as f:
        f.write(compressed_data)

    print(f"[INFO] 使用 lckfb_save_jpg() 保存完毕: {filename}")


# ========== 自动创建图片保存文件夹 & 计算已有图片数量 ==========
image_folder = "/data/data/images"

# 若不存在该目录则创建
try:
    os.stat(image_folder)  # 尝试获取目录信息
except OSError:
    os.mkdir(image_folder)  # 若失败则创建该目录

# 统计当前目录下以 “lckfb_XX.jpg” 命名的文件数量，自动从最大编号继续
image_count = 0
existing_images = [fname for fname in os.listdir(image_folder)
                   if fname.startswith("lckfb_") and fname.endswith(".jpg")]

if existing_images:
    # 提取编号并找出最大值
    numbers = []
    for fname in existing_images:
        # 假设文件名格式为 "lckfb_XX.jpg"
        # 取中间 XX 部分转为数字
        try:
            num_part = fname[6:11]  # "lckfb_" 长度为6，取到 ".jpg" 前还要注意下标
            numbers.append(int(num_part))
        except:
            pass
    if numbers:
        image_count = max(numbers)

try:
    print("[INFO] 初始化摄像头 ...")
    sensor = Sensor(id=sensor_id)
    sensor.reset()

    # 在本示例中使用 VGA (640x480) 做演示
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    # ========== 初始化显示 ==========
    if DISPLAY_MODE == "VIRT":
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=FPS)
    elif DISPLAY_MODE == "LCD":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "HDMI":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)

    # ========== 初始化媒体管理器 ==========
    MediaManager.init()

    # ========== 启动摄像头 ==========
    sensor.run()
    print("[INFO] 摄像头已启动，进入主循环 ...")

    fps = time.clock()

    while True:
        fps.tick()
        os.exitpoint()

        #抓取通道0的图像
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        #按键处理（检测上升沿）
        current_time = time.ticks_ms()
        button_state = button.value()

        if button_state == 1 and button_last_state == 0:  # 上升沿
            if current_time - last_press_time > debounce_delay:
                # LED闪烁提示
                PHOTO_LED.low()   # 点亮LED
                time.sleep_ms(20)
                PHOTO_LED.high()  # 熄灭LED

                # 拍照并保存
                image_count += 1
                filename = f"{image_folder}/lckfb_{image_count:05d}_{img.width()}x{img.height()}.jpg"
                print(f"[INFO] 拍照保存 -> {filename}")

                # 直接调用自定义的 lckfb_save_jpg() 函数
                lckfb_save_jpg(img, filename, quality=95)

                last_press_time = current_time

        button_last_state = button_state

        img.draw_string_advanced(0, 0, 32, str(image_count), color=(255, 0, 0))
        img.draw_string_advanced(0, DISPLAY_HEIGHT-32, 32, str(fps.fps()), color=(255, 0, 0))

        Display.show_image(img)



except KeyboardInterrupt:
    print("[INFO] 用户停止")
except BaseException as e:
    print(f"[ERROR] 出现异常: {e}")
finally:
    if 'sensor' in locals() and isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
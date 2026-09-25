# 导入所需模块
import time, os, urandom, sys
from media.display import *
from media.media import *

# 显示模式选择：可以是 "VIRT"、"LCD" 或 "HDMI"
DISPLAY_MODE = "VIRT"

# 根据模式设置显示宽高
if DISPLAY_MODE == "VIRT":
    # 虚拟显示器模式
    DISPLAY_WIDTH = ALIGN_UP(1920, 16)
    DISPLAY_HEIGHT = 1080
elif DISPLAY_MODE == "LCD":
    # 3.1寸屏幕模式
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
elif DISPLAY_MODE == "HDMI":
    # HDMI扩展板模式
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
else:
    raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

# 显示测试函数
def display_test():
    print(f"显示测试，当前模式为 {DISPLAY_MODE}")

    # 创建用于绘图的图像对象
    img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888)

    # 根据模式初始化显示器
    if DISPLAY_MODE == "VIRT":
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)
    elif DISPLAY_MODE == "LCD":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "HDMI":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)

    # 初始化媒体管理器
    MediaManager.init()

    try:
        while True:
            img.clear()  # 清除图像内容
            for i in range(10):  # 循环绘制10个字符串
                # 随机生成字符串位置、颜色和大小
                x = (urandom.getrandbits(11) % img.width())  # 随机X坐标
                y = (urandom.getrandbits(11) % img.height())  # 随机Y坐标
                r = urandom.getrandbits(8)  # 红色分量
                g = urandom.getrandbits(8)  # 绿色分量
                b = urandom.getrandbits(8)  # 蓝色分量
                size = (urandom.getrandbits(30) % 64) + 32  # 字体大小（32到96之间）

                # 绘制字符串，支持中文字符
                img.draw_string_advanced(
                    x, y, size, "Hello World!，你好庐山派！！！", color=(r, g, b),
                )

            # 将绘制结果显示到屏幕
            Display.show_image(img)

            time.sleep(1)  # 暂停1秒
            os.exitpoint()  # 可用的退出点
    except KeyboardInterrupt as e:
        print("用户终止：", e)  # 捕获键盘中断异常
    except BaseException as e:
        print(f"异常：{e}")  # 捕获其他异常
    finally:
        # 清理资源
        Display.deinit()
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)  # 启用睡眠模式的退出点
        time.sleep_ms(100)  # 延迟100毫秒
        MediaManager.deinit()

# 主程序入口
if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)  # 启用退出点
    display_test()  # 调用显示测试函数




    # 导入所需模块
import time, os, urandom, sys
from media.display import *
from media.media import *

# 显示模式选择：可以是 "VIRT"、"LCD" 或 "HDMI"
DISPLAY_MODE = "LCD"

# 根据模式设置显示宽高
if DISPLAY_MODE == "VIRT":
    # 虚拟显示器模式
    DISPLAY_WIDTH = ALIGN_UP(1920, 16)
    DISPLAY_HEIGHT = 1080
elif DISPLAY_MODE == "LCD":
    # 3.1寸屏幕模式
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
elif DISPLAY_MODE == "HDMI":
    # HDMI扩展板模式
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
else:
    raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

# 显示测试函数
def display_test():
    print(f"显示测试，当前模式为 {DISPLAY_MODE}")

    # 创建用于绘图的图像对象
    img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888)

    # 根据模式初始化显示器
    if DISPLAY_MODE == "VIRT":
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)
    elif DISPLAY_MODE == "LCD":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "HDMI":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)

    # 初始化媒体管理器
    MediaManager.init()

    try:
        while True:
            img.clear()  # 清除图像内容
            for i in range(10):  # 循环绘制10个字符串
                # 随机生成字符串位置、颜色和大小
                x = (urandom.getrandbits(11) % img.width())  # 随机X坐标
                y = (urandom.getrandbits(11) % img.height())  # 随机Y坐标
                r = urandom.getrandbits(8)  # 红色分量
                g = urandom.getrandbits(8)  # 绿色分量
                b = urandom.getrandbits(8)  # 蓝色分量
                size = (urandom.getrandbits(30) % 64) + 32  # 字体大小（32到96之间）

                # 绘制字符串，支持中文字符
                img.draw_string_advanced(
                    x, y, size, "Hello World!，你好庐山派！！！", color=(r, g, b),
                )

            # 将绘制结果显示到屏幕
            Display.show_image(img)

            time.sleep(1)  # 暂停1秒
            os.exitpoint()  # 可用的退出点
    except KeyboardInterrupt as e:
        print("用户终止：", e)  # 捕获键盘中断异常
    except BaseException as e:
        print(f"异常：{e}")  # 捕获其他异常
    finally:
        # 清理资源
        Display.deinit()
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)  # 启用睡眠模式的退出点
        time.sleep_ms(100)  # 延迟100毫秒
        MediaManager.deinit()

# 主程序入口
if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)  # 启用退出点
    display_test()  # 调用显示测试函数
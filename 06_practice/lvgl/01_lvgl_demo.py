# LVGL基础演示程序 - K230平台
# 功能：展示LVGL图形库的基本使用方法，包括显示初始化、界面创建和动画效果
# 特点：支持HDMI输出，1920x1080分辨率，包含多语言文本和PNG动画

# 导入必要的模块
from media.display import *      # 显示相关功能（HDMI/LCD驱动）
from media.media import *        # 媒体管理器（内存管理）
import time, os, sys, gc        # 基础库：时间、系统、垃圾回收
import lvgl as lv               # LVGL图形库主模块
import uctypes                  # 用于内存地址操作

# 显示参数设置（HDMI 1920x1080分辨率）
DISPLAY_WIDTH = ALIGN_UP(1920, 16)   # 屏幕宽度（1920像素，16字节对齐）
DISPLAY_HEIGHT = 1080                # 屏幕高度（1080像素）

def display_init():
    """显示初始化函数
    功能：初始化K230的HDMI显示输出，配置LT9611芯片
    参数：无
    返回：无
    """
    # 初始化LT9611 HDMI芯片，支持1920x1080输出
    # to_ide=False表示不在IDE中显示（纯HDMI输出）
    Display.init(Display.LT9611, to_ide = False)
    
    # 初始化媒体管理器，分配显示缓冲区内存
    MediaManager.init()

def display_deinit():
    """显示系统反初始化函数
    功能：程序退出时清理HDMI显示资源，释放内存和硬件资源
    参数：无
    返回：无
    """
    # 启用退出点睡眠模式，允许系统进入低功耗状态
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    
    # 延时50ms确保所有显示操作完成，避免资源冲突
    time.sleep_ms(50)
    
    # 反初始化HDMI显示驱动，关闭LT9611芯片
    Display.deinit()
    
    # 释放媒体缓冲区，回收内存资源给系统
    MediaManager.deinit()

def disp_drv_flush_cb(disp_drv, area, color):
    """LVGL显示刷新回调函数
    功能：将LVGL渲染完成的图像数据发送到HDMI显示
    参数：
        disp_drv: 显示驱动结构体（LVGL内部使用）
        area: 需要刷新的区域坐标（当前未使用）
        color: 图像数据缓冲区指针
    """
    global disp_img1, disp_img2

    # 检查是否为最后一帧渲染数据
    if disp_drv.flush_is_last() == True:
        # 根据缓冲区地址判断当前使用的是哪个图像对象
        # 实现双缓冲机制：一个缓冲区渲染，另一个显示
        if disp_img1.virtaddr() == uctypes.addressof(color.__dereference__()):
            Display.show_image(disp_img1)  # 显示第一缓冲区内容
        else:
            Display.show_image(disp_img2)  # 显示第二缓冲区内容
    
    # 通知LVGL当前帧刷新完成，可以开始下一帧渲染
    disp_drv.flush_ready()

def lvgl_init():
    """LVGL图形系统初始化函数
    功能：完成LVGL核心初始化，配置显示驱动和双缓冲
    参数：无
    返回：无
    """
    global disp_img1, disp_img2

    # 初始化LVGL核心系统
    lv.init()

    # 创建显示设备
    disp_drv = lv.disp_create(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    disp_drv.set_flush_cb(disp_drv_flush_cb)  # 设置显示刷新回调函数
    
    # 创建双缓冲区用于无闪烁渲染
    # disp_img1和disp_img2是两个图像对象，实现无闪烁渲染
    disp_img1 = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.BGRA8888)
    disp_img2 = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.BGRA8888)
    
    # 配置显示缓冲区：双缓冲模式，直接渲染
    disp_drv.set_draw_buffers(disp_img1.bytearray(), disp_img2.bytearray(), 
                             disp_img1.size(), lv.DISP_RENDER_MODE.DIRECT)

def lvgl_deinit():
    """LVGL系统反初始化函数
    功能：清理LVGL资源，释放内存
    参数：无
    返回：无
    """
    global disp_img1, disp_img2

    # 反初始化LVGL核心系统
    lv.deinit()
    
    # 删除缓冲区对象，释放内存
    del disp_img1
    del disp_img2

def user_gui_init():
    """用户界面初始化函数
    功能：创建演示界面，包含多语言文本和PNG动画
    参数：无
    返回：无
    """
    # 资源文件路径（SD卡中的演示资源）
    res_path = "/sdcard/examples/15-LVGL/data/"

    # 加载英文字体（Montserrat 16像素）
    font_montserrat_16 = lv.font_load("A:" + res_path + "font/montserrat-16.fnt")
    
    # 创建英文标签，显示现代术语解释
    ltr_label = lv.label(lv.scr_act())  # 在当前屏幕创建标签
    ltr_label.set_text("In modern terminology, a microcontroller is similar to a system on a chip (SoC).")
    ltr_label.set_style_text_font(font_montserrat_16, 0)  # 设置字体
    ltr_label.set_width(310)  # 设置宽度为310像素
    ltr_label.align(lv.ALIGN.TOP_MID, 0, 0)  # 顶部居中对齐

    # 加载中文字体（宋体16像素，支持CJK字符）
    font_simsun_16_cjk = lv.font_load("A:" + res_path + "font/lv_font_simsun_16_cjk.fnt")
    
    # 创建中文标签，显示嵌入式系统定义
    cz_label = lv.label(lv.scr_act())
    cz_label.set_style_text_font(font_simsun_16_cjk, 0)  # 设置中文字体
    cz_label.set_text("嵌入式系统（Embedded System），\n是一种嵌入机械或电气系统内部、具有专一功能和实时计算性能的计算机系统。")
    cz_label.set_width(310)  # 设置宽度为310像素
    cz_label.align(lv.ALIGN.BOTTOM_MID, 0, 0)  # 底部居中对齐

    # 创建动画图像数组（4帧PNG动画）
    anim_imgs = [None] * 4
    
    # 加载第1帧PNG图片
    with open(res_path + 'img/animimg001.png', 'rb') as f:
        anim001_data = f.read()
    anim_imgs[0] = lv.img_dsc_t({
        'data_size': len(anim001_data),
        'data': anim001_data
    })
    anim_imgs[-1] = anim_imgs[0]  # 最后一帧与第一帧相同，实现循环

    # 加载第2帧PNG图片
    with open(res_path + 'img/animimg002.png', 'rb') as f:
        anim002_data = f.read()
    anim_imgs[1] = lv.img_dsc_t({
        'data_size': len(anim002_data),
        'data': anim002_data
    })

    # 加载第3帧PNG图片
    with open(res_path + 'img/animimg003.png', 'rb') as f:
        anim003_data = f.read()
    anim_imgs[2] = lv.img_dsc_t({
        'data_size': len(anim003_data),
        'data': anim003_data
    })

    # 创建动画图像控件
    animimg0 = lv.animimg(lv.scr_act())  # 在当前屏幕创建动画图像
    animimg0.center()  # 居中显示
    animimg0.set_src(anim_imgs, 4)  # 设置动画源（4帧图像）
    animimg0.set_duration(2000)  # 设置动画持续时间为2秒
    animimg0.set_repeat_count(lv.ANIM_REPEAT_INFINITE)  # 无限循环播放
    animimg0.start()  # 开始动画

def mouse_read_cb(indev_drv, data):
    """鼠标/触控输入读取回调函数
    功能：模拟鼠标输入，提供固定坐标给LVGL
    参数：
        indev_drv: 输入设备驱动结构体
        data: 输入数据结构体，需要填充坐标和状态
    """
    # 设置鼠标坐标（屏幕中心位置）
    data.point = lv.point_t({100, 100})
    # 设置鼠标状态为释放（未按下）
    data.state = lv.INDEV_STATE.RELEASED

def keyboard_read_cb(indev_drv, data):
    """键盘输入读取回调函数
    功能：模拟键盘输入，当前返回无按键状态
    参数：
        indev_drv: 输入设备驱动结构体
        data: 输入数据结构体，需要填充按键值和状态
    """
    # 设置按键值为0（无按键）
    data.key = 0
    # 设置按键状态为释放
    data.state = lv.INDEV_STATE.RELEASED

def main():
    """主函数
    功能：程序入口，初始化系统并运行主循环
    参数：无
    返回：无
    """
    # 启用退出点，允许优雅退出
    os.exitpoint(os.EXITPOINT_ENABLE)
    
    try:
        # 初始化显示系统
        display_init()
        
        # 初始化LVGL图形系统
        lvgl_init()
        
        # 创建用户界面
        user_gui_init()
        
        # 主循环：持续运行LVGL任务处理器
        while True:
            time.sleep_ms(lv.task_handler())
            
    except BaseException as e:
        # 捕获并打印异常信息
        print(f"Exception {e}")
    finally:
        # 清理资源
        lvgl_deinit()
        display_deinit()
        gc.collect()  # 强制垃圾回收

# 程序入口点
if __name__ == "__main__":
    main()

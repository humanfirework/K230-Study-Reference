# LVGL触控演示程序 - K230平台
# 功能：展示基本的LVGL界面创建、触控交互和动画效果

# 导入必要的模块
import time, os, sys, gc        # 基础库
from media.display import *      # 显示相关功能
from media.media import *        # 媒体管理器
import lvgl as lv               # LVGL图形库
from machine import TOUCH       # 触控驱动

# 显示参数设置
DISPLAY_WIDTH = ALIGN_UP(800, 16)   # 屏幕宽度（800像素，16字节对齐）
DISPLAY_HEIGHT = 480                # 屏幕高度（480像素）

def display_init():
    """显示初始化函数
    功能：初始化K230的显示系统，配置ST7701 LCD控制器
    参数：无
    返回：无
    """
    # 初始化ST7701 LCD控制器，设置800x480分辨率
    # to_ide=True表示同时在IDE中显示（调试用）
    Display.init(Display.ST7701, width = 800, height = 480, to_ide = True)
    # 初始化媒体管理器，管理显示缓冲区
    MediaManager.init()

def display_deinit():
    """显示系统反初始化函数
    功能：程序退出时清理显示资源，释放内存和硬件资源
    参数：无
    返回：无
    """
    # 启用退出点睡眠模式，允许系统进入低功耗状态
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    # 延时50ms确保所有显示操作完成
    time.sleep_ms(50)
    # 反初始化显示驱动，关闭LCD控制器
    Display.deinit()
    # 释放媒体缓冲区，回收内存资源
    MediaManager.deinit()

def disp_drv_flush_cb(disp_drv, area, color):
    """LVGL显示刷新回调函数
    功能：将LVGL渲染好的图像数据发送到LCD屏幕显示
    参数：
        disp_drv: 显示驱动结构体
        area: 需要刷新的区域（LVGL内部使用）
        color: 图像数据缓冲区指针
    """
    global disp_img1, disp_img2

    # 检查是否为最后一帧数据
    if disp_drv.flush_is_last() == True:
        # 根据缓冲区地址判断使用哪个图像对象
        if disp_img1.virtaddr() == uctypes.addressof(color.__dereference__()):
            # 显示第一缓冲区内容
            Display.show_image(disp_img1)
            print(f"disp disp_img1 {disp_img1}")
        else:
            # 显示第二缓冲区内容
            Display.show_image(disp_img2)
            print(f"disp disp_img2 {disp_img2}")
        time.sleep(0.01)  # 短暂延时确保显示稳定

    # 通知LVGL刷新完成，可以开始下一帧渲染
    disp_drv.flush_ready()

class touch_screen():
    """触控屏幕驱动类
    功能：封装K230的触控驱动，为LVGL提供触控输入支持
    """
    def __init__(self):
        """初始化触控设备"""
        self.state = lv.INDEV_STATE.RELEASED  # 初始状态为释放

        # 创建LVGL输入设备驱动
        self.indev_drv = lv.indev_create()
        self.indev_drv.set_type(lv.INDEV_TYPE.POINTER)  # 设置为指针类型（触控/鼠标）
        self.indev_drv.set_read_cb(self.callback)       # 设置读取回调函数
        
        # 初始化硬件触控驱动（0表示第一个触控设备）
        self.touch = TOUCH(0)

    def callback(self, driver, data):
        """触控数据读取回调函数
        功能：从硬件读取触控数据并转换为LVGL格式
        参数：
            driver: LVGL输入设备驱动
            data: LVGL触控数据结构体
        """
        x, y, state = 0, 0, lv.INDEV_STATE.RELEASED  # 默认值
        
        # 读取触控数据（最多读取1个点）
        tp = self.touch.read(1)
        if len(tp):
            # 解析触控数据
            x, y, event = tp[0].x, tp[0].y, tp[0].event
            # 事件类型：2=按下，3=移动，其他为释放
            if event == 2 or event == 3:
                state = lv.INDEV_STATE.PRESSED
        
        # 设置触控坐标和状态给LVGL
        data.point = lv.point_t({'x': x, 'y': y})
        data.state = state

def lvgl_init():
    """LVGL图形库初始化函数
    功能：完成LVGL的完整初始化，包括显示驱动和触控驱动
    参数：无
    返回：无
    """
    global disp_img1, disp_img2

    # 初始化LVGL核心
    lv.init()

    # 创建LVGL显示驱动
    disp_drv = lv.disp_create(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    disp_drv.set_flush_cb(disp_drv_flush_cb)  # 设置显示刷新回调
    
    # 创建两个显示缓冲区（双缓冲机制）
    # BGRA8888格式：每个像素32位（8位蓝+8位绿+8位红+8位透明）
    disp_img1 = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.BGRA8888)
    disp_img2 = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.BGRA8888)
    
    # 设置双缓冲区及渲染模式
    disp_drv.set_draw_buffers(disp_img1.bytearray(), disp_img2.bytearray(), disp_img1.size(), lv.DISP_RENDER_MODE.DIRECT)
    
    # 初始化触控驱动
    tp = touch_screen()

def lvgl_deinit():
    global disp_img1, disp_img2

    lv.deinit()
    del disp_img1
    del disp_img2

def btn_clicked_event(event):
    """按钮状态切换事件处理函数
    功能：处理按钮点击事件，切换按钮文字状态（on/off）
    参数：
        event: LVGL事件对象，包含事件源信息
    """
    btn = lv.btn.__cast__(event.get_target())  # 获取事件源（按钮对象）
    label = lv.label.__cast__(btn.get_user_data())  # 获取之前保存的标签对象
    if "on" == label.get_text():
        label.set_text("off")
    else:
        label.set_text("on")

def user_gui_init():
    """创建主界面UI
    功能：创建包含标签、按钮、动画图片的演示界面
    参数：无
    返回：无
    """
    # 资源文件路径
    res_path = "/sdcard/examples/15-LVGL/data/"

    # 加载英文字体并创建顶部标签
    font_montserrat_16 = lv.font_load("A:" + res_path + "font/montserrat-16.fnt")
    ltr_label = lv.label(lv.scr_act())
    ltr_label.set_text("In modern terminology, a microcontroller is similar to a system on a chip (SoC).")
    ltr_label.set_style_text_font(font_montserrat_16,0)
    ltr_label.set_width(310)  # 设置标签宽度
    ltr_label.align(lv.ALIGN.TOP_MID, 0, 0)  # 顶部居中对齐

    # 加载中文字体并创建底部标签
    font_simsun_16_cjk = lv.font_load("A:" + res_path + "font/lv_font_simsun_16_cjk.fnt")
    cz_label = lv.label(lv.scr_act())
    cz_label.set_style_text_font(font_simsun_16_cjk, 0)
    cz_label.set_text("嵌入式系统（Embedded System），\n是一种嵌入机械或电气系统内部、具有专一功能和实时计算性能的计算机系统。")
    cz_label.set_width(310)
    cz_label.align(lv.ALIGN.BOTTOM_MID, 0, 0)  # 底部居中对齐

    # 准备动画图片数据
    anim_imgs = [None]*4
    with open(res_path + 'img/animimg001.png','rb') as f:
        anim001_data = f.read()
    anim_imgs[0] = lv.img_dsc_t({
        'data_size': len(anim001_data),
        'data': anim001_data
    })
    anim_imgs[-1] = anim_imgs[0]  # 第四帧复用第一帧

    with open(res_path + 'img/animimg002.png','rb') as f:
        anim002_data = f.read()
    anim_imgs[1] = lv.img_dsc_t({
        'data_size': len(anim002_data),
        'data': anim002_data
    })

    with open(res_path + 'img/animimg003.png','rb') as f:
        anim003_data = f.read()
    anim_imgs[2] = lv.img_dsc_t({
        'data_size': len(anim003_data),
        'data': anim003_data
    })

    # 创建动画图片控件
    animimg0 = lv.animimg(lv.scr_act())
    animimg0.center()  # 屏幕中心对齐
    animimg0.set_src(anim_imgs, 4)  # 设置4帧动画源
    animimg0.set_duration(2000)  # 2秒完成一次循环
    animimg0.set_repeat_count(lv.ANIM_REPEAT_INFINITE)  # 无限循环
    animimg0.start()  # 开始动画

    # 创建交互按钮
    btn = lv.btn(lv.scr_act())
    btn.align(lv.ALIGN.CENTER, 0, lv.pct(25))  # 中心下方25%位置
    label = lv.label(btn)
    label.set_text('on')
    btn.set_user_data(label)  # 将标签对象保存为用户数据
    btn.add_event(btn_clicked_event, lv.EVENT.CLICKED, None)  # 注册点击事件

def main():
    """主函数
    功能：程序入口，初始化所有系统并运行主循环
    参数：无
    返回：无
    """
    os.exitpoint(os.EXITPOINT_ENABLE)
    try:
        # 切换到资源文件所在目录
        os.chdir("/sdcard/examples/15-LVGL")
        
        # 系统初始化
        display_init()  # 显示系统初始化
        lvgl_init()     # LVGL库初始化
        user_gui_init() # 用户界面初始化
        
        # 主循环：处理LVGL任务和触控事件
        while True:
            time.sleep_ms(lv.task_handler())  # 处理LVGL任务并延时
    except BaseException as e:
        import sys
        sys.print_exception(e)
    finally:
        # 清理资源
        lvgl_deinit()
        display_deinit()
        gc.collect()

if __name__ == "__main__":
    # 当脚本直接运行时执行主函数
    main()

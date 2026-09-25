"""
LVGL触摸演示程序（FreeType字体支持）

该程序演示了在K230开发板上使用LVGL图形库创建带有触摸功能的用户界面，
并支持FreeType字体渲染。程序主要功能包括：
1. 初始化ST7701显示控制器，支持800x480分辨率显示
2. 配置双缓冲显示机制以提高渲染性能
3. 集成触摸屏输入设备支持
4. 使用FreeType引擎渲染中英文字体
5. 创建包含文本标签、动画图像和交互按钮的用户界面
6. 实现按钮点击事件处理

程序结构：
- display_init/deinit: 显示模块初始化和反初始化
- disp_drv_flush_cb: 显示驱动刷新回调函数
- touch_screen: 触摸屏输入设备类
- lvgl_init/deinit: LVGL图形库初始化和反初始化
- user_gui_init: 用户界面元素创建
- main: 主程序循环
"""

# 导入显示相关模块
from media.display import *
# 导入媒体管理模块
from media.media import *
# 导入系统相关模块：time(时间处理), os(操作系统接口), sys(系统特定参数), gc(垃圾回收)
import time, os, sys, gc
# 导入LVGL图形库
import lvgl as lv
# 导入触摸屏模块
from machine import TOUCH

# 定义显示宽度，使用ALIGN_UP确保宽度是16的倍数，以满足内存对齐要求
DISPLAY_WIDTH = ALIGN_UP(800, 16)
# 定义显示高度
DISPLAY_HEIGHT = 480

def display_init():
    """
    初始化显示模块
    配置ST7701显示控制器，设置显示分辨率，并初始化媒体管理器
    """
    # 使用ST7701显示控制器初始化显示，设置宽度为800，高度为480，to_ide参数表示是否在IDE中显示
    Display.init(Display.ST7701, width = 800, height = 480, to_ide = True)
    # 初始化媒体管理器，用于管理图像和其他媒体资源
    MediaManager.init()

def display_deinit():
    """
    反初始化显示模块
    在程序退出时调用，用于释放显示和媒体资源
    """
    # 启用系统睡眠模式
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    # 延时50毫秒，确保操作完成
    time.sleep_ms(50)
    # 反初始化显示模块
    Display.deinit()
    # 释放媒体缓冲区
    MediaManager.deinit()

def disp_drv_flush_cb(disp_drv, area, color):
    """
    显示驱动刷新回调函数
    负责将LVGL渲染的图像数据发送到显示设备
    
    参数:
    disp_drv: 显示驱动对象
    area: 需要刷新的区域
    color: 颜色数据缓冲区
    """
    global disp_img1, disp_img2

    # 检查是否是最后一次刷新操作
    if disp_drv.flush_is_last() == True:
        # 通过比较虚拟地址确定当前使用的是哪个缓冲区
        if disp_img1.virtaddr() == uctypes.addressof(color.__dereference__()):
            # 显示第一个缓冲区的内容
            Display.show_image(disp_img1)
            print(f"disp disp_img1 {disp_img1}")
        else:
            # 显示第二个缓冲区的内容
            Display.show_image(disp_img2)
            print(f"disp disp_img2 {disp_img2}")
        # 短暂延时以确保显示稳定
        time.sleep(0.01)

    # 通知LVGL刷新操作已完成
    disp_drv.flush_ready()

class touch_screen():
    """
    触摸屏输入设备类
    负责处理触摸屏输入事件，并将触摸数据传递给LVGL
    """
    def __init__(self):
        """
        初始化触摸屏输入设备
        """
        # 初始化触摸状态为释放状态
        self.state = lv.INDEV_STATE.RELEASED

        # 创建LVGL输入设备驱动
        self.indev_drv = lv.indev_create()
        # 设置设备类型为指针设备（触摸屏）
        self.indev_drv.set_type(lv.INDEV_TYPE.POINTER)
        # 设置读取回调函数
        self.indev_drv.set_read_cb(self.callback)
        # 初始化硬件触摸屏设备
        self.touch = TOUCH(0)

    def callback(self, driver, data):
        """
        触摸屏读取回调函数
        从硬件读取触摸数据并更新LVGL输入设备状态
        
        参数:
        driver: 输入设备驱动
        data: 输入设备数据结构
        """
        # 初始化坐标和状态
        x, y, state = 0, 0, lv.INDEV_STATE.RELEASED
        # 从触摸屏读取最多1个触摸点的数据
        tp = self.touch.read(1)
        # 如果有触摸数据
        if len(tp):
            # 提取第一个触摸点的坐标和事件类型
            x, y, event = tp[0].x, tp[0].y, tp[0].event
            # 如果是按下或移动事件，设置状态为按下
            if event == 2 or event == 3:
                state = lv.INDEV_STATE.PRESSED
        # 更新触摸点坐标
        data.point = lv.point_t({'x': x, 'y': y})
        # 更新触摸状态
        data.state = state

def lvgl_init():
    """
    初始化LVGL图形库
    配置显示驱动、双缓冲区和输入设备
    """
    global disp_img1, disp_img2

    # 初始化LVGL核心库
    lv.init()
    # 初始化FreeType字体渲染引擎，参数(1, 0, 65535)分别表示缓存大小、字体格式和最大字体数
    lv.freetype_init(1, 0, 65535)
    # 创建显示驱动，设置显示分辨率
    disp_drv = lv.disp_create(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    # 设置显示驱动的刷新回调函数
    disp_drv.set_flush_cb(disp_drv_flush_cb)
    # 创建两个图像缓冲区用于双缓冲渲染
    disp_img1 = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.BGRA8888)
    disp_img2 = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.BGRA8888)
    # 设置显示驱动的绘制缓冲区
    disp_drv.set_draw_buffers(disp_img1.bytearray(), disp_img2.bytearray(), disp_img1.size(), lv.DISP_RENDER_MODE.DIRECT)
    # 初始化触摸屏输入设备
    tp = touch_screen()

def lvgl_deinit():
    """
    反初始化LVGL图形库
    在程序退出时调用，用于释放LVGL相关资源
    """
    global disp_img1, disp_img2

    # 反初始化FreeType字体渲染引擎
    lv.freetype_uninit()
    # 反初始化LVGL核心库
    lv.deinit()
    # 删除显示缓冲区对象
    del disp_img1
    # 删除显示缓冲区对象
    del disp_img2

def btn_clicked_event(event):
    """
    按钮点击事件处理函数
    切换按钮标签文本在"on"和"off"之间
    
    参数:
    event: 事件对象，包含触发事件的控件信息
    """
    # 获取触发事件的按钮对象
    btn = lv.btn.__cast__(event.get_target())
    # 获取按钮关联的标签对象
    label = lv.label.__cast__(btn.get_user_data())
    # 根据当前标签文本切换为相反状态
    if "on" == label.get_text():
        label.set_text("off")
    else:
        label.set_text("on")

def user_gui_init():
    """
    初始化用户界面
    创建标签、动画图像和按钮等UI元素
    """
    # 定义资源文件路径
    res_path = "/sdcard/examples/15-LVGL/data/"

    # 创建中文字体对象，加载SourceHanSansSC字体文件，设置字体大小为20
    chinese_font = lv.freetype_font_create("/sdcard/res/font/SourceHanSansSC-Normal-Min.ttf", 20, 0)
    # 检查字体是否加载成功
    if not chinese_font:
        raise Exception("Failed to load fonts")
    
    # 创建英文标签
    ltr_label = lv.label(lv.scr_act())
    # 设置标签文本内容
    ltr_label.set_text("In modern terminology, a microcontroller is similar to a system on a chip (SoC).")
    # 设置标签使用的字体
    ltr_label.set_style_text_font(chinese_font,0)
    # 设置标签宽度
    ltr_label.set_width(400)
    # 设置标签对齐方式为顶部居中
    ltr_label.align(lv.ALIGN.TOP_MID, 0, 0)

    # 创建中文标签
    cz_label = lv.label(lv.scr_act())
    # 设置标签使用的字体
    cz_label.set_style_text_font(chinese_font, 0)
    # 设置标签文本内容
    cz_label.set_text("嵌入式系统（Embedded System），\n是一种嵌入机械或电气系统内部、具有专一功能和实时计算性能的计算机系统。")
    # 设置标签宽度
    cz_label.set_width(400)
    # 设置标签对齐方式为底部居中
    cz_label.align(lv.ALIGN.BOTTOM_MID, 0, 0)

    # 创建动画图像数组
    anim_imgs = [None]*4
    # 读取第一张动画图像
    with open(res_path + 'img/animimg001.png','rb') as f:
        anim001_data = f.read()

    # 创建LVGL图像描述符
    anim_imgs[0] = lv.img_dsc_t({
    'data_size': len(anim001_data),
    'data': anim001_data
    })
    # 将最后一张图像设置为第一张图像（形成循环）
    anim_imgs[-1] = anim_imgs[0]

    # 读取第二张动画图像
    with open(res_path + 'img/animimg002.png','rb') as f:
        anim002_data = f.read()

    anim_imgs[1] = lv.img_dsc_t({
    'data_size': len(anim002_data),
    'data': anim002_data
    })

    # 读取第三张动画图像
    with open(res_path + 'img/animimg003.png','rb') as f:
        anim003_data = f.read()

    anim_imgs[2] = lv.img_dsc_t({
    'data_size': len(anim003_data),
    'data': anim003_data
    })

    # 创建动画图像控件
    animimg0 = lv.animimg(lv.scr_act())
    # 将动画图像控件居中显示
    animimg0.center()
    # 设置动画图像源和帧数
    animimg0.set_src(anim_imgs, 4)
    # 设置动画持续时间（毫秒）
    animimg0.set_duration(2000)
    # 设置动画重复次数为无限循环
    animimg0.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
    # 开始播放动画
    animimg0.start()

    # 创建按钮控件
    btn = lv.btn(lv.scr_act())
    # 设置按钮对齐方式为居中，垂直方向偏移25%
    btn.align(lv.ALIGN.CENTER, 0, lv.pct(25))
    # 创建按钮标签
    label = lv.label(btn)
    # 设置按钮标签初始文本
    label.set_text('on')
    # 将标签关联到按钮的用户数据
    btn.set_user_data(label)
    # 为按钮添加点击事件处理函数
    btn.add_event(btn_clicked_event, lv.EVENT.CLICKED, None)

def main():
    """
    主函数
    程序入口点，负责初始化系统、运行主循环和清理资源
    """
    # 启用系统退出点，允许程序响应系统退出信号
    os.exitpoint(os.EXITPOINT_ENABLE)
    try:
        # 初始化显示模块
        display_init()
        # 初始化LVGL图形库
        lvgl_init()
        # 初始化用户界面
        user_gui_init()
        # 主循环：不断处理LVGL任务
        while True:
            # 执行LVGL任务处理，并根据返回值延时
            time.sleep_ms(lv.task_handler())
    # 捕获所有异常并打印错误信息
    except BaseException as e:
        import sys
        sys.print_exception(e)
    # 反初始化LVGL图形库
    lvgl_deinit()
    # 反初始化显示模块
    display_deinit()
    # 执行垃圾回收
    gc.collect()

# 程序入口点
# 当脚本作为主程序运行时（而非被导入为模块时），执行main函数
if __name__ == "__main__":
    main()

# ========================= 库导入 =========================
from media.display import *
from media.media import *
from media.sensor import *
import time, os, sys, gc, math, struct
import lvgl as lv
import image
from machine import TOUCH, Pin, FPIOA, UART
import ulab.numpy as np
import uctypes

# ======================= 全局配置 =======================
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
CAMERA_WIDTH, CAMERA_HEIGHT = 640, 480

# 全局阈值（可被动态修改）
RED_THRESHOLD = [(85, 100, -18, 50, -18, 51)]
GRAY_THRESHOLD = [(82, 212)]
BLOB_AREA_THRESHOLD = 5
RECT_AREA_THRESHOLD = 20000

# 全局状态
current_mode = 0
threshold_values = list(RED_THRESHOLD[0])
gray_threshold_values = list(GRAY_THRESHOLD[0])
sensor = None
disp_img1 = None
disp_img2 = None

# ======================= 摄像头初始化 =======================
def camera_init():
    sensor = Sensor(id=2)
    sensor.reset()
    sensor.set_framesize(width=CAMERA_WIDTH, height=CAMERA_HEIGHT)
    sensor.set_pixformat(Sensor.RGB565)
    sensor.run()
    return sensor

# ======================= 显示系统初始化 =======================
def display_init():
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()

def display_deinit():
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(50)
    Display.deinit()
    MediaManager.deinit()

# ======================= LVGL初始化 =======================
def disp_drv_flush_cb(disp_drv, area, color):
    global disp_img1, disp_img2
    if disp_drv.flush_is_last():
        img = disp_img1 if disp_img1.virtaddr() == uctypes.addressof(color.__dereference__()) else disp_img2
        Display.show_image(img)
    disp_drv.flush_ready()

class touch_screen:
    def __init__(self):
        self.indev_drv = lv.indev_create()
        self.indev_drv.set_type(lv.INDEV_TYPE.POINTER)
        self.indev_drv.set_read_cb(self.callback)
        self.touch = TOUCH(0)

    def callback(self, driver, data):
        x, y, state = 0, 0, lv.INDEV_STATE.RELEASED
        tp = self.touch.read(0)
        if tp:
            x, y, event = tp[0].x, tp[0].y, tp[0].event
            state = lv.INDEV_STATE.PRESSED if event in [2, 3] else lv.INDEV_STATE.RELEASED
        data.point = lv.point_t({'x': x, 'y': y})
        data.state = state

def lvgl_init():
    global disp_img1, disp_img2
    lv.init()
    disp_drv = lv.disp_create(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    disp_drv.set_flush_cb(disp_drv_flush_cb)
    disp_img1 = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.BGRA8888)
    disp_img2 = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.BGRA8888)
    disp_drv.set_draw_buffers(disp_img1.bytearray(), disp_img2.bytearray(),
                             disp_img1.size(), lv.DISP_RENDER_MODE.DIRECT)
    tp = touch_screen()

def lvgl_deinit():
    lv.deinit()
    global disp_img1, disp_img2
    del disp_img1, disp_img2
    disp_img1 = disp_img2 = None

# ======================= 视觉识别函数 =======================
def color_tracking(sensor, threshold):
    img = sensor.snapshot()
    blobs = img.find_blobs([threshold], pixels_threshold=BLOB_AREA_THRESHOLD)
    result = {"x": 0, "y": 0, "found": False, "img": img}
    if blobs:
        largest = max(blobs, key=lambda b: b.pixels())
        result.update({"x": largest.cx(), "y": largest.cy(), "found": True})
        img.draw_rectangle(largest.x(), largest.y(), largest.w(), largest.h(), color=(0, 255, 0), thickness=2)
        img.draw_cross(largest.cx(), largest.cy(), color=(0, 255, 0), size=10)
    return result

def rect_detection(sensor, gray_threshold, min_area):
    img = sensor.snapshot()
    gray = img.to_grayscale()
    binary = gray.binary([gray_threshold]).dilate(1).erode(1)
    rects = binary.find_rects(threshold=int(min_area * 1.5))
    valid = [r for r in rects if r.w() * r.h() >= min_area and 0.3 <= max(r.w(), r.h()) / min(r.w(), r.h()) <= 3]
    for i, r in enumerate(valid):
        color = (255, 0, 0) if i == 0 else (0, 255, 0)
        img.draw_rectangle(r.x(), r.y(), r.w(), r.h(), color=color, thickness=2)
    return {"rects": valid, "img": img}

# ======================= 主程序 =======================
def main():
    global sensor, current_mode, threshold_values, gray_threshold_values, RED_THRESHOLD, GRAY_THRESHOLD
    try:
        display_init()
        lvgl_init()
        sensor = camera_init()
        scr = lv.scr_act()
        scr.set_style_bg_color(lv.color_hex(0x1a1a1a), 0)

        # 标题
        title = lv.label(scr)
        title.set_text("K230 机器视觉系统")
        title.set_pos(50, 20)
        title.set_style_text_color(lv.color_white(), 0)

        # 按钮容器
        btn_container = lv.obj(scr)
        btn_container.set_pos(50, 100)
        btn_container.set_size(700, 350)
        btn_container.set_style_bg_color(lv.color_hex(0x2a2a2a), 0)
        btn_container.set_style_border_width(0, 0)
        btn_container.set_style_radius(10, 0)
        btn_container.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP)
        btn_container.set_flex_main_place(lv.FLEX_ALIGN.SPACE_EVENLY)
        btn_container.set_style_pad_all(20, 0)

        # 按钮样式
        btn_style = lv.style_t()
        btn_style.init()
        btn_style.set_bg_color(lv.color_hex(0x667eea))
        btn_style.set_radius(15)
        btn_style.set_shadow_width(10)
        btn_style.set_shadow_color(lv.color_hex(0x333333))
        btn_style.set_shadow_ofs_x(0)
        btn_style.set_shadow_ofs_y(5)

        # 任务定义
        tasks = [
            {"name": "颜色追踪", "icon": "🎯", "func": run_color_tracking},
            {"name": "矩形识别", "icon": "⬜", "func": run_rect_detection},
            {"name": "阈值调节", "icon": "⚙️", "func": run_threshold_config}
        ]
        buttons = []

        for task in tasks:
            btn = lv.btn(btn_container)
            btn.set_size(200, 120)
            btn.add_style(btn_style, 0)
            content = lv.obj(btn)
            content.set_size(180, 100)
            content.center()
            content.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            content.set_flex_main_place(lv.FLEX_ALIGN.CENTER)
            lv.label(content).set_text(task["icon"])
            lv.label(content).set_text(task["name"])
            buttons.append(btn)

        # 状态栏
        status_bar = lv.obj(scr)
        status_bar.set_pos(0, DISPLAY_HEIGHT - 40)
        status_bar.set_size(DISPLAY_WIDTH, 40)
        status_bar.set_style_bg_color(lv.color_hex(0x333333), 0)
        status_label = lv.label(status_bar)
        status_label.set_text("就绪 - 点击按钮进入任务")
        status_label.set_pos(20, 10)
        status_label.set_style_text_color(lv.color_hex(0xcccccc), 0)

        # 事件绑定
        def create_handler(task):
            def handler(e):
                status_label.set_text(f"正在进入: {task['name']}")
                task['func']()
            return handler

        for btn, task in zip(buttons, tasks):
            btn.add_event_cb(create_handler(task), lv.EVENT.CLICKED, None)

        # 主循环
        while True:
            lv.timer_handler()
            time.sleep_ms(10)

    except KeyboardInterrupt as e:
        print("user stop:", e)
    except BaseException as e:
        print("Exception:", e)
        sys.print_exception(e)
    finally:
        if sensor:
            sensor.stop()
        display_deinit()
        lvgl_deinit()
        gc.collect()

# ======================= 任务实现 =======================
def run_color_tracking():
    global sensor, RED_THRESHOLD
    print("开始颜色追踪...")
    while True:
        result = color_tracking(sensor, RED_THRESHOLD[0])
        Display.show_image(result['img'])
        if TOUCH(0).read(0):
            break
        time.sleep_ms(50)

def run_rect_detection():
    global sensor, GRAY_THRESHOLD
    print("开始矩形识别...")
    while True:
        result = rect_detection(sensor, GRAY_THRESHOLD[0], RECT_AREA_THRESHOLD)
        Display.show_image(result['img'])
        if TOUCH(0).read(0):
            break
        time.sleep_ms(50)

def run_threshold_config():
    global sensor, threshold_values, gray_threshold_values, RED_THRESHOLD, GRAY_THRESHOLD
    tp = TOUCH(0)
    threshold_modes = {
        'red_point': {
            'name': '红点识别(LAB)',
            'values': threshold_values.copy(),
            'labels': ['L最小', 'L最大', 'A最小', 'A最大', 'B最小', 'B最大'],
            'ranges': [(0, 100), (0, 100), (-128, 127), (-128, 127), (-128, 127), (-128, 127)]
        },
        'gray_rect': {
            'name': '矩形识别(灰度)',
            'values': gray_threshold_values.copy(),
            'labels': ['最小值', '最大值'],
            'ranges': [(0, 255), (0, 255)]
        }
    }
    current_mode_key = 'red_point'
    current_values = threshold_modes[current_mode_key]['values'].copy()

    def draw_ui():
        img = sensor.snapshot()
        img.draw_rectangle(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, color=(50, 50, 50), fill=True)
        mode = threshold_modes[current_mode_key]
        y = 100
        for i, (label, val, (min_v, max_v)) in enumerate(zip(mode['labels'], current_values, mode['ranges'])):
            img.draw_string(50, y, f"{label}: {val}", color=(255, 255, 255), scale=2)
            bar_w = int((val - min_v) / (max_v - min_v) * 400)
            img.draw_rectangle(200, y + 30, max(1, bar_w), 20, color=(255, 0, 0), fill=True)
            y += 60
        # 预览
        preview = sensor.snapshot()
        if current_mode_key == 'red_point':
            blobs = preview.find_blobs([tuple(current_values)], pixels_threshold=5)
            for b in blobs:
                preview.draw_rectangle(b.x(), b.y(), b.w(), b.h(), color=(0, 255, 0), thickness=2)
        else:
            gray = preview.to_grayscale()
            binary = gray.binary([tuple(current_values)])
            preview = binary.to_rgb565()
        scaled = preview.resize(160, 120)
        img.draw_image(scaled, DISPLAY_WIDTH - 180, 100)
        return img

    while True:
        Display.show_image(draw_ui())
        pts = tp.read(0)
        if pts:
            x, y = pts[0].x, pts[0].y
            if y > DISPLAY_HEIGHT - 60:
                if x < 100:
                    break  # 返回
                elif 300 < x < 400:
                    current_mode_key = 'gray_rect' if current_mode_key == 'red_point' else 'red_point'
                    current_values = threshold_modes[current_mode_key]['values'].copy()
                elif 500 < x < 600:
                    if current_mode_key == 'red_point':
                        threshold_values[:] = current_values
                        RED_THRESHOLD[0] = tuple(current_values)
                    else:
                        gray_threshold_values[:] = current_values
                        GRAY_THRESHOLD[0] = tuple(current_values)
                    print("已保存")
        time.sleep_ms(100)
        lv.timer_handler()
        gc.collect()

# ======================= 程序入口 =======================
if __name__ == "__main__":
    main()

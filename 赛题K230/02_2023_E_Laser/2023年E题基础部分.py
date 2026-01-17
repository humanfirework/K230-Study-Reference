# bilibili搜索学不会电磁场看教程
# 第14课，视觉相关的题目受到光线干扰非常严重，但是有时候组委会规定不得使用补光灯
# 这时候就需要调整阈值，然而，测评的时候不能带电脑，所以，就有了这个解决方案

import time
import os
import sys

from media.sensor import *
from media.display import *
from media.media import *
from time import ticks_ms
from machine import FPIOA
from machine import Pin
from machine import PWM
from machine import Timer
from machine import TOUCH
from machine import UART

sensor = None

try:
    # PID对象，用于控制步进电机
    class PID_step_motor:
        def __init__(self, kp, ki, target=240):
            self.e = 0
            self.e_last = 0
            self.kp = kp
            self.ki = ki
            self.target = target
        def cal(self, value):
            self.e = self.target - value
            delta = self.kp * (self.e-self.e_last) + self.ki * self.e
            self.e_last = self.e
            return delta

    fpioa = FPIOA()
    fpioa.set_function(11, FPIOA.UART2_TXD)
    fpioa.set_function(12, FPIOA.UART2_RXD)
    uart2 = UART(UART.UART2, 115200)
    rx_order = [0xAA, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x02, 0xFF, 0xFF]
    def send_order(number, dir_, steps):
        global rx_order, uart2
        rx_order[2] = number
        rx_order[3] = dir_
        rx_order[4] = (steps // 256) % 256
        rx_order[5] = steps % 256
        rx_order[6] = sum(rx_order[2:6]) % 256
        uart2.write(bytes(rx_order))

    sensor = Sensor(width=1920, height=1080)
    sensor.reset()

    # 鼠标悬停在函数上可以查看允许接收的参数
    sensor.set_framesize(width=1920, height=1080)
    sensor.set_pixformat(Sensor.RGB565)

    Display.init(Display.ST7701, to_ide=True, width=800, height=480)
    # 初始化媒体管理器
    MediaManager.init()
    # 启动 sensor
    sensor.run()

    # 设置按键
    fpioa.set_function(53, FPIOA.GPIO53)
    fpioa.set_function(32, FPIOA.GPIO32)
    fpioa.set_function(34, FPIOA.GPIO34)
    fpioa.set_function(35, FPIOA.GPIO35)
    fpioa.set_function(42, FPIOA.GPIO42)
    fpioa.set_function(52, FPIOA.GPIO52)
    fpioa.set_function(37, FPIOA.GPIO37)
    key = Pin(53, Pin.IN, Pin.PULL_DOWN)

    # 启动
    s5 = Pin(32, Pin.IN, Pin.PULL_UP)

    s6 = Pin(34, Pin.IN, Pin.PULL_UP)
    s7 = Pin(35, Pin.IN, Pin.PULL_UP)
    s8 = Pin(42, Pin.IN, Pin.PULL_UP)

    # 标定
    s9 = Pin(52, Pin.IN, Pin.PULL_UP)

    # 状态切换
    s10 = Pin(37, Pin.IN, Pin.PULL_UP)

    #设置激光笔
    fpioa.set_function(33, FPIOA.GPIO33)
    pin = Pin(33, Pin.OUT)
    pin.value(0)

    clock = time.clock()

    # 状态标识，死循环中会根据不同的flag值执行相应的逻辑
    # flag = 1则识别激光点
    # flag = 2则可以调整阈值
    # flag = 3第一问，第二问标定
    # flag = 4第一问模式
    flag = 0
    state_lst = ['normal', 'red_point', 'threshold', '(1)(2)set', '(1)', '(2)', '(3)(4)']

    start_flag = 0
    process_rect_flag = 0
    process_rect_flag_3_4 = 0

    center_point = []
    rect_points_lst = [[], [], [], []]
    rect_points_lst_3_4 = [[], [], [], []]

    # 初始化中心点和PID对象
    c_x = 320
    c_y = 320 # 这两个值是随便写的，因为后面的代码会改
    pid_x = PID_step_motor(-0.2, -0.1, c_x)
    pid_y = PID_step_motor(-0.2, -0.1, c_y)

    # 裁剪图像的ROI，格式为(x, y, w, h)，推荐使用480*480的大小，此大小性能高，而且刚好可以铺满LCD屏幕
    cut_roi = (600, 360, 360, 360)

    # 向屏幕输出图像，脱机运行时可以选择注释img.compress_for_ide()来提升性能
    def show_img_2_screen():
        global img
        if(img.height()>480 or img.width() > 800):
            scale = max(img.height() // 480, img.width() // 800) + 1
            img.midpoint_pool(scale, scale)
        img.compress_for_ide()
        Display.show_image(img, x=(800-img.width())//2, y=(480-img.height())//2)

    # 触摸计数器，达到一定的数值后开启阈值编辑模式，防止误触
    touch_counter = 0

    # 触摸屏初始化
    tp = TOUCH(0)

    # 存储阈值
    threshold_dict = {'rect': [(78, 255)], 'red_point':\
    [(52, 100, 24, 127, -49, 41), (29, 73, 19, 127, -57, 89)]}
    # 清空阈值（可以注释掉，这里只是为了演示阈值编辑功能）
#    threshold_dict['rect'] = []
#    threshold_dict['red_point'] = []

    def detect_red_point():
        global pin, img, red_x, red_y
        pin.value(1)
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        img = img.copy(roi=cut_roi)
        blobs = img.find_blobs(threshold_dict['red_point'], False,\
                               x_stride=1, y_stride=1, \
                               pixels_threshold=20, margin=False)
        for blob in blobs:
            img.draw_rectangle(blob.x(), blob.y(), blob.w(), blob.h(), color=(0, 255, 0), thickness=2, fill=False)
            red_x = blob.x() + blob.w() / 2
            red_y = blob.y() + blob.h() / 2
        show_img_2_screen()

    def linear_process(point_1, point_2, num=10):
        if abs(point_2[0] - point_1[0]) < 2 and abs(point_2[1] - point_1[1]) < 2:
            return [point_1, point_2]
        else:
            points_lst = []
            delta_x_ = (point_2[0] - point_1[0]) / num
            delta_y_ = (point_2[1] - point_1[1]) / num
            for i in range(num):
                points_lst.append([point_1[0] + delta_x_*i, point_1[1] + delta_y_*i])
            points_lst.append(point_2)
            return points_lst
    pt_2 = 0


    while True:
        clock.tick()
        os.exitpoint()

#        # 绘制方框，参数依次为：x, y, w, h, 颜色，线宽，是否填充
#        img.draw_rectangle(1000, 50, 300, 200, color=(0, 0, 255), thickness=4, fill=False)

        if s10.value() == 0:
            flag = (flag + 1) % len(state_lst)
            if flag == 2:
                flag = flag + 1
            img = image.Image(800, 480, image.RGB565)
            img.draw_rectangle(0, 0, 800, 480, color=(255, 255, 255), thickness=2, fill=True)
            img.draw_string_advanced(320, 240, 30, "switch_to_{}".format(state_lst[flag]), color=(0, 0, 0))
            show_img_2_screen()
            start_flag = 0
            time.sleep(2)

        # 如果按下了按键，就识别矩形
        if key.value() == 1:
            pin.value(0)
            time.sleep_ms(3000)
            for i in range(5):
                img = sensor.snapshot(chn=CAM_CHN_ID_0)
                img = img.copy(roi=cut_roi)
                img_rect = img.to_grayscale(copy=True)
                img_rect = img_rect.binary(threshold_dict['rect'])
                rects = img_rect.find_rects(threshold=10000)

                def order_two_rects(corner_1, corner_2):
                    c_1_x, c_1_y = corner_1[0][0], corner_1[0][1]
                    distance_lst  = [(i_ - c_1_x)**2 + (j_ - c_1_y)**2 for i_, j_ in corner_2]
                    idx_min = distance_lst.index(min(distance_lst))
                    corner_2 = corner_2[idx_min:] + corner_2[:idx_min]
                    return corner_1, corner_2


                if not rects == None:
                    for rect in rects:
                        corner = rect.corners()
                        img.draw_line(corner[0][0], corner[0][1], corner[1][0], corner[1][1], color=(0, 255, 0), thickness=5)
                        img.draw_line(corner[2][0], corner[2][1], corner[1][0], corner[1][1], color=(0, 255, 0), thickness=5)
                        img.draw_line(corner[2][0], corner[2][1], corner[3][0], corner[3][1], color=(0, 255, 0), thickness=5)
                        img.draw_line(corner[0][0], corner[0][1], corner[3][0], corner[3][1], color=(0, 255, 0), thickness=5)
                # 检测到两个框就说明检测大概率正确
                if len(rects) == 2:
                    corner_1, corner_2 = order_two_rects(rects[0].corners(), rects[1].corners())
                    rect_points_lst_3_4 = [[(x1 + x2)/2, (y1+y2)/2] for (x1, y1), (x2, y2) in zip(corner_1, corner_2)]
                    img.draw_line(int(rect_points_lst_3_4[0][0]), int(rect_points_lst_3_4[0][1]), int(rect_points_lst_3_4[1][0]), int(rect_points_lst_3_4[1][1]), color=(255, 255, 0), thickness=2)
                    img.draw_line(int(rect_points_lst_3_4[1][0]), int(rect_points_lst_3_4[1][1]), int(rect_points_lst_3_4[2][0]), int(rect_points_lst_3_4[2][1]), color=(255, 255, 0), thickness=2)
                    img.draw_line(int(rect_points_lst_3_4[2][0]), int(rect_points_lst_3_4[2][1]), int(rect_points_lst_3_4[3][0]), int(rect_points_lst_3_4[3][1]), color=(255, 255, 0), thickness=2)
                    img.draw_line(int(rect_points_lst_3_4[3][0]), int(rect_points_lst_3_4[3][1]), int(rect_points_lst_3_4[0][0]), int(rect_points_lst_3_4[0][1]), color=(255, 255, 0), thickness=2)

                    show_img_2_screen()
                    time.sleep_ms(500)
                    break
                else:
                    img.draw_string_advanced(30, 30, 30, "识别错误", color=(0, 0, 0))
                    show_img_2_screen()
                    time.sleep_ms(500)


        # flag=1则识别激光点并进行PID运算
        elif flag == 1:
            pin.value(1)
            img = sensor.snapshot(chn=CAM_CHN_ID_0)
            img = img.copy(roi=cut_roi)
            blobs = img.find_blobs(threshold_dict['red_point'], False,\
                                   x_stride=1, y_stride=1, \
                                   pixels_threshold=20, margin=False)
            for blob in blobs:
                img.draw_rectangle(blob.x(), blob.y(), blob.w(), blob.h(), color=(0, 255, 0), thickness=2, fill=False)
                red_x = blob.x() + blob.w() / 2
                red_y = blob.y() + blob.h() / 2

#                delta_x = pid_x.cal(red_x)
#                dir_ = 1 if delta_x > 0 else 0
#                send_order(0, dir_, abs(int(delta_x)))

#                delta_y = pid_y.cal(red_y)
#                dir_ = 1 if delta_y < 0 else 0
#                send_order(1, dir_, abs(int(delta_y)))
                break
            show_img_2_screen()

        # 如果flag = 2，则启动阈值调整功能
        elif flag == 2:
            # 打开激光笔
            pin.value(1)

            # 清空当前的阈值
            for key_ in threshold_dict.keys():
                threshold_dict[key_] = []

            button_color = (150, 150, 150)
            text_color = (0, 0, 0)

            # 创建一个画布，用来绘制按钮
            img = image.Image(800, 480, image.RGB565)
            img.draw_rectangle(0, 0, 800, 480, color=(255, 255, 255), thickness=2, fill=True)


            # 按钮--返回，编辑完成后返回
            img.draw_rectangle(0, 0, 160, 40, color=button_color, thickness=2, fill=True)
            img.draw_string_advanced(0+50, 0, 30, "返回", color=text_color)

            # 按钮--切换，切换编辑的阈值对象
            img.draw_rectangle(800-160, 0, 160, 40, color=button_color, thickness=2, fill=True)
            img.draw_string_advanced(800-160+50, 0, 30, "切换", color=text_color)

            # 按钮--归位，滑块归位
            img.draw_rectangle(0, 480-40, 160, 40, color=button_color, thickness=2, fill=True)
            img.draw_string_advanced(0+50, 480-40, 30, "归位", color=text_color)

            # 按钮--保存，将当前阈值添加到阈值列表中
            img.draw_rectangle(800-160, 480-40, 160, 40, color=button_color, thickness=2, fill=True)
            img.draw_string_advanced(800-160+50, 480-40, 30, "保存", color=text_color)
            # 绘制12个按钮，对应了6个滑块的控制
            for j in [0, 800 - 160]:
                for i in range(60, 420, 60):
                    img.draw_rectangle(j, i, 160, 40, color=button_color, thickness=2, fill=True)

            # 定义一个函数，判断按下的按钮是哪一个，滑块按钮左边依次为0~5，右边依次为6~11
            def witch_key(x, y):
                if x < 160:
                    if y < 40:
                        return "return"
                    if y > 480 - 40:
                        return "reset"
                    if not y > 60:
                        return None
                    if (y - 60) % 60 < 40:
                        return str((y - 60) // 60)
                elif x > 800-160:
                    if y < 40:
                        return "change"
                    if y > 480 - 40:
                        return "save"
                    if not y > 60:
                        return None
                    if (y - 60) % 60 < 40:
                        return str((y - 60) // 60 + 6)
                return None

            # 可以调多个阈值
            threshold_mode_lst = list(threshold_dict.keys())
            threshold_mode = 'rect'
            threshold_current = [0, 255, 0, 255, 0, 255]

            while True:
                img_ = sensor.snapshot(chn=CAM_CHN_ID_0)
                img_ = img_.copy(roi=cut_roi)
#                print(threshold_mode)
                if threshold_mode == 'rect':
                    img_ = img_.to_grayscale()
                    img_ = img_.binary([threshold_current[:2]])
                    img_ = img_.to_rgb565()
                elif threshold_mode == 'red_point':
                    img_ = img_.binary([[i - 128 for i in threshold_current]])
                    img_ = img_.to_rgb565()
                img.draw_image(img_, (800-img_.width()) // 2, (480-img_.height()) // 2)



                points = tp.read()
                if len(points) > 0:
                    # 判断按下了哪个键
                    button_ = witch_key(points[0].x, points[0].y)
                    if button_:
                        # 如果是返回键
                        if button_ == "return":
                            flag = 0
                            time.sleep_ms(2000)
                            break
                        # 如果是切换键
                        elif button_ == "change":
                            threshold_mode = threshold_mode_lst[(threshold_mode_lst.index(threshold_mode) + 1) % len(threshold_mode_lst)]
                            img.draw_rectangle(200, 200, 300, 40, color=button_color, thickness=2, fill=True)
                            img.draw_string_advanced(200, 200, 30, "调整:{}".format(threshold_mode), color=text_color)
                            show_img_2_screen()
                            time.sleep_ms(3000)
                        # 如果是归位键
                        elif button_ == "reset":
                            threshold_current = [0, 255, 0, 255, 0, 255]
                            img.draw_rectangle(200, 200, 300, 40, color=button_color, thickness=2, fill=True)
                            img.draw_string_advanced(200, 200, 30, "滑块归零", color=text_color)
                            show_img_2_screen()
                            time.sleep_ms(3000)
                        # 如果是保存键
                        elif button_ == "save":
                            if threshold_mode == 'red_point':
                                threshold_dict[threshold_mode].append([i - 127 for i in threshold_current])
                            elif threshold_mode == 'rect':
                                threshold_dict[threshold_mode].append(threshold_current[:2])
                            img.draw_rectangle(200, 200, 300, 40, color=button_color, thickness=2, fill=True)
                            img.draw_string_advanced(200, 200, 30, "保存成功", color=text_color)
                            show_img_2_screen()
                            time.sleep_ms(3000)
                        else:
                            print("OK")
                            if int(button_) >= 6:
                                threshold_current[int(button_)-6] = min(255, threshold_current[int(button_)-6]+2)
                            elif int(button_) < 6:
                                threshold_current[int(button_)] = max(0, threshold_current[int(button_)]-2)
#                print(threshold_current)
                show_img_2_screen()

        # 第一第二问标定
        elif flag == 3:
            pin.value(0)
            counter_1_2_set = 0
            while True:
                img = sensor.snapshot(chn=CAM_CHN_ID_0)
                img = img.copy(roi=cut_roi)
                blobs = img.find_blobs(threshold_dict['red_point'], False,\
                                       x_stride=1, y_stride=1, \
                                       pixels_threshold=20, margin=False)
                red_x, red_y = None, None
                for blob in blobs:
                    img.draw_rectangle(blob.x(), blob.y(), blob.w(), blob.h(), color=(0, 255, 0), thickness=2, fill=False)
                    red_x = blob.x() + blob.w() / 2
                    red_y = blob.y() + blob.h() / 2
                show_img_2_screen()
                if s9.value() == 0:
                    if not red_x == None:
                        if counter_1_2_set == 4:
                            center_point = [red_x, red_y]
                        else:
                            rect_points_lst[counter_1_2_set] = [red_x, red_y]

                        img.draw_string_advanced(20, 20, 30, "1_2_set_{}".format(counter_1_2_set), color=(0, 255, 0))
                        show_img_2_screen()
                        counter_1_2_set += 1
                        counter_1_2_set = counter_1_2_set % 5
                        time.sleep(1)
                if s10.value() == 0:
                    flag = 4
                    img.draw_string_advanced(30, 30, 30, "switch_to_{}".format(state_lst[flag]), color=(0, 0, 0))
                    show_img_2_screen()
                    time.sleep(1)
                    start_flag = 0
                    break
        # 第一问，回到原点
        elif flag == 4:
            detect_red_point()
            if s5.value() == 0:
                start_flag = 1
            if start_flag == 1 and (not red_x == None):
                pid_x.target = center_point[0]
                pid_y.target = center_point[1]
                delta_x = pid_x.cal(red_x)
                dir_ = 1 if delta_x > 0 else 0
                send_order(0, dir_, abs(int(delta_x)))

                delta_y = pid_y.cal(red_y)
                dir_ = 1 if delta_y < 0 else 0
                send_order(1, dir_, abs(int(delta_y)))
                if abs(red_x - pid_x.target) < 2 and abs(red_y - pid_y.target) < 2:
                    start_flag = 0
        # 运行第二问
        elif flag == 5:
            if s5.value() == 0:
                start_flag = 1
                if process_rect_flag == 0 and (not rect_points_lst[-1] == []):
                    process_rect_flag = 1
                    processed_points_lst = linear_process(rect_points_lst[0], rect_points_lst[1], 10) + \
                    linear_process(rect_points_lst[1], rect_points_lst[2], 10) + \
                    linear_process(rect_points_lst[2], rect_points_lst[3], 10) + \
                    linear_process(rect_points_lst[3], rect_points_lst[0], 10)
                    processed_points_lst = [processed_points_lst[0]] * 5 + processed_points_lst
            if start_flag == 0:
                pt_2 = 0

            if start_flag == 1:
                pid_x.target = processed_points_lst[pt_2][0]
                pid_y.target = processed_points_lst[pt_2][1]
                for _ in range(5):
                    detect_red_point()
                    delta_x = pid_x.cal(red_x)
                    dir_ = 1 if delta_x > 0 else 0
                    send_order(0, dir_, abs(int(delta_x)))

                    delta_y = pid_y.cal(red_y)
                    dir_ = 1 if delta_y < 0 else 0
                    send_order(1, dir_, abs(int(delta_y)))
                pt_2 += 1
                pt_2 = min(pt_2, len(processed_points_lst)-1)
            detect_red_point()
        # 运行第三四问
        elif flag == 6:
            if s5.value() == 0:
                start_flag = 1
                if process_rect_flag_3_4 == 0 and (not rect_points_lst_3_4[-1] == []):
                    process_rect_flag_3_4 = 1
                    processed_points_lst_3_4 = linear_process(rect_points_lst_3_4[0], rect_points_lst_3_4[1], 8) + \
                    linear_process(rect_points_lst_3_4[1], rect_points_lst_3_4[2], 8) + \
                    linear_process(rect_points_lst_3_4[2], rect_points_lst_3_4[3], 8) + \
                    linear_process(rect_points_lst_3_4[3], rect_points_lst_3_4[0], 8)
                    processed_points_lst_3_4 = [processed_points_lst_3_4[0]] * 5 + processed_points_lst_3_4
            if start_flag == 0:
                pt_3_4 = 0

            if start_flag == 1:
                pid_x.target = processed_points_lst_3_4[pt_3_4][0]
                pid_y.target = processed_points_lst_3_4[pt_3_4][1]
                for _ in range(5):
                    detect_red_point()
                    delta_x = pid_x.cal(red_x)
                    dir_ = 1 if delta_x > 0 else 0
                    send_order(0, dir_, abs(int(delta_x)))

                    delta_y = pid_y.cal(red_y)
                    dir_ = 1 if delta_y < 0 else 0
                    send_order(1, dir_, abs(int(delta_y)))
                pt_3_4 += 1
                pt_3_4 = min(pt_3_4, len(processed_points_lst_3_4)-1)
            detect_red_point()



        else:
            pin.value(1)
            img = sensor.snapshot(chn=CAM_CHN_ID_0)
            img = img.copy(roi=cut_roi)
#            img.draw_string_advanced(50, 50, 80, "fps: {}".format(clock.fps()), color=(255, 0, 0))
            show_img_2_screen()

        # 实现一个长按屏幕进入阈值编辑模式的效果
        points = tp.read()
        if len(points) > 0:
            touch_counter += 1
            if touch_counter > 20:
                flag = 2
            print(points[0].x)
        else:
            touch_counter -= 2
            touch_counter = max(0, touch_counter)

except KeyboardInterrupt as e:
    print("用户停止: ", e)
except BaseException as e:
    print(f"异常: {e}")
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()


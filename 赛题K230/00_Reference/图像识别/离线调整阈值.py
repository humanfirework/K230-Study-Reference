# 视觉相关的题目受到光线干扰非常严重，但是有时候组委会规定不得使用补光灯
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

sensor = None

try:
    # PID对象，用于控制舵机
    class PID:
        def __init__(self, kp, ki, input_value, target=320):
            self.e = 0
            self.e_last = 0
            self.kp = kp
            self.ki = ki
            self.target = target
            self.input_value = input_value
        def cal(self, value):
            self.e = self.target - value
            delta = self.kp * (self.e-self.e_last) + self.ki * self.e
            self.e_last = self.e
            self.input_value = self.input_value + delta
            return self.input_value

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

    fpioa = FPIOA()
    fpioa.help()
    # 设置按键
    fpioa.set_function(53, FPIOA.GPIO53)
    key = Pin(53, Pin.IN, Pin.PULL_DOWN)

    #设置舵机和激光笔
    fpioa.set_function(33, FPIOA.GPIO33)
    fpioa.set_function(46, FPIOA.PWM2)
    fpioa.set_function(42, FPIOA.PWM0)
    pin = Pin(33, Pin.OUT)
    pin.value(0)

    #上下转
    pwm_2 = PWM(2, 50)
    pwm_2.duty(1.5/20*100)
    pwm_2.enable(1)

    #左右转
    pwm_0 = PWM(0, 50)
    pwm_0.duty(1.6/20*100)
    pwm_0.enable(1)

    clock = time.clock()

    # 状态标识，死循环中会根据不同的flag值执行相应的逻辑
    # flag = 1则识别激光点
    # flag = 2则可以调整阈值
    flag = 0

    # 初始化中心点和PID对象
    c_x = 320
    c_y = 320 # 这两个值是随便写的，因为后面的代码会改
    pid_x = PID(-0.002, -0.0003, 1.5/20*100, c_x)
    pid_y = PID(-0.002, -0.0003, 1.5/20*100, c_y)

    # 裁剪图像的ROI，格式为(x, y, w, h)，推荐使用480*480的大小，此大小性能高，而且刚好可以铺满LCD屏幕
    cut_roi = (540, 300, 480, 480)

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
    threshold_dict = {'rect': [(59, 246)], 'red_point':\
    [(47, 80, 9, 91, -55, 63), (16, 37, 23, 74, -48, 52)]}
    # 清空阈值（可以注释掉，这里只是为了演示阈值编辑功能）
    threshold_dict['rect'] = []
    threshold_dict['red_point'] = []

    while True:
        clock.tick()
        os.exitpoint()

#        # 绘制方框，参数依次为：x, y, w, h, 颜色，线宽，是否填充
#        img.draw_rectangle(1000, 50, 300, 200, color=(0, 0, 255), thickness=4, fill=False)

        # 如果按下了按键，就识别矩形，然后记录中心点坐标
        if key.value() == 1:
            time.sleep_ms(2000)
            for i in range(5):
                img = sensor.snapshot(chn=CAM_CHN_ID_0)
                img = img.copy(roi=cut_roi)
                img_rect = img.to_grayscale(copy=True)
                img_rect = img_rect.binary(threshold_dict['rect'])
                rects = img_rect.find_rects(threshold=10000)

                if not rects == None:
                    for rect in rects:
                        corner = rect.corners()
                        img.draw_line(corner[0][0], corner[0][1], corner[1][0], corner[1][1], color=(0, 255, 0), thickness=5)
                        img.draw_line(corner[2][0], corner[2][1], corner[1][0], corner[1][1], color=(0, 255, 0), thickness=5)
                        img.draw_line(corner[2][0], corner[2][1], corner[3][0], corner[3][1], color=(0, 255, 0), thickness=5)
                        img.draw_line(corner[0][0], corner[0][1], corner[3][0], corner[3][1], color=(0, 255, 0), thickness=5)
                        c_x = sum([corner[k][0] for k in range(4)])/4
                        c_y = sum([corner[k][1] for k in range(4)])/4

                # 检测到两个框就说明检测大概率正确，切换flag=1
                if len(rects) == 2:
                    show_img_2_screen()
                    print("center_point: {}".format([round(c_x), round(c_y)]))
                    flag = 1
                    time.sleep_ms(500)
                    # 设置PID的目标值
                    pid_x.target = c_x
                    pid_y.target = c_y
                    break
            if flag == 0:
                print("识别错误")

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
                c_x = blob.x() + blob.w() / 2
                c_y = blob.y() + blob.h() / 2
                new_duty = pid_x.cal(c_x)
                if new_duty > 2.5/20*100:
                    new_duty = 2.5/20*100
                if new_duty < 0.5/20*100:
                    new_duty = 0.5/20*100
                pwm_0.enable(0)
                pwm_0.duty(round(new_duty, 2))

                pwm_0.enable(1)
                new_duty = pid_y.cal(c_y)
                if new_duty > 2.5/20*100:
                    new_duty = 2.5/20*100
                if new_duty < 0.5/20*100:
                    new_duty = 0.5/20*100
                pwm_2.enable(0)
                pwm_2.duty(round(new_duty, 2))
                pwm_2.enable(1)
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
                print(threshold_mode)
                if threshold_mode == 'rect':
                    img_ = img_.to_grayscale()
                    img_ = img_.binary([threshold_current[:2]])
                    img_ = img_.to_rgb565()
                elif threshold_mode == 'red_point':
                    img_ = img_.binary([[i - 127 for i in threshold_current]])
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
                print(threshold_current)
                show_img_2_screen()


        else:
            img = sensor.snapshot(chn=CAM_CHN_ID_0)
            img = img.copy(roi=cut_roi)
            img.draw_string_advanced(50, 50, 80, "fps: {}".format(clock.fps()), color=(255, 0, 0))
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

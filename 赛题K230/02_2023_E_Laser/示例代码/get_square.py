import time
from media.sensor import *
from media.display import *
from media.media import *
from ybUtils.YbKey import YbKey
from ybUtils.YbUart import YbUart

key = YbKey()
uart = YbUart(baudrate=115200)

WIDTH = 640
HEIGHT = 480
sensor = Sensor(width = WIDTH, height = HEIGHT, fps=30)
sensor.reset()
time.sleep_ms(100)
sensor.set_framesize(width = WIDTH, height = HEIGHT)
sensor.set_pixformat(sensor.RGB565)

red_light = (67, 100, -3, 40, -6, 11)


flag_find_first_rect = False
flag_find_second_rect = False
first_rect_corners = [[0,0] for _ in range(4)]
second_rect_corners =[[0,0] for _ in range(4)]
show_first_rect = False
show_second_rect = False
show_target_rect = True

Display.init(Display.ST7701, width = WIDTH, height = HEIGHT, to_ide = True)
MediaManager.init()

sensor.run()
clock = time.clock()

found_rect = 0
send_state = 0


def send_target_data(target):
    n = 0
    for i in range(4):
        cx_h,cx_l,cx_z,cy_h,cy_l,cy_z = conversion_postion(target[i][0],target[i][1])

        uart.write(bytearray([0x55, 0xaa, 0x10+n, int(cx_h), int(cx_l),int(cx_z),0xfa]))
#        uart.write(bytearray([0x55]))
#        time.sleep_ms(1)
#        uart.write(bytearray([0xaa]))
#        time.sleep_ms(1)
#        uart.write(bytearray([0x10+n]))
#        time.sleep_ms(1)
#        uart.write(bytearray([int(x_h)]))
#        time.sleep_ms(1)
#        uart.write(bytearray([int(x_l)]))
#        time.sleep_ms(1)
#        uart.write(bytearray([0xfa]))
        time.sleep_ms(3)
        n+=1

        uart.write(bytearray([0x55, 0xaa, 0x10+n, int(cy_h), int(cy_l),int(cy_z),0xfa]))

#        uart.write(bytearray([0x55]))
#        time.sleep_ms(1)
#        uart.write(bytearray([0xaa]))
#        time.sleep_ms(1)
#        uart.write(bytearray([0x10+n]))
#        time.sleep_ms(1)
#        uart.write(bytearray([int(y_h)]))
#        time.sleep_ms(1)
#        uart.write(bytearray([int(y_l)]))
#        time.sleep_ms(1)
#        uart.write(bytearray([0xfa]))


        time.sleep_ms(3)
        n+=1

def color_blob(img,hano,color):#寻找指定颜色最大色块
    blobs = img.find_blobs([hano],roi=light_roi,merge = True)
    if blobs:
        #print(blobs)
        #print('light')
        global last_cx
        global last_cy
        for blob in blobs:
            roi = (blob.x()-5,blob.y()-5,blob.w()+10,blob.h()+10)#得到亮斑外接圆范围
            #img.draw_rectangle(blob[0:4],color=(0,0,255)) # 画矩形
            #if img.find_blobs([color],roi=roi,merge = True):#找到了指定颜色
            if img.find_blobs([color],roi=roi,x_stride=1, y_stride=1,
                             area_threshold=0, pixels_threshold=0,merge=False,margin=1):#找到了指定颜色
               #print('red')
               cx = blob[5]
               cy = blob[6]
               img.draw_rectangle(blob[0:4],color=(0,0,255)) # 画矩形
               img.draw_cross(blob[5], blob[6],color=(0,0,255)) # 画十字
               last_cx = cx#更新坐标
               last_cy = cy#更新坐标
               #print(cx,cy)
               return cx, cy, 1
        return last_cx, last_cy, 0
    return last_cx, last_cy, 0
    
def conversion_postion(x,y):
    if x > 510:
       x_h = 255
       x_l = 255
       x_z = x-255-255
    elif 510>=x>=255:
       x_h = 255
       x_l = x-255
       x_z = 0
    else:
       x_h = x
       x_l = 0
       x_z = 0
    if y > 510:
       y_h = 255
       y_l = 255
       y_z = y-255-255
    elif 510>=y>=255:
       y_h = 255
       y_l = y-255
       y_z = 0
    else:
       y_h = y
       y_l = 0
       y_z = 0
    return x_h,x_l,x_z,y_h,y_l,y_z




while True:
    clock.tick()
    os.exitpoint()
    img = sensor.snapshot()
    img = img.gaussian(1)

    if key.value() == 0:
        flag_find_first_rect = False
        flag_find_second_rect = False
        found_rect = 0
    # 找内框
    if flag_find_first_rect == False:
        # threshold 参数用于设置检测阈值(threshold大小和要检测矩形的像素大小有关，将阈值设定在要检测矩形的面积范围内可以减少外界其他噪声)
        # x_gradient 和 y_gradient 参数用于设置边缘梯度阈值（x_gradient 和 y_gradient越大识别越准确但耗费时间越长，x_gradient 和 y_gradient越小越快但干扰性大）
        # 两者都和环境亮度有关
        # 找矩形调整threshold，x_gradient, y_gradient这三个值
        for rect in img.find_rects(threshold = 80000, x_gradient=10, y_gradient=10):
            if rect:
                flag_find_first_rect = True
                # 获取矩形的四个角的坐标
                first_rect_corners = rect.corners()
                area = rect.magnitude() #矩形像素面积大小
                print(area)
    # 找外框，可以根据IDE粗略的估计矩形像素大小设置合适的阈值
    if flag_find_first_rect == True:
        if flag_find_second_rect == False:
            for rect in img.find_rects(threshold = 60000, x_gradient=10, y_gradient=10):
                if rect:
                    area = rect.magnitude()
                    if area < 90000:
                        flag_find_second_rect = True
                        # 获取矩形的四个角的坐标
                        second_rect_corners = rect.corners()
                    print(area)

    if flag_find_first_rect == True and flag_find_second_rect == True:
        if found_rect == 0:
            found_rect = 1
            print("first:", first_rect_corners)
            print("second:", second_rect_corners)
        if show_first_rect:
            # 绘制内框矩形的四条边
            img.draw_line(first_rect_corners[0][0], first_rect_corners[0][1], first_rect_corners[1][0], first_rect_corners[1][1], color=(255, 255, 255))
            img.draw_line(first_rect_corners[1][0], first_rect_corners[1][1], first_rect_corners[2][0], first_rect_corners[2][1], color=(255, 255, 255))
            img.draw_line(first_rect_corners[2][0], first_rect_corners[2][1], first_rect_corners[3][0], first_rect_corners[3][1], color=(255, 255, 255))
            img.draw_line(first_rect_corners[3][0], first_rect_corners[3][1], first_rect_corners[0][0], first_rect_corners[0][1], color=(255, 255, 255))
            # 圈出内框顶点
            for p in first_rect_corners:
                img.draw_circle(p[0], p[1], 3, color = (0, 255, 0))
        if show_second_rect:
            # 绘制外框矩形的四条边
            img.draw_line(second_rect_corners[0][0], second_rect_corners[0][1], second_rect_corners[1][0], second_rect_corners[1][1], color=(255, 255, 255))
            img.draw_line(second_rect_corners[1][0], second_rect_corners[1][1], second_rect_corners[2][0], second_rect_corners[2][1], color=(255, 255, 255))
            img.draw_line(second_rect_corners[2][0], second_rect_corners[2][1], second_rect_corners[3][0], second_rect_corners[3][1], color=(255, 255, 255))
            img.draw_line(second_rect_corners[3][0], second_rect_corners[3][1], second_rect_corners[0][0], second_rect_corners[0][1], color=(255, 255, 255))
            # 圈出外框顶点
            for p in second_rect_corners:
                img.draw_circle(p[0], p[1], 3, color = (255, 0, 0))

        # 当检测到第一个矩形(found_rect=1)时
        if found_rect == 1:
            # 将第二个矩形的四个角点转换为列表并复制给目标矩形
            target_rect_corners = [list(second_rect_corners[0]), list(second_rect_corners[1]), list(second_rect_corners[2]), list(second_rect_corners[3])]
            found_rect = 2  # 更新状态为已找到第二个矩形
            
            # 调整目标矩形的四个角点位置，使其位于内外矩形之间
            # 左上角点调整：x坐标减去内外矩形x差的一半，y坐标加上内外矩形y差的一半
            target_rect_corners[0][0] -= int(abs(second_rect_corners[0][0] - first_rect_corners[0][0])/2)
            target_rect_corners[0][1] += int(abs(second_rect_corners[0][1] - first_rect_corners[0][1])/2)
            # 右上角点调整：x坐标加上内外矩形x差的一半，y坐标加上内外矩形y差的一半
            target_rect_corners[1][0] += int(abs(second_rect_corners[1][0] - first_rect_corners[1][0])/2)
            target_rect_corners[1][1] += int(abs(second_rect_corners[1][1] - first_rect_corners[1][1])/2)
            # 右下角点调整：x坐标加上内外矩形x差的一半，y坐标减去内外矩形y差的一半
            target_rect_corners[2][0] += int(abs(second_rect_corners[2][0] - first_rect_corners[2][0])/2)
            target_rect_corners[2][1] -= int(abs(second_rect_corners[2][1] - first_rect_corners[2][1])/2)
            # 左下角点调整：x坐标减去内外矩形x差的一半，y坐标减去内外矩形y差的一半
            target_rect_corners[3][0] -= int(abs(second_rect_corners[3][0] - first_rect_corners[3][0])/2)
            target_rect_corners[3][1] -= int(abs(second_rect_corners[3][1] - first_rect_corners[3][1])/2)
            print("target:", target_rect_corners)

        # 如果显示目标矩形标志为真且已找到第二个矩形，则绘制目标矩形
        if show_target_rect and found_rect == 2:
            # 绘制目标矩形的四条边(白色)
            img.draw_line(target_rect_corners[0][0], target_rect_corners[0][1], target_rect_corners[1][0], target_rect_corners[1][1], color=(255, 255, 255))
            img.draw_line(target_rect_corners[1][0], target_rect_corners[1][1], target_rect_corners[2][0], target_rect_corners[2][1], color=(255, 255, 255))
            img.draw_line(target_rect_corners[2][0], target_rect_corners[2][1], target_rect_corners[3][0], target_rect_corners[3][1], color=(255, 255, 255))
            img.draw_line(target_rect_corners[3][0], target_rect_corners[3][1], target_rect_corners[0][0], target_rect_corners[0][1], color=(255, 255, 255))
            
            # 在目标矩形的四个角点绘制蓝色小圆点(半径3像素)
            for p in target_rect_corners:
                img.draw_circle(p[0], p[1], 3, color = (0, 0, 255))
            
            # 控制数据发送频率，每10帧发送一次目标矩形数据
            send_state += 1
            if send_state > 10:
                send_state = 0
                send_target_data(target_rect_corners)

    Display.show_image(img)
    time.sleep_ms(10)

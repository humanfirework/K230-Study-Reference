#By B站@程欢欢的智能控制集 20250730
#例程序使用OpenMV4运行，OpenMV4Plus亦可

import sensor, image, time
from pyb import millis

sensor.reset()
sensor.set_hmirror(False)
sensor.set_vflip(False)
sensor.set_transpose(False)
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.VGA)

#sensor.set_contrast(0) #对比度
sensor.set_windowing([200,120,240,240])
#sensor.skip_frames(time = 2000)
#exposure = sensor.get_exposure_us()
#sensor.set_auto_exposure(False,exposure_us=500)  #

clock = time.clock()

#黑框和白底的颜色阈值，可以宽泛一些。如果效果不好，则打开我注释掉的
thr_write = (60, 100, -20, 20, -20, 20)
thr_black = (0, 35, -20, 20, -20, 20)

count = 0 #测试切换像素的临时变量
state = 1  #测试切换像素的临时变量

target_offset = [-1,-1] #目标补偿量，根据视角倾斜角度而设，暂时手动填写
target = [0,0] #目标坐标，自动计算
view_offset = [0,0] #视角偏移补偿量，自动计算
deviation = [0,0] #偏差量，最终输出结果
while(True):
    timer = millis()
    clock.tick()
    '''
    count += 1
    if count > 40:
        count = 0
        if state == 1:
            state = 0
            #sensor.reset()
            #sensor.set_pixformat(sensor.RGB565)
            sensor.set_framesize(sensor.QVGA)
        else:
            state = 1
            #sensor.reset()
            #sensor.set_pixformat(sensor.RGB565)
            sensor.set_framesize(sensor.VGA)
            sensor.set_windowing(320,240)
    '''

    img = sensor.snapshot()

    black_blobs = img.find_blobs([thr_black],merge =False) #找黑框

    if black_blobs:  #如果有目标
        for single_black_blob in black_blobs:
            #img.draw_rectangle(single_black_blob.rect(),color=(255,0,255)) #绘制初步找黑框结果
            #找到的目标中，符合阈值的面积和总的区域之间的比值。因为黑框内部不是黑色，所以这个比值不会很大。
            if single_black_blob.pixels() / (single_black_blob.w()*single_black_blob.h()) < 0.3:
                #img.draw_rectangle(single_black_blob.rect(),color=(0,255,255))#绘制符合条件的区域
                #在区域内找白色
                write_blobs = img.find_blobs([thr_write],area_threshold=2,roi =single_black_blob.rect(), merge =False)
                if write_blobs:#如果有目标
                    largest_white = max(write_blobs, key=lambda b: b.area())#找到最大的块
                    #img.draw_rectangle(largest_white.rect(),color=(255,0,0)) #绘制识别结果
                    #p = single_black_blob.pixels() / (single_black_blob.w()*single_black_blob.h())
                    #img.draw_string(largest_white.x(),largest_white.y(),str(p),color=(255,0,0))#在屏幕上显示测试数据
                    #绘制黑框的中心点
                    #img.draw_cross(single_black_blob.cx()+target_offset[0],single_black_blob.cy()+target_offset[1],color=(0,255,255))
                    #判断条件1：黑色区域面积和白色区域面积的比例；判断条件2：黑框和白色区域中心坐标的差值
                    if (2 < largest_white.pixels() / single_black_blob.pixels() < 4) and\
                        abs( largest_white.cx() - single_black_blob.cx() ) < 10 and \
                        abs( largest_white.cy() - single_black_blob.cy() ) < 10 :

                        target = [largest_white.cx()+target_offset[0], largest_white.cy()+target_offset[1] ] #白色区域中心坐标
                        img.draw_cross(target,color=(255,0,0),thickness=3) #绘制在画布上
    #print('目标',target)
    view_offset[0] += round((target[0]-120)*0.5) #偏差量累加到视野补偿中。120是画面中心坐标
    view_offset[1] += round((target[1]-120)*0.5)

    view_offset[0] = min(200, max(0, view_offset[0] )) #限制视野补偿的最大、最小值
    view_offset[1] = min(120, max(0, view_offset[1] ))

    #包含视野补偿的偏差量。这是最终用于云台运动的量！但注意，画布的Y轴与直角坐标系的Y周相反！
    err = [target[0]+view_offset[0]-200, target[1]+view_offset[1]-120]
    #print('执行量',err)
    img.draw_line(0,120, 240,120)
    img.draw_line(120,0,120,240)
    img.draw_circle(err[0]+120,err[1]+120,5,fill=True,color=(255,0,0)) #将总的偏差量绘制在画布上

    #因为画面有数码变焦的裁切，所以此功能通过改变裁切位置，让靶始终处于画面中心。如果不需要可以注释掉整个这部分。
    sensor.set_windowing([200+view_offset[0], 120+view_offset[1], 240,240])
    #print(200+view_offset[0], 120+view_offset[1])
    timer = millis() - timer
    print('用时',timer,'实时帧速',1000/timer,'平均帧速',clock.fps())

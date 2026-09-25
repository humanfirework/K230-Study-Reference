#By B站@程欢欢的智能控制集 20250730
#例程序使用OpenMV4运行，OpenMV4Plus亦可
# 2025年全国大学生电子设计竞赛E题 - 简易自行瞄准装置
# OpenMV图像识别部分代码

import sensor, image, time  # 导入OpenMV核心库
from pyb import millis  # 导入pyb库用于时间测量

# 摄像头初始化设置
sensor.reset()  # 重置摄像头
sensor.set_hmirror(False)  # 水平镜像关闭
sensor.set_vflip(False)    # 垂直翻转关闭
sensor.set_transpose(False)  # 图像转置关闭
sensor.set_pixformat(sensor.RGB565)  # 设置图像格式为RGB565（彩色）
sensor.set_framesize(sensor.VGA)  # 设置分辨率为VGA(640x480)

#sensor.set_contrast(0) #对比度
sensor.set_windowing([200,120,240,240])  # 设置窗口裁剪：从(200,120)开始，裁剪240x240的区域
#sensor.skip_frames(time = 2000)  # 跳过前2000ms的帧，等待摄像头稳定
#exposure = sensor.get_exposure_us()  # 获取当前曝光时间
#sensor.set_auto_exposure(False,exposure_us=500)  # 关闭自动曝光，手动设置曝光时间500us

clock = time.clock()  # 创建时钟对象，用于计算帧率

# 颜色阈值设置（LAB颜色空间）
# thr_write: 白色区域的阈值 (L_min, L_max, A_min, A_max, B_min, B_max)
# 白色：亮度高(60-100)，A/B通道接近0(-20到20)
# thr_black: 黑色区域的阈值
# 黑色：亮度低(0-35)，A/B通道接近0(-20到20)

# 颜色阈值定义：白色和黑色的LAB范围
thr_write = (60, 100, -20, 20, -20, 20)  # 白色阈值
thr_black = (0, 35, -20, 20, -20, 20)   # 黑色阈值

# 测试变量（可忽略）
count = 0 #测试切换像素的临时变量
state = 1  #测试切换像素的临时变量

# 系统变量初始化
target_offset = [-1,-1] #目标补偿量，根据视角倾斜角度而设，暂时手动填写
target = [0,0] #目标坐标，自动计算 [x,y]
view_offset = [0,0] #视角偏移补偿量，自动计算 [x,y]
deviation = [0,0] #偏差量，最终输出结果 [x,y]
# 主循环
while(True):
    timer = millis()  # 记录当前时间
    clock.tick()  # 更新帧率时钟
    
    # 以下代码是测试用的分辨率切换功能，已注释掉
    '''
    count += 1
    if count > 40:
        count = 0
        if state == 1:
            state = 0
            #sensor.reset()
            #sensor.set_pixformat(sensor.RGB565)
            sensor.set_framesize(sensor.QVGA)  # 切换到QVGA分辨率
        else:
            state = 1
            #sensor.reset()
            #sensor.set_pixformat(sensor.RGB565)
            sensor.set_framesize(sensor.VGA)   # 切换回VGA分辨率
            sensor.set_windowing(320,240)
    '''

    img = sensor.snapshot()  # 获取一帧图像

    # 步骤1：在整幅图像中查找黑色区域（可能的目标框）
    black_blobs = img.find_blobs([thr_black],merge =False) #找黑框

    if black_blobs:  #如果找到黑色区域
        for single_black_blob in black_blobs:
            #img.draw_rectangle(single_black_blob.rect(),color=(255,0,255)) #绘制初步找黑框结果
            
            # 过滤条件：黑色区域的填充率不能太高（<30%），避免实心物体
            # 因为真正的目标框内部是白色，所以黑色边框的填充率应该较低
            if single_black_blob.pixels() / (single_black_blob.w()*single_black_blob.h()) < 0.3:
                #img.draw_rectangle(single_black_blob.rect(),color=(0,255,255))#绘制符合条件的区域
                
                # 步骤2：在黑色区域内查找白色区域（目标内部）
                write_blobs = img.find_blobs([thr_write],area_threshold=2,roi =single_black_blob.rect(), merge =False)
                if write_blobs:  # 如果找到白色区域
                    largest_white = max(write_blobs, key=lambda b: b.area())  # 选择最大的白色区域
                    
                    #p = single_black_blob.pixels() / (single_black_blob.w()*single_black_blob.h())
                    #img.draw_string(largest_white.x(),largest_white.y(),str(p),color=(255,0,0))#在屏幕上显示测试数据
                    
                    # 步骤3：验证目标有效性
                    # 条件1：白色区域面积与黑色框面积的比例在2-4之间（合理的目标比例）
                    # 条件2：白色区域中心与黑色框中心的距离小于10像素（中心对齐）
                    if (2 < largest_white.pixels() / single_black_blob.pixels() < 4) and\
                        abs( largest_white.cx() - single_black_blob.cx() ) < 10 and \
                        abs( largest_white.cy() - single_black_blob.cy() ) < 10 :

                        # 步骤4：计算目标坐标
                        target = [largest_white.cx()+target_offset[0], largest_white.cy()+target_offset[1] ] #白色区域中心坐标
                        img.draw_cross(target,color=(255,0,0),thickness=3) #绘制在画布上（红色十字标记目标）
    #print('目标',target)  # 调试输出：打印目标坐标
    
    # 步骤5：计算视角补偿
    # 将目标位置与画面中心的偏差量累加到视角补偿中
    # 120是画面中心坐标（240x240窗口的中心）
    view_offset[0] += round((target[0]-120)*0.5)  # X轴补偿
    view_offset[1] += round((target[1]-120)*0.5)  # Y轴补偿

    # 限制视角补偿的范围，防止超出图像边界
    view_offset[0] = min(200, max(0, view_offset[0] ))  # X轴范围：0-200
    view_offset[1] = min(120, max(0, view_offset[1] ))  # Y轴范围：0-120

    # 步骤6：计算最终偏差量
    # 包含视角补偿的偏差量，这是最终用于云台运动的控制量
    # 注意：画布的Y轴与直角坐标系的Y轴相反！
    err = [target[0]+view_offset[0]-200, target[1]+view_offset[1]-120]
    #print('执行量',err)  # 调试输出：打印最终控制量
    
    # 绘制参考线：十字准星
    img.draw_line(0,120, 240,120)  # 水平线
    img.draw_line(120,0,120,240)   # 垂直线
    img.draw_circle(err[0]+120,err[1]+120,5,fill=True,color=(255,0,0)) #绘制最终偏差点（红色圆点）

    # 步骤7：数码变焦功能
    # 通过改变窗口裁剪位置，让目标始终处于画面中心
    # 如果不需要此功能，可以注释掉整个这部分
    
    sensor.set_windowing([200+view_offset[0], 120+view_offset[1], 240,240])
    #print(200+view_offset[0], 120+view_offset[1])  # 调试输出：打印新的窗口位置
    
    # 性能统计
    timer = millis() - timer  # 计算处理时间
    print('用时',timer,'实时帧速',1000/timer,'平均帧速',clock.fps())  # 打印性能数据

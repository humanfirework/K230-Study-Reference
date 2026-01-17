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

#red_light = (67, 100, -3, 40, -6, 11)
light = (85, 100, 25, -16, -16, 51)
red_light = (0, 100, 22, 80, -27, 94)
light_roi =(100,40,600,420)#根据自己的硬件结构修改！！！



Display.init(Display.ST7701, width = WIDTH, height = HEIGHT, to_ide = True)
MediaManager.init()

sensor.run()
clock = time.clock()

last_cx = 300 #初始点x坐标
last_cy = 220 #初始点y坐标

#last_cx = 0
#last_cy = 400




# 寻找最大色块面积的函数
# 参数blobs: 检测到的所有色块列表
def find_max_blob(blobs):
    # 对色块列表按照周长进行降序排序
    # 使用lambda函数获取每个色块的周长作为排序依据
    blobs.sort(key=lambda x:x.perimeter(),reverse=True);
    
    # 初始化一个空字典用于存储最大色块信息
    max_value={}
    
    # 获取排序后的第一个色块(周长最大的色块)
    max_value=blobs[0];
    
    # 返回最大色块
    return max_value;


# 发送目标位置数据的函数
# 参数x,y: 目标位置的x和y坐标值
def send_target_data(x,y):
    n = 0  # 计数器，用于记录发送次数
    
    # 循环4次发送数据，提高传输可靠性
    for i in range(4):
        # 将x坐标分解为高8位和低8位
        x_h = (x>>8)&0xFF  # 取x的高8位
        x_l = x&0xFF       # 取x的低8位
        
        # 将y坐标分解为高8位和低8位
        y_h = (y>>8)&0xFF  # 取y的高8位
        y_l = y&0xFF       # 取y的低8位
        
        # 发送x坐标数据包
        # 数据包格式: [0x55, 0xaa, 0xff, x_h, x_l, 0xfa]
        # 0x55 0xaa: 数据包头
        # 0xff: 表示这是x坐标数据
        # x_h, x_l: x坐标的高低位
        # 0xfa: 数据包尾
        uart.write(bytearray([0x55, 0xaa, 0xff, int(x_h)&0xFF, int(x_l)&0xFF, 0xfa]))
        
        time.sleep_ms(3)  # 短暂延时，防止数据冲突
        n += 1  # 计数器递增
        
        # 发送y坐标数据包
        # 数据包格式: [0x55, 0xaa, 0x00, y_h, y_l, 0xfa]
        # 0x00: 表示这是y坐标数据
        uart.write(bytearray([0x55, 0xaa, 0x00, int(y_h)&0xFF, int(y_l)&0xFF, 0xfa]))
        
        time.sleep_ms(3)  # 短暂延时
        n += 1  # 计数器递增

"""
将x和y坐标值分解为多个字节，用于串口通信协议
参数:
    x: 横坐标值
    y: 纵坐标值
返回值:
    返回6个分量(x_h, x_l, x_z, y_h, y_l, y_z)，每个分量都是0-255之间的值
"""
def conversion_postion(x,y):
    
    # 处理x坐标
    if x > 510:  # 如果x大于510
       x_h = 255  # 高8位设为255
       x_l = 255  # 中8位设为255
       x_z = x-255-255  # 剩余部分存入x_z
    elif 510>=x>=255:  # 如果x在255到510之间
       x_h = 255  # 高8位设为255
       x_l = x-255  # 中8位为x减去255
       x_z = 0  # 剩余部分为0
    else:  # 如果x小于255
       x_h = x  # 高8位直接设为x值
       x_l = 0  # 中8位为0
       x_z = 0  # 剩余部分为0

    # 处理y坐标（逻辑与x相同）
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


def color_blob(img,hano,color):#寻找指定颜色最大色块
    blobs = img.find_blobs([hano],roi=light_roi,merge = True)
    if blobs:
        #print(blobs)
        #print('light')
        global last_cx
        global last_cy
        for blob in blobs:
            # 这样做的目的是确保在后续处理中能完整包含色块及其周围区域
            # 避免因边缘检测或位置计算导致的误差
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
                # 情况1: 成功检测到目标
                return cx, cy, 1  # 返回当前坐标和状态1
        # 情况2: 未检测到目标        
        return last_cx, last_cy, 0  # 返回上一次坐标和状态0
    # 情况3: 其他错误情况
    return last_cx, last_cy, 0  # 返回上一次坐标和状态0


while True:
    clock.tick()
    os.exitpoint()
    img = sensor.snapshot()
    img = img.gaussian(1)
    img = sensor.snapshot().lens_corr(strength = 1.7 , zoom = 1.0)
    cx,cy,ok= color_blob(img,light,red_light)
    cx_h,cx_l,cx_z,cy_h,cy_l,cy_z = conversion_postion(cx,cy)

    img.draw_rectangle(light_roi,color=(0,0,255)) # rect
    uart.write(bytearray([0x55,0xaa,0x00,int(cx_h),int(cx_l),int(cx_z),0xfa]))
    uart.write(bytearray([0x55,0xaa,0xff,int(cy_h),int(cy_l),int(cy_z),0xfa]))

    Display.show_image(img)



"""
 * 串口数据解码函数
 * 功能：从环形缓冲区中解码K230传输的数据帧
 * 协议格式：0x55 0xAA [数据1] [数据2] [数据3] [数据4] 0xFA
 * 
 * @param ringbuff 环形缓冲区指针
 * @param data1-4 用于存储解码后的4个数据
 * @return 解码成功返回0，失败返回1

 
 * 参数说明：
 * @param ringbuff - 指向环形缓冲区的指针，用于存储接收到的串口原始数据
 * @param data1    - 输出参数，用于存储解码后的第一个数据
 * @param data2    - 输出参数，用于存储解码后的第二个数据
 * @param data3    - 输出参数，用于存储解码后的第三个数据
 * @param data4    - 输出参数，用于存储解码后的第四个数据

uint8_t DataDecode1(RingBuff_t *ringbuff, uint8_t *data1, uint8_t *data2, uint8_t *data3, uint8_t *data4) {
    static uint8_t uart_dec_count;  // 数据帧解码状态计数器
    static uint8_t uart_rec_data[6]; // 存储接收到的6字节数据
    uint8_t ret = 1;  // 默认返回失败状态

    // 从环形缓冲区读取1字节数据
    if(Read_RingBuff(ringbuff, &uart_rec_data[uart_dec_count]) == RINGBUFF_ERR) {
        return 1;
    }

    // 帧头验证(0x55)
    if((uart_dec_count == 0) && (uart_rec_data[uart_dec_count] != 0x55)) {
        uart_rec_data[uart_dec_count] = 0;  // 无效数据清零
    }
    // 帧头第二字节验证(0xAA)
    else if((uart_dec_count == 1) && (uart_rec_data[uart_dec_count] != 0xaa)) {
        uart_rec_data[uart_dec_count] = 0;
        uart_rec_data[uart_dec_count-1] = 0;
        uart_dec_count = 0;  // 重置状态计数器
    }
    // 帧尾验证(0xFA)
    else if((uart_dec_count == 6) && (uart_rec_data[uart_dec_count] != 0xfa)) {
        // 无效帧，清空前6字节数据
        for(int i=0; i<6; i++) {
            uart_rec_data[i] = 0;
        }
        uart_dec_count = 0;
    }
    else {
        // 成功接收完整数据帧
        if(uart_dec_count == 6) {
            // 提取有效数据(跳过帧头2字节和帧尾1字节)
            *data1 = uart_rec_data[2];
            *data2 = uart_rec_data[3];
            *data3 = uart_rec_data[4];
            *data4 = uart_rec_data[5];
            ret = 0;  // 返回成功状态
        }
        uart_dec_count++;
        if(uart_dec_count == 7) {
            uart_dec_count = 0;  // 重置计数器
        }
    }
    return ret;
}

"""
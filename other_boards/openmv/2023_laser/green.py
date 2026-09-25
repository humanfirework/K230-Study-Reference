import time, sensor, lcd
from pyb import UART
THRESHOLD_R = [(0, 255, 15, 255, -8, 61)]
THRESHOLD_R = [(0, 255, 15, 255, -8, 61)]
CENTER_X = 160
CENTER_Y = 167
def sending_data(dx, dy):
	global uart
	flx = 0
	fly = 0
	if dx < 0:
		dx = -dx
		flx = 1
	if dy < 0:
		dy = -dy
		fly = 1
	FH = bytearray([0xA1, 0x02, flx, dx, fly, dy, 0x1A])
	uart.write(FH)
uart = UART(3,115200)
uart.init(115200, bits=8, parity=None, stop=1)
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_contrast(3)
sensor.set_auto_exposure(False, 1200)
sensor.set_auto_whitebal(False)
sensor.set_auto_gain(False)
sensor.set_hmirror(False)
sensor.set_vflip(True)
err_dx = 0
err_dy = 0
once = 1
blob = []
task = 1
while True:
	# 这段代码实现了基于颜色识别的目标追踪功能，主要分为红色目标追踪和绿色目标追踪两种模式

	# 图像采集与预处理
	img = sensor.snapshot()  # 从摄像头获取一帧图像
	img.lens_corr(1.4)       # 应用镜头畸变校正(1.4为校正系数)
	img.draw_cross(CENTER_X, CENTER_Y)  # 在图像中心绘制十字标记

	# 串口指令处理
	if uart.any():           # 检查串口是否有数据
		task = uart.read(1)  # 从串口读取1字节指令数据
		if task == b'1':      # 如果收到'1'指令(红色目标追踪)
			once = 1          # 设置初次运行标志

	# 红色目标追踪模式
	if task == b'1':
		# 根据是否初次运行，选择不同的搜索区域
		if once == 1:  # 初次运行:全图搜索
			blobs = img.find_blobs(THRESHOLD_R, pixels_threshold=2, area_threshold=15)
		else:          # 非初次运行:仅在中心区域(ROI)搜索
			blobs = img.find_blobs(THRESHOLD_R, roi=(CENTER_X-35, CENTER_Y-35, 70, 70), 
								pixels_threshold=2, area_threshold=3)
		
		# 寻找距离中心最近的红色斑点
		blob = []
		dst = 150  # 初始距离阈值
		for b in blobs:
			# 计算斑点中心坐标
			x = b[0] + int(b[2]/2)
			y = b[1] + int(b[3]/2)
			# 计算与图像中心的曼哈顿距离
			dx = abs(x - CENTER_X)
			dy = abs(y - CENTER_Y)
			if dx + dy < dst:  # 更新最近斑点
				blob = b
				dst = dx + dy
		
		if blob:  # 如果找到有效斑点
			# 计算斑点中心坐标
			cx = blob[0] + int(blob[2]/2)
			cy = blob[1] + int(blob[3]/2)
			
			if once == 1:  # 初次运行处理
				# 计算并发送位置误差
				err_dx = cx - CENTER_X
				err_dy = cy - CENTER_Y
				sending_data(-err_dx, -err_dy)
				img.draw_line(CENTER_X, CENTER_Y, cx, cy)  # 绘制追踪线
				
				# 如果误差足够小，进入精确追踪模式
				if abs(err_dx) <= 5 and abs(err_dy) <= 5:
					past = blob  # 保存当前斑点信息
					once = 0     # 清除初次运行标志
			else:  # 精确追踪模式
				# 获取上次斑点的中心坐标
				cx_past = past[0] + int(past[2]/2)
				cy_past = past[1] + int(past[3]/2)
				
				# 检查斑点移动是否在合理范围内(防抖动)
				if abs(cx - cx_past) < 35 and abs(cy - cy_past) < 35:
					# 计算并发送新的误差数据
					err_dx = cx - CENTER_X
					err_dy = cy - CENTER_Y
					past = blob  # 更新斑点信息
					sending_data(-err_dx, -err_dy)
					img.draw_line(CENTER_X, CENTER_Y, cx, cy)

	# 绿色目标追踪模式(用于重新校准中心位置)
	elif task == b'2':
		# 在全图搜索绿色斑点
		blobs = img.find_blobs(THRESHOLD_G, pixels_threshold=2, area_threshold=15)
		blob.clear()
		dst = 150
		
		# 寻找距离当前中心最近的绿色斑点
		for b in blobs:
			x = b[0] + int(b[2]/2)
			y = b[1] + int(b[3]/2)
			dx = abs(x - CENTER_X)
			dy = abs(y - CENTER_Y)
			if dx + dy < dst:
				blob = b
				dst = dx + dy
		
		# 如果找到绿色斑点，更新中心坐标
		if blob:
			CENTER_X = blob[0] + int(blob[2]/2)
			CENTER_Y = blob[1] + int(blob[3]/2)
			task = b'0'  # 重置任务标志
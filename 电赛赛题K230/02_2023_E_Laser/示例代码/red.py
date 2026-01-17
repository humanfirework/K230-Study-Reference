import time, sensor, lcd
from pyb import UART
THRESHOLD_R = [(0, 100, 25, 127, -33, 30)]
THRESHOLD_G = [(57, 100, -45, 18, -45, 43)]
THRESHOLD = 125
DIV_TASK_2 = 10
DIV_TASK_3 = 6
ROI = (10, 10, 90, 90)
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
sensor.set_framesize(sensor.QQVGA)
sensor.set_windowing((120, 120))
sensor.set_auto_whitebal(True)
sensor.skip_frames(time = 20)
sensor.set_hmirror(False)
sensor.set_vflip(True)
sensor.set_auto_exposure(False,1000)
lcd.init()
clock = time.clock()
cnt_find_rect = 0
p_array = []
flgstart = 0
flgend = 0
flgend3 = 0
cnt = 0
err_dx = 0
err_dy = 0
task = b'0'
goal_task2 = 0
goal_task3 = 0
goal_task4 = 0
cx_screen = 60
cy_screen = 60
p0 = (97, 19)
p1 = (19, 22)
p2 = (20, 98)
p3 = (98, 98)
d0 = (93, 21)
d1 = (51, 22)
d2 = (52, 51)
d3 = (93, 50)
point_temp = []
while True:
	img = sensor.snapshot()  # 获取摄像头当前帧图像
	if uart.any():  # 检查串口是否有数据
		task = uart.read(1)  # 读取任务指令(1字节)
		FH = bytearray([0xA1,0x33,0X1A])  # 准备应答帧头
		uart.write(FH)  # 发送应答帧
	# 在图像中寻找红色阈值范围内的色块
	blobs = img.find_blobs(THRESHOLD_R, pixels_threshold = 1, area_threshold = 1)
	blob = []
	for b in blobs:  # 绘制所有检测到的色块矩形框
		img.draw_rectangle(b.rect(), color = (0, 255, 0), scale = 1, thickness = 1)
	# 寻找最大色块
	max_size=0
	for b in blobs:
		if b.pixels() > max_size:
			blob = b
			max_size = b.pixels()
	if blob:  # 计算色块中心坐标
		cx = blob[0] + int(blob[2] / 2)
		cy = blob[1] + int(blob[3] / 2)
	# 任务1: 单点追踪
	if task == b'1':
		img.draw_string(0, 0, "task:1")  # 显示当前任务
		img.draw_cross(point_temp[0][0], point_temp[0][1])  # 绘制目标十字
		if blob:
			err_dx = cx - point_temp[0][0]  # 计算X轴误差
			err_dy = cy - point_temp[0][1]  # 计算Y轴误差
			# 当误差小于阈值时完成任务
			if abs(err_dx) < 1 and abs(err_dy) < 1:
				task = b'0'
				FH = bytearray([0xA1, 0x11, 0x1A])  # 准备完成帧
				uart.write(FH)
				print('1')
		sending_data(err_dx, err_dy)  # 发送误差数据
	
	# 任务2: 四点顺序追踪
	elif task == b'2':
		img.draw_string(0, 0, "task:2")
		points = (point_temp[1], point_temp[2], point_temp[3], point_temp[4])
		if blob:
			err_dx = cx - points[goal_task2][0]
			err_dy = cy - points[goal_task2][1]
			# 根据当前目标点调整误差计算方式
			if goal_task2 == 1:
				err_dy = 0
			elif goal_task2 == 2:
				err_dx = 0
			elif goal_task2 == 3:
				err_dy = 0
			elif goal_task2 == 0 and flgend == 1:
				err_dx = 0
			print(err_dx, err_dy)
			# 当误差小于阈值时切换到下一个目标点
			if abs(err_dx) < 2 and abs(err_dy) < 2:
				goal_task2 = goal_task2 + 1
				if goal_task2 == 4:  # 完成所有目标点
					flgend = 1
					goal_task2 = 0
				elif flgend == 1:  # 完成整个任务
					task = b'0'
					goal_task2 = 0
					FH = bytearray([0xA1, 0x11, 0x1A])
					uart.write(FH)
					print("OK")
					flgend = 0
		sending_data(err_dx, err_dy)
	# 任务3/4: 矩形轮廓追踪
	elif task == b'4' or task == b'3':
		# 初始化阶段: 检测矩形并计算轨迹点
		if cnt_find_rect > 10 and flgstart == 0:
			flgstart = 1
			# 计算矩形中心
			corner_cx = int((corner[3][0] + corner[2][0] + corner[1][0] + corner[0][0]) / 4)
			corner_cy = int((corner[3][1] + corner[2][1] + corner[1][1] + corner[0][1]) / 4)
			corner_temp = []
			# 调整角点位置
			for i in range(4):
				dx = corner_cx - corner[i][0]
				dy = corner_cy - corner[i][1]
				x = corner[i][0] + int(dx * 0.06)
				y = corner[i][1] + int(dy * 0.08)
				corner_temp.append((x, y))
			corner = corner_temp
			# 生成矩形轨迹点
			p_array.append(corner[0])
			for i in range(4):
				next = i + 1
				if i == 3:
					next = 0
				dy = (corner[next][1] - corner[i][1]) / DIV_TASK_3
				dx = (corner[next][0] - corner[i][0]) / DIV_TASK_3
				for j in range(DIV_TASK_3):
					pointx = int(corner[i][0] + dx * (j + 1))
					pointy = int(corner[i][1] + dy * (j + 1))
					p_array.append((pointx, pointy))
			print(len(p_array))
			for p in p_array:  # 绘制轨迹点
				img.draw_circle(p[0], p[1], 1)
		# 矩形检测阶段
		elif flgstart == 0:
			# 寻找符合条件的矩形
			rects = img.find_rects(threshold = 1000)
			for r in rects:
				rect = r.rect()
				if (rect[0] > 15 and rect[1] > 15
					and rect[2] < 60 and rect[3] < 60
					and (rect[0] + rect[2]) < 100
					and (rect[1] + rect[3]) < 100
					and (rect[0] + rect[2]) > 25
					and (rect[1] + rect[3]) > 25):
					cnt_find_rect = cnt_find_rect + 1
					img.draw_rectangle(rect, color = (255, 0, 0))
					corner = r.corners()
					for point in r.corners():  # 绘制角点
						img.draw_circle(point[0], point[1], 5, color = (0, 255, 0))
					break
		print(len(p_array))
		# 追踪阶段
		if blob and flgstart == 1:
			print(goal_task4)
			err_dx = cx - p_array[goal_task4][0]
			err_dy = cy - p_array[goal_task4][1]
			# 当误差小于阈值时切换到下一个轨迹点
			if abs(err_dx) < 2 and abs(err_dy) < 2:
				goal_task4 = goal_task4 + 1
				if goal_task4 == len(p_array):  # 完成整个轨迹
					task = b'0'
					goal_task4 = 0
					FH = bytearray([0xA1, 0x11, 0x1A])
					uart.write(FH)
					print("OK")
					flgstart = 0
					p_array = []
					cnt_find_rect = 0
		if flgstart == 1:
			sending_data(err_dx, err_dy)
	# 任务9: 目标点标定
	elif task == b'9':
		point_temp.append((cx, cy))  # 记录当前点坐标
		img.draw_string(0, 0, "task:5")
		for p in point_temp:  # 绘制所有标定点
			img.draw_circle(p[0], p[1], 1)
		FH = bytearray([0xA1, 0x44, 0x1A])  # 发送标定完成帧
		uart.write(FH)
		task = b'0'
	# 任务6
	elif task == b'6':
		img.draw_string(0, 0, "task:6")
	lcd.display(img)
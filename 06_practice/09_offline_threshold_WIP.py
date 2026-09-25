#ltxdysl
from maix import touchscreen, display, image, app, time, camera

# 初始化触摸屏和显示
ts = touchscreen.TouchScreen()
disp = display.Display()
cam = camera.Camera(552, 368)
flag = 0
# 按钮标签和位置
buttons = {
    "EXIT": [0, 0, 100, 50],  # x, y, width, height
    "-": [20, 150, 50, 75],
    "+": [480, 150, 50, 75],
    "Lmin": [5, 300, 90, 50],
    "Lmax": [95, 300, 90, 50],
    "Amin": [185, 300, 90, 50],
    "Amax": [275, 300, 90, 50],
    "Bmin": [365, 300, 90, 50],
    "Bmax": [455, 300, 90, 50],
    "Change": [455, 0, 90, 50]
}

# 当前选择的阈值类型
# 假设 thresholds 是一个包含六个元素的列表，分别代表 Lmin, Lmax, Amin, Amax, Bmin, Bmax
thresholds = [50, 50, 0, 0, 0, 0]

# 按钮点击事件处理函数
def button_clicked(button_name):
    global flag
    global current_threshold_index  # 使用索引来表示当前选中的阈值
    if button_name == "EXIT":
        app.set_exit_flag(True)  # 设置退出标志
    elif button_name in ["Lmin", "Lmax", "Amin", "Amax", "Bmin", "Bmax"]:
        # 根据按钮名称确定当前阈值的索引
        if button_name == "Lmin":
            current_threshold_index = 0
        elif button_name == "Lmax":
            current_threshold_index = 1
        elif button_name == "Amin":
            current_threshold_index = 2
        elif button_name == "Amax":
            current_threshold_index = 3
        elif button_name == "Bmin":
            current_threshold_index = 4
        elif button_name == "Bmax":
            current_threshold_index = 5
        print(f"Selected {button_name}")
    elif button_name in ["+", "-"]:
        if current_threshold_index is not None:
            change_threshold(button_name)
    elif button_name == "Change":
        flag = 1
        

# 按钮调整阈值函数
def change_threshold(button_name):
    global thresholds
    step = 1
    if current_threshold_index is None:
        print("Error: No threshold selected.")
        return
    if not (0 <= current_threshold_index < len(thresholds)):
        print(f"Error: {current_threshold_index} is not a valid threshold index.")
        return
    if button_name == "-":
        thresholds[current_threshold_index] -= step
    elif button_name == "+":
        thresholds[current_threshold_index] += step
    #print(f"{current_threshold_index}: {thresholds[current_threshold_index]}")
    return thresholds




# 绘制按钮和显示当前阈值的函数
def draw_buttons_and_threshold():
    global thresholds
    thresholds1 = [thresholds[0],thresholds[1],thresholds[2],thresholds[3],thresholds[4],thresholds[5]]
    img = cam.read()
    img.binary([thresholds])
    for button_name, button_pos in buttons.items():        
        img.draw_rect(button_pos[0], button_pos[1], button_pos[2], button_pos[3], image.COLOR_WHITE)
        img.draw_string(button_pos[0] + 10, button_pos[1] + 20, button_name, image.COLOR_WHITE)
        
    # # 显示当前阈值
    # for threshold_name, threshold_value in thresholds.items():
    #     threshold_text = f"{threshold_name}: {threshold_value}"
    #     img.draw_string(220, 50 + buttons[threshold_name][1], threshold_text, image.COLOR_WHITE)
    
    return img




# 检查触摸位置是否在按钮区域内
def is_in_button(x, y, button_pos):
    return x > button_pos[0] and x < button_pos[0] + button_pos[2] and y > button_pos[1] and y < button_pos[1] + button_pos[3]


while not app.need_exit():
    if flag == 0:
        img = draw_buttons_and_threshold()
        disp.show(img)

        x, y, pressed = ts.read()
        if pressed:
            for button_name, button_pos in buttons.items():
                if is_in_button(x, y, button_pos):
                    button_clicked(button_name)
                    print(thresholds)
                    break
    elif flag ==1:
      #在这之后可以根据自己的需要写代码
        img = cam.read()
        Threshold = thresholds
        blobs = img.find_blobs([Threshold], pixels_threshold=500)
        for blob in blobs:

            img.draw_rect(blob[0], blob[1], blob[2], blob[3], image.COLOR_GREEN)
        disp.show(img)


        

    time.sleep_ms(50)
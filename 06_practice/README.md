# 06_practice —— 能直接改成赛题程序的骨架

这一层是**从"看懂 API"到"写得出赛题代码"之间的那一步**：9 个板子上跑的脚本（外加 1 份浏览器仿真），共同构成一套可复用的工程骨架 —— 带状态机、带按键/串口双通道切换、带触摸屏 LAB 阈值在线标定、带 UART 帧封装、带 PID 巡线闭环。
`01_basics/` 告诉你某个 API 长什么样，`05_cv_lite/` 告诉你预处理有多快，这一层告诉你**这些东西怎么在一个 4 天做完的程序里共处**。
走完你应该能：拿 `01_all_in_one.py` 改出自己赛题的程序骨架；说清楚"稳定判定"（连续 N 帧才认）该写在哪一层；知道 `struct.pack` 的帧格式怎么和对端 STM32 对上；以及为什么这一层的串口发送路径**一次都没有通过**。

## 文件清单

| 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `01_all_in_one.py` | **本仓库最该复用的一份**：状态机骨架 + 触摸屏在线调阈值 | `TOUCH(0)` `tp.read()` `find_rects()` `binary()` `uart2.readinto(Rxbuf, 5)` | 542 行；800×480 + `Display.ST7701`；状态 0/1/2/3/8/9 |
| `02_key_switch_ui.py` | 同一骨架的"纯按键"版：0-3 四态循环 + 状态卡画面 | `handle_key_state_switch()` `display_state_info()` `uart2.any()` `uart2.read(5)` | 640×480 + `Display.VIRT`；触控被注释掉（19 行） |
| `03_nested_rect.py` | **内外框判别**：面积排序取前二为外框/内框，角点按顺时针归一化 | `find_rects(threshold=int(rect_area_threshold*1.5))` `r.w()*r.h()` `rect.corners()` `sort_corners_clockwise()` | 还含一段红色激光点追踪并真的调 `send_data()`；`find_rects` 的 `threshold` 和"面积"被混用了 |
| `04_triangle.py` | **两阶段时序**：识别三角形 → 3 秒倒计时 → 转激光追踪 | `find_lines(threshold=1000, theta_margin=25, rho_margin=25)` `detect_triangle_and_generate_path()` `find_blobs(RED_THRESHOLD)` `max(..., key=lambda x: x.pixels())` | 最近路径点用欧氏距离手算；本目录唯一在循环里成功调到 `send_data()` 的地方（然后就崩了） |
| `05_polygon_from_lines.py` | 从**离散线段**反推多边形顶点、边数、类型 | `find_line_segments()` + `extend_line()` `find_polygon_vertices(tolerance=15)` `find_polygons_from_lines(min_sides=3, max_sides=8, tolerance=25)` `classify_polygon_type()` | 246 行纯 Python 几何；这是 `get_regression` 路线的反面教材（能跑，但代码量差一个数量级） |
| `06_curve_recognition_WIP.py` | 曲线识别 —— **不可用**，见下文专节 | `to_grayscale()` `gaussian(2)` `find_edges(EDGE_CANNY, …)` `find_blobs(…)` `get_pixel()` | 689 行；作者在原文件名里就写了"有问题" |
| `08_color_line_following.py` | 四色可切换的 PID 巡线 + 电机帧输出 | `find_blobs([th], roi=下半屏, pixels_threshold=100, area_threshold=100)` `calculate_pid()` `struct.pack('<BHH', …)` | KP=1.2 KI=0.1 KD=0.3 BASE=400；⚠️ 负速度必崩，见下文 |
| `08_line_following_sim.html` | `08_color_line_following.py` 的**浏览器仿真器**：画布 + PID 滑条 + 数据帧 hex 打印 | 纯 JS（Canvas 2D + `FuncAnimation` 等价手轮） | 双击即开；⚠️ 它的"阈值"是死数据，见下文 |
| `lvgl/01_lvgl_demo.py` | LVGL 基础控件 + PNG 动画 + 多语言字体 | `import lvgl as lv` `lv.init()` `lv.font_load("A:…fnt")` | `Display.LT9611`（HDMI），`to_ide=False` |
| `lvgl/02_lvgl_touch.py` | LVGL + 自写触摸输入设备驱动 | `lv.indev_create()` `set_type(lv.INDEV_TYPE.POINTER)` `set_read_cb()` | `Display.ST7701` 800×480 |
| `lvgl/03_lvgl_freetype.py` | LVGL + FreeType 中文矢量字体 | `lv.freetype_init(1, 0, 65535)` `lv.freetype_font_create(ttf, 20, 0)` `lv.freetype_uninit()` | 唯一需要 `.ttf` 的一份 |
| `lvgl/first.py` | ⚠️ **不是 LVGL 代码**：`draw_string_advanced` 随机彩色文字 demo，而且是两份脚本首尾拼接 | `urandom.getrandbits()` `img.clear()` | 见已知问题；保留不删的理由也在那儿 |

## 旧名 → 新名

旧目录 `平时练习/`。**这次重命名不是美化，是修 bug**：同一个目录里混着三种编号写法——`1.Module.py`（点号）、`8,颜色巡线.py` 和 `9,脱机调阈值.py`（**ASCII 逗号**，是点号的误输入）、`LVGL屏幕/1，LVGL demo.py`（**全角逗号**）。三种写法在文件浏览器和 FAT32 SD 卡上排序结果各不相同，你永远不知道"下一个文件"是哪个。统一成 `NN_` 之后排序唯一。

| 旧名 | 新名 |
| --- | --- |
| `1.Module.py` | `01_all_in_one.py` |
| `2.按键控制切换界面.py` | `02_key_switch_ui.py` |
| `3.内外框矩形识别.py` | `03_nested_rect.py` |
| `4.三角形识别.py` | `04_triangle.py` |
| `5.多边形识别_基于线段.py` | `05_polygon_from_lines.py` |
| `6.曲线识别（有问题）.py` | `06_curve_recognition_WIP.py` |
| `7.监控和可视化通过串口传输的模拟量数据.py` | （已移出）`../pc_tools/serial_plot_monitor.py` |
| `8,颜色巡线.py` | `08_color_line_following.py` |
| `颜色巡线仿真.html` | `08_line_following_sim.html` |
| `9,脱机调阈值.py` | （已移出）`../other_boards/maixpy/offline_threshold_tuner.py` |
| `LVGL屏幕/1，LVGL demo.py` | `lvgl/01_lvgl_demo.py` |
| `LVGL屏幕/2，LVGL touch demo.py` | `lvgl/02_lvgl_touch.py` |
| `LVGL屏幕/3，LVGL touch demo freetype.py` | `lvgl/03_lvgl_freetype.py` |
| `LVGL屏幕/first.py` | `lvgl/first.py`（原名保留） |

**关于编号现在的两个洞**：重命名当时是连续的 `01_`–`09_`；下一个 commit 把 `07_`（PC 脚本）和 `09_`（MaixPy 脚本）移出了本目录，于是留下空号。**故意不重编号**——它们的位置本身就是信息，说明"这里曾经有一份不属于 K230 的文件，它现在在别处"。
`08_line_following_sim.html` 与 `08_color_line_following.py` **共享 `08_` 前缀也是有意的**：它俩是一对（板子脚本 + 它的仿真器），排在一起才对。

## 为什么 `06_curve_recognition_WIP.py` 不是"有 bug"而是"不可用"

原作者对它的判断写在**文件名**里（`6.曲线识别（有问题）.py`）。读完 689 行之后的结论是：它的问题不是某个参数没调好，是**架构选错了**，调参救不回来。

核心在 `extract_curve_points()`（191 行起）：

```python
for y in range(blob.y(), blob.y() + blob.h(), 2):     # 216 行：隔 2 行扫
    for x in range(blob.x(), blob.x() + blob.w()):    # 218 行：逐列扫
        if 0 <= x < DISPLAY_WIDTH and 0 <= y < DISPLAY_HEIGHT:   # 220 行
            if edge_img.get_pixel(x, y) > 0:                     # 222 行
```

`DISPLAY_WIDTH/HEIGHT = 800, 480`（31–32 行）。blob 一旦覆盖全画面，最坏情况是 **240 行 × 800 列 = 19.2 万次 `get_pixel()`**，加上同样次数的边界判断，**每帧约 38 万次 Python 层调用**。这不是"慢一点"——吞吐量的上限由 MicroPython 解释器的调用开销决定，`curve_area_threshold`、`curve_edge_threshold` 那些旋钮一个都影响不了它。同一件事在固件里做一次 C 循环就完事（`05_cv_lite/grayscale_find_edges.py`），或者干脆不需要逐像素（`get_regression`）。
再叠上两个具体缺陷，就是"完全不能用"：

- **第 201 行那个阈值匹配所有像素。** `curve_binary_threshold = [(30, 255)]`（46 行）在这里被当 6 元组消费：`(0, curve_binary_threshold[0][1], -128, 127, -128, 127)` → `(0, 255, -128, 127, -128, 127)`。L 从 0 到 255、A/B 覆盖整个定义域 —— **每个像素都是前景**。所以那个双重循环必然扫遍全图，那个"降阈值以检测更精细的曲线"的注释（46 行）从来没有生效过。
- **`gray_img.gaussian(curve_smooth_kernel)`（172 行）里 `curve_smooth_kernel = 2`（49 行）是偶数核。** 高斯核需要奇数半径；外面套着宽泛的 `except Exception`（184 行），所以就算它失败也只会静默 `return None`，你永远看不到错误 —— 表现就是"程序没报错但什么都没检测到"。

**正确做法**：看 `../01_basics/11_line_following.py` 的 `img.get_regression([(255, 255)])`，逐像素拟合在固件 C 里做，Python 只拿一条线；要分段曲线就按行取若干 ROI、每块一次 `get_regression`。这份文件的骨架（状态机、串口收帧、状态卡显示）是好的，值得留下；**`extract_curve_points()` 整个函数应当替换掉，不是修补**。

## `01_all_in_one.py` 到底是什么

不是"一个综合示例"，是一份**赛题程序模板**，这是它值得单独讲的原因。

- **状态机**（454–509 行）：状态 0=复位待机、1/2/3=任务位（现在只有 `img.draw_string_advanced` 占位和一句 `# 这里可以添加具体的识别逻辑`）、8=阈值调节、9=暂停等串口。你的赛题代码就填在 1/2/3 那三个 `elif` 里。
- **双通道切换**：GPIO53 按键本地切（`handle_key_press()`，104 行，含 50ms 消抖 + 等释放）；UART2 远端切（464–474 行，收 5 字节 `55 XX FF FF FF`，`XX` 就是新状态码）。比赛时队友在 MCU 侧一发命令就能让 K230 换任务，这个接口非常值。
- **`handle_threshold_adjustment()`（128–426 行）**：左右分屏的触摸屏标定 UI —— 左边是实时二值化预览，右边是滑块面板，三个按钮（返回/切换/保存）。LAB 模式 6 个滑块、灰度模式 2 个。
  **这是全仓库最值钱的 300 行**：赛场上你没时间改代码重烧录，只有时间拖滑块。它就是 `../other_boards/maixpy/offline_threshold_tuner.py`（MaixPy 那份）在 K230 上的等价物，所以那份才被移出去了。
- **可复用清单**：`display_state_info()` 状态卡画面、`send_data()` 帧封装（有 bug，见下）、`try/except/finally` 完整收尾（430–542 行，这一条是对的）。

⚠️ **`send_data(x, y)` 从来没通过。** 64 行 `struct.pack('<BHHHH', 1, x, y)` —— 格式串要 5 个值，只给了 3 个 → 每次调用 `struct.error`。`02_key_switch_ui.py:69`、`03_nested_rect.py:67`、`04_triangle.py:70` **同一处、同一个错**。
`01` 和 `02` 里 `send_data()` 定义了但从未被调用，所以这个错一直是潜伏的；`03` 和 `04` 在激光追踪分支里真的调它，于是那两条路径**一碰到激光点就抛异常**，被外层 `except BaseException` 打印一行"Exception …"后整个程序结束。
按格式串意图（`B` + 4×`H` = 9 字节 + 头尾 = 11 字节）和 `08` 的实际用法（`'<BHH'`，类型 + 左速 + 右速 = 5 字节 + 头尾 = 7 字节）来看，`'<BHH'` 才是这几个文件想要的；但本仓库保持代码原样不改，动手前请先和对端 STM32 的解析器对齐字节数。

## 练习建议

1. **把 `01_all_in_one.py` 变成"任务 1 = 找最大红色色块并打印中心"。** 只改 `elif state == 1:` 那一个分支（484–489 行），不动骨架；用状态 8 的触摸屏把 `RED_THRESHOLD` 调好并保存。
   完成标准：按 GPIO53 → 进调参 → 拖滑块到屏幕上左半边的二值化预览里"只有红杯是白的" → 按保存 → 返回 → 再按键到状态 1 → 屏幕上显示的中心坐标随杯子移动，且**把杯子拿走后不崩、也不误报**。
2. **验证 `struct.error` 并给出你自己的帧格式。** 在 `04_triangle.py` 上复现：跑到激光追踪分支，让它调用 `send_data()`。
   完成标准：能贴出那行异常原文；然后写出你自己打算用的帧（几个字节、每字节含义、有无校验），并**在 `08_line_following_sim.html` 底部的数据帧显示区里把它排出来对一遍**——仿真器已经帮你打了 hex，别浪费。
3. **同一根胶带，三种巡线实现，量帧率。** (a) `05_polygon_from_lines.py` 的 `find_line_segments` + 自己拼；(b) `08_color_line_following.py` 的 `find_blobs` 取质心；(c) `../01_basics/11_line_following.py` 的 `get_regression`。
   完成标准：三条都有实测 fps 数字，且 (c) ≥ (b) ≥ (a)。（如果结论相反，把数字贴出来——那说明 (a) 里 `max_theta_diff=` 那个关键字确实报错了，见已知问题。）
4. **给 `08_color_line_following.py` 做无硬件验证。** 不接电机，只串口监听，把它和 `../pc_tools/serial_plot_monitor.py` 连起来看输出。
   完成标准：PC 侧能看到字节流；你会亲眼看到直线巡线时数据正常，一旦 PID 输出转负（车要反向修正）程序就抛 `struct.error`。这条做完，下一个练习才有意义。
5. **补 `lvgl/` 的资源缺口，让 3 个 LVGL demo 至少跑起来一个。**
   完成标准：`lvgl/03_lvgl_freetype.py` 能在屏上画出中文。这只需要一个 ttf —— `ls /sdcard/res/font/` 先看固件给了什么，找不到就把 `SourceHanSansSC-Normal-Min.ttf` 拷到那个路径。

## 已知问题 / 注意事项

以下逐条从代码核实。完整分级清单见 [docs/02_known_issues.md](../docs/02_known_issues.md)。

- ⚠️ **四处 `struct.pack('<BHHHH', 1, x, y)` 参数个数不对**：`01_all_in_one.py:64`、`02_key_switch_ui.py:69`、`03_nested_rect.py:67`、`04_triangle.py:70`。5 个字段传 3 个值 → `struct.error`，串口发送路径**从未通过**。前两处潜伏（没人调用），后两处在激光追踪里必触发。
- ⚠️ **`08_color_line_following.py:71` 的 `'<BHH'` 装不下负数。** 67–68 行把速度钳到 `±1000`，紧接着用 `H`（**无**符号 short）打包 → 第一次 PID 输出为负就 `struct.error`。也就是说这台"车"只能往一个方向修正。
- ⚠️ **`08_color_line_following.py:74–75` 每帧打两行，其中一行是 `frame.hex()` 全帧转大写。** 这是**全仓库最严重的单个帧率杀手**：`send_motor_data()` 每帧被调用至少一次（没检测到色块时也调 `send_motor_data(0, 0)`），每次都往 UART 打两行文本。做帧率实验前先注释掉这两行。
- **`08_color_line_following.py` 没有 `os.exitpoint()`**（全文 0 处），所以 IDE 的停止按钮打不断它；`06_curve_recognition_WIP.py:565` 有。
- **`08_color_line_following.py:10` 和 `:65` 的注释引用了 `5.贝塞尔曲线.py`**（"使用5.贝塞尔曲线.py的配置"、"使用5.贝塞尔曲线.py的格式"）。**本目录没有这个文件**，`05_` 是多边形识别。它的旧编号沿用了 `平时练习/` 里另一套序列，那份代码不在这个仓库；所以那两处"照它改"的说明是查不到对照的。
- ⚠️ **`01_all_in_one.py` 的调参界面"看到的"和"存下的"不是同一个阈值。** 预览走 183 行 `processed_img.binary([[i - 128 for i in slider_values]])`（**六个值统统减 128**），保存走 371 行 `RED_THRESHOLD.extend([tuple(slider_values)])`（**原样存**）。初始值 `[85, 100, -18, 50, -18, 51]` 经预览会变成 `[-43, -28, -66, -78, -146, -77]`，L 分量都负了 —— 预览画面和你的判定条件描述的**不是同一个色域**。用这个 UI 调出来的阈值，落盘后主循环里的行为跟你刚才看到的对不上。**动手前先在心里加 128 校验一遍**（或者干脆只用它的"矩形/灰度"模式，那条路径 188 行 `binary([slider_values[:2]])` 是不偏移的，预览和保存一致）。
- **`01_all_in_one.py:462` 每帧白算一次 `find_rects()`。** `rects = img_binary.find_rects()` 赋值之后**全文再没被读过**；同上的还有 `img_gray`/`img_binary`（它们是 `find_rects` 的中间量）。也就是说状态 0/1/2/3 里每帧都跑一遍 800×480 的灰度化 + 二值化 + 矩形检测，纯粹为了丢掉结果。第一次改这份文件就该把这三行挪进 `elif state == 1:` 里面。
- **`01_all_in_one.py` 的 `import cv_lite`、`from machine import Timer`、`from machine import PWM`、`import ulab.numpy as np` 都没有被用到**（`cv_lite` 只 import 不调用）。这一份是 `05_cv_lite/` 的接口在赛题骨架里唯一可能的接入点，现在空着。
- **`05_polygon_from_lines.py:194` 用关键字传参：`find_line_segments(merge_distance=20, max_theta_diff=10)`。⚠️ 形参名可疑。** 位置传参 `find_line_segments(roi, merge_distance, max_theta_diff)`（见 `../01_basics/04_find_line_segments.py`）**是对的，别改**；但官方形参名是 `max_theta_difference`，不是 `max_theta_diff`。这里用关键字写，如果固件按名字绑定就会 `TypeError`。本仓库不改代码 —— **请实测这一行并把结论写回来**。另外这一处也没传 `roi`，是"用默认全图"的正确用法。
- **`01/02/03/04/06` 之间互不兼容，别当成同一份文件的版本。** 光串口收帧的帧头就有三种：`01:468`、`03:315`、`04:376` 认 `Rxbuf[0] == 0x55`；`02:170` 认 `0xAA`；`06:575` 认"头 `0xAA` 且尾 `0x55`"。显示后端也不同：`01` 是 `Display.ST7701` 800×480，`02/03/04/06` 全是 `Display.VIRT`（`02` 还是 640×480）。**这些不是"渐进改进"，是几台不同硬件上各写一份留下的**，抄的时候认准一份为准（推荐 `01`）。
- **`06_curve_recognition_WIP.py` 里 `find_blobs` 之前那句 `edge_img.find_blobs(...)`（198 行）用的 L 上限 255 也说明它对 `find_blobs` 的 LAB 语义理解错位**：Canny 出的边在灰度图上，`find_blobs` 却按 LAB 六元组传。加上前一条的"阈值匹配一切"和"偶数高斯核"，这份文件里三个错误互相掩盖，`except Exception` 让它们都只表现为"没检测到"。
- **`08_line_following_sim.html`：它仿真的是**控制环**，不是识别环。** 4 组 LAB 阈值（267–270 行）声明了但**全文没有任何一处读取 `.threshold`** —— 画布上那条线就是一个纯色方块，位置由几何给出，不做任何像素分类。PID 部分（`kp=1.2 / ki=0.1 / kd=0.3 / baseSpeed=400`、积分限 ±50、速度限 ±1000）与 `08_color_line_following.py` **逐值一致**，所以调控制参数是有效的。
  ⚠️ 但它同时**掩盖了板子上那个致命 bug**：第 366 行 `new Uint8Array([…, leftSpeed & 0xFF, (leftSpeed >> 8) & 0xFF, …])` 用位掩码打包，负速度在 JS 里能正常出补码；板子上 `struct.pack('<BHH')` 的 `H` 是**无**符号，同样这个值会直接抛异常。**在仿真器里跑得漂亮的参数，上板可能在第一次反向修正时就崩。**
  另：画布是 800×400（175 行），不是板子的 800×480。
- ⚠️ **`lvgl/` 三个 demo 现在都跑不起来，缺的是资源文件而不是代码。** 逐个核实过的路径：
  - `01_lvgl_demo.py:115`、`02_lvgl_touch.py:159`、`03_lvgl_freetype.py:200` 都用 `res_path = "/sdcard/examples/15-LVGL/data/"`，需要其下 `font/montserrat-16.fnt`、`font/lv_font_simsun_16_cjk.fnt`、`img/animimg001.png`…`animimg003.png`。
  - `02_lvgl_touch.py:226` 还 `os.chdir("/sdcard/examples/15-LVGL")`。
  - `03_lvgl_freetype.py:203` 需要 `/sdcard/res/font/SourceHanSansSC-Normal-Min.ttf`，加载失败会 `raise Exception("Failed to load fonts")`。
  **这些一个都不在本仓库里**，它们在嘉楠官方 SD 镜像上。先用 `os.listdir("/sdcard/examples/")` 确认你的镜像有没有 `15-LVGL`；没有就得自己把字体和 PNG 拷进去。`15-LVGL` 这个目录名同样是厂商教程章节号，和你在这份 README 里看到的 `23-CV_Lite`（`../05_cv_lite/` 的前身）是一个来源。
- ⚠️ **`lvgl/first.py` 不是 LVGL 代码，而且是两份脚本首尾拼接。** 全文没有 `import lvgl`，内容是 `img.draw_string_advanced(x, y, size, "Hello World!，你好庐山派！！！")` 的随机彩色文字 demo（1 份 `DISPLAY_MODE = "VIRT"` 版 + 1 份 `"LCD"` 版）。两半除了 `DISPLAY_MODE` 那一行**几乎逐字相同**，各自都定义了一次 `display_test()`（26 行、109 行），**后定义的 LCD 版覆盖前一个 VIRT 版**，于是 1–82 行整体成为死代码。
  留着不删是刻意的：这是"两份脚本被粘进同一个文件"这种事故的可辨识样本 —— 看到函数重复定义，先想是不是复制粘贴串了，而不是急着改前一份。
- **`03_nested_rect.py:219–250` 与 `04_triangle.py:113–140` 的激光追踪是同一段逻辑的两份拷贝**（`find_blobs(RED_THRESHOLD)` → `max(…, key=x.pixels())` → 欧氏距离找最近路径点 → `send_data()`），差别只在 `04` 前面多了一步三角形路径生成。要复用时先确认你只需要一份，别把两份都带进项目。
- **`01/02/03/04/06` 五个文件里 `blob_area_threshold = 5`，但它被当 `pixels_threshold` 用。** 例如 `03:132` / `03:219` / `04:113`：`img.find_blobs(RED_THRESHOLD, pixels_threshold=blob_area_threshold)` —— 变量名叫"面积"、实参是"像素数"、值是 **5**。也就是说**一坨 5 个像素的噪点就能通过筛选**，随后 `max(red_blobs, key=lambda x: x.pixels())`（`03:230`、`04:116`）从这个大概率是噪声的集合里挑像素最多的那个当"激光点"。同理 `rect_area_threshold = 20000` 在 `03:142` 被写成 `find_rects(threshold=int(rect_area_threshold * 1.5))`，而 `find_rects` 的 `threshold` 是**矩形度评分**、不是面积门槛（面积过滤是紧接着 147–148 行另做的）。这些名字都是"看起来对、语义错"，抄之前先确认你要过滤的到底是哪一个量。

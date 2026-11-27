# 已知问题清单

> **这份文件是缺陷的唯一事实源。** 目录 README 只写"能不能跑"的摘要并链到具体条目，不再重复现象和成因。
>
> - 代码状态：除下面 **P0-3** 的两处拼写外，仓库代码保持原样，一行未改。
> - 行号基于提交 `a2822e9`。改过代码后请重新定位。
> - 编号是稳定标识，**不保证连续**：删掉的条目不会重新编号。
> - 每条都标"核实方式"和"状态"。当前没有任何一条经过上板验证 —— 这是这份清单最需要补的一块。

## 怎么用这份清单

### 证据等级

| 等级 | 含义 | 当前数量 |
| --- | --- | --- |
| **已上板验证** | 在庐山派 K230 上实跑过，有现象或日志 | **0 条** |
| **读代码核实** | 结论只依赖语言语义或代码结构（未定义名、参数个数、不可达分支、常量恒真） | 绝大多数 |
| **待上板确认** | 结论依赖固件行为（星号导入是否带出名字、关键字形参名、资源是否存在、帧率） | 少数 |

⚠️ 这份清单里没有"实测"这一档：所有结论要么是**读代码核实**，要么是**待上板确认**。凡是没有上板跑过的，都不写成结论。

### 按症状找

| 症状 | 先看 |
| --- | --- |
| 一运行就 `TypeError` / `NameError` | P0-1、P0-3、P0-4、P2-15、P2-16 |
| 跑一下"安静退出"，没有 traceback | P1-6（`except` 只打印一行）——先加 `sys.print_exception` |
| IDE 停止按钮没反应 / 每次都要断电 | P1-4、P1-5 |
| 调好的阈值下次开机就变了 | P1-2、P1-8 |
| 串口发不出去 / 对端收不到 | P0-2、P2-7、P2-11、P3-1（详见 [docs/06](06_uart_protocol.md)） |
| 识别结果时好时坏 | P2-3、P2-6、P2-9、P3-1（接收端无重同步） |
| 帧率低 | P1-9、P2-8、P3-16 |
| 模型/资源加载失败 | P3-2、P3-3、P3-4 |
| 文件连语法都不过 | P0-5 |

### P0 / P1 索引

| ID | 位置 | 一句话 | 状态 |
| --- | --- | --- | --- |
| [P0-1](#p0-1) | `2024_E_tic_tac_toe/main_tic_tac_toe.py` | 缺显式 `import os` 却用 `os.exitpoint()` | 待上板确认 |
| [P0-2](#p0-2) | `06_practice`、`2023_E_laser`、`laser_drawing` 共 10 处 | `struct.pack` 格式串要 5 个、只给 3 个 | 读代码核实 |
| [P0-3](#p0-3) | `01_basics/01_camera_open.py`、`02_data_collection/03_uart_test.py` | `Sensor` 关键字拼错 | **已修** |
| [P0-4](#p0-4) | `01_basics/11_line_following.py:63` | `THRESHOLD = D(90, 23)`，`D` 未定义 | 读代码核实 |
| [P0-5](#p0-5) | 3 个归档文件 | 语法解析失败 | 不修 |
| [P1-1](#p1-1) | `2025/.../main_multi_constraint.py:86` | `len(...) != 8` 恒真，整条抗干扰路径未生效 | 读代码核实 |
| [P1-2](#p1-2) | `2025/.../main_thresh_ui_{fast,accurate}.py` | 进调参界面会把标定值覆盖成写死的默认值 | 读代码核实 |
| [P1-3](#p1-3) | 同上 | `Situation == 1`（开始识别）掉进空分支 | 读代码核实 |
| [P1-4](#p1-4) | `05_cv_lite` 27 个 + 4 处 | 裸 `while True` 绕过生命周期，中断要断电 | 读代码核实 |
| [P1-5](#p1-5) | `01_basics/02_drawing.py` 等 3 个 | `finally` 被截断，缺 `MediaManager.deinit()` | 读代码核实 |
| [P1-6](#p1-6) | `2025/.../main_thresh_ui_accurate.py` | 三处走到即崩，且异常只打印一行 | 读代码核实 |
| [P1-7](#p1-7) | `2023_E_laser/k230_full.py` | `beep_pwm`、`Red_thresholds` 未定义，在"追踪成功"时崩 | 读代码核实 |
| [P1-8](#p1-8) | `06_practice/01_all_in_one.py` | 调参预览与保存的阈值差 128 | 待上板确认 |
| [P1-9](#p1-9) | `2024_E_tic_tac_toe/main_tic_tac_toe.py:321` | 每帧 `sleep(0.05)`，帧率上限约 20 FPS | 读代码核实 |

---

## P0 · 启动即失败，或主路径必然抛异常

<a id="p0-1"></a>
### P0-1 · 三子棋主程序没有显式 `import os`，却调用 `os.exitpoint()`

- **位置**：`07_contest/2024_E_tic_tac_toe/main_tic_tac_toe.py:1446`（主循环第一句）、`:1498`（`finally` 里）。
- **现象**：如果 `os` 不在全局命名空间，第一次进主循环就 `NameError: name 'os' is not defined`，被 `:1487` 的 `except BaseException` 打印一行后静默退出。
- **成因**：文件只 `import math / struct / time` 和 `from media.* import *`。`media` 的星号导入是否带出 `os`，拿不到固件 `media.py` 源码，无法静态确认。仓库里 3 份亚博例程（`sample_code/get_square.py:135`、`sample_code/red_light.py:166`、`yahboom_reference/get_light3.py:90`）同样没有 `import os` 却调用 `os.exitpoint()` —— 说明某些固件下它可能是可用的。
- **建议改法**：文件开头加 `import os`（官方模板全部显式导入）。**本次没有改**：无法确认原程序是否真的崩，而且改动会让这个 1500 行文件的全部行号 +1。
- **核实方式**：读代码 + 对照[嘉楠 v1.3 sensor 例程页](https://www.kendryte.com/k230_canmv/zh/v1.3/example/media/sensor.html)；上板跑一次即知。
- **状态**：待上板确认。

<a id="p0-2"></a>
### P0-2 · 10 处 `struct.pack` 格式串与实参个数不匹配

**后果：`send_data()` 一被调用就 `struct.error`。这些脚本的整条串口输出链路，在调用点上是断的。**

| 文件 | 行 | 格式串 | 需要 | 实给 |
| --- | --- | --- | --- | --- |
| `06_practice/01_all_in_one.py` | 64 | `'<BHHHH'` | 5 | 3 |
| `06_practice/02_key_switch_ui.py` | 69 | `'<BHHHH'` | 5 | 3 |
| `06_practice/03_nested_rect.py` | 67 | `'<BHHHH'` | 5 | 3 |
| `06_practice/04_triangle.py` | 70 | `'<BHHHH'` | 5 | 3 |
| `07_contest/2023_E_laser/k230_full.py` | 59, 66 | `'<BHHHH'` | 5 | 3 |
| `07_contest/laser_drawing/02_triangle_exposure.py` | 61, 70, 75 | `'<BHHHH'` | 5 | 3 |
| `07_contest/laser_drawing/02_triangle_exposure.py` | 81 | `'<BHHHHH'` | 6 | 5 |

- **现象**：`struct.error: pack expected 5 items for packing (got 3)`。
- **触发点**：`06_practice/03_nested_rect.py:250` 和 `04_triangle.py:136` 在激光追踪分支里真的调用 `send_data()`，走到就抛。`01`、`02` 只定义未调用，属于潜伏。
- **成因**：想发的是 `type + x + y` 三字段，格式串多写了两个 `H`。
- **建议改法**：**收窄格式串**（`'<BHHHH'` → `'<BHH'`），不要补零凑参数 —— 补零会静默改变线上字节数。收窄后与仓库里本来就正确的 30 处 `'<BHH'` 一致。
- **核实方式**：读代码逐处核对；可用脚本机械检查"格式项数 vs 实参个数"。
- **状态**：读代码核实。**未修**（属协议，见 [docs/06](06_uart_protocol.md)）。

<a id="p0-3"></a>
### P0-3 · 两处 `Sensor()` 关键字拼错（已按官方手册修正）

| 文件 | 行 | 改前 | 改后 |
| --- | --- | --- | --- |
| `01_basics/01_camera_open.py` | 13 | `Sensor(channe = sensor_id)` | `Sensor(id = sensor_id)` |
| `02_data_collection/03_uart_test.py` | 33 | `Sensor(wihth = picture_width, …)` | `Sensor(width = picture_width, …)` |

- **现象**：`channe` / `wihth` 都不是合法关键字，构造时 `TypeError`，这两个文件在出第一帧之前就停。
- **依据**：嘉楠 v1.3 [Sensor 模块 API 手册](https://www.kendryte.com/k230_canmv/zh/v1.3/api/mpp/K230_CanMV_Sensor%E6%A8%A1%E5%9D%97API%E6%89%8B%E5%86%8C.html) 写的是 `sensor = Sensor(id, [width, height, fps])`；庐山派 [使用摄像头](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/use-sensor.html) 写明默认 CSI2 即 `id=2`，官方例程就是 `Sensor(id=sensor_id)`。
- **改法**：只把关键字改对，其余一行未动。提交 `a2822e9`。
- **状态**：已修（2026-11-27）。仍建议上板确认能出第一帧。

<a id="p0-4"></a>
### P0-4 · `11_line_following.py:63` 的 `THRESHOLD = D(90, 23)`

- **现象**：`D` 从未定义，`NameError`，进不了主循环。
- **成因**：看字面是灰度阈值，正常写法是 `THRESHOLD = (下限, 上限)`；但 `(90, 23)` 的下限大于上限，无法确定作者本意是 `(0, 90)`、`(23, 90)` 还是别的。
- **为什么没改**：庐山派 wiki 的图像识别栏目没有巡线/线性回归页，嘉楠 v1.3 的 `get_regression` 例程页也不存在，找不到官方原文；猜一个值就是"看起来对"的修复。
- **建议改法**：先在你的光照下量一条黑线的灰度直方图，再定 `(下限, 255)`；同时删掉第 64 行重复的 `Display.init`（它会覆盖 `DISPLAY_MODE` 的选择）和重复的 `BINARY_VISIBLE`。
- **状态**：读代码核实，未修。

<a id="p0-5"></a>
### P0-5 · 3 个文件语法解析失败（都在归档目录）

| 文件 | 行 | 症状 |
| --- | --- | --- |
| `07_contest/2024_E_tic_tac_toe/skeleton_incomplete.py` | 184 | `def receive_and_unpack():` 空函数体 |
| `07_contest/2023_E_laser/error/error2.py` | 375 | f-string 里空的 `{}` + 裸 `str()` |
| `07_contest/2023_E_laser/error/error3.py` | 369 | 同上 |

`skeleton_incomplete.py` 是未完成骨架；`error2/3` 是失败尝试。**不要凭猜补实现** —— 可用版本是 `main_tic_tac_toe.py` 和 `2023_E_laser/` 下的三个主脚本。状态：读代码核实，不修。

---

## P1 · 静默改变结果、资源不释放、每次要断电

<a id="p1-1"></a>
### P1-1 · 2025"多限制条件"版：`len(...) != 8` 是恒真门

- **位置**：`07_contest/2025_E_self_aiming/result/main_multi_constraint.py:86`（`if len(outer_points) != 8: continue`）。
- **现象**：`min_corners()` 返回最小外接矩形，按定义恒为 4 个点，永远不等于 8。每一轮都在这里 `continue`，`find_nested_rects()` 每帧返回 `None`。
- **后果**：文件名里的"多限制条件"从未生效，每帧都退回 `find_best_rect()`，行为和 `main_thresh_ui_fast.py` 一样。
- **建议改法**：删掉这个恒真门，让下一段的 `area_ratio >= 1.5` 生效。
- **⚠️ 改前必读**：这条路径从未运行过。删门之后，外层 O(n²) 的双重循环会真的开始跑（预期帧率下降），下游没执行过的分支也会开始跑。必须上板。
- **状态**：读代码核实，未修。

<a id="p1-2"></a>
### P1-2 · 触摸调参 UI 会覆盖你标定好的阈值

- **位置**：`2025_E_self_aiming/result/main_thresh_ui_fast.py` 与 `main_thresh_ui_accurate.py` 各一份 `init_slider_values()`。
- **现象**：函数形参 `mode` 从未使用，函数体读全局 `threshold_mode`；三个返回值是写死的，和本文件真正的默认值 `rect_binary_default / _small / _large` 不一致，两个文件之间也分叉（大面积档一份 `[75,200]`、一份 `[85,200]`）。
- **后果**：一进调参界面，滑块跳到一组你没设过的值；按"保存"就把赛场光照下调好的阈值静默覆盖 —— 这正是这个功能要避免的事故。
- **建议改法**：让 `init_slider_values` 真正使用 `mode`，直接从 `rect_binary_default/_small/_large` 读（单一数据源），调用点传 `threshold_mode`。
- **⚠️ 连带**：`global threshold_mode` 必须出现在该作用域首次使用之前，否则 `SyntaxError: name 'threshold_mode' is used prior to global declaration`。
- **状态**：读代码核实，未修。

<a id="p1-3"></a>
### P1-3 · `Situation == 1` 是死状态

- **位置**：`main_thresh_ui_fast.py:502`、`main_thresh_ui_accurate.py:793`（分派链）。
- **现象**：注释写着 `0:未初始化, 1:开始识别, 2:停止识别, 3:阈值调节`；STM32 发 `55 01 FF FF` 确实把 `Situation` 置 1，但分派链是 `if == 0 / elif == 2 / elif == 3 / else: pass` —— 正式命令"开始识别"掉进什么都不做的 `else`，反而是开机状态 0 在识别。
- **对照**：`2023_E_laser/main_high_fps.py` 判的是 `== 1`，可以看这条链在复制中怎么变形的。
- **建议改法**：`if Situation in (0, 1):`，既让命令生效，又保留"开机即识别"（不接 MCU 也能单独调）。别"顺手清理"成只判 `== 1`，那会毁掉离线调试。
- **状态**：读代码核实，未修。

<a id="p1-4"></a>
### P1-4 · 裸 `while True` 绕过 CanMV 生命周期（27 + 4 处）

| 位置 | 具体情况 |
| --- | --- |
| `05_cv_lite/` 全部 27 个 | 没有 `try`；`while True` 之后写着 `sensor.stop()` / `Display.deinit()` / `os.exitpoint(ENABLE_SLEEP)` / `MediaManager.deinit()`，**全部不可达** |
| `03_ai_demos/05_object_tracking.py:409` | 裸循环，无 `try/finally`、无 `exitpoint`，循环后也没有 `deinit()` |
| `06_practice/08_color_line_following.py:197-228` | 全文 0 处 `os.exitpoint()`，IDE 停止按钮打不断 |
| `04_number_classification/code/v1.2.2/cls_video_1_2_2.py:121`、`v1.3/cls_video_1_3.py:62` | 裸循环，清理代码不可达 |

- **后果**：中断程序后媒体缓冲区不释放，**必须给板子断电重启**才能再跑。4 天赛制里这是实打实的时间损失。
- **建议改法**（每个文件两处）：① `while True:` 第一条语句加裸 `os.exitpoint()`；② 用 `try:` 包住主循环，把尾部清理缩进进 `finally:`。
- **⚠️ 别改错**：尾部已有的 `os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)` 要保留 —— 它和循环里的裸调用是两件事。机械地"加个 exitpoint"会把它重复一遍。
- **状态**：读代码核实，未修（厂商例程按"不改"处理，见 [docs/07](07_maintenance.md#14-改代码前的五步)）。

<a id="p1-5"></a>
### P1-5 · 三个文件的 `finally:` 被截断，缺 `MediaManager.deinit()`

| 文件 | 现状 |
| --- | --- |
| `01_basics/02_drawing.py` | `finally` 停在注释 `# 释放媒体缓冲区`，后面的调用没写 |
| `02_data_collection/02_capture_burst.py` | 同上，注释还写着"（自动处理）" |
| `02_data_collection/03_uart_test.py` | 只 `deinit` 了 Display，没有 MediaManager |

后果同 P1-4。`capture_burst` 那句"自动处理"是假的，正是它让这个缺失一直没人怀疑 —— 改的时候把注释一起改掉。状态：读代码核实，未修。

<a id="p1-6"></a>
### P1-6 · 2025 高精版三处走到即崩，且被异常处理掩盖

- **文件**：`result/main_thresh_ui_accurate.py`。
- **位置**：
  - `:829`、`:843` 无条件调 `max_rect.corners()`，但 `:678` 那个 `RectLike` 只有 `rect()` / `center()` / `area()`，**没有 `corners()`** → `AttributeError`。
  - `:950` 读 `matrix`，而 `matrix` 只在 `:850` 的四点分支里赋值 → 非四边形那帧 `UnboundLocalError`。
  - `:14` `import cv_lite`，模块不在仓库（嘉楠官方模块，见 P3-2 的说明）。
- **共同根因**：文件末尾 `except BaseException as e: print(f"异常: {e}")` 只打印一行、不带 traceback，程序静默退出，看起来像"跑一下就没了"。
- **最重要的改法**：先加 `sys.print_exception(e)`（三个主程序都该加）。它不修任何 bug，但能让剩下所有的都被看见。
- **状态**：读代码核实，未修。

<a id="p1-7"></a>
### P1-7 · 2023 那套在"追踪成功"那一刻崩

- **文件**：`07_contest/2023_E_laser/k230_full.py`。
- **位置**：
  - `:411-414` `beep_pwm.freq(1000)` / `.enable(True)` / `.enable(False)`，但 `beep_pwm` 全文从未实例化（`:16` 只 import 了 `PWM`）→ `NameError`，恰好发生在"追踪完成、距离 ≤ 3 cm"那一刻。
  - `:359` `img.find_blobs(Red_thresholds)`，而本文件定义的是 `RED_THRESHOLD`（`:26`）→ 大小写笔误，走到就 `NameError`。
- **建议改法**：补蜂鸣器实例化，或注释掉那三行。**别猜引脚** —— 这块板子的蜂鸣器脚位在仓库里没有记录，PWM 通道填错可能打到激光（GPIO48）或云台轴上。
- **状态**：读代码核实，未修。

<a id="p1-8"></a>
### P1-8 · `01_all_in_one.py` 调参界面"看到的"和"存下的"不是同一个阈值

- **位置**：`06_practice/01_all_in_one.py:183`（预览）与 `:371` / `:374`（保存）。
- **现象**：预览走 `binary([[i - 128 for i in slider_values]])`，六个值统统减 128；保存走 `RED_THRESHOLD.extend([tuple(slider_values)])`，原样存。初始值 `[85, 100, -18, 50, -18, 51]` 经预览变成 `[-43, -28, -66, -78, -146, -77]`，L 分量都负了。
- **范围**：只有红点（LAB 颜色）这条路受影响；灰度矩形模式 `:188` 的 `binary([slider_values[:2]])` 不偏移，和保存值自洽。
- **建议改法**：让 183 和 371 用同一个表达式（要么都在预览换算，要么都在保存换算）。
- **⚠️ 改完必须重新标定红点**，因为卡上存过的红点阈值全部偏了 128。
- **状态**：待上板确认（`-128` 的换算意图是否正确，要在板上看二值化画面），未修。

<a id="p1-9"></a>
### P1-9 · 三子棋的帧率上限来自一个 `sleep`

- **位置**：`main_tic_tac_toe.py:321`（`receive_and_unpack()` 开头的 `time.sleep(0.05)`），该函数在主循环 `:1451` 每帧调用一次。
- **后果**：单这一行把系统钉在约 20 FPS，和你调什么阈值、画不画 ROI 无关。做帧率实验前必须先知道它的存在。
- **建议改法**：先确认非阻塞读（`uart.any()`）能不能替掉它；能的话帧率提升是白来的。注意 `any()` 不在官方 UART 手册的方法列表里（P3-25），换固件要先测。
- **状态**：读代码核实，未修。

---

## P2 · 特定路径抛异常，或结果错但能跑

<a id="p2-1"></a>
### P2-1 · 三子棋：悔棋检测是不可达的死代码

`stable_frames` 全程只做 `+= 1` 或 `= 0`，从不往负方向走，所以 `if stable_frames[row][col] <= -STABLE_FRAME_THRESHOLD` 恒假 —— "棋子被拿走就重置棋盘"永远不会执行。要让它生效，需要在"该格未检测到棋子"时往负方向累加，但那会改变整局行为，**必须实物复测**。状态：读代码核实，未修。

<a id="p2-2"></a>
### P2-2 · 三子棋：机器人想好了落点，但没交出去

`computer_move()`（`:812-821`）算出 `row/col`、从 `ninepoints` 取出 `x`、`y`，然后函数就结束了 —— 既没 `return` 也没发送，调用点 `:672` 也忽略返回值。它确实改了 `board`（棋局状态是对的），但执行机构不知道往哪落子。真正的坐标是在 `task6_computer_fore()` 里另算一遍的，两处 `index` 映射必须人肉保持一致。状态：读代码核实，未修。

<a id="p2-3"></a>
### P2-3 · 巡线示例的 `roi` 超出画面宽度

`01_basics/04_find_line_segments.py`：`picture_width = 400`，但 `roi = (0, 0, 480, 240)`。越界 roi 在 CanMV 上会报错。建议从分辨率变量推导，别写死。状态：读代码核实，未修。

<a id="p2-4"></a>
### P2-4 · `03_find_rectangles.py` 的显示分支是死的

`DISPLAY_MODE` 分支算好了宽高，但 `:51` 无条件 `Display.init(Display.VIRT, width=1920, height=1080)`，选 LCD / HDMI 都没用；而循环末尾的居中坐标按 `DISPLAY_WIDTH/HEIGHT`（LCD 分支写的是 480×320）算，画面会贴到 1920×1080 虚拟屏左上角。另外这块板子的 ST7701 是 800×480，同目录 `04/05/08/09/10/11/12` 的 LCD 分支都是 800×480，只有 `03` 是 480×320。状态：读代码核实，未修。

<a id="p2-5"></a>
### P2-5 · 2025 的模型部署脚本有 6 处问题（嘉楠平台导出件）

| 位置 | 问题 |
| --- | --- |
| `det_image_1_2_2.py` / `det_video_1_2_2.py` | `right = int(round(dw - 0.1))` 是复制漏改；`left == right` 使水平 padding 比 `output_size[0] - new_w` 少 1 像素 → **每个检测框坐标都带偏移**。应为 `dw + 0.1` |
| `det_image_1_3.py` / `det_video_1_3.py` | `root_path + "/deploy_config.json"`，而 `root_path` 已以 `/` 结尾 → 双斜杠 |
| `det_video_1_3.py` | 默认 `display_mode = "lt9611"`（HDMI 1080p），这块板子是 ST7701 800×480 |
| `cls_video_1_3.py:30` | 同上，默认 `"lt9611"` |
| `det_video_1_2_2.py:181` | `time.sleep(1)`，但全文没有 `import time` |
| 单图脚本 | 要的 `test.jpg` 不在仓库，两个脚本找的路径还不一样（`/sdcard/mp_deployment_source/test.jpg` vs `/sdcard/test.jpg`） |

⚠️ 这些是平台导出件，**从平台重新导出会覆盖本地补丁**。状态：读代码核实，不修。

<a id="p2-6"></a>
### P2-6 · `get_binary_threshold` 的边界值掉进错误档

三个 2025 主程序都有（`main_thresh_ui_fast.py:30`、`main_thresh_ui_accurate.py:34`、`main_multi_constraint.py:28`）：

```python
if area < 5000: ...
elif area > 5000 and area < 20000: ...   # area == 5000 时两个条件都不成立
else: return rect_binary_large
```

`area == 5000` 掉到大面积档。改成 `elif 5000 <= area < 20000:`。表现是"目标停在某个特定距离时阈值莫名跳一档"，很难查。状态：读代码核实，未修。

<a id="p2-7"></a>
### P2-7 · 电机速度用无符号格式打包

`06_practice/08_color_line_following.py`：先把速度钳到 `±1000`，再 `struct.pack('<BHH', 1, int(left_speed), int(right_speed))`。`'H'` 是无符号 16 位，PID 输出为负就 `struct.error`。

两种改法都会改线上格式，**必须和写单片机固件的人对齐**：

| 方案 | 改动 | MCU 侧 |
| --- | --- | --- |
| (a) `'<Bhh'` 有符号 | 最小 | 解析端改成有符号 |
| (b) 保持 `'H'` + 偏移 `+1000` | 稍大 | 减回 1000；所有字段保持无符号，和仓库其它帧一致 |

状态：读代码核实，未修。

<a id="p2-8"></a>
### P2-8 · 主程序里逐帧无条件打印

`08_color_line_following.py:74-75` 每帧打两行，其中一行是 `frame.hex()` 全帧转大写 —— 单个帧率杀手。`01_basics/` 里的 fps 打印是教学反馈，**不算缺陷**；要收敛的只是主程序里逐帧无条件打印的那些。状态：读代码核实，未修。

<a id="p2-9"></a>
### P2-9 · `blob_area_threshold` 被当 `pixels_threshold` 用，值是 5

`06_practice/03_nested_rect.py:132`、`:219`，`04_triangle.py:113`：

```python
blob_area_threshold = 5
red_blobs = img.find_blobs(RED_THRESHOLD, pixels_threshold=blob_area_threshold)
```

变量名写"面积"、实参是"像素数"、值是 5 —— 一坨 5 像素的噪点就能通过筛选，随后 `max(..., key=x.pixels())` 从大概率是噪声的集合里挑一个当"激光点"。同理 `rect_area_threshold = 20000` 在 `03:142` 被写成 `find_rects(threshold=int(rect_area_threshold * 1.5))`，而 `find_rects` 的 `threshold` 是矩形度评分、不是面积门槛（面积过滤是紧接着 `:147-148` 另做的）。两处都不报错，只让结果难以解释。状态：读代码核实，未修。

<a id="p2-10"></a>
### P2-10 · 两个"画图形"的脚本根本没有串口

`07_contest/laser_drawing/04_pentagram.py`、`07_ui_debug.py` 全文没有 `uart`。它们只能算路径规划演示，接不上激光打标机。按 01→07 的顺序抄到这两份，会以为"前面那些 UART 代码是可选的"。状态：读代码核实，未修。

<a id="p2-11"></a>
### P2-11 · 收包长度不一致：4 字节的协议，5 字节的读法

| 文件:行 | 读法 | 实际协议 |
| --- | --- | --- |
| `2025/.../main_thresh_ui_fast.py:483-485` | `bytearray(4)` + `readinto(4)` + `== 4` | `55 XX FF FF` = 4 字节 ✅ |
| `2025/.../main_thresh_ui_accurate.py:778-779` | `bytearray(5)` + `readinto(5)` | 4 字节 → **命令分支永远不成立** |
| `2023_E_laser/main_high_fps.py:186-187` | `bytearray(5)` + `readinto(5)` + `== 5` | 同上 |
| `2023_E_laser/k230_full.py:165-166` | 5 字节 | 同上 |

状态：读代码核实，未修。

<a id="p2-12"></a>
### P2-12 · `find_line_segments` 用关键字传参，形参名两份官方文档不一致

`06_practice/05_polygon_from_lines.py:194`、`06_practice/04_triangle.py:306`：

```python
lines = img.find_line_segments(merge_distance=20, max_theta_diff=10)
```

嘉楠 v1.3 image 手册的形参名是 `max_theta_difference`；庐山派特征检测页的官方例程却写 `max_theta_diff`。**两份官方来源互相矛盾**，所以不能断定这里必 `TypeError`。最保守的改法是改成位置传参 `find_line_segments(roi, 20, 10)`，不要猜关键字。状态：待上板确认，未修。

<a id="p2-13"></a>
### P2-13 · 三子棋的 RGB 指示灯从来没被驱动过

`main_tic_tac_toe.py:17-23` 初始化 `LED_R`(62) / `LED_G`(20) / `LED_B`(63) 并各 `high()` 一次（低电平点亮，`high` = 灭），之后全文再没有任何一处操作它们；`LED = LED_R` 是个从未被读过的死变量。"用灯色指示状态"只存在于变量名里。要接的话，挂点在 `update_board_state()` 与 `task6_computer_fore()` 末尾。状态：读代码核实，未修。

<a id="p2-14"></a>
### P2-14 · 2023 `variants/` 里 3 个文件在 `finally` 之后粘着 100–166 行死函数

| 文件 | `finally` 位置 | 文件长度 | 尾部死代码 |
| --- | --- | --- | --- |
| `variants/k230_basic_done.py` | 510 | 610 | 100 行，含 `def laser_track()`（:527） |
| `variants/k230_entry.py` | 290 | 456 | 166 行，含 `laser_rect()`（:307）、`laser_track()`（:373） |
| `variants/k230_pencil_mark.py` | 340 | 506 | 166 行，同上 |

`laser_track` / `laser_rect` 全文只出现在 `def` 行，调用次数为 0。读代码的人很容易误以为"绕框/追踪"已经接上。状态：读代码核实，未修。

<a id="p2-15"></a>
### P2-15 · 三子棋：任务 3 命令先到时 `board_angle` 未定义

`main_tic_tac_toe.py:359` 在收到 `FF 00 03 FE`（任务 3）时调用 `task3_send_angle(board_angle)`，而 `board_angle` 只在 `:1483` 识别到矩形后才赋值，模块顶部没有初始化，`receive_and_unpack()` 的 `global` 列表里也没有它。如果 MCU 在识别出棋盘之前就发任务 3，这里 `NameError`，被外层 `except` 吞掉后整程序退出。状态：读代码核实，未修。

<a id="p2-16"></a>
### P2-16 · 2023：`variants/` 与 `sample_code/` 里 5 处未定义名

| 文件:行 | 未定义的名字 | 触发条件 |
| --- | --- | --- |
| `variants/k230_basic.py:357` | `send_target_data` | 走到该分支 |
| `variants/k230_basic_variant2.py:376` | `send_target_data` | 同上 |
| `variants/k230_entry.py:97` | `uart` | 该文件用的是 `uart2`，这里是 `uart` |
| `variants/k230_pencil_mark.py:97` | `uart` | 同上 |
| `sample_code/get_square.py:79` | `light_roi` | 亚博例程，本仓库只有这一份，可能漏拷了定义 |

状态：读代码核实，未修（`sample_code` 是亚博件，不改）。

<a id="p2-17"></a>
### P2-17 · MaixPy 离线调阈值：`current_threshold_index` 未初始化

`other_boards/maixpy/offline_threshold_tuner.py`：`:30` 声明了 `global current_threshold_index`，但全文没有模块级初始化（赋值只发生在 `button_clicked()` 的分量分支 `:36-46`）。上电后第一个按下的按钮如果是 `+` 或 `-`，`:49` 就 `NameError`。作者显然想写 `current_threshold_index = None`（下面三处都在防 `None`）。状态：读代码核实，未修。

<a id="p2-18"></a>
### P2-18 · 采图脚本第 11 次按键会 `OSError`

`02_data_collection/02_capture_burst.py:89` 每次按键都 `os.mkdir(save_folder + class_lst[class_id])`，`class_id` 从 -1 开始按 10 个类别循环。第 11 次按键回到第 1 类，目录已存在 → `OSError`，被外层 `except BaseException` 捕获后程序退出。建议 `try/except OSError: pass`，或在启动时一次性建好 10 个目录。状态：读代码核实，未修。

<a id="p2-19"></a>
### P2-19 · 2025 三个主程序丢失目标时都不关激光

三个文件的 `LED.value(1/0)` 各只有两处，都在"检出矩形且距中心 < 30 px"的分支里（`main_thresh_ui_fast.py:612,615`、`main_thresh_ui_accurate.py:938,941`、`main_multi_constraint.py:420,423`）。没检出矩形时只清计数、发上一帧预测点，**不操作 GPIO48** —— 上一帧刚把激光打开的话，目标移走后它会一直亮着。

- **建议改法**：在"未检出"分支显式 `LED.value(0)`，或在每帧开头先关、命中再开。
- **状态**：读代码核实，未修。

---

## P3 · 性能、一致性、依赖

> P3 一行一条。改动收益小，但抄代码前值得知道。

<a id="p3-1"></a>
- **P3-1 · 串口协议不统一，接收端无重同步。** 10 族帧布局、4 个 STM32 工程各解析各的，详见 [docs/06](06_uart_protocol.md)。同处还有 C 解析器的三个边界缺陷：缓冲区 128 字节但 `GetLength()` 最大只报 127；写满 128 字节后 `readIndex == writeIndex`，"满"被当成"空"；`writeIndex + length < BUFFER_SIZE` 应为 `<=`。`snippets/uart_rx_tx.c` 还 `#include "command.h"`，而那份头文件只声明了 6 个函数中的 2 个，片段单独放进任何工程都编译不过。
<a id="p3-2"></a>
- **P3-2 · `deploy_config.json` 不在仓库，8 个部署脚本却都要读它。** 根 `.gitignore:13` 有一条 `deploy_config.json`，磁盘上也没有该文件。它是嘉楠平台导出件的一部分（据脚本注释与 `docs/README.pdf` 推断），但仓库里无法核实其内容。新克隆只有 kmodel、没有配置，跑单图/视频脚本会立刻失败。
<a id="p3-3"></a>
- **P3-3 · `03_ai_demos/` 需要 26 个外部资产。** 18 个 `.kmodel` + `prior_data_320.bin` + 7 个方向/手势 `.bin`，全部来自官方 SD 镜像的 `/sdcard/examples/kmodel/` 与 `/sdcard/examples/utils/`，一个都不在仓库。
<a id="p3-4"></a>
- **P3-4 · `06_practice/lvgl/` 缺资源。** `/sdcard/examples/15-LVGL/data/` 下的 `font/montserrat-16.fnt`、`font/lv_font_simsun_16_cjk.fnt`、`img/animimg001-003.png`，以及 `/sdcard/res/font/SourceHanSansSC-Normal-Min.ttf`。
<a id="p3-5"></a>
- **P3-5 · `05_cv_lite/` 两套系列已分叉。** 编号版（`01_`–`16_`）用带参 `_ex` 白平衡接口，原名版用无参版；同名算法两套 API，学生不知道该抄哪个。
<a id="p3-6"></a>
- **P3-6 · `06_practice/lvgl/first.py` 不是 LVGL 代码。** 全文没有 `import lvgl`，是两份 `draw_string_advanced` 脚本首尾拼接，后一份覆盖前一份的 `display_test` 定义，1–82 行整体成为死代码。
<a id="p3-7"></a>
- **P3-7 · `pc_tools/serial_plot_monitor.py` 三处问题。** `time_buffer.append(len(data_buffer) - 1)` 在 `deque(maxlen=200)` 填满后恒为 199，X 轴塌成一条竖线；`ax.relim()`/`autoscale_view()` 与显式 `set_xlim` 互相抵消；`'COM4'` 写死。另：它监控的发送端不在本仓库。
<a id="p3-8"></a>
- **P3-8 · `12_find_apriltag_full.py:132-141` 的焦距注释是 OpenMV OV7725 的资料。** 与 GC2093 无关，照抄会算错距离。
<a id="p3-9"></a>
- **P3-9 · 43 个文件用了 `image.` 常量却没有 `import image`。** 分布：`05_cv_lite` 19、`07_contest` 11、`01_basics` 7、`06_practice/lvgl` 4、`04` 的 `cls_image_1_3.py`、`maixpy` 1。这个名字是从 `from media.sensor import *` 顺带进来的；今天能跑，但静态检查看不出来。
<a id="p3-10"></a>
- **P3-10 · `Display.init` 的 `quality=` 三种写法并存。** `05_cv_lite` 里 `quality=100` 5 个、`quality=50` 16 个、不写 6 个。它直接决定回传 IDE 的 JPEG 质量和帧率，却没有任何说明。
<a id="p3-11"></a>
- **P3-11 · `07_rgb888_open.py` 的输入与其他形态学示例不可比。** 它 `threshold_value = 0`（Otsu 自动阈值），`05/06/08/09/10/11` 都是 100。按顺序跑会得出错误结论。
<a id="p3-12"></a>
- **P3-12 · `snippets/uart_rx_tx.c` 与 `serial_packet/Core/Src/command.c` 是同一份代码。** 只差文件末尾一个换行。改一处必须同步另一处。
<a id="p3-13"></a>
- **P3-13 · `.gitignore` 两条反向规则已指向不存在的目录。** `!Data/Number image/*.png`、`!Data/dataset/**/*.jpg` 里的 `Data/` 早已改成 `data/`。数据集现在没被忽略，纯粹因为没有任何 `*.jpg` 规则 —— 一旦有人加一条，800 张图会静默消失。
<a id="p3-14"></a>
- **P3-14 · `05_cv_lite` 其余五处一致性问题。** `rgb888_calc_histogram_1.py:23` 建了 1280×720/90fps 的 sensor，随后又设成 640×480；`rgb888_find_blobs.py:41-42` 的阈值是 `[Rmin,Rmax,Gmin,Gmax,Bmin,Bmax]`，不是 `01_basics/07` 那套 LAB；`11_rgb888_morph_gradient.py` 文件名叫 `morph_gradient`、函数叫 `rgb888_gradient`；`grayscale_find_rectangle.py` 文件名单数、函数名复数；27 个文件全用 `Display.VIRT`，接 LCD 不显示；27 个都 import 了 `Pin`/`_thread`/`ulab` 却几乎不用。
<a id="p3-15"></a>
- **P3-15 · `06_practice/01_all_in_one.py` 三处小问题。** `:462` 每帧白算一次 `find_rects()` 且结果从不被读（`img_gray`/`img_binary` 同）；`:9` `import cv_lite`、`from machine import Timer/PWM`、`ulab.numpy` 都没用到；`:192` `draw_image(..., alpha=255, roi=(...))` 里的 `roi` 不在 v1.3 手册签名里（待上板）。
<a id="p3-16"></a>
- **P3-16 · `06_practice` 五个文件互不兼容。** 串口收帧帧头三种（`01:468`、`03:315`、`04:376` 认 `0x55`；`02:170` 认 `0xAA`；`06:575` 认 `0xAA`+`0x55`），显示后端也不同（`01` 是 ST7701 800×480，`02/03/04/06` 是 VIRT）。抄的时候认准一份。另：`06_curve_recognition_WIP.py` 的三处错误（阈值匹配一切、偶数高斯核、`find_blobs` 按 LAB 传 Canny 边）互相掩盖，详见 [该目录 README](../06_practice/README.md#这里有什么)。
<a id="p3-17"></a>
- **P3-17 · `06_practice/lvgl/02_lvgl_touch.py:55`、`03_lvgl_freetype.py:77` 用了 `uctypes.addressof` 但没有 `import uctypes`。** 嘉楠官方 LVGL 例程页同样漏写，所以不能证明是笔误；先记下。
<a id="p3-18"></a>
- **P3-18 · `03_ai_demos` 三处一致性。** 17/18 个文件默认 `rgb888p_size=[1920,1080]`，对 800×480 屏是浪费；18 个文件里 `KeyboardInterrupt` 出现 0 次（Ctrl-C 被当普通异常）；`aidemo`/`aicube` 的函数签名是这批代码里最容易随固件版本变的部分。
<a id="p3-19"></a>
- **P3-19 · `02_data_collection` 三处。** `02_capture_burst.py:119` 的 FPS 覆盖层三处叠错（字符串无 `{}` 占位符、`y=768` 在 480×320 帧外、`clock` 从未使用）；`:43` `fpioa.help()` 把整颗 SoC 的引脚表打到串口；`05_data_collect.py:72` 的居中偏移按 800×480 屏算，但它的帧是 1024×768。
<a id="p3-20"></a>
- **P3-20 · `04_number_classification` 三处。** `cls_video_1_2_2.py:166` 写死判定阈值 `score >= 0.7`，OSD 和 UART 都用它、不是 `deploy_config.json`；`cls_image_1_2_2.py` 一张图读四遍（99/117/127 行各 `image.Image(...)` 一次）；`read_deploy_config()` 的 `except ValueError` 里 `config` 未赋值，失败后继续用会 `UnboundLocalError`。
<a id="p3-21"></a>
- **P3-21 · 亚博 `menu_threshold_ui/change_threshold.py` 忽略调用方传进来的阈值。** `:12` 备份了入参，`:14-17` 立刻用硬编码默认值重新绑定局部名。第三方件，不改；要用就自己抄一份改。
<a id="p3-22"></a>
- **P3-22 · `reference/` 两处。** `6，颜色识别.py`(111 行) 与 `6，颜色识别（二）.py`(120 行) 是两讲不同的课，不是重名事故；`basic_gpio/`、`image_recognition/` 的串口例程只发 8 字节裸数据，没有任何帧格式，不能当通信协议用。
<a id="p3-23"></a>
- **P3-23 · `other_boards/openmv/2023_laser/green.py:3-4` 把 `THRESHOLD_R` 连续赋值两次。** 值相同、无害，是改过忘删的痕迹。别照这个结构写多组阈值。
<a id="p3-24"></a>
- **P3-24 · `other_boards/stm32/` 里 1310 个 `.pack/` 缓存文件（约 156 MB）在版本库里。** 不影响正确性；要瘦身单独处理，别顺手 `git rm`。见 [docs/07](07_maintenance.md#8-gitignore-与仓库体积)。
<a id="p3-25"></a>
- **P3-25 · `uart.flush()`、`uart.any()`、`k_sensor_gain()` 不在官方手册的方法列表里。** 仓库里 20 多处在用 `flush()`，`02_key_switch_ui.py:167` 用 `any()`，`05_cv_lite/03`、`grayscale_find_rectangle.py` 直接调 `k_sensor_gain()`。能用 ≠ 有文档保证；换固件先测。

---

## 需要作者判定（不是 bug，也别顺手改）

| 事项 | 情况 | 为什么不能替你定 |
| --- | --- | --- |
| 三子棋任务 4 与任务 6 走同一个函数 | `task4_start` 在 `:1470` 触发 `task6_computer_fore()`，`task6_start` 在 `:1475` 触发同一个函数，全文没有 `task4_*` 专用函数 | 可能题目要求任务 4/6 相同，也可能复制漏改。只有经历过那次比赛的人知道；拆开会改变得分行为 |
| 2025 的"开始识别"应该是什么行为 | 状态 0 在识别、状态 1 空转（P1-3） | 两种改法对应两种预期：上电即识别（实验台方便）或命令驱动（比赛更稳）。先定行为，再改代码 |

## 澄清：这些**不是** bug

查官方手册后发现下面几条曾被误判。列在这里，防止后来者改错。

| 说法 | 实际 |
| --- | --- |
| "`find_line_segments(roi, merge_distance, max_theta_diff)` 参数顺序错了" | **顺序是对的。** 官方签名 `find_line_segments([roi[, merge_distance=0[, max_theta_difference=15]]])`，`roi` 就在第一位。`01_basics/04` 和 `06` 的位置传参写法正确 |
| "`find_blobs` 没有 `margin` 参数，应该写 `merge`" | `margin` **是**合法参数（在 `merge` 之后），是"色块向外扩多少像素"的整数，所以 `margin=True` 不报错（等价 1）。只是语义上作者多半想要 `merge=True` —— 这是注释错，不是崩溃 |
| "`draw_string_advanced(..., scale=)` 是非法参数" | 官方 v1.2 手册签名里没有 `scale`，但庐山派官方例程自己在用 `scale=2`。**冲突未决** → 别改，上板确认。若固件报 `TypeError`，删掉 `scale=` 即可，字号由第 3 个位置参数控制 |
| "`gaussian(2)` 偶数核必然抛异常" | CanMV 文档未明说。`06_curve_recognition_WIP.py` 里外面套了宽泛 `except`，看不到错误、只会静默返回 `None`。**待上板** |
| "`compressed_for_ide()` 该把返回值赋回 `img`" | 手册确认它**返回新对象**，所以丢弃返回值的写法确实是空操作。把 JPEG 结果再交给 `Display.show_image` 是否可行需上板确认；这行本来无害 → 保留现状 |
| "vendor 目录里的中文文件名该一起英文化" | **不要。** 立创和亚博的教程按中文编号引用这些文件，改名会切断与本仓库外部资料的对应关系 |
| "`variants/k230_basic_variant2.py` 是重复文件，删掉" | 旧名带"副本"，但和 `k230_basic.py` 差 **192 行**（105 增 / 87 删），阈值和 `send_data` 载荷都不同。不是副本 |
| "`laser_drawing/05_digits_EMPTY.py` 是垃圾，删掉" | 0 字节，从未实现。留着是为了让教程序列上的缺口**可见**，见 [docs/07](07_maintenance.md#4-刻意保留的文件真实情况) |

---

## 处理优先级

不是"修复顺序"，是"如果只能改三条，改哪三条"。改行为的每一条都必须单独上板。

1. **先让错误可见**：三个 2025 主程序和 2023 的三个主脚本，`except` 里加 `sys.print_exception(e)`。不修任何 bug，但让后面所有的都能被看见。
2. **P0-2 / P0-3 / P0-4**：机械、可核对。P0-3 已完成；P0-2 要和 MCU 侧一起定帧格式；P0-4 需要你先量一条线的灰度。
3. **P1-4 / P1-5**：一次性解决"每次都要断电"，性价比最高，但涉及 27 个厂商例程 —— 建议"另存副本再改"，不要动原文件。
4. **P1-2 / P1-8**：赛前关键（会毁掉标定），改完必须重新标定一次。
5. **P1-1 / P1-3 / P1-6 / P1-7**：都会改变行为，逐条改、逐条上板。
6. **P2-7 + P3-1**：协议统一，必须和写单片机固件的人一起定，别单方面改线上格式。
7. **P2 其余按需；P3 随手。**

## 上板验证记录

> 这张表现在是空的。每验证一条，加一行；"已上板验证"的条目要从"待上板确认"里移出来。

| 日期 | 固件版本 | 文件 | 结论 | 证据（截图/日志/串口输出） |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

# 已知问题清单

> **这份文档只归类，不修改。** 仓库里所有代码目前保持原样 —— 一行 `.py`/`.c` 都没动过。
> 每一条都给了文件、行号、症状、成因、建议改法。你想动哪条就单独改、单独上板验证。
>
> 行号已逐条 grep 核实过（基于当前 HEAD）。文件如果被改过，请先重新定位再动手。

## 严重程度定义

| 级别 | 含义 |
| --- | --- |
| **P0** | 一执行就崩，或该功能从来没通过 |
| **P1** | 静默毁掉你的工作 / 每次都要断电重启 |
| **P2** | 结果错但能跑 |
| **P3** | 性能、文档、一致性 |

---

## P0-1 · `07_contest/2024_E_tic_tac_toe/main_tic_tac_toe.py` 缺 `import os`

**这一条单独看，因为它意味着一个 1500 行的"成品"其实从未运行过。**

- **位置**：全文只 `import math` / `import struct` / `import time` 和 `from media.* import *`；
  但 **第 1446 行** `os.exitpoint()`（主循环内）、**第 1498 行** `os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)`（finally 内）
- **症状**：第一次进主循环就 `NameError: name 'os' not defined`
- **成因**：`media.*` 的星号导入不提供 `os`。写的时候大概是照着别的模板抄了 `os.exitpoint()` 却漏了导入
- **改法**：文件开头加 `import os`
- **连带影响**：这个文件里的另外两处死代码（P2-1、P2-2）之所以一年都没被发现，就是因为根本跑不到那里

## P0-2 · 10 处 `struct.pack` 格式串与参数个数不匹配

**后果：`send_data()` 一被调用就抛 `struct.error`。也就是说这些脚本的整条串口输出链路从来没有通过。**

| 文件 | 行 | 格式串 | 需要 | 实给 |
| --- | --- | --- | --- | --- |
| `06_practice/01_all_in_one.py` | 64 | `'<BHHHH'` | 5 | 3 |
| `06_practice/02_key_switch_ui.py` | 69 | `'<BHHHH'` | 5 | 3 |
| `06_practice/03_nested_rect.py` | 67 | `'<BHHHH'` | 5 | 3 |
| `06_practice/04_triangle.py` | 70 | `'<BHHHH'` | 5 | 3 |
| `07_contest/2023_E_laser/k230_full.py` | 59, 66 | `'<BHHHH'` | 5 | 3 |
| `07_contest/laser_drawing/02_triangle_exposure.py` | 61, 70, 75 | `'<BHHHH'` | 5 | 3 |
| `07_contest/laser_drawing/02_triangle_exposure.py` | 81 | `'<BHHHHH'` | 6 | 5 |

- **成因**：想发的是 `type + x + y` 三字段，格式串却多写了两个 `H`
- **建议改法**：**收窄格式串**（`'<BHHHH'` → `'<BHH'`），**不要**补零凑参数。
  补零会静默改变单片机解析的线上格式；收窄才符合作者本意，也和仓库里本来就正确的
  30 处 `'<BHH'` 一致（`'<BHH'` 是这个仓库事实上的标准帧）
- **自查命令**：这是可机械检查的。全仓库扫一遍只要比较"格式项数"和"实参个数"

## P0-3 · `Sensor()` 关键字拼错，文件根本无法启动

| 文件 | 行 | 现状 | 应为 |
| --- | --- | --- | --- |
| `01_basics/01_camera_open.py` | 13 | `Sensor(channe = sensor_id)` | `Sensor(id=sensor_id)` |
| `02_data_collection/03_uart_test.py` | 33 | `Sensor(wihth = picture_width, ...)` | `Sensor(width = picture_width, ...)` |

症状：`TypeError`。第二个还连带 `02_data_collection/` 整个目录跑不动。

## P0-4 · `01_basics/11_line_following.py:63` `THRESHOLD = D(90, 23)`

`D` 未定义 → `NameError`，脚本启动即崩。应为 `THRESHOLD = (90, 23)`。

**同文件另外两个问题**：第 64 行又无条件调了一次 `Display.init(Display.ST7701, ...)`，
把上面按 `DISPLAY_MODE` 分支做的初始化覆盖掉（选 VIRT/HDMI 无效）；
`BINARY_VISIBLE` 定义了两次。

## P0-5 · 3 个文件语法不过（都在归档目录，不影响主线）

| 文件 | 行 | 症状 |
| --- | --- | --- |
| `07_contest/2024_E_tic_tac_toe/skeleton_incomplete.py` | 184 | `def receive_and_unpack():` 函数体为空 → `expected an indented block` |
| `07_contest/2023_E_laser/error/error2.py` | 375 | f-string 里空的 `{}` + 裸 `str()` |
| `07_contest/2023_E_laser/error/error3.py` | 369 | 同上 |

`skeleton_incomplete.py` 是**未完成骨架**（主循环只剩 snapshot→show，三子棋逻辑都不在里面）；
`error2/3` 是失败尝试，那两处的表达式被删空了。**不要凭猜补实现** ——
可用版本分别是 `main_tic_tac_toe.py` 和 `2023_E_laser/` 下的三个主脚本。

## P0-6 · 平台不对的文件（已经隔离，列在这里是为了别被误抄）

| 文件 | 判据 | 在本仓库的哪里 |
| --- | --- | --- |
| `other_boards/maixpy/offline_threshold_tuner.py` | `from maix import ...` | MaixPy / MaixCAM，CanMV 上第一行 import 就失败 |
| `other_boards/openmv/2023_laser/{green,red}.py` | `from pyb import UART` | OpenMV，K230 没有 `pyb` |
| `other_boards/openmv/nuedc_2025_e/`（3 个文件） | 同上 | 别人的 OpenMV4 版 2025 E 题方案 |

K230 侧的等价实现：`other_boards/maixpy/` 那个功能已经存在于
`06_practice/01_all_in_one.py` 的 `handle_threshold_adjustment()`。

---

## P1-1 · 2025 三个主程序里，有一个同名功能从未执行过

**文件**：`07_contest/2025_E_self_aiming/result/main_multi_constraint.py:86`

```python
outer_points = outer_blob.min_corners()   # 第 81 行
if len(outer_points) < 4: continue        # 第 82 行
if len(outer_points) != 8: continue       # 第 86 行 ← 恒真
```

- **成因**：`min_corners()` 返回的是**最小外接矩形**，按定义恒为 4 个点，永远不可能等于 8。
  注释说"只有 8 个顶点才是目标矩形"，这个判断在任何阈值下都表达不了它的意图
- **后果**：每一轮都 `continue` → `find_nested_rects()` 每帧返回 `None` →
  整个"多限制条件"（外框套内框抗干扰）从未生效，每帧都退回到和 `main_thresh_ui_fast.py`
  一样的 `find_best_rect()`。文件名和实际行为不符
- **真正的判据在下一段**：`area_ratio = outer_area / outer_blob.area()` 配 `>= 1.5`
  ——空心双层框的外接面积远大于像素面积，这个区分是站得住的
- **改法**：删掉第 84–87 行这个恒真门，让 `area_ratio` 生效
- ⚠️ **必须上板验证**：这条路径在仓库历史上一次都没跑过。外层对按面积排序的 blobs 是
  O(n²)，此前一直在第一轮短路退出，现在才真正付这个代价（预期帧率下降）；
  而且 `find_nested_rects()` 首次返回非 None 后，下游从未执行过的代码路径会开始跑

## P1-2 · 触摸调参 UI 会**毁掉**你标定好的阈值

**文件**：`result/main_thresh_ui_fast.py` 与 `main_thresh_ui_accurate.py`（两份各一份）

`init_slider_values(mode)` 有两个问题叠加：

1. **形参 `mode` 从未被使用**，函数体读的是全局 `threshold_mode`；而调用点传的是
   `current_mode`，它的值是字符串常量 `'gray_rect'`
2. **三个返回值是写死的**，和本文件真正的默认值 `rect_binary_default/_small/_large` 不一致，
   并且**两个文件之间也已经分叉**（大面积档一份是 `[75,200]`，一份是 `[85,200]`）

- **后果**：一进阈值界面，滑块就跳到一组你没设过的数值；这时按"保存"，
  就把你在赛场光照下调好的阈值静默覆盖掉了 —— **这恰好是这个功能被造出来要避免的那类事故**
- **改法**：让 `init_slider_values` 真正使用 `mode`，并直接从 `rect_binary_default/_small/_large`
  读取（单一数据源），调用点改传 `threshold_mode`
- ⚠️ 改这条会牵动 `global threshold_mode` 的声明位置：`global` 必须出现在该作用域
  **首次使用之前**，否则从"只读"变成"先读后声明"，`compile()` 会报
  `SyntaxError: name 'threshold_mode' is used prior to global declaration`。
  把它上移到函数开头，并删掉循环里那份重复声明

另外同一 UI 还有两处小问题：左侧预览把 400×240 的帧不缩放直接画进 400×480 半屏（下半屏空白）；
`TOUCH(0)` 每次进 UI 都重新初始化且从不 deinit。

## P1-3 · `Situation == 1` 是死状态（两个主程序）

**位置**：`main_thresh_ui_fast.py:502`、`main_thresh_ui_accurate.py:793`

三个文件的第 469 / 760 行注释都写着 `0:未初始化, 1:开始识别, 2:停止识别, 3:阈值调节`，
而 STM32 发来的 `55 01 FF FF` 确实把 `Situation` 置成 1。
但分派链只有 `if == 0 / elif == 2 / elif == 3 / else: pass` ——
**"开始识别"这条正式命令掉进了什么都不做的 `else`**，反而是开机状态 0 在识别。

- **对照**：祖先版本 `07_contest/2023_E_laser/main_high_fps.py` 判的就是 `== 1`，可以看看这条链是怎么在复制中变形的
- **改法**：`if Situation in (0, 1):`。同时接受两者，既让命令生效，又保留"开机即识别"
  （不接 MCU 也能在实验台上单独调）
- ⚠️ 别"顺手清理"成只判 `== 1`，那会毁掉离线调试

## P1-4 · 27 个 cv_lite 示例缺 `try/finally` 与循环内 `os.exitpoint()`

**范围**：`05_cv_lite/` 全部 27 个文件。核实方法：`grep -c "try:" 05_cv_lite/**/*.py` → 全为 0。

- **症状**：文件末尾的 `sensor.stop()` / `Display.deinit()` / `MediaManager.deinit()`
  位于裸 `while True:` **之后**，永远执行不到 —— 是死代码；
  循环内也没有裸 `os.exitpoint()`，所以 **IDE 的停止按钮无效**
- **合起来的后果**：每次中断程序后媒体缓冲区不释放，**必须给板子断电重启**才能再跑。
  这是本仓库最劝退的一条
- **改法**（每个文件两处）：
  1. 在 `while True:` 的**第一条语句**位置插入 `os.exitpoint()`
  2. 用 `try:` 包住主循环，把尾部清理代码缩进进 `finally:`
  3. ⚠️ 尾部已有的 `os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)` **要保留** —— 它和循环里那个裸调用是两回事，
     机械地"加个 exitpoint"会把它重复一遍

## P1-5 · 三个文件的 `finally:` 被截断，缺 `MediaManager.deinit()`

| 文件 | 现状 |
| --- | --- |
| `01_basics/02_drawing.py` | `finally` 块停在注释 `# 释放媒体缓冲区`，后面的调用没写 |
| `02_data_collection/02_capture_burst.py` | 同上，且那句注释写的是 `# 释放媒体缓冲区(自动处理)` |
| `02_data_collection/03_uart_test.py` | 只 deinit 了 Display，没有 MediaManager |

**后果同 P1-4：跑一次就得断电。** `02_capture_burst.py` 里那句"（自动处理）"是假的 ——
正是这句注释让这个缺失一直没人怀疑。改的时候把注释一起改掉。

## P1-6 · 2025 高精版有三处必崩，且被异常处理掩盖

**文件**：`result/main_thresh_ui_accurate.py`（987 行，三个主程序里最大的一个）

| 位置 | 问题 |
| --- | --- |
| 第 14 行 | `import cv_lite`，而 `cv_lite` 不在本仓库（庐山派固件提供）。缺了就 `ImportError` |
| 约 678–693 行 | 兜底用的 `RectLike` 类**没有 `corners()` 方法**，但第 **829、843** 行无条件调 `max_rect.corners()` → `AttributeError` |
| 第 950 行附近 | `matrix` 只在 `len(corners)==4` 分支内赋值，却在每帧末尾无条件读 → 非四边形那帧 `NameError`，否则显示上一帧的旧状态 |

- **三处都藏在同一个根因后面**：文件末尾 `except BaseException as e: print(f"异常: {e}")`
  只打印一行文字、不带 traceback，所以程序**静默退出**，看起来像"跑一下就没了"
- **最重要的改法是先改这里**：加 `sys.print_exception(e)`。
  不加这条，这个目录里下一个同类 bug 仍然会这样隐身。（三个主程序都该加）

## P1-7 · 2023 那套在"追踪成功"那一刻崩

**文件**：`07_contest/2023_E_laser/k230_full.py`

- **第 411–414 行**：`beep_pwm.freq(1000)` / `.enable(True)` / `.enable(False)`，
  但 `beep_pwm` **全文件从未实例化**（第 16 行 import 了 `PWM` 却没有任何 `PWM(...)`）
  → 恰好在"追踪完成、距离≤3cm"那一刻 `NameError`，也就是**唯一会被判分的那一刻**
- **改法**：要么补上蜂鸣器实例化，要么注释掉这三行。
  **别猜引脚** —— 这块板子的蜂鸣器脚位在本仓库的代码和文档里都没有记录，
  PWM 通道填错有可能把输出打到激光（GPIO48）或云台轴上
- **第 359 行**：`img.find_blobs(Red_thresholds)`，而本文件定义的名字是
  **`RED_THRESHOLD`**（第 26 行，且第 187/200/234 行用的都是它）→ 大小写笔误，走到就 `NameError`

---

## P2-1 · 三子棋：悔棋检测是不可达的死代码

`main_tic_tac_toe.py`：`stable_frames` 全程只做 `+= 1` 或 `= 0`，从不往负方向走，
所以 `if stable_frames[row][col] <= -STABLE_FRAME_THRESHOLD` 恒假 ——
"棋子被拿走就重置棋盘"这段永远不会执行。
要让它生效需要在"该格未检测到棋子"时把计数往负方向累加，但那会改变整局对弈行为，**必须实物复测**。

## P2-2 · 三子棋：机器人想好了落点，但没交出去

`main_tic_tac_toe.py` 的 `computer_move()`（第 817 行起）算出 `row/col` 后
从 `ninepoints` 取出 `x`、`y`，然后**函数就结束了** —— 既没 `return` 也没发送，
调用点（第 672 行）也忽略返回值。它确实改了 `board`（所以棋局状态是对的），
但执行机构不知道要往哪落子。

## P2-3 · 巡线的 `roi` 超出画面宽度

`01_basics/04_find_line_segments.py`：`picture_width = 400`，但 `roi = (0, 0, 480, 240)`。
CanMV 对越界 roi 会报错。建议直接从分辨率变量推导，别写死。

## P2-4 · `01_basics/03_find_rectangles.py` 的显示分支是死的

`DISPLAY_MODE` 分支算好了宽高，但第 51 行无条件执行
`Display.init(Display.VIRT, width=1920, height=1080, to_ide=True)`，
于是选 LCD / HDMI 都没用；而循环末尾的居中坐标按 `DISPLAY_WIDTH/HEIGHT`（LCD 分支是 480×320）
计算，画面会跑到 1920×1080 虚拟屏左上角。
另外 LCD 分支的 480×320 是另一块 3.1 寸屏的参数，**这块板子的 ST7701 是 800×480**。
同目录 `04_find_line_segments.py` 的写法是对的，可以对照。

## P2-5 · letterbox padding 少一像素，检测框整体偏移

`07_contest/2025_E_self_aiming/find_rect/`：

- `det_image_1_2_2.py` / `det_video_1_2_2.py`：`right = int(round(dw - 0.1))`
  是从上一行 `left` 复制粘贴漏改的。`left == right` 使水平总 padding 比
  `output_size[0] - new_w` **少 1 像素**，送进 `ai2d.set_pad_param` 的图比模型输入窄 1 像素
  → **每一个检测框坐标都带偏移**。应为 `dw + 0.1`，与 `bottom = dh + 0.1` 对称
- `det_image_1_3.py` / `det_video_1_3.py`：`root_path + "/deploy_config.json"`，
  而 `root_path` 已经以 `/` 结尾 → 拼出双斜杠
- `det_video_1_3.py`：默认 `display_mode = "lt9611"`（HDMI 1080p），
  而同目录 v1.2.2 脚本和**这块板子本身**都是 ST7701 800×480
- `det_video_1_2_2.py`：第 185 行 `time.sleep(1)`，但全文**没有 `import time`**
- 单图脚本要的 `test.jpg` **不在仓库里**，而且两个脚本找的路径不一样：
  `det_image_1_2_2.py` 读 `/sdcard/mp_deployment_source/test.jpg`，
  `det_image_1_3.py` 读 `/sdcard/test.jpg`。别只拷一份

⚠️ 这些是嘉楠在线平台导出的脚本，**从平台重新导出会覆盖你的本地补丁**。

## P2-6 · `get_binary_threshold` 的边界值掉进错误的档

三个 2025 主程序都有（`main_thresh_ui_fast.py:30`、`main_thresh_ui_accurate.py:34`、
`main_multi_constraint.py:28`）：

```python
if area < 5000: ...
elif area > 5000 and area < 20000: ...   # area 正好 5000 时两个条件都不成立
else: return rect_binary_large
```

`area == 5000` 会掉到大面积档。改成 `elif 5000 <= area < 20000:`。
实时系统里的表现是"目标停在某个特定距离时阈值莫名跳一档"，很难查。

## P2-7 · 电机速度用无符号格式打包

`06_practice/08_color_line_following.py`：先把速度钳到 `±1000`，再
`struct.pack('<BHH', 1, int(left_speed), int(right_speed))`。
`'H'` 是**无符号** 16 位，而 PID 输出很容易为负 → `struct.error`。

两种改法都会改变线上格式，**必须和写单片机固件的人对齐**：

| 方案 | 代码改动 | MCU 侧 |
| --- | --- | --- |
| (a) 改 `'<Bhh'` 有符号 | 最小 | 解析端要改成有符号 |
| (b) 保持 `'H'` + 偏移 `+1000` | 稍大 | 减回 1000 即可；**所有字段保持无符号**，和仓库其它帧格式一致 |

倾向 (b)，但它要求对端配合，不能单方面发货。

## P2-8 · 27 个文件每帧 `print`，个别还打整帧 hex dump

`06_practice/08_color_line_following.py` 每帧打两行、含 `frame.hex()` 全帧转大写 ——
这是全仓库最严重的单个帧率杀手。`01_basics/` 里几个示例每帧打 fps。
另外 `03_ai_demos/` 部分文件每帧 `gc.collect()`。

⚠️ 但**教学目录里的 print 不全是 bug**：在 `01_basics/` 它是有意的反馈。
只该收敛主程序里逐帧无条件打印的那些。

---

## P3 · 一致性与文档

1. **仓库里有 4 套互不兼容的串口帧格式**，而且**没有任何一处做字节流重同步**。
   所有接收路径都是 `n = uart.readinto(buf, N); if n == N: 校验` ——
   丢一个字节，之后每一次读都在解析错位数据，**永远不会自愈**。
   现象是"识别偶尔不对"，是最难查的一类故障。
   | 格式 | 谁在用 |
   | --- | --- |
   | `AA + type:B + x:H + y:H + 55`（7 字节） | 事实标准，30 处。2025 主程序、`06_practice/08` |
   | `55 + XX + FF + FF`（4 字节，下行命令） | 2025 主程序接收侧（`Rxbuf[0]==0x55`）|
   | `AA + len + payload + checksum` | `other_boards/stm32/snippets/uart_rx_tx.c` |
   | 收 5 字节但注释说 4 字节 | `main_thresh_ui_accurate.py`、`2023_E_laser/main_high_fps.py` |

   ⚠️ 那个 C 解析器会**丢弃 `06_practice/` 发出的每一帧**。
   还有 `uart_rx_tx.c` 自身：`#include "command.h"` 在本仓库不存在；环形缓冲 off-by-one
   （`GetLength` 满时只报 127/128；`GetRemain` 空时返回 128，于是写满 128 字节会让
   `read==write`、"满"被当成"空"、数据全丢）；边界 `< BUFFER_SIZE` 应为 `<=`。

2. **根 README 此前有两处虚假声明**（本次已改）：声称 2021 年有整理资料（该目录一直是空的）；
   声称三个 2025 主程序"经过调试、可以直接运行"。

3. **`.gitignore` 把 `deploy_config.json` 排除在版本控制外**，所以新克隆只拿到 kmodel、
   拿不到旁边的配置，而部署脚本读 `root_path + "/deploy_config.json"` → 立刻失败。
   修法：删掉那条 ignore 规则或 `git add -f` 两份配置。
   同文件里 `det_results/`、`cls_results/` 也被忽略，而 `det_results/` 那 35 张图是检测器
   真跑过的唯一物证，值得入库。

4. **`03_ai_demos/` 需要 26 个外部资产**，一个都不在仓库（18 个 `.kmodel` +
   `prior_data_320.bin` + 7 个方向/手势图标 `.bin`），来自官方 CanMV SD 镜像的
   `/sdcard/examples/kmodel/` 与 `/sdcard/examples/utils/`。

5. **`06_practice/lvgl/` 缺资源**：`/sdcard/examples/15-LVGL/data/` 下的
   `font/montserrat-16.fnt`、`font/lv_font_simsun_16_cjk.fnt`、`img/animimg001-003.png`，
   以及 `/sdcard/res/font/SourceHanSansSC-Normal-Min.ttf`。

6. **`05_cv_lite/` 两套系列已分叉**（编号版用带参 `_ex` 白平衡接口，命名版用无参版），
   同名算法两套 API，学生会不知道该抄哪个。

7. **`06_practice/lvgl/first.py` 不是 LVGL 代码**，而且是两份脚本首尾拼接、
   后一份覆盖前一份的 `display_test` 定义。

8. **`pc_tools/serial_plot_monitor.py`**：`time_buffer.append(len(data_buffer) - 1)`
   在 `deque(maxlen=200)` 填满后恒为 199，X 轴全部塌到一个点；
   `ax.relim()`/`autoscale_view()` 和显式 `set_xlim` 互相抵消，滑窗不生效；`'COM4'` 写死。
   而且**它监控的那个发送端不在本仓库**（K230 没有用户可用 ADC，模拟量必然来自外部 MCU）。

9. **`01_basics/12_find_apriltag_full.py` 尾部关于焦距 fx/fy 的注释是 OpenMV OV7725 的资料**，
   和这块板子的 GC2093 无关，照抄会算错距离。

---

## 澄清：这些**不是** bug，别去"修"

查官方 API 手册后发现下面几条曾被误判。列在这里防止后来者改错。

| 说法 | 实际 |
| --- | --- |
| "`find_line_segments(roi, merge_distance, max_theta_diff)` 参数顺序错了" | **顺序是对的。** 官方签名 `find_line_segments([roi[, merge_distance=0[, max_theta_difference=15]]])`，roi 就在第一位。`01_basics/04` 和 `06` 的写法以及那句教学注释都正确 |
| "`find_blobs` 没有 `margin` 参数，应该写 `merge`" | `margin` **是**合法参数（在 `merge` 之后），是"色块向外扩多少像素"的整数，所以 `margin=True` 不报错（等价 1）。只是语义上作者多半想要 `merge=True` —— 这是**注释写错了**，不是崩溃 |
| "`draw_string_advanced(..., scale=)` 是非法参数" | 官方 v1.2 手册的签名里没有 `scale`，**但庐山派官方例程自己在用 `scale=2`**。冲突未决 → 别改，上板确认。若你的固件报 `TypeError`，删掉 `scale=` 即可，字号由第 3 个位置参数控制 |
| "`gaussian(2)` 偶数核必然抛异常" | CanMV 文档未明说。在 `06_practice/06_curve_recognition_WIP.py` 里它外面套了宽泛 `except`，所以看不到错误、只会静默返回 None。标为待实测 |
| "`compressed_for_ide()` 该把返回值赋回 img" | 手册确认它**返回新对象**，所以丢弃返回值的写法确实是空操作。但把 JPEG 结果再交给 `Display.show_image` 是否可行需上板确认，而这行本来无害 → 保留现状 |
| "vendor 目录里的中文文件名该一起英文化" | **不要。** 立创和亚博的教程按中文编号引用这些文件，改名会切断与本仓库外部资料的对应关系 |
| "`variants/k230_basic_variant2.py` 是重复文件，删掉" | 它的前身名字叫"副本"，但和 `k230_basic.py` **差约 236 行**（阈值和 send_data 载荷都不同）。不是副本 |
| `laser_drawing/05_digits_EMPTY.py` 是垃圾，删掉 | 0 字节，从未实现。留着是为了让教程序列上的缺口**可见** |

---

## 如果要开始修，建议的顺序

1. **`P0-1` 三子棋补 `import os`** —— 一行，且是"这个文件能不能跑"的开关
2. **`P0-2` 十个 `struct.pack`** —— 机械、可自动核对，改完串口链路才第一次真正存在
3. **`P0-3/P0-4` 三个 typo** —— 各一行
4. **`P1-4/P1-5` 生命周期** —— 一次性解决"每次都要断电"，性价比最高
5. **`P1-6` 先加 `sys.print_exception`** —— 它不修任何 bug，但让剩下所有的都能被看见
6. `P1-2` UI 覆盖阈值（赛前关键）、`P1-3` 死状态、`P1-1` 恒真门 —— 这三个都会改变运行行为，逐个改、逐个上板
7. `P2-*` 按需
8. `P2-7`、以及串口协议统一 —— **要和 MCU 侧一起定**，别单方面改线上格式

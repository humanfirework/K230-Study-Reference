# laser_drawing — 激光/振镜画图形（非赛题，练手与演示用）

## 这是什么

一组「让激光点（或云台指针）在识别到的矩形区域内沿矢量路径移动、把图形'画'出来」的程序：三角形、带曝光压制的三角形、圆、五角星、贝塞尔曲线，外加一个 LVGL 触摸调参界面和一份纯浏览器的 UI 仿真页。

技术上它是 2023 E 题追踪链路的另一个方向：追踪是"让激光**追**目标"，这里是"让激光**按预定轨迹走**"，两者共用同一套硬件（K230 视觉 + UART2 出坐标 + STM32 驱动两轴）与同一套骨架（找最大矩形 → 在矩形里生成路径点 → 逐点发送 → 判断到位）。

> 这个目录**以前没有被任何 README 提过**（旧版 `07_contest/README.md` 完全没写它）。它的旧名是 `电赛赛题K230/绘制图像/`，在 `89e6ffc` 改名为 `07_contest/laser_drawing/`。

## 题目 PDF

不适用 —— 本目录不对应某一年的赛题。要回到赛题语境，看 [`../2023_E_laser/README.md`](../2023_E_laser/README.md) 的"基础部分：绕矩形轨迹走"。

## 代码文件清单

| 文件 | 行数 | 大小 | 作用 | 状态 |
|---|---:|---:|---|---|
| `01_triangle.py` | 318 | 12,309 B | 等边三角形：`draw_equilateral_triangle()` 顶点朝上算三点，`generate_triangle_path_points(…, interpolation_steps=20)` 沿三条边插值成路径点，逐点 `send_data(x,y)`；边长取 `min(rect_width, rect_height) // 2` | 可用 |
| `02_triangle_exposure.py` | 351 | 13,155 B | 同上，但每帧先做**手动曝光压制**：`exposure_gain = 0.5`（注释给出推荐范围 0.2~3.0），用 `cv_lite.rgb888_adjust_exposure([h, w], img_np, exposure_gain)` 压暗，为了在强光下把激光点从背景里分出来。**依赖 `cv_lite`（本仓库没有）**，且含 4 处 `struct.pack` 参数错误 | **不完整**（缺依赖 + 4 处必抛异常） |
| `03_circle.py` | 294 | 11,844 B | 圆：`generate_circle_path_points(cx, cy, r, interpolation_steps=60)` 用 `cos/sin` 均匀取点，半径 `min(w,h) // 4`（第 189 行），绘制时另用 `interpolation_steps=100` | 可用 |
| `04_pentagram.py` | 247 | 11,440 B | ⚠️ **架构与其余全部不同**：不经 STM32、不发 UART，K230 用 `from machine import PWM, FPIOA, Pin` **直接 PWM 打两轴舵机云台**（X=GPIO42/PWM0，Y=GPIO52/PWM4，`SERVO_FREQ_HZ = 50`），自带 `PD_Controller`（`Kp = Kd = 0.00001`）与状态机 `STATE_SEARCHING_RECT → …`；`calculate_star_path(rect)` 以 −90° 起、每次 72° 取 5 个顶点，再按笔画顺序 `[0,2,4,1,3]` 返回 | 可用（需外接舵机云台，与 01/03/06 不是同一套硬件） |
| `05_digits_EMPTY.py` | **0** | **0 B** | **空文件。** 旧名 `绘制图像/4.绘制数字.py` —— 教程里那一节存在，代码从来没写。改名时特意在文件名里挂上 `_EMPTY`，把"这是序列里的一个洞"写在脸上 | **不完整（占位，从未实现）** |
| `06_bezier.py` | 359 | 13,403 B | 贝塞尔：`bezier_quadratic(p0,p1,p2,t)` / `bezier_cubic(p0,p1,p2,p3,t)` 两个求值器，`generate_heart_bezier_path()`（倒立爱心，4 段三次曲线）、`generate_s_bezier_path()`、`generate_sine_bezier_path(…, cycles=2)` 三种图案 | 可用 |
| `07_ui_debug.py` | 300 | 11,454 B | **LVGL 图形界面版**：`import lvgl as lv` + `uctypes`，手写 `disp_drv_flush_cb` 与 `touch` 输入驱动，把 `camera_init()` / `color_tracking()` / `rect_detection()` 组织成 LVGL 页面。**全文没有任何 `uart.write`** —— 它是调参/演示壳，不发控制帧 | 可用（需 LVGL 支持，见 `../../06_practice/lvgl/`） |
| `ui_simulation.html` | 728 | 28,374 B | `07_ui_debug.py` 那个界面的**浏览器仿真版**（`<title>K230 UI界面仿真</title>`）。双击用 Chrome/Edge 打开即可，纯前端、无外部依赖、不需要网络 | 仅浏览器，**不可上板** |

## 为什么 5 个画图程序留着 5 份，而不是抽成一个公共模块

**这是有意的，不要"顺手合并"。**

实测重复度（`git diff --no-index --numstat`）：

| 对比 | 增 / 删 | 共同行数占前者 |
|---|---|---:|
| `01_triangle.py` ↔ `02_triangle_exposure.py` | +71 / −38 | **88%** |
| `01_triangle.py` ↔ `03_circle.py` | +59 / −83 | **74%** |
| `01_triangle.py` ↔ `06_bezier.py` | +167 / −126 | **60%** |

也就是说骨架（硬件初始化、`find_max_Rect()`、`find_laser_point()`、`distance()`、三个 `send_*`、主循环的"到位判定 + 逐点推进"）**确实是复制粘贴的**，真正不同的只有中间那一小块路径生成器。

保留 5 份的理由（对比赛场景是实打实的）：

1. **每个文件都是一个能单独丢上板子就跑的完整单元。** 赛场上你要换图形，是整份文件拷过去，不是带着一堆模块去找 import 关系。
2. **它们的依赖不同，合并会把轻量版拖重。** `01/03/06` 只用 `machine` + `media`；`02` 多 `import cv_lite` + `import ulab.numpy` 和 `gc`；`04` 换成 `PWM` 直驱、**完全没有 UART**；`07` 是 LVGL + uctypes。抽公共模块的话，"我只想要一个能画三角形的最小脚本"这件事就没了。
3. **`02` 的那 4 处 `struct.pack` 错误恰好证明复制的代价**，但它是**教学材料而不是待修 bug**（见下面「已知问题」）—— 你从 01 复制改出 05 的时候，很容易把字段数和实参数改错，而 Python **只有真正调用到那一行才报错**。把 5 份留着，就是把这个教训留在原地。

**实际不同的东西，一张表说完：**

| 文件 | 路径生成 | 出帧方式 | 特殊依赖 |
|---|---|---|---|
| `01_triangle` | 3 顶点 + 边插值 20 步 | `AA\|<BHH>\|x\|y\|55`(7B)、`AA\|<BHHHHHHHHHH>\|4 角点+中心\|55`(23B)、`AA\|<BHHHH>\|laser+target\|55`(11B) | 无 |
| `02_triangle_exposure` | 同 01 | 同 01 的三种格式，但**参数个数全错** | `cv_lite`、`ulab.numpy`、`gc` |
| `03_circle` | 60/100 步均匀圆周采样 | 同 01 | 无 |
| `04_pentagram` | 5 顶点 × 笔画序 `[0,2,4,1,3]` | **不发帧**，PWM 脉宽直写舵机 | `PWM` 云台硬件 |
| `06_bezier` | 二/三次贝塞尔求值，爱心/S 形/正弦三种 | 同 01 | 无 |
| `07_ui_debug` | 无（只做识别与显示） | **不发帧** | `lvgl`、`uctypes`、`TOUCH` |

## 旧名 → 新名

`89e6ffc`：`电赛赛题K230/绘制图像/` → `07_contest/laser_drawing/`，并按 tutorial 顺序统一 `NN_英文语义.py` 前缀。本目录**没有**参与 `28b5f40`（没有非 K230 文件）。

| 旧名 | 新名 |
|---|---|
| `绘制图像/` | `laser_drawing/` |
| `绘制图像/1.画三角形.py` | `01_triangle.py` |
| `绘制图像/1.画三角形（调整曝光后）.py` | `02_triangle_exposure.py` |
| `绘制图像/2.绘制圆形.py` | `03_circle.py` |
| `绘制图像/3.五角星.py` | `04_pentagram.py` |
| `绘制图像/4.绘制数字.py` | `05_digits_EMPTY.py`（**0 字节**，`_EMPTY` 是改名时加的标记，原文件名不体现它是空的） |
| `绘制图像/5.贝塞尔曲线.py` | `06_bezier.py` |
| `绘制图像/6,UI界面调试.py` | `07_ui_debug.py`（旧名里那个逗号 `6,` 是笔误） |
| `绘制图像/ui_simulation.html` | `ui_simulation.html`（不改） |

注意新旧序号**不对应**：旧编号 `1,1,2,3,4,5,6` → 新编号 `01,02,03,04,05,06,07`。旧的两个"1"是同一次实验的两个版本，新编号把它们拆成 01/02。别拿旧编号去对新文件名。

## 已知问题（全部实测）

1. **`02_triangle_exposure.py` 有 4 处 `struct.pack` 格式串与实参个数不匹配 —— 每一处被调用就抛异常。**

   | 行 | 代码 | 格式要几个 / 实到几个 |
   |---|---|---|
   | 61 | `struct.pack('<BHHHH', 1, x, y)` | 5 / 3 |
   | 70 | `struct.pack('<BHHHH', 10+i, x, y)` | 5 / 3 |
   | 75 | `struct.pack('<BHHHH', 15, center[0], center[1])` | 5 / 3 |
   | 81 | `struct.pack('<BHHHHH', 20, laser_x, laser_y, target_x, target_y)` | 6 / 5 |

   实测异常文本：`struct.error: pack expected 5 items for packing (got 3)` 与 `pack expected 6 items for packing (got 5)`。
   对照：`01_triangle.py` 的**同名三个函数**是对的（第 58 行 `<BHH` 3 参、第 70 行 `<BHHHHHHHHHH` 11 参、第 89 行 `<BHHHH` 5 参）—— 所以这是 02 从 01 复制后改格式串、忘了同步实参的典型事故。**`02` 里所有对外发帧路径都会炸，它只能当"纯视觉演示"看，不能进控制系统。** 注意 `01/03/06` 三个文件里的 `<BHHHHHHHHHH`（11 字段 11 实参）和 `<BHHHH`（5/5）都是正确的，别误伤。
2. **`02_triangle_exposure.py` 需要 `cv_lite`（本仓库没有）。** 第 11 行 `import cv_lite`、第 214 行 `cv_lite.rgb888_adjust_exposure(...)`。该模块由庐山派固件/SD 镜像提供；板上是否可用，在 IDE 终端里执行一次 `import cv_lite` 就知道。缺它则这个文件在第一行就 ImportError，问题 1 反而永远碰不到。
3. **`05_digits_EMPTY.py` 是 0 字节空文件。** `wc -l` = 0、`ast.parse` 恰好通过（空程序合法），所以它不会报错，只会被误认为"这个功能已经有了"。**保留它是有意的**，别删；真要补做"画数字"，从这里起步，而不是从 06 复制（数字笔画是不连续路径，`generate_*_path` 那套首尾相连的采样逻辑不适用）。
4. **`04_pentagram.py` 与同目录其它文件不是同一套硬件，不能互换。** 它 `Display.init(Display.VIRT, …)`、RGB565 全分辨率采集，靠 `Gimbal` + `PD_Controller` 直接写 PWM 脉宽。后果是：`Kp = Kd = 0.00001` 这两个数值只对**你手上那台舵机云台的脉宽-角度增益**成立，换一台就要重调；而且它不发 UART 帧，所以**电控那边永远收不到它的输出**，别指望它能替代 01/03/06。
5. **`07_ui_debug.py` 与 `ui_simulation.html` 都不出帧。** 全文 `uart.write` 出现 0 次。它们只负责"把阈值调出来给人看"，调出来的值需要你手工抄进 `.py` 的阈值常量里 —— 没有回写通路，这是设计缺口而不是 bug。
6. **`ui_simulation.html` 只能在电脑浏览器里看。** 它不是 K230 网页、也不能拷到 SD 卡跑（K230 上没有浏览器运行时）。它的用途只有一个：在上板之前先在电脑上把布局、按钮位置、配色定下来，减少反复烧录。

## 练习建议

1. **把 02 的 4 处 struct 错误修掉，并用字节级对拍证明你改对了**
   在临时副本里改（别动原文件）。两种改法任选：补实参，或缩格式串 —— 但要能说出为什么选这种。
   **通过标准**：`python -c "import struct; print(len(struct.pack('<BHH',1,300,200)))"` 之类的字节数核对，加上上板后用串口助手实测：`flag=1, x=300, y=200` 时收到的完整帧必须是 `AA 01 2C 01 C8 00 55`（`<HH` **小端**：`300 = 0x012C` → `2C 01`；`200 = 0x00C8` → `C8 00`）。字节序抄错是最常见的失手点，把这一点写进你的报告里。**收不到 7 个字节、或第 3~6 字节对不上，就是没过。**

2. **量"曝光压制"到底换来了什么（这是本目录唯一必须测的题）**
   `02_triangle_exposure.py` 第 198 行的 `exposure_gain = 0.5`，注释推荐 0.2~3.0。
   任务：固定同一靶标与同一激光模块，把 `exposure_gain` 依次设为 `0.2 / 0.5 / 1.0 / 2.0 / 3.0`，每组量三个数：
   ① `find_laser_point()` **命中帧率** = 100 帧里成功取到激光点的帧数；
   ② 该帧的 FPS 读数均值（`cv_lite` 那步是额外开销，必须看它吃掉多少）；
   ③ 激光点在屏幕上的**抖动半径**（连续 30 帧命中坐标相对均值的最大偏离像素数）。
   **通过标准**：交出 5×3 的实测表，并明确指出"命中帧率 ≥ 90% 且 FPS 下降不超过 30%"的 `exposure_gain` 区间。如果不存在这样的区间，直接写"当前硬件条件下压制曝光不划算"——**那也是合格的结论，比硬凑一个数强。** 只写"调亮/调暗了"没有数字，不合格。

3. **补做 `05_digits_EMPTY.py`，逼自己处理"不连续路径"**
   任务：在识别到的矩形内画一个数字（题目自选，建议 `1` 和 `8`：一个只有直线，一个有闭环）。
   **通过标准**：(a) 文件不再是 0 字节，并把 `_EMPTY` 从文件名里去掉（同时更新本 README 的表格与「已知问题 3」）；(b) 报告里给出**抬笔/落笔的次数**与总路径长度（像素数）—— 数字 `8` 至少要 1 次抬笔，`1` 的三段笔画要 2 次；(c) 让队友在靶标前进 20 次，统计"笔画起点被正确对准"的次数，**≥ 18 次**。这道题的意义是：`01/03/06` 的路径都是**一条连续闭合曲线**，画数字需要引入"路径分段 + 空移"这一层，那是它们谁都没有的。别用 `if` 硬绕，认真设计一下 `Path = list[Segment]` 的形状。

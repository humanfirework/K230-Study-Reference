# 2023_E_laser — 2023 年 E 题「运动目标控制与自动追踪系统」

## 题目要求与本目录的做法

2023 E 题要求做一个能接收/显示坐标、并驱动激光笔（红或绿）瞄准与追踪运动目标的装置：基础部分要能按给定坐标定位激光点、并绕一个铅笔绘制的矩形轨迹走；发挥部分要求用视觉实时识别另一支激光点（或目标）并做动态追踪，追踪误差以厘米计。

本目录里有**两条完全不同的技术路线**，别混着看：

1. **UART → STM32 路线（主流程）**：K230 只做视觉，把坐标用串口帧发给一块 STM32，由 STM32 驱动两轴步进电机云台。代表文件 `main_high_fps.py`（400×240 灰度 + `find_blobs` + 一帧速度外推 + 稳定计数 + 发帧）、`k230_full.py`（多状态任务机）、`basic_part.py`（触摸屏离线调阈值 + PID 控制步进电机）。STM32 侧的工程不在这里，在 `../../other_boards/stm32/`。
2. **PWM 直驱云台路线（`reference_gimbal/`）**：K230 自己用 `PWM` 直接打舵机（X=GPIO42/PWM0，Y=GPIO52/PWM4，50 Hz），不经串口、不管 STM32。这是 LCKFB 例程风格的三条独立程序，适合先单独验证「视觉 → 云台转」这件事能不能通，再切回路线 1。

`variants/` 是同一份基础代码在不同阶段的 6 个存档，`error/` 是 4 次失败尝试，`yahboom_reference/` 是亚博 (Yahboom) K230 方案的完整移植包（含它自己的 STM32 工程，工程部分已挪到 `other_boards/stm32/`）。

## 题目 PDF

`E题_运动目标控制与自动追踪系统.pdf`（230,727 字节，本目录内，保留原中文名）。
同一份题面也在 `../../NUEDC_TOPIC-master/真题/2023/`。

## 代码文件清单

### 本目录主脚本

| 文件 | 行数 | 作用 | 状态 |
|---|---:|---|---|
| `main_high_fps.py` | 345 | 帧率优先版：400×240 GRAYSCALE，`find_blobs` 找矩形，一帧速度外推，稳定 3 帧才更新，UART2 发 `AA\|type:B\|x:H\|y:H\|55`，距屏幕中心 (200,120) < 30 px 时 GPIO48 打激光。**2025 年那三个 main 的直系祖先，且状态机写对了** | 可用 |
| `basic_part.py` | 518 | 触摸屏离线调 LAB 阈值 + PID 控步进电机（`send_order()` 发 `AA AA num dir steps_hi steps_lo sum FF FF`）。开头注明来源：bilibili「学不会电磁场」第 14 课 | 可用 |
| `k230_full.py` | 463 | 多状态任务机（打点 5 点、追踪、绕框），功能最全但有两处会抛异常的实现错误（见「已知问题」） | **不完整**（有 NameError 与 struct 参数错误） |

### `variants/`（6 个，同一基础的迭代存档）

| 文件 | 行数 | 作用 | 状态 |
|---|---:|---|---|
| `k230_basic.py` | 418 | 基础追踪版，发 `AA\|<BHHHH>\|(x,y,x1,y1)\|55`（11 B）与 `AA\|<B10H>\|(5 点)\|55`（23 B）两种帧 | 可用 |
| `k230_basic_variant2.py` | 436 | ⚠️ **不是 `k230_basic.py` 的副本**（旧名 `K230 基本 - 副本.py` 骗人）。两者 `git diff --no-index --numstat` = **+105 / −87 行**：阈值结构从 `RED_THRESHOLD`（3 个元组的列表）换成单个 `Red_thresholds = (72, 99, -6, 46, -40, 25)`，`find_blobs` 参数与发帧方式（改成 `55 AA 00 xh xl yh yl fa` 合并包）全不一样 | 可用（但与 basic 是两套代码） |
| `k230_basic_done.py` | 610 | 基础题完成版，发 `55 AA …FA` 单轴 6 字节包 | 可用（尾部有死代码，见下） |
| `k230_entry.py` | 456 | 初级版（A4 长宽比过滤思路的早期形态） | 可用（尾部有死代码） |
| `k230_pencil_mark.py` | 506 | 铅笔线框打点版 | 可用（尾部有死代码） |
| `yedan.py` | 203 | 只做「内外嵌套矩形」检测并 `print` 结果，**完全不用串口**（`uart.write` 出现 0 次）。LCKFB 例程抬头 | 可用（纯调试脚本） |

### `error/`（4 次失败尝试）

| 文件 | 行数 | 状态 |
|---|---:|---|
| `error1.py` | 189 | 已废弃（能通过语法解析；早期 VIRT/LCD/HDMI 显示分支版） |
| `error2.py` | 415 | **已废弃：语法就不通过**。`SyntaxError` at line 375 — `print(f"发送数据: 状态={}, X={}, Y={}")` 里是空 `{}`，同行 `uart2.write('!' + str() + ',' + str() + '@')` 的 `str()` 也没传参 |
| `error3.py` | 397 | **已废弃：语法就不通过**。`SyntaxError` at line 369，同样是空 `{}` + 裸 `str()` |
| `error4.py` | 522 | 已废弃（能解析；红/绿/激光三阈值版，被 `variants/` 取代） |

### `reference_gimbal/`（5 个，PWM 直驱云台路线，LCKFB 风格）

| 文件 | 行数 | 作用 | 状态 |
|---|---:|---|---|
| `main.py` | 770 | 菜单式主程序：KEY1(GPIO27) 复位、KEY2(14) 云台画正方形、KEY3(61) 矢量循迹、KEY4(40) 自动追踪红绿目标、KEY5(46) 暂停/继续 | 可用（**独立架构**，不发 UART 坐标帧） |
| `advanced_part.py` | 299 | 发挥部分：云台 + 绿色 LED(GPIO) + 蜂鸣器 `PWM(1, …)` | 可用 |
| `basic_tasks_34.py` | 312 | 基础部分第 3、4 小题 | 可用 |
| `camera_track_test.py` | 158 | 摄像头追踪单元测试 | 可用 |
| `gimbal_driver.py` | 125 | 纯舵机驱动演示：X=GPIO42/PWM0，Y=GPIO52/PWM4，50 Hz，脉宽 0.5~2.5 ms，中心 1.6 ms，正方形边长 ±0.1 ms | 可用 |

### `sample_code/`（现只剩 2 个文件）

`get_square.py`(232) 与 `red_light.py`(243) —— 都是亚博例程，**`from ybUtils.YbKey import YbKey` / `YbUart`，本仓库没有 `ybUtils` 包，跑不了**。
原本这里还有 `green.py`、`red.py` 两个文件，已确认它们是 OpenMV 代码（`from pyb import UART`），在 `28b5f40` 移到了 `../../other_boards/openmv/2023_laser/`。**本目录不再是"缺一半"的状态，是被清出去了。**

### `yahboom_reference/`（亚博 K230 完整方案，第三方）

保留原文件名与 `LICENSE`。Python 端 `get_rect.py`(356) 与 `get_light3.py`(99) 发 `A3/B3 + N×(x_hi,x_lo,y_hi,y_lo) + C3`（**大端**）；`menu_threshold_ui/` 是它的触摸屏菜单阈值工具（5 个文件，`main.py` 88 行、`get_rect_ui.py` 344 行、`change_threshold.py` 192 行、`otherKey.py` 40/27 行）。`ReadMe.txt` 里有作者本人的思路说明，值得一读（特别是"识别不到内框就按外框比例缩放生成内框"这招）。它对应的两个 STM32 工程（`2023 - green`、`2023 - red`）已在 `28b5f40` 移到 `../../other_boards/stm32/yahboom_2023_green/` 与 `_red/`。

⚠️ **`yahboom_reference/menu_threshold_ui/change_threshold.py` 有缺陷**（见「已知问题」）。它是第三方 vendored 代码，**本仓库故意不修改**，只记录。

## 旧名 → 新名

第一次改名：`89e6ffc`（`电赛赛题K230` → `07_contest`，同时英文化子目录与文件名）
第二次搬家：`28b5f40`（非 K230 代码移出到 `other_boards/`）

| 旧名（`89e6ffc` 之前） | `89e6ffc` 之后 | `28b5f40` 之后（现在） |
|---|---|---|
| `电赛赛题K230/02_2023_E_Laser/` | `07_contest/2023_E_laser/` | 同左 |
| `…/2023年E题基础部分.py` | `…/basic_part.py` | 同左 |
| `…/K230.py` | `…/k230_full.py` | 同左 |
| `…/main（高帧率）.py` | `…/main_high_fps.py` | 同左 |
| `…/ERROR/ERROR1.PY` | `…/error/error1.py` | 同左（`.PY` 大写后缀某些工具链不当 Python 处理，故改小写） |
| `…/ERROR/ERROR2.py`…`ERROR4.py` | `…/error/error2.py`…`error4.py` | 同左 |
| `…/参考/main.py` | `…/reference_gimbal/main.py` | 同左 |
| `…/参考/云台驱动.py` | `…/reference_gimbal/gimbal_driver.py` | 同左 |
| `…/参考/发挥部分.py` | `…/reference_gimbal/advanced_part.py` | 同左 |
| `…/参考/基础34题.py` | `…/reference_gimbal/basic_tasks_34.py` | 同左 |
| `…/参考/摄像头追踪测试代码.py` | `…/reference_gimbal/camera_track_test.py` | 同左 |
| `…/示例代码/get_square.py` | `…/sample_code/get_square.py` | 同左 |
| `…/示例代码/red_light.py` | `…/sample_code/red_light.py` | 同左 |
| `…/示例代码/green.py` | `…/sample_code/green.py` | **`other_boards/openmv/2023_laser/green.py`** |
| `…/示例代码/red.py` | `…/sample_code/red.py` | **`other_boards/openmv/2023_laser/red.py`** |
| `…/合集/K230 基本.py` | `…/variants/k230_basic.py` | 同左 |
| `…/合集/K230 基本 - 副本.py` | `…/variants/k230_basic_variant2.py` | 同左（**它不是副本**） |
| `…/合集/K230（基础题完成）.py` | `…/variants/k230_basic_done.py` | 同左 |
| `…/合集/K230 （初级）.py` | `…/variants/k230_entry.py` | 同左 |
| `…/合集/K230 （铅笔激光标点）.py` | `…/variants/k230_pencil_mark.py` | 同左 |
| `…/合集/yedan.py` | `…/variants/yedan.py` | 同左 |
| `…/K230参考/` | `…/yahboom_reference/` | 同左 |
| `…/K230参考/2023 - green/2023 - green/` | `…/yahboom_reference/2023 - green/2023 - green/` | **`other_boards/stm32/yahboom_2023_green/2023 - green/`** |
| `…/K230参考/2023 - red/2023 - red/` | `…/yahboom_reference/2023 - red/2023 - red/` | **`other_boards/stm32/yahboom_2023_red/2023 - red/`** |
| `…/E题_运动目标控制与自动追踪系统.pdf` | 同名（不改） | 同左 |
| `赛题K230/02_2023_E_Laser/`（最初提交 `f2aa2af`） | — | 仓库根更早叫 `赛题K230/`，`5b4dd92` 才改成 `电赛赛题K230/` |

`yahboom_reference/` 内部（含 `menu_threshold_ui/`）的中文与 `2023 - green` 这类带空格的名字**故意保持原样**：亚博的教程按这些编号称呼文件，改名等于断掉回溯线索。

## 已知问题（全部实测核对）

1. **`k230_full.py`：`beep_pwm` 从未实例化 → 追踪成功那一刻 NameError。**
   文件第 16 行 `from machine import PWM`，但全文没有任何 `PWM(...)` 构造。第 411~414 行却在 `if tracking_complete:` 分支里调 `beep_pwm.freq(1000)` / `beep_pwm.enable(True)` / `.enable(False)`。
   后果：唯一能"报喜"的路径必炸，异常被第 447 行 `except BaseException as e: print(f"Exception {e}")` 吞掉，只输出一行 `Exception name 'beep_pwm' is not defined`，然后 `finally` 收尾、程序安静退出。**"追踪成功了但机器不动"就是这个**。

2. **`k230_full.py`：两处 `struct.pack` 参数个数不匹配。**
   第 59 行 `struct.pack('<BHHHH', 1, x, y)`、第 66 行 `struct.pack('<BHHHH', 2, x, y)` —— 格式要 5 个字段，只传 3 个，实测抛 `struct.error: pack expected 5 items for packing (got 3)`。所以 `send_data()` 与 `send_target_data()` **一旦被调用就异常**；只有 `send_five_points()`（第 84 行 `<B10H` + 11 个实参）是对的。

3. **`variants/k230_basic_variant2.py` 不是 `k230_basic.py` 的副本。**
   实测 `git diff --no-index --numstat` = **105 added / 87 removed**（共 192 行差异，文件各 418 / 436 行）。差异不只是格式：阈值数据结构、`find_blobs` 调用、UART 发帧格式全不同（详见上表）。**旧名「- 副本」会让人把它当重复文件删掉，所以改名了 —— 但别按"basic 的备份"来读它。**

4. **`variants/` 里 3 个文件在 `finally:` 之后还粘着 100+ 行永不执行的函数定义。**
   `k230_basic_done.py`：`finally:` 在第 510 行，文件 610 行 → 尾部 **100 行**，含 `def laser_track()`（第 527 行）。
   `k230_entry.py`：`finally:` 在第 290 行，文件 456 行 → 尾部 **166 行**，含 `def laser_rect()`（307）、`def laser_track()`（373）。
   `k230_pencil_mark.py`：`finally:` 在第 340 行，文件 506 行 → 尾部 **166 行**，含 `def laser_rect()`、`def laser_track()`。
   核对方法：全文件里 `laser_track` / `laser_rect` **只出现在 `def` 行**，调用次数为 0 —— 它们是**永远不被调用的死代码**。而且因为 `finally` 之后语句仍会被解释器执行到"定义"这一步，读代码的人很容易误以为它们生效了（"绕框""追踪"功能其实并没有接上）。

5. **`error/error2.py`(line 375) 与 `error/error3.py`(line 369) 不能通过语法解析。**
   两处都是 `print(f"发送数据: 状态={}, X={}, Y={}")` —— f-string 里写空 `{}`；紧邻上一行 `uart2.write('!' + str() + ',' + str() + '@')` 的 `str()` 也没实参，即使能解析也只会送出 `!,@`。这两个文件**连 import 都做不到**，只能当文字材料看。

6. **`yahboom_reference/menu_threshold_ui/change_threshold.py`（第三方，不修改）：调用方传进来的阈值一定被忽略。**
   第 9 行签名 `def run_threshold_ui(sensor, tp, key, key_esc, thresholds, WIDTH=640, HEIGHT=480):`；第 12 行 `original_thresholds = [row[:] for row in thresholds]` 刚把入参备份好，第 14~17 行立刻 `thresholds = [[0,100,-128,127,-128,127], [0,100,-128,127,-128,127]]` 用硬编码默认值把局部名重新绑定。
   于是界面上显示的永远是全量程默认值，而不是你辛苦调好的那组。
   **本仓库不修改它**：它是 vendored 的厂商代码，改了就和亚博教程对不上号。要用这套菜单，自己抄一份改，或直接把入参当唯一来源重写。

## 练习建议

1. **先修 `k230_full.py` 的两处崩溃，用「改前 / 改后」验证你真的定位对了**
   要求：不重写文件，只补 `beep_pwm` 的构造（参考同仓库 `reference_gimbal/advanced_part.py:157` 的 `PWM(1, BEEP_FREQ, BEEP_DUTY, enable=False)` 写法）和第 59/66 行的 `struct.pack` 实参。
   **通过标准**：把第 447 行的 `print(f"Exception {e}")` 换成 `sys.print_exception(e)` 临时打印栈，跑一次完整追踪流程，**输出里既没有 `NameError` 也没有 `struct.error`**；然后改回原打印方式，并把你只动了哪几行记在 commit message 里。（不许动 `.py` 之外的行为，也不许顺手"优化"别的地方。）

2. **量帧率，而不是看"画面在动"**
   `main_high_fps.py` 的 `picture_width/height = 400/240`、`DISPLAY` 是 ST7701 800×480；`reference_gimbal/main.py` 用 `Display.VIRT`/`ST7701` 的组合不同，帧率必然不同。
   任务：在**同一目标、同一光照**下，分别记录 `main_high_fps.py`、`k230_basic.py`、`k230_basic_done.py` 三个脚本屏幕上打印的 FPS（连续 30 次采样），列成表，写清各自掉了多少。再对 `main_high_fps.py` 把 `TARGET_STABILITY_THRESHOLD`（第 61 行，当前 3）改成 3 和 6，各测 20 次追踪，记录「从目标进入视野到第一帧发坐标」的帧数。
   **通过标准**：交出一张「脚本 × FPS(均值/最小)」「阈值 × 首帧延迟(中位/最大)」的实测表，数字来自屏幕或串口打印，不许写"感觉流畅"。

3. **证明 `variants/k230_basic_variant2.py` 与 `k230_basic.py` 不是同一份代码**
   不许打开编辑器对比着读，必须用命令：`git diff --no-index --numstat variants/k230_basic.py variants/k230_basic_variant2.py` 与 `diff … | wc -l`。
   **通过标准**：报告里给出实测的增删行数（本次核对结果是 **+105 / −87**），并能说出**至少三处实质差异**（阈值数据结构、`find_blobs` 实参、UART 发帧格式各算一处），并解释为什么"是副本"这个旧文件名会让人误删。

4. **（选做，跨到 `other_boards/`）把亚博那对能自洽的协议跑通一次**
   本目录唯一自洽的收发对是 `yahboom_reference/get_rect.py` ↔ `../../other_boards/stm32/yahboom_2023_red/2023 - red/dsp/bsp_uart.c`（`A3 + x_hi,x_lo,y_hi,y_lo + C3`，**大端**）。
   **通过标准**：STM32 串口助手上抓到 6 字节且 `RxBuffer[5] == 0xC3`（该工程第 42 行就是这个判据），并亲手验证一次：把你 K230 端换成 `struct.pack('<HH', x, y)`（小端）后，STM32 解析出的坐标会错成什么值。**这道题的目的就是让你记住本仓库有大小端两套约定**，见 [`../README.md`](../README.md) 的协议表。

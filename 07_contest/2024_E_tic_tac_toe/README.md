# 2024_E_tic_tac_toe — 2024 年 E 题「三子棋游戏装置」

## 题目要求与本目录的做法

2024 E 题要求做一台三子棋（井字棋）游戏装置：视觉识别棋盘与黑白棋子摆放位置、判断玩家是否作弊（多拿/少拿棋子、违规落子），并由"电脑方"选择落点、通过串口把坐标交给执行机构落子，还要按题目分档完成若干项基础/发挥任务。

本目录的做法是**纯视觉 + 纯逻辑**：160×120 低分辨率采集（换帧率），`find_rects` 找到棋盘外框后按透视关系算出九点栅格，每个棋格开一个小 ROI 用 LAB 阈值判断有没有子、是黑是白，用连续帧计数器（`stable_frames`，阈值 10 帧）去抖；棋局规则与"电脑怎么下"用 **Alpha-Beta 剪枝的极小极大搜索**（深度上限 4）；对外用 UART2 发 `FF | 任务ID | 数据 | FE` 帧。执行机构（落子伺服）不在本仓库。

> **⚠️ 先说清一件事：能用的那份是 `main_tic_tac_toe.py`，不是名字更像主程序的 `skeleton_incomplete.py`。**
> 后者的旧名是 `2024-E-master.py` —— 一个"master"结尾、看起来最像正式工程的文件，实际是一份被掏空的骨架，**连语法都过不了**。见下面「已知问题」。

## 题目 PDF

`E题_三子棋游戏装置.pdf`（181,295 字节，本目录内，保留原中文名）。
同一份题面也在 `../../NUEDC_TOPIC-master/真题/2024/`。

## 代码文件清单

| 文件 | 行数 | 大小 | 作用 | 状态 |
|---|---:|---:|---|---|
| `main_tic_tac_toe.py` | **1503** | 69,880 B | 完整方案：视觉棋盘/棋子识别 + 棋局状态机 + Alpha-Beta 极小极大 + UART 帧 + 任务 1~6 分支。**本目录唯一值得读的实现**，但因漏 `import os` 目前跑不起来（一行可修） | 不完整（1 处致命缺陷 + 3 处逻辑缺陷） |
| `skeleton_incomplete.py` | 244 | 7,429 B | 同一份代码掏空后的骨架：只留下 `float_to_bytes` / `build_frame` / `get_chess_presence_status` / `get_chess_color_status` / `max_rect` / `send_data_frame` / `send_data` 的壳，`receive_and_unpack()` **函数体是空的** | 已废弃（**不通过语法解析**，无法 import / 无法运行） |
| `E题_三子棋游戏装置.pdf` | — | 181,295 B | 官方题面 | 可用 |

## `main_tic_tac_toe.py` 的内部结构（按行号索引）

| 位置 | 内容 |
|---|---|
| 12~19 | `fpioa.set_function(11/12, UART2_TXD/RXD)`；GPIO 62/20/63 设为 `LED_R` / `LED_G` / `LED_B`，`drive=7` |
| 20~23 | 三个 LED 上电即 `high()`（板子低电平点亮，即全灭），`LED = LED_R` 起了个别名 |
| 27~35 | `picture_width=160`、`picture_height=120`；三块 ROI：棋盘 `roi_qipan=(30,0,100,120)`、黑棋盒 `roi_heiqi=(0,0,30,120)`、白棋盒 `roi_baiqi=(130,0,30,120)` |
| 36~43 | UART2 115200 8N1；自定义帧头帧尾 `FRAME_HEADER=0xFF` / `FRAME_FOOTER=0xFE` |
| 82~83 | 棋子 LAB 阈值：`white_threshold = [(53,100,-35,38,-30,33)]`、`black_threshold = [(0,21,-36,17,-15,30)]` |
| 85~90 | 棋盘 `board` 3×3；`PLAYER='X'`、`COMPUTER='O'` |
| 95~97 | `stable_frames` 3×3 计数器、`STABLE_FRAME_THRESHOLD = 10` |
| 167~193 | `max_rect()`：`img.find_rects(roi=roi_qipan, threshold=8000)` 找棋盘 |
| 194~217 | `cal_ninepoints(rect)`：由矩形角点插值出九宫格中心 |
| 218~265 | `cal_boardlines()` / `draw_board()` / `cal_roi()`（每个棋格一个小 ROI） |
| 278~314 | `send_data_frame()` / `send_data(task_id,…)`：任务 0x02 发两个 `<f` float32 坐标；0x03 发两个 `<H` 位状态；0x05 发复位 |
| 316~… | `receive_and_unpack()`：逐字节 `uart.read(1)` 扫 `0xFF … 0xFE`，解析任务 ID / 子任务 ID 并切换状态 |
| 673~736 | `update_board_state(img)`：逐格 `find_blobs` + `stable_frames` 去抖，写 `board` |
| 738~757 | `check_winner()` / `is_full()` |
| 759~797 | **`minimax(board, depth, is_maximizing, alpha, beta, max_depth=4)`** —— Alpha-Beta 剪枝 |
| 798~811 | `find_best_move()`：对每个空格试落，取分数最高者 |
| 812~822 | `computer_move()` —— **有缺陷，见下** |
| 924~1055 | `calculate_board_angle()` / `task3_send_angle()`（题目第 3 项：报棋盘角度） |
| 1056~1400 | `task5_player_fore()`、`task6_computer_fore()`：玩家/电脑轮流落子与作弊判定 |
| 1414~1500 | 主循环 |

## 给第一次接触它的同学：Alpha-Beta 在讲什么

井字棋状态空间很小，可以直接"看到底"：谁赢、还是平局。极小极大搜索就是**两个人轮流做对自己最有利的假设**：

- 轮到电脑（`is_maximizing=True`）：把每个空格试着填上 `O`，递归问"之后局面最好能到几分"，取**最大**的那个。
- 轮到玩家（`is_maximizing=False`）：同样试填 `X`，但取**最小**——因为对手不会让你舒服。
- 叶子打分：电脑赢 `+1`、玩家赢 `−1`、平局或到深度上限 `0`（见 759~768 行）。
- 顶层 `find_best_move()` 就是"哪个空格的返回值最大，我就下哪"。

**剪枝**是这段代码真正值得学的地方（779~781、793~795 行）：维护两个边界 `alpha`（我保证能拿到的下界）和 `beta`（对手允许我拿到的上界）。搜索途中一旦发现 `beta <= alpha`，说明这条分支的后续变化**已经不可能影响最终选择**——对手有更差的选择，轮不到这里；于是 `break`，整棵子树不看了。

直觉版本：你在挑餐厅，已经找到一家 8 分的。走到另一家的第 3 道菜尝出 5 分，且你知道这家整体不会比最差那道好——那第 4~10 道菜就不用尝了。

井字棋里它省的是常数，但**同一套 `alpha/beta` 骨架搬到五子棋/四子棋就省指数**。理解了这份 40 行的实现，你就能读所有棋盘 AI。要留意的三点限制：`max_depth=4`（默认参数）意味着它不是完全求解，会漏掉更深的杀招；评分只有 `±1/0` 的胜负值，没有"占中心""连成两颗"这类局面分，所以浅层里判断力有限；`find_best_move()` 顶层把 `alpha` 初值设为 `−inf`、`beta` 设为 `+inf` 但**没有在候选之间更新**，也就是说顶层其实没剪枝，剪枝只发生在递归内部。这三点是设计取舍，不是错误。

## 旧名 → 新名

第一次改名：`89e6ffc`（`电赛赛题K230` → `07_contest`）。本目录**没有**参与 `28b5f40`（非 K230 代码搬家），因为里面全是 K230 代码。

| 旧名（`89e6ffc` 之前） | 现在 | 说明 |
|---|---|---|
| `电赛赛题K230/03_2024_E_ThreePieceChess/` | `07_contest/2024_E_tic_tac_toe/` | 去年份前缀 + 英文名直说内容 |
| `…/Three-piece chess.py` | `…/main_tic_tac_toe.py` | **这才是主程序**；旧名只有"三子棋"三个字，看不出它比另一个文件更完整 |
| `…/2024-E-master.py` | `…/skeleton_incomplete.py` | ⚠️ 旧名里的 `-master` 是误导：它不是"母程序"，是一份**语法都不通过**的空壳骨架。改名是为了让你别再先打开它 |
| `…/E题_三子棋游戏装置.pdf` | 同名（不改） | 赛题 PDF 保留原中文名 |
| `赛题K230/03_2024_E_ThreePieceChess/…`（最初提交 `f2aa2af`） | — | 仓库根早期叫 `赛题K230/`，`5b4dd92` 才改成 `电赛赛题K230/` |

## 已知问题（全部实测核对）

### 1. 致命：`main_tic_tac_toe.py` **从来没有 `import os`**，却调用了 `os.exitpoint()`

实测 import 段（第 1~9 行）只有：

```
import math
import struct
from media.sensor import *
from media.display import *
from media.media import *
from machine import UART
from machine import Pin
from machine import FPIOA
import time
```

而 `os.` 出现两次：

| 行 | 代码 |
|---|---|
| 1446 | `os.exitpoint()` —— 主循环 `while True:` 的**第一句** |
| 1498 | `os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)` —— `finally:` 里 |

文件**语法是通的**（`py_compile` / `ast.parse` 都不报错），但一进 `while True` 就 `NameError: name 'os' is not defined`，然后被第 1487~1488 行的 `except BaseException as e: print(f"异常: {e}")` 吞掉，`finally` 收尾，程序安静退出、什么都不做。

**结论：这份 1500 行的程序实际上一次都没有真正跑过主循环。**
`os` 在 CanMV 上通常由 `from media.sensor import *` 之类带进来吗？——**不要赌**。同一仓库里 `main_thresh_ui_fast.py` 第一行就是 `import time, os, sys` 显式导入；`os.exitpoint()` 的语义（允许 IDE 中断阻塞调用）也必须显式开启才可靠。

这条还解释了下面 2、3 两条为什么从来没人发现：**主循环连第一轮都没走完，循环体内部的逻辑错误根本没机会暴露。** 修它只要一行 `import os`，但**本仓库故意不改**（仓库整体回到原始代码状态，只做目录/命名/文档），记在这里。

### 2. `stable_frames` 只增不减 → "棋子被拿走"的重置分支永远进不去

第 703/717 行 `stable_frames[row][col] += 1`，第 707/721/731 行 `= 0`。全文**没有任何一处减 1**。于是它的取值恒 ≥ 0。

而第 727~731 行写着：

```
if stable_frames[row][col] <= 0 and board[row][col] != ' ':
    ...
    if stable_frames[row][col] <= -STABLE_FRAME_THRESHOLD:   # 第 729 行
        board[row][col] = ' '      # 认定棋子被拿走
```

`<= -10` 的分支**不可达**。后果：玩家把已落的棋子从棋盘上拿走（这正是题目里"作弊"要抓的动作之一），程序状态里的 `board` 不会跟着变空——那格永远显示有子。这段代码写了，但从没生效过。

### 3. `computer_move()` 算出落点坐标后**既没 return 也没发送**

第 812~822 行：

```
def computer_move(board):
    move = find_best_move(board)
    if move:
        row, col = move
        board[row][col] = COMPUTER
        index = row * 3 + col
        x = ninepoints[index][0]
        y = ninepoints[index][1]
```

函数到这就结束了（无 `return`，也没有 `send_data(...)`）。也就是说：**Alpha-Beta 辛苦算出的落点被丢掉了。** 真正发给 STM32 的坐标是在别处（`task6_computer_fore()` 第 1109/1241/1330 行附近 `x_computer, y_computer = ninepoints[index]`）另算一遍的。
这不算崩溃，但意味着 `computer_move()` 是个"只改 `board`、不产出坐标"的半成品，两个地方的 `index` 映射逻辑必须人肉保持一致，很容易改一处漏一处。

### 4. RGB 灯只是初始化了，从来没被状态驱动

第 17~23 行设置 `LED_R`(62) / `LED_G`(20) / `LED_B`(63) 并全部 `high()`（=灭），`LED = LED_R`。
此后全文再无 `LED` / `LED_R` / `LED_B` 的操作，`LED_G` 也只出现在第 18、21 行。也就是说**「用 RGB 灯指示识别/落子状态」这件事只在文件头搭了个架子，状态机里一处都没接**。想加指示的话，挂点在第 673 行 `update_board_state()` 与第 1191 行 `task6_computer_fore()` 的末尾。

### 5. 主循环每帧固定睡 50 ms，帧率上限被压到约 20 FPS

`receive_and_unpack()` 第 321 行开头是 `time.sleep(0.05)`，而它在主循环第 1449 行**每帧都被调一次**。这个 50 ms 是为"读串口别把 CPU 吃满"加的，代价是把整条视觉链路的帧率天花板压到约 20 FPS，与 `find_rects(threshold=8000)` 的实际开销混在一起，你无法从 FPS 读数判断识别本身快不快。做帧率优化实验时要先知道有这一存在。

### 6. `task4_start` 与 `task6_start` 走的是同一个函数（意图未验证）

第 1471~1476 行：`if task4_start: task6_computer_fore(img)`、`if task5_start: task5_player_fore(img)`、`if task6_start: task6_computer_fore(img)`。全文**没有 `task4_*` 专用函数**（只有 `task4_start` / `task4_executed` 这类标志位）。这**可能**是有意复用，**也可能**是复制粘贴漏改；仅凭代码无法判断，标记为**未验证**，做题目前请对照题面确认第 4 项与第 6 项要求是否真的相同。

## 练习建议

1. **一行修好它，然后量"修之前 vs 修之后"**
   在 `main_tic_tac_toe.py` 第 1 行前加 `import os`（**只加这一行**），另存为临时副本跑，别污染原文件。
   **通过标准**：屏幕上能看到棋盘 ROI 紫框（第 1454~1456 行画的三个框）与九点标记；串口打印出现"接收到字节：0x…"以外的**主循环输出**，说明 `os.exitpoint()` 不再抛 `NameError`；记录此时 FPS 数值，并验证它 ≤ 20（因为缺陷 5 的 `time.sleep(0.05)`）。如果你测到的 FPS > 20，说明你没真正跑到那一行，回去检查。

2. **实测 Alpha-Beta 的剪枝效果（这道题必须出数字）**
   在 `find_best_move()` 里加两个计数器（试落次数 / 递归调用次数），对下面三种空棋盘局面各跑一次：全空、电脑先手占中心、以及文件里注释掉的那个 `board1 = [['O',' ','X'],[' ','O',' '],['O','X','X']]`（第 1457~1460 行）。
   **通过标准**：交出一张表「局面 × 深度上限 3/4/5 × 试落次数 × 耗时 ms」。并回答：把 `max_depth` 从 4 提到 5 后，前面那个局面里 `check_winner` 有没有改变 `find_best_move` 的选择？如果一次都没变，说明 4 层在这个局面已经够用；变了就报出变到哪个格子。**耗时不许"估算"，必须来自 `time.ticks_ms()` 差值。**

3. **把 `stable_frames` 的"取子"分支真的跑通**
   目标是让缺陷 2 里那条 `<= -STABLE_FRAME_THRESHOLD` 变成可达。两种做法任选：给"检测到空格"的分支加 `-= 1`，或者把判据改成不依赖负值。
   **通过标准**：摆一颗子 → 等 `board` 里出现它（看第 704 行 `>= STABLE_FRAME_THRESHOLD` 命中时的打印）→ 把子拿走 → **在 2 秒内**看到程序把该格重新置为 `' '`，并且 `get_chess_presence_status()` 的 9 位状态里对应位翻转。用串口打印的状态位对比，不许用"看起来对了"。同时记录：阈值 10 帧改成 5 帧和 20 帧，从"拿走子"到"状态翻转"分别多少毫秒——这题的意义是让你把"去抖帧数"翻译成"人手上真实秒数"。

4. **（跨目录）统一一份你自己的协议**
   本题的 `FF | 任务ID | float32… | FE`（第 278~314 行）和 2023/2025 的 `AA…55`、STM32 例程的 `AA+len+checksum` 全都不一样（完整表见 [`../README.md`](../README.md)）。
   **通过标准**：为这道题写一份 6~10 字节的帧定义（含坐标字节序、有没有校验和），Python 端改 `send_data()`，C 端在 `../../other_boards/stm32/serial_packet/` 里改 `Command_GetCommand()` 配套解析；连发 1000 帧，**STM32 收到的帧数与每帧 float32 值 100% 对得上**。

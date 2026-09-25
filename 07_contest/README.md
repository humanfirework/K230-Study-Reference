# 07_contest — 历年电赛赛题（K230 部分）

本目录存放**在 CanMV K230（立创·庐山派）上跑的电赛赛题代码**，按年份分目录。
非 K230 的代码（OpenMV / MaixPy / STM32 工程）不在这里，已挪到仓库根的 `other_boards/`。

> ⚠️ 本 README 之前的一版写有下列**错误内容**，已全部按实测重写。若你在别处看到这些说法，以本文件为准：
>
> | 旧说法 | 实测结果 |
> |---|---|
> | 「包含 2021、2023、2024 年资料」 | **2021 年在本目录下一份资料都没有**，`2021_F_drug_car/` 是个空目录。题目 PDF 在 `NUEDC_TOPIC-master/真题/2021/` |
> | 2025 三个 main「经过调试、可以直接运行」 | 三个都**不能直接跑完**：`main_thresh_ui_accurate.py` 顶部 `import cv_lite`，该模块不在本仓库；三个文件各有一批逻辑缺陷，见 [2025 README](2025_E_self_aiming/README.md) |
> | 目录结构 `04_2025_E_SelfAiming/Result`、`00_Reference`、`方法及参考/迭代版本` | 已在 `89e6ffc` 改名，这些旧路径**均不存在** |
> | 全文未提 `laser_drawing/` | 该目录有 7 个文件（含 1 个 0 字节占位、1 个 HTML），见 [laser_drawing README](laser_drawing/README.md) |
> | `find_rect/` 含 `deploy_config.json`、`det_results/` | 实际只有 `README.pdf` + 4 个 `det_*.py` + `mp_deployment_source/`（内仅 1 个 `.kmodel`）。`deploy_config.json` 和 `test.jpg` **不在仓库里** |

## 各年份状态一览

| 目录 | 赛题 | 代码量 | 能跑吗 | 详情 |
|---|---|---|---|---|
| `2021_F_drug_car/` | 2021 F 题 智能送药小车 | **0 文件**（空目录） | — | [README](2021_F_drug_car/README.md) |
| `2023_E_laser/` | 2023 E 题 运动目标控制与自动追踪 | 主脚本 3 个（518 / 463 / 345 行）+ `variants/`(6) `error/`(4) `reference_gimbal/`(5) `sample_code/`(2) `yahboom_reference/` | 部分。`k230_full.py` 有 NameError 与 struct 参数错误；`error/error2.py`、`error3.py` **语法就不通过** | [README](2023_E_laser/README.md) |
| `2024_E_tic_tac_toe/` | 2024 E 题 三子棋游戏装置 | `main_tic_tac_toe.py` **1503 行**（真方案）+ `skeleton_incomplete.py` 244 行 | 都跑不了。主程序**漏了 `import os`**，第一轮循环即 NameError；骨架文件 `def receive_and_unpack():` 空体，**不通过语法解析** | [README](2024_E_tic_tac_toe/README.md) |
| `2025_E_self_aiming/` | 2025 E 题 简易自行瞄准装置（**本仓库作者的原创**） | `result/` 3 个 main（655 / 987 / 451 行）+ `find_rect/` 模型部署 4 脚本 + `methods_reference/iterations/` 9 个迭代版 | 有条件。`main_thresh_ui_fast.py` 是三者中最接近可用的；另两个分别依赖缺失的 `cv_lite` 与含从未执行过的核心分支 | [README](2025_E_self_aiming/README.md) |
| `laser_drawing/` | 非赛题：振镜/激光画图形 | 7 文件（含 0 字节 `05_digits_EMPTY.py`、728 行 `ui_simulation.html`） | 部分。`02_triangle_exposure.py` 有 4 处 struct 参数不匹配；`02` 还依赖 `cv_lite` | [README](laser_drawing/README.md) |
| `reference/` | 厂商例程（LCKFB + 亚博） | `image_recognition/` 12 + `basic_gpio/` 12 + `yahboom_ported/` 4 | 大多可用；`yahboom_ported/` 4 个都需要仓库外的 `ybUtils` | [README](reference/README.md) |

各年份目录内还有自己的 README，其中含**旧名 → 新名对照表**、逐文件状态表、已知问题和练习建议。找具体文件该看哪个版本，请先读年份 README，不要凭目录名猜。

## ⚠️ 全仓库串口协议不统一

这是本目录最容易踩的坑：**同一个 UART2、同一块 STM32，各处发的是互不兼容的帧**。常见的说法是「有 4 种」，实测全仓库共 **10 种**（下表每行都在代码里逐字核对过）：

| 帧格式（`struct` 前缀省略，字节序见备注） | 谁发（K230/Python） | 谁解析 |
|---|---|---|
| `AA \| type:B \| x:H \| y:H \| 55`（7 B，小端） | `2023_E_laser/main_high_fps.py`、`2025_E_self_aiming/result/` 三个 main、`2025_E_self_aiming/methods_reference/iterations/` 全部、`laser_drawing/01,03,06` | 仓库内**无**对应接收端 |
| `AA \| B+10H（5 个点） \| 55`（23 B） | `2023_E_laser/k230_full.py:84`、`2023_E_laser/variants/k230_basic.py:84` | 仓库内**无** |
| `AA \| B+4H（2 个点） \| 55`（11 B） | `2023_E_laser/variants/k230_basic.py:62`、`laser_drawing/01,03,06` 的 `send_tracking_data` | 仓库内**无** |
| `AA \| <BHHHH> 但只传 3 个参数` → **抛 struct.error** | `2023_E_laser/k230_full.py:59,66` | — 是缺陷，不是协议 |
| `FF \| 任务ID + float32… \| FE` | `2024_E_tic_tac_toe/main_tic_tac_toe.py` | 它自己的 `receive_and_unpack()` |
| `AA \| len \| payload… \| 累加和` | 仓库内**无** Python 端 | `../other_boards/stm32/snippets/uart_rx_tx.c`、`../other_boards/stm32/serial_packet/` |
| `A3/B3 \| (x_hi,x_lo,y_hi,y_lo)×N \| C3`（**大端**） | `2023_E_laser/yahboom_reference/get_rect.py`、`get_light3.py` | `../other_boards/stm32/yahboom_2023_green`、`_red` 的 `dsp/bsp_uart.c` |
| `55 AA \| cmd \| 坐标(大端) \| FA`（6 B 单轴 / 8 B 合并两种） | `2023_E_laser/variants/{k230_basic_done,k230_entry,k230_pencil_mark,k230_basic_variant2}.py` | 不在仓库 |
| `A1 02 flx dx fly dy 1A`（带符号增量） | `../other_boards/openmv/2023_laser/{green,red}.py` | 不在仓库 |
| `DATA,lx,ly,rx,ry\r\n`（ASCII） | `../other_boards/openmv/nuedc_2025_e/激光矩形集中调参/激光矩形集中调参.py` | 不在仓库 |
| 步进电机指令 `AA AA num dir steps_hi steps_lo sum FF FF` | `2023_E_laser/basic_part.py:42 send_order()` | 不在仓库 |

结论：**唯一自洽的一对**是「亚博 K230 Python ↔ 亚博 STM32 工程」（大端 `A3…C3`）。你自己的代码（2023 主脚本、2025、laser_drawing）发出的 `AA…55` 帧，仓库里**没有任何一个 STM32 工程能解析**——`../other_boards/stm32/snippets/uart_rx_tx.c` 会因为读不到长度字节和校验和而丢弃全部帧，细节见 [`../other_boards/stm32/README.md`](../other_boards/stm32/README.md)。

参赛时请**先定协议再写代码**，把选定的那一帧格式同时写进 Python 和 C 两边，不要指望复用本目录里现成的一段。

## 题目 PDF 位置

赛题 PDF 保留原中文名，放在对应年份目录里；`NUEDC_TOPIC-master/真题/` 是收录历届全部题目的题库（2021 的 F 题只在那里）：

| 赛题 | 文件 |
|---|---|
| 2021 F 智能送药小车 | `../NUEDC_TOPIC-master/真题/2021/F_智能送药小车.pdf`（另有 `F_智能送药小车数字字模.pdf`） |
| 2023 E 运动目标控制与自动追踪系统 | `2023_E_laser/E题_运动目标控制与自动追踪系统.pdf` |
| 2024 E 三子棋游戏装置 | `2024_E_tic_tac_toe/E题_三子棋游戏装置.pdf` |
| 2025 E 简易自行瞄准装置 | `2025_E_self_aiming/E题_简易自行瞄准装置.pdf` |

## 建议阅读顺序

1. `reference/basic_gpio/12，串口测试.py` → 确认 UART2 引脚与收发通。
2. `reference/image_recognition/4，矩形检测.py` 与 `离线调整阈值.py` → 两个基本功。
3. `2025_E_self_aiming/result/main_thresh_ui_fast.py` → 最短的完整视觉闭环（识别 → 预测 → 稳定判定 → 发帧 → 打激光）。
4. `2023_E_laser/main_high_fps.py` → 上面那个文件的状态机**祖先**，且它把 `Situation == 1` 写对了。
5. `2024_E_tic_tac_toe/main_tic_tac_toe.py` → 仓库里唯一带算法（Alpha-Beta 剪枝极小极大）的文件。

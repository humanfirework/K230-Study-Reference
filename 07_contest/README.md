# 07_contest —— 历年赛题（K230 部分）

本目录存放**在 CanMV K230（立创·庐山派）上跑的电赛赛题代码**，按年份分目录。非 K230 的代码（OpenMV / MaixPy / STM32 工程）不在这里，在仓库根的 `other_boards/`。

## 这里有什么

| 目录 | 赛题 | 代码量 | 状态（读代码核实，未上板） | 详情 |
| --- | --- | --- | --- | --- |
| `2021_F_drug_car/` | 2021 F 智能送药小车 | **0 个 `.py`**，只有一份 README | 没做过 | [README](2021_F_drug_car/README.md) |
| `2023_E_laser/` | 2023 E 运动目标控制与自动追踪 | 3 个主脚本（345 / 463 / 518 行）+ `variants/` 6 + `error/` 4 + `reference_gimbal/` 5 + `sample_code/` 2 + `yahboom_reference/` | 部分：`k230_full.py` 两处未定义名（[P1-7](../docs/02_known_issues.md#p1-7)）；`error2/3` 语法不过（[P0-5](../docs/02_known_issues.md#p0-5)）；`variants` 5 处未定义名（[P2-16](../docs/02_known_issues.md#p2-16)） | [README](2023_E_laser/README.md) |
| `2024_E_tic_tac_toe/` | 2024 E 三子棋游戏装置 | `main_tic_tac_toe.py` **1503 行**（真方案）+ 244 行空壳骨架 | 待上板：缺显式 `import os`（[P0-1](../docs/02_known_issues.md#p0-1)）；悔棋死代码（[P2-1](../docs/02_known_issues.md#p2-1)）；落点没交出去（[P2-2](../docs/02_known_issues.md#p2-2)） | [README](2024_E_tic_tac_toe/README.md) |
| `2025_E_self_aiming/` | 2025 E 简易自行瞄准装置（作者原创） | `result/` 3 个 main（655 / 987 / 451 行）+ `find_rect/` 4 脚本 + `iterations/` 9 + `error/` 2 | 待上板：三处走到就崩（[P1-6](../docs/02_known_issues.md#p1-6)）；"多限制"恒真门（[P1-1](../docs/02_known_issues.md#p1-1)）；调参 UI 覆盖阈值（[P1-2](../docs/02_known_issues.md#p1-2)） | [README](2025_E_self_aiming/README.md) |
| `laser_drawing/` | 非赛题：激光画图形 | 7 个脚本 + 1 个浏览器仿真页（含 1 个 0 字节占位） | 部分：`02_triangle_exposure.py` 4 处 `struct.pack` 错（[P0-2](../docs/02_known_issues.md#p0-2)）；`04`、`07` 不发帧（[P2-10](../docs/02_known_issues.md#p2-10)） | [README](laser_drawing/README.md) |
| `reference/` | 厂商例程（立创 + 01Studio + 亚博） | 28 个 `.py` | 厂商原件；两个 OCR/YOLO 例程缺 3 个 kmodel + `dict.txt`（[P3-22](../docs/02_known_issues.md#p3-22)） | [README](reference/README.md) |

各年份目录内还有自己的 README：逐文件说明、练习、"能不能跑"的细节。找具体文件先读年份 README，不要凭目录名猜。

## 题目 PDF

题面保留中文名，放在对应年份目录里；`NUEDC_TOPIC-master/真题/` 是收录历届全部题目的题库（2021 的 F 题只在那里）：

| 赛题 | 文件 |
| --- | --- |
| 2021 F 智能送药小车 | `../NUEDC_TOPIC-master/真题/2021/F_智能送药小车.pdf`（另有 `F_智能送药小车数字字模.pdf`） |
| 2023 E 运动目标控制与自动追踪系统 | `2023_E_laser/E题_运动目标控制与自动追踪系统.pdf` |
| 2024 E 三子棋游戏装置 | `2024_E_tic_tac_toe/E题_三子棋游戏装置.pdf` |
| 2025 E 简易自行瞄准装置 | `2025_E_self_aiming/E题_简易自行瞄准装置.pdf` |

## 能不能跑

上表是逐目录的读代码结论，**没有一条上板验证过**。每个年份的具体阻塞点、证据等级和改法，在年份 README 与 [docs/02](../docs/02_known_issues.md)。

## 串口协议：本目录没有统一的一套

同一个 UART2、同一块 STM32，各年份发的是互不兼容的帧。按字节布局至少能分出 6 族（`AA…55` 的 7 / 11 / 22–23 字节、`55 AA … FA` 的 6–10 字节、2024 的 `FF … FE`、亚博的 `A3 … C3`），仓库里**没有任何一个 STM32 工程**能解析本目录自写的 `AA…55`。

完整的帧布局、发送端索引、STM32 解析器的逐行流程和一份可用的重同步实现，都在 [docs/06_uart_protocol.md](../docs/06_uart_protocol.md)。**参赛时先定协议再写代码，把同一张表写进 Python 和 C 两边。**

## 练习与阅读顺序

练习：按下面顺序读，每读完一份写一句"它回答了题目的哪一问"。

1. `reference/basic_gpio/12，串口测试.py` → 确认 UART2 引脚与收发通。
2. `reference/image_recognition/4，矩形检测.py` 与 `离线调整阈值.py` → 两个基本功。
3. `2025_E_self_aiming/result/main_thresh_ui_fast.py` → 一条完整的视觉闭环（识别 → 预测 → 稳定判定 → 发帧 → 打激光），三个 2025 主程序里最短的一份。
4. `2023_E_laser/main_high_fps.py` → 上面那个文件的状态机祖先，而且它把 `Situation == 1` 判对了。
5. `2024_E_tic_tac_toe/main_tic_tac_toe.py` → 仓库里唯一带博弈算法（Alpha-Beta 剪枝极小极大）的文件。

## 相关

- [串口协议](../docs/06_uart_protocol.md) · [已知问题](../docs/02_known_issues.md) · [学习路线 · 阶段 5](../docs/03_learning_roadmap.md)
- 平台归类规则见 [`../other_boards/README.md`](../other_boards/README.md)：`from maix` → MaixPy，`pyb` / 全局 `sensor` → OpenMV，`.c/.h/.ioc` → STM32

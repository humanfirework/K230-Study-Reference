# other_boards —— 不跑在 K230 上的代码，按平台隔离

这里放的是同一个赛题系统的另一半，或者同一算法在另一块板子上的原型。判断依据是文件 import 了什么，而不是它当初躺在哪个赛题目录下。所有文件按原件保留，本仓库只做隔离和说明，不在这里改代码。

## 这里有什么

| 名字 | 平台 | 是什么 | 状态 |
| --- | --- | --- | --- |
| [`maixpy/`](maixpy/README.md) | MaixCAM（Sipeed MaixPy） | 1 个 `.py`：离线调阈值工具，触摸屏点按钮改 LAB 分量 | 平台不符 |
| [`openmv/`](openmv/README.md) | OpenMV | 5 个 `.py`：`2023_laser/` 绿/红一对；`nuedc_2025_e/` 程欢欢的 OpenMV4 版 2025 E 题（MIT，含 `激光矩形集中调参/`） | 平台不符 |
| [`stm32/`](stm32/README.md) | STM32F103C8T6 ×2、STM32F103ZET6 ×2 | 4 个 CubeMX + Keil 工程 + 1 个 `.c` 片段 | 需 Keil 与对应硬件 |

归位规则，看一眼文件头就能判断：

| 文件里出现 | 归到 |
| --- | --- |
| `from maix import …` | [`maixpy/`](maixpy/README.md) |
| `import sensor, image`（全局名）或 `from pyb import …` | [`openmv/`](openmv/README.md) |
| `.c` / `.h` / `.ioc` / `.uvprojx` | [`stm32/`](stm32/README.md) |

串口是这里最需要留意的一条：这些老工程的帧格式与 K230 侧的 `AA … 55` 对不上，唯一自洽的一对是亚博的 `A3 … C3`。完整对照见 [串口协议](../docs/06_uart_protocol.md)。

## 能不能跑

都不能在 K230 上跑：`maix` 与 `pyb` 在这块板子上不存在（读代码核实）。它们各自需要 MaixCAM、OpenMV、STM32 硬件，不属于你的平台。`openmv/nuedc_2025_e/` 连"在 OpenMV 上能不能跑"都未验证（待上板确认）。协议与缓冲区问题见 [P3-1](../docs/02_known_issues.md#p3-1)、[P3-23](../docs/02_known_issues.md#p3-23)。

## 练习

1. 从每个目录各挑一个文件，用文件头（import 或扩展名）判断它属于哪个平台；对 Python 文件再指出它在 K230 上会失败在哪一行。
2. 把 `openmv/2023_laser` 的 `A1` 帧与 [docs/06 的族表](../docs/06_uart_protocol.md)对上，写出它属于第几族、缺什么字段。
3. 读 `stm32/serial_packet/Core/Src/command.c:104-136`，说出 `AA … 55` 为什么会被逐字节丢掉。

## 相关

- 平台与串口：[docs/01 上手](../docs/01_getting_started.md)、[docs/06 串口协议](../docs/06_uart_protocol.md)
- 缺陷清单：[docs/02](../docs/02_known_issues.md)
- 官方入口（OpenMV、MaixPy、亚博、ST）：[docs/04](../docs/04_official_resources.md)
- 子目录：[maixpy](maixpy/README.md)、[openmv](openmv/README.md)、[stm32](stm32/README.md)

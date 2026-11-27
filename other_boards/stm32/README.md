# stm32 —— 系统的执行端（K230 看，这里动）

K230 算完坐标、发一串字节就结束了；转云台、走电机、跑闭环的是这里的固件。四个 CubeMX + Keil 工程加一个 `.c` 片段，都是厂商或工具生成的原件，工程内的文件名一个没改——改名会破坏 `.uvprojx` 里的相对路径。

## 这里有什么

| 工程 | 芯片 | 是什么 | 状态 |
| --- | --- | --- | --- |
| `oled_display/CODE/` | STM32F103C8T6 | CubeMX + Keil。I2C1 驱动 OLED，能显示中文；USART2 由 CubeMX 生成，`main.c` 没有解析逻辑 | 待上板确认（不解析帧） |
| `serial_packet/` | STM32F103C8T6 | 环形缓冲 + 帧解析（`Core/Src/command.c`），收到完整帧后原样回显，不接执行机构 | 待上板确认（回显骨架） |
| `yahboom_2023_green/` | STM32F103ZET6 | 亚博 2023 E 题绿端电控。`dsp/bsp_uart.c` 解析 10 字节 `A3 … C3`，PID + 电机 | 待上板确认（需亚博硬件） |
| `yahboom_2023_red/` | STM32F103ZET6 | 同方案红端/主控。解析 6 字节 `A3 … C3`，四个角点自算中心 | 待上板确认（需亚博硬件） |
| `snippets/uart_rx_tx.c` | — | 与 `serial_packet/Core/Src/command.c` 同一份代码，只差末尾一个换行（[P3-12](../../docs/02_known_issues.md#p3-12)） | 读代码核实（不能单独编译） |

### 四个工程怎么选

只做串口练习，用 `serial_packet`；要一块屏显示状态，用 `oled_display`；亚博两个工程是 2023 E 的完整电控，`dsp/` 下有串口解析和电机闭环，只有拿到对应硬件时才用得上。`snippets/uart_rx_tx.c` 不要单独建工程，它只是 `command.c` 的阅读副本。

### 每个工程的入口

| 工程 | 入口 | 先看什么 |
| --- | --- | --- |
| `oled_display` | `CODE/Core/Src/main.c` | `:90` I2C1 初始化、`:93` `OLED_Init()`、`:97` 中文显示 |
| `serial_packet` | `serial_packet/Core/Src/main.c:116-124` | 取帧后回显；那个空循环是留给你填 payload 的位置 |
| `yahboom_2023_*` | `2023 - */Core/Src/main.c` 与 `dsp/task.c` | 主循环的任务分支，以及 `dsp/` 的驱动分层 |

### 怎么编译

1. 装 Keil MDK 与 STM32F1 DFP；工程里缓存的是 `STM32F1xx_DFP.2.2.0`。
2. 打开对应 `.uvprojx`：`oled_display/CODE/MDK-ARM/CODE.uvprojx`、`serial_packet/MDK-ARM/Serial port packet.uvprojx`、`yahboom_2023_*/2023 - */MDK-ARM/2022.uvprojx`。
3. 改过 `.ioc` 就先 `Project → Generate Code`，再 F7 编译，ST-Link 下载。CubeMX 只重写它管的文件，`USER CODE BEGIN/END` 之间和 `dsp/` 这类自定义目录会保留。
4. 也可以直接烧仓库里的 `.hex`：`oled_display/CODE/MDK-ARM/CODE/CODE.hex`、`serial_packet/MDK-ARM/Serial port packet/Serial port packet.hex`。亚博两个工程没有 `.hex`，必须自己编译。
5. 两个工程路径含空格（`Serial port packet.uvprojx`、`2023 - green/`）。工具报"找不到文件"时先给路径加引号，别先怀疑工程坏了。
6. `Objects/`、`Listings/`、`*.axf` 已被根 `.gitignore` 排除，看不到编译产物是正常的；第一次打开要全量编译。

### 两个亚博工程解析的是什么

绿端 `bsp_uart.c` 判 `RxBuffer[9] == 0xC3`，取四对坐标；红端判 `RxBuffer[5] == 0xC3`，取一对坐标。两边都按大端拼 `(hi << 8) | lo`，红端再由四个角点自算中心。这是全仓库唯一一对能和 Python 发帧端对上的工程，但要求发送端颜色数固定，否则帧长变了会静默丢帧（读代码核实）。

### 为什么和 K230 的帧对不上

格式不同，`AA … 55` 全部被逐字节丢弃（偶发 `0xAA` 可能凑出假帧）。第二字节在你的代码里是 `flag`，解析器却把它当成整帧长度；长度取 1 时校验和算出来是 0，与帧头的 `0xAA` 比，必然不等。解析器的门槛是 `command.c:108` 的 `< 4` 和 `:118` 的 `< length`。完整帧布局、流程图和十族对照在 [docs/06](../../docs/06_uart_protocol.md)，这里不重画。

### 环形缓冲的三处边界

1. `Command_GetLength()` 用 `% BUFFER_SIZE` 算长度（`command.c:58-60`），取值域是 0..127，所以 128 字节的数组最多只报 127。
2. `Command_GetRemain()` 是 `128 - GetLength()`（`:70-71`）。缓冲区空时它返回 128，于是 `Command_Write(data, 128)` 的 `GetRemain() < length` 判断为假，被允许写满；写满后 `writeIndex` 绕回与 `readIndex` 重合，`GetLength()` 立刻返回 0，主循环把这 128 字节当成"空"，整批丢掉。
3. `writeIndex + length < BUFFER_SIZE` 应为 `<=`（`:86`）：恰好填满时数据本来都落在数组内，不必进绕回分支；当前写法也是上面那条路径的触发点之一。

以上都是读代码核实。第 2 条是"满"被当成"空"的典型写法，改缓冲区别只改容量。

### 先读哪三个文件

- `serial_packet/Core/Src/command.c`：帧提取加环形缓冲，全目录最短的一份解析器。
- `yahboom_2023_*/dsp/bsp_uart.c`：中断收包、大端拼坐标、按帧尾判完整。
- `oled_display/CODE/Core/Src/main.c`：CubeMX 生成的骨架，以及中文取模显示怎么调用。

## 能不能跑

四个工程的 CubeMX/Keil 结构齐全，能否编译通过待上板确认；需要 Keil、STM32F1 DFP 和对应硬件，当前没有已上板验证。`serial_packet` 的 payload 处理是空的（`serial_packet/Core/Src/main.c:120-124`），只回显；`oled_display` 不解析帧。`snippets/uart_rx_tx.c` 的 `#include "command.h"` 只声明了 6 个函数中的 2 个，单独放进任何工程都编译不过（[P3-1](../../docs/02_known_issues.md#p3-1)）。`.pack/` 缓存 1310 个文件、约 156 MB 在版本库里（[P3-24](../../docs/02_known_issues.md#p3-24)），不影响正确性，瘦身见 [docs/07](../../docs/07_maintenance.md#8-gitignore-与仓库体积)。

## 练习

1. 编译 `serial_packet` 并烧进去，确认它能回显自己解析出的帧。
2. 用串口助手发 `AA 05 01 00 B0`（长度 5；校验和 = `AA+05+01+00` 的低 8 位），确认它被接受并回显；再把 `B0` 改成 `00`，确认整帧被丢弃。
3. 把 `AA … 55` 帧接进去，观察它被逐字节丢弃；再让 `0xAA` 出现在 payload 里，看是否凑出假帧。
4. 修环形缓冲的 `<=`，写一个"写满 128 字节再读"的用例。

## 相关

- 串口协议与族表：[docs/06](../../docs/06_uart_protocol.md)
- 缺陷：[P3-1](../../docs/02_known_issues.md#p3-1)、[P3-12](../../docs/02_known_issues.md#p3-12)、[P3-24](../../docs/02_known_issues.md#p3-24)
- 仓库体积与忽略规则：[docs/07](../../docs/07_maintenance.md#8-gitignore-与仓库体积)
- 官方入口（ST、亚博）：[docs/04](../../docs/04_official_resources.md)
- 上级目录：[`other_boards/README.md`](../README.md)

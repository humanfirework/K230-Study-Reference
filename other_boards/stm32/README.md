# stm32 — 系统的另一半（K230 只负责"看"，这里负责"动"）

## 直接回答那句常被问的话：「STM32 那堆东西有用吗？」

**有用。而且没有它，你的整套装置根本不会动。**

分工是这样：

| | 干什么 | 不干什么 |
|---|---|---|
| **K230（CanMV）** | 采集图像、二值化、找矩形/色块、算目标中心、做外推、把坐标发出去 | ❌ 不转云台、不走步进电机、不做闭环 PID |
| **STM32（本目录）** | **解析串口帧**、跑 PID、输出 PWM 驱动两轴云台/电机、驱动 OLED 显示状态 | ❌ 完全不看摄像头 |

K230 上那些 `AA … 55` 帧发出去之后，**接收方就是这里的代码**。把本目录当"没用的老代码"删掉，等于把你装置的执行端删掉。

> 顺带一句：本目录里 `snippets/uart_rx_tx.c` 是最能说明"两边对接"这件事的文件 —— 它**恰好和所有 Python 端对不上**，见下面「关键：协议对不上」。这也是它被保留着的原因，不是它的缺陷。

## 内容清单

四个完整的 STM32CubeMX + Keil MDK 工程（每个都有 `.ioc` 和 `MDK-ARM/*.uvprojx`）+ 一个独立 `.c` 片段。

| 目录 | 目标芯片（读自 `.ioc`） | 是什么 | 状态 |
|---|---|---|---|
| `oled_display/` | **STM32F103C8T6**（`Mcu.Name=STM32F103C(8-B)Tx`） | CubeMX 工程 `CODE.ioc` + Keil `CODE/MDK-ARM/CODE.uvprojx`。I2C1 驱动 OLED，含 `OLED.c` / `OLED_Font.c`（**能显示中文**：`OLED_ShowCHinese(0, 4, 0, 16)`）。`main.c` 第 93~97 行初始化 + 显示数字/字符串/中文；USART2 由 CubeMX 生成（`MX_USART2_UART_Init()`）**但 `main.c` 里没有任何解析逻辑** | 可用（纯显示例程，**不解析任何帧**） |
| `serial_packet/` | **STM32F103C8T6** | **串口分包接收的骨架工程**（`Serial port packet.ioc`）。`Core/Src/command.c` 实现环形缓冲 + `Command_GetCommand()` 帧提取；`main.c` 第 116~124 行拿到帧后**原样 UART 回显**，那个 `for(int i = 2; i < commandLength - 1; i += 2)` 循环体是空的 —— 那就是留给你填"从 payload 逐对取坐标"的位置 | 可用（**是骨架，不是成品**） |
| `yahboom_2023_green/` | **STM32F103ZET6**（`2022.ioc`） | 亚博 2023 E 题方案的**绿光端电控**：`dsp/bsp_uart.c` 解析 K230 帧（要求 10 字节：`A3 + 4×(x_hi,x_lo) + C3`，红/绿激光各一对坐标），`pid_motor.h` + TIM2/TIM3/TIM5/TIM6 驱动电机，OLED 实时显示 `Red_X` / `Green_X` | 可用（第三方，需亚博硬件） |
| `yahboom_2023_red/` | **STM32F103ZET6** | 同一方案的**红光/主控端**：`bsp_uart.c` 解析 6 字节帧（`A3 + (x_hi,x_lo) + (y_hi,y_lo) + C3`，判据是 `RxBuffer[5] == 0xC3`）或 `B3` 开头的多点包；`main.c` 第 127~128 行**由四个角点自己算中心**（`Midpiont_X = ((Top_Left_X+Top_Right_X)/2 + (Lower_Left_X+Lower_Right_X)/2)/2`），并用 `HAL_TIM_PWM_Stop_IT(&htim2, TIM_CHANNEL_2)` 等控制运动 | 可用（第三方，需亚博硬件） |
| `snippets/uart_rx_tx.c` | — | 136 行独立 `.c` 片段（**没有配套 `.h`**）。它就是 `serial_packet/Core/Src/command.c` 的前身/同源文件：两者实测**只差文件末尾一个换行符**（`diff` 只报 line 137）。原属 `02_data_collection/`，因为它是"抄下来准备改的通用代码"而不是 K230 代码，`28b5f40` 移到这里 | 不完整（见「已知问题」） |

## 怎么编译

**这些是 STM32 工程，不能在 K230/CanMV 上"运行"，也不要用 CanMV IDE 打开。**

### 通用步骤（两个 LCKFB 风格工程 + 两个亚博工程都适用）

1. 装 **STM32CubeMX**（ST 官方，免费）与 **Keil MDK-ARM**（µVision）。两个工程都是 MDK 项目，`.uvprojx` 是 µVision 工程文件。
2. **改芯片支持包**：`MDK-ARM/RTE/_*/RTE_Components.h` 与 Keil 的 Pack Installer 关联。若提示缺 `STM32F1xx_DFP`（本仓库 `.pack` 缓存里那个版本是 **2.2.0**），在 Pack Installer 里装 `STM32F1 Series → Device Family Pack` 即可。
3. **如果 `.pack` 被删过**（见下面"体积"一节）：打开 Keil → `Project → Manage → Run-Time Package for Micromulator` → 勾选 `STM32F1xx_DFP` → Keil 会自动重新下载，**不需要**从本仓库找回。
4. 打开工程：µVision → `Project → Open Project` → 选
   - `oled_display/CODE/MDK-ARM/CODE.uvprojx`
   - `serial_packet/MDK-ARM/Serial port packet.uvprojx`（⚠️ **路径含空格**，个别旧版本工具链对空格敏感，编译报错先怀疑这点）
   - `yahboom_2023_green/2023 - green/MDK-ARM/2022.uvprojx` 或同目录的 `2023-green.uvprojx`（两份工程文件都在，后者配 `2023-green.code-workspace`，即作者还用了 **EIDE 扩展**）
   - `yahboom_2023_red/2023 - red/MDK-ARM/…uvprojx`
5. **想改外设/引脚就改 `.ioc`**：`oled_display/CODE/CODE.ioc`、`serial_packet/Serial port packet.ioc`、`yahboom_2023_*/2023 - */2022.ioc`。用 CubeMX 打开 → 改 → `Project → Generate Code`。⚠️ 生成只会重写 CubeMX 管的文件，`Core/Src/main.c` 里 `USER CODE BEGIN/END` 注释块**之间**的内容与 `dsp/` 这类自定义目录会保留 —— 别把自定义代码写在生成区里。
6. 编译：F7。下载到板子用 ST-Link（`DebugConfig/*_STM32F103C8_1.0.0.dbgconf` / `…F103ZE…` 是调试配置）。
7. `Objects/`、`Listings/`、`*.axf`、`*.map`、`*.o` **已被仓库根 `.gitignore` 排除**，所以你看不到编译产物是正常的 —— 第一次打开就得自己全量编译，慢是预期的。
8. 预编译好的固件：`oled_display/CODE/MDK-ARM/CODE/CODE.hex` 与 `serial_packet/MDK-ARM/Serial port packet/Serial port packet.hex` **在仓库里**（`.hex` 没被 ignore），用 ST-Link 或飞线直接烧这两个就行，不必装 Keil。

### 想跳过 Keil

`.hex` 直接用 ST-Link Utility / STM32CubeProgrammer 烧。**但亚博那两个工程没有 `.hex`**，必须自己编译。

## ⚠️ 关键：这里的解析器和你的 K230 代码**对不上**

### `snippets/uart_rx_tx.c`（与 `serial_packet`）要的帧

读 `Command_GetCommand()`（第 104~136 行）逐条推出来的：

```
byte[0] = 0xAA           ← 第 112 行硬判：不是 0xAA 就丢一个字节继续找
byte[1] = length         ← 第 117 行：**整帧总长度**（含帧头、长度字节、校验和）
byte[2 .. length-2]      = payload
byte[length-1] = 校验和   ← 第 122~126 行：sum = Σ byte[0 .. length-2]，与末字节比对，不等就跳过 1 字节重找
COMMAND_MIN_LENGTH = 4    ← 第 4 行：不足 4 字节不处理
```

### 你的 K230 Python 实际发的帧

```
b'\xAA' + struct.pack('<BHH', flag, x, y) + b'\x55'
→ AA | flag | x_lo | x_hi | y_lo | y_hi | 55   （共 7 字节）
```

**没有长度字节，没有校验和。** 出处：`../../07_contest/2025_E_self_aiming/result/main_thresh_ui_fast.py:436,442`、`main_thresh_ui_accurate.py:727,733`、`main_multi_constraint.py:235,241`、`../../07_contest/2023_E_laser/main_high_fps.py:145,151`，以及 `../../07_contest/laser_drawing/{01,03,06}…` 与 `../../07_contest/2025_E_self_aiming/methods_reference/iterations/` 全部 9 个文件。

### 后果

把这个 C 解析器接到你的 K230 上：**`Command_GetCommand()` 永远返回 0，每一帧都被丢弃。**
机制具体是这样：`byte[0] == 0xAA` 侥幸通过 → `length = Command_Read(readIndex+1) = flag`（0 或 1）→ `Command_GetLength() < 1` 时返回 0；等缓冲里攒够后，第 122~126 行拿前 `length-1` 字节的和与末字节比，`flag=1` 时它只比对 1 个字节，**几乎必然不等** → `Command_AddReadIndex(1)`，重新开始。如此反复，直到那个 `0x55` 帧尾被当成一次新的搜索起点。**你看到的是"STM32 一个字节都没解出来"。**

### 全仓库帧格式对照表（谁发 ↔ 谁解析）

| # | 帧格式 | 谁发 | 谁解析 | 能对上吗 |
|---|---|---|---|---|
| 1 | `AA \| flag:B \| x:H \| y:H \| 55`（7 B，**小端**，无校验） | 2023 `main_high_fps.py`、2025 三个 main、2025 `iterations/` 全部、`laser_drawing/{01,03,06}` | **无** | ❌ |
| 2 | `AA \| B+10H（5 点） \| 55`（23 B） | `../../07_contest/2023_E_laser/k230_full.py:84`、`../../07_contest/2023_E_laser/variants/k230_basic.py:84` | **无** | ❌ |
| 3 | `AA \| B+4H（2 点） \| 55`（11 B） | `../../07_contest/2023_E_laser/variants/k230_basic.py:62`、`../../07_contest/laser_drawing/{01,03,06}` 的 `send_tracking_data` | **无** | ❌ |
| 4 | `AA \| <BHHHH> \| 55` 但**只传 3 个实参** → `struct.error` | 2023 `k230_full.py:59,66` | — | ❌（发送端就抛异常） |
| 5 | `AA \| B+10H \| 55`（23 B，4 角点+中心） | `laser_drawing/{01,03,06}` 的 `send_rect_data` | **无** | ❌ |
| 6 | `FF \| 任务ID \| float32… \| FE` | 2024 `main_tic_tac_toe.py` | 同一文件自己的 `receive_and_unpack()`（K230↔K230 自环） | ⚠️ 只对自己 |
| 7 | `AA \| len \| payload… \| sum` | **无 Python 端** | ✅ `snippets/uart_rx_tx.c`、`serial_packet/` | ❌（没人发给它） |
| 8 | `A3/B3 \| (x_hi,x_lo,y_hi,y_lo)×N \| C3`（**大端**） | `../../07_contest/2023_E_laser/yahboom_reference/get_rect.py:92,260`、`get_light3.py:84` | ✅ `yahboom_2023_red/…/dsp/bsp_uart.c`（6 B，判 `RxBuffer[5]==0xC3`） | ✅ **唯一自洽的一对** |
| 9 | `A3 \| (x_hi,x_lo,y_hi,y_lo) × N \| C3`，N = 检出颜色数 | `get_light3.py:84`（`best_points` 来自 `color_list`，红+绿两色 → N=2 → 8 B payload → **共 10 B**） | ✅ `yahboom_2023_green/…/dsp/bsp_uart.c`（判 `RxBuffer[9]==0xC3`，取 `Red_X=buf[1..2]`、`Red_Y=buf[3..4]`、`Green_X=buf[5..6]`、`Green_Y=buf[7..8]`） | ✅ 对得上，**但前提是 `color_list` 里正好两种颜色**（改成 1 种发 6 B、3 种发 14 B，`RxBuffer[9]` 就不是 `0xC3` 了，会静默丢帧） |
| 10 | `A1 02 flx dx fly dy 1A`（带符号**增量**）等 | `openmv/2023_laser/{green,red}.py` | **无** | ❌ |
| — | `DATA,<lx>,<ly>,<rx>,<ry>\r\n`（ASCII） | `openmv/nuedc_2025_e/激光矩形集中调参/…:180` | **无** | ❌ |
| — | 步进电机指令 `AA AA num dir steps_hi steps_lo sum FF FF`（**大端** steps + 累加和） | 2023 `basic_part.py:42-49` | 步进驱动器（非 STM32） | ✅ 但那是驱动器协议 |

**结论**：全仓库**唯一能直接对上**的是第 8、9 两行（亚博自己的那对 Python ↔ STM32 工程），而它是**大端** —— 你自己所有代码是**小端**。
赛场上的正确做法：**先定协议，再写代码**，同时改 Python 与 C 两边 —— 别指望复用现成的某一段。要练对接，就用第 7 行那对（`serial_packet`）当基础，把 Python 端改成 `AA + len + payload + sum`。

## 旧名 → 新名

`89e6ffc`（`电赛赛题K230` → `07_contest`）时它们还留在 `07_contest/reference/stm32/` 和 `07_contest/2023_E_laser/yahboom_reference/` 下；`28b5f40` 才把它们移出。工程内部文件**一个都没改名**。

| 最原始（`f2aa2af` / `5b4dd92`） | `89e6ffc` 之后 | 现在（`28b5f40`） |
|---|---|---|
| `电赛赛题K230/00_Reference/STM32/OLED/CODE/` | `07_contest/reference/stm32/OLED/CODE/` | **`other_boards/stm32/oled_display/CODE/`** |
| `电赛赛题K230/00_Reference/STM32/Serial port packet/` | `07_contest/reference/stm32/Serial port packet/` | **`other_boards/stm32/serial_packet/`** |
| `赛题K230/02_2023_E_Laser/K230参考/2023 - green/2023 - green/` | `07_contest/2023_E_laser/yahboom_reference/2023 - green/2023 - green/` | **`other_boards/stm32/yahboom_2023_green/2023 - green/`** |
| `赛题K230/02_2023_E_Laser/K230参考/2023 - red/2023 - red/` | `07_contest/2023_E_laser/yahboom_reference/2023 - red/2023 - red/` | **`other_boards/stm32/yahboom_2023_red/2023 - red/`** |
| `02_Data_Collection/04_串口收发.c` | `02_data_collection/04_uart_rx_tx.c` | **`other_boards/stm32/snippets/uart_rx_tx.c`** |
| 上述各工程内部（`.ioc` / `Core/` / `MDK-ARM/` / `dsp/` 全部文件） | 原名保留 | **原名保留**（`2022.ioc`、`Serial port packet.uvprojx`、`bsp_uart.c`、`pid_motor.h` 等一个未改） |

⚠️ 为什么工程内文件名不改：它们是 CubeMX/Keil **自动写入** `.uvprojx` 的相对路径。改一个 `.c` 的文件名而不同步改工程文件，Keil 直接报"找不到源文件"。**这些是第三方/工具生成的工程，不是你的代码，改名等于搞坏它。**

`28b5f40` 的语义也值得记一笔：这次搬迁**不是删掉这些代码，而是把它们挪到该在的地方**。它们原本挂在 `reference/`（参考）和 `yahboom_reference/`（亚博参考）下面，看起来像"可看可不看的例程"；实际上它们是**你的装置必须烧的那一份固件**。

## 已知问题（逐条在文件里核对过）

### `snippets/uart_rx_tx.c` 的三个问题

1. **`#include "command.h"`（第 1 行）—— 本目录的 `snippets/` 里没有这个头文件。**
   它在 `serial_packet/Core/Inc/command.h`。而且那个头文件**只声明了两个函数**：
   ```
   uint8_t Command_Write(uint8_t *data, uint8_t length);
   uint8_t Command_GetCommand(uint8_t *command);
   ```
   本片段却**定义并使用**了 `Command_AddReadIndex()`、`Command_Read()`、`Command_GetLength()`、`Command_GetRemain()` —— 这四个头文件里没有。所以这个 `.c` **不能脱离 `serial_packet` 工程单独编译**：把 `command.h` 拷到 `snippets/` 也会因为那几个函数没有原型/`static` 声明而在严格编译下报 warning/error。
   它的正确用法：**当成 `serial_packet/Core/Src/command.c` 的"原始草稿"来读**（两者实测只差一个末尾换行），或者直接把它连同配套 `command.h` 一起拷进你自己的 CubeMX 工程 `Core/Src/` + `Core/Inc/`。

2. **环形缓冲区差一（off-by-one）：容量实际只有 127，且写满 128 字节会"读作空"，静默丢全部数据。**
   ```
   #define BUFFER_SIZE 128
   uint8_t Command_GetLength()  { return (writeIndex + BUFFER_SIZE - readIndex) % BUFFER_SIZE; }   // 第 58~60 行
   uint8_t Command_GetRemain()  { return BUFFER_SIZE - Command_GetLength(); }                        // 第 70~72 行
   ```
   - `% BUFFER_SIZE` 的取值域是 **0..127**，所以 `GetLength()` **永远报不出 128** —— 明明 128 字节的数组，可用容量只有 127。
   - `GetRemain()` 在缓冲区**空**的时候返回 **128**（128 − 0）。于是 `Command_Write(data, 128)` 的第 82 行判断 `GetRemain() < length` → `128 < 128` 为**假** → **允许一次写满 128 字节**。
   - 写满之后 `writeIndex` 绕回与 `readIndex` **重合**（第 86~93 行走 `else` 分支：`firstLength = 128 - writeIndex`，末尾 `writeIndex = length - firstLength`），`GetLength()` 立刻返回 **0** → 主循环认为"缓冲区为空"，**那 128 字节全部无声丢失**。
   - 讽刺的是文件里第 41~56 行**注释掉的那个旧版本**是显式区分了空/满两种状态的（`writeIndex + 1 == readIndex` 判满、返回 `BUFFER_SIZE`）。**改成取模写法的人把"满"这个状态弄丢了。** 这是环形缓冲区的教科书级经典 bug，值得专门看一眼。
   - 关于第 86 行的 `if (writeIndex + length < BUFFER_SIZE)`：**它应该是 `<=`**（`writeIndex + length == 128` 时数据完全落在数组内，不必绕回）。当前写法不是"错到破坏数据"，但会把恰好填满数组的那一次写推进绕回分支，与上面第 3 点合起来正是"写满 128 → 读作空"的触发路径之一；同时也多了一次长度为 0 的 `memcpy`。

3. **`readIndex` / `writeIndex` 是 `uint8_t`（第 11、13 行，注释还写着 `//0~255`）。** 这个类型刚好能装下 0..127 的下标，**但注释说明作者当时以为它能到 255**，这正是上面那组混淆的来源。（`Command_Read(uint8_t i)` 第 29~32 行用 `i % BUFFER_SIZE` 兜住了越界读取，所以越界不会踩内存，只会读到错位的旧数据。）

### 其他

4. **`serial_packet` 的 payload 处理是空的。** `Core/Src/main.c` 第 119~123 行那个 `for (int i = 2; i < commandLength - 1; i += 2)` **循环体内什么都没有**（只有一行空注释和一次多余的 `,`）。整个工程的实际行为是**把收到的完整帧原样 `HAL_UART_Transmit` 回显**。它是"分包接收怎么写"的教学骨架，**不是能直接交付的电控程序**。

5. **`oled_display` 不解析任何帧。** `main.c` 里只有 `MX_USART2_UART_Init()`（CubeMX 自动生成）与 `Error_Handler` 里的 `printf`；全文**没有 `Command_*` 调用**。别以为它能配合 K230 收坐标 —— 它只演示 OLED（含中文取模显示）。

6. **两个 `yahboom_2023_*` 工程里各带约 78 MB 的 Keil `.pack` 器件支持包缓存。**
   实测（`du -sh`）：
   ```
   88M  yahboom_2023_green/2023 - green      ← 其中 78M 是 2023 - green/MDK-ARM/.pack/
   88M  yahboom_2023_red/2023 - red          ← 其中 78M 是 2023 - red/MDK-ARM/.pack/
   68M  oled_display/CODE                    ← Drivers/（CMSIS + STM32F1xx_HAL_Driver）
   68M  serial_packet                        ← Drivers/（同上）
   ```
   `.pack/` 里是完整的 `Keil/STM32F1xx_DFP.2.2.0`（含 `Boards/…/Blinky.uvprojx`、`Middleware/CAN/…` 等几百个 ST 例程）。
   **它是可再生的**：Keil 的 Pack Installer 会重新下载同一份包（见上面"怎么编译"第 3 步）。
   ⚠️ **本目录当前不删除它，一个文件都没动。是否清掉由仓库主人决定**（代价对比：留着 = 仓库多 ~156 MB 且离线也能编译；删掉 = 首次编译要联网下载 DFP，但 `.ioc` / `Core/` / `dsp/` 全部不受影响）。真要清，也应连同 `.gitignore` 一起加规则（`*.pck` 已经在忽略列表里了，但 `.pack/` 目录本身没有），**并且要先确认 `git` 里已被跟踪的那些 `.pack` 文件是否要一并处理** —— 这一步不要顺手做。

7. **`serial_packet` 与 `yahboom_*` 的路径含空格**（`Serial port packet.uvprojx`、`2023 - green/`）。某些 shell / CI / 旧工具链对空格路径处理不干净；报"找不到文件"时先给路径加引号，别怀疑工程本身坏了。这些名字是 CubeMX/Keil 按工程名自动生成的，**不建议改名**（改一次要同步 `.uvprojx` 内部所有路径）。

## 练习建议

1. **用现成 `.hex` 把"帧发出去 → STM32 收不到"这个事故亲眼复现一遍（必须计数）**
   任务：`serial_packet/MDK-ARM/Serial port packet/Serial port packet.hex` 直接烧进一块 STM32F103C8T6（不用装 Keil）。ST-Link 的串口或 USB-TTL 接 USART2，同时 K230 跑 `../../07_contest/2025_E_self_aiming/result/main_thresh_ui_fast.py` 发 `AA…55` 帧。
   **通过标准**：① 统计 K230 端打印的 `数据帧:` 条数与 STM32 回显（它会把解出的帧原样发回来）的字节数，**回显必须为 0 字节**，且 K230 至少发了 100 帧；② 把 `Command_GetCommand()` 里 `return 0;` 的两个位置各加一行 `printf("len=%d chk=%d\n", length, sum);`，抓 ≥20 行输出，**用它们解释每一帧是在哪一步被丢的**（是 `GetLength() < COMMAND_MIN_LENGTH`、还是 `!= 0xAA`、还是校验和不等）。
   只有拿到"回显恒为 0"+"具体在哪一步丢"这两组证据，你才算真的理解协议为什么必须两边同时改。

2. **把第 8 号格式（唯一自洽的那对）拆开验证字节序**
   任务：烧 `yahboom_2023_red/`，用 `../../07_contest/2023_E_laser/yahboom_reference/get_rect.py` 的组包写法（`bytes([0xA3, x_hi, x_low, y_high, y_low, 0xC3])`）手动构造一帧 `x=300, y=200`。
   **通过标准**：STM32 OLED 上 `Top_Left_X` / `Top_Left_Y` 显示的必须是 300 / 200（大端拼接：`(0x01<<8)|0x2C = 300`、`(0x00<<8)|0xC8 = 200`）。然后**把 Python 端换成 `struct.pack('<HH', 300, 200)` 重发一次**（发出字节 `2C 01 C8 00`），OLED 上应变成 `11265` / `51200`（`(0x2C<<8)|0x01 = 0x2C01`、`(0xC8<<8)|0x00 = 0xC800`）—— 把这个错值抄进报告，并用它反推"字节序错了会偏多少倍"。**能算对这一步，你以后就不会在赛场把大小端搞混。**

3. **量一次你自己那套 `AA…55` 帧在 115200 上的真实带宽余量（必须出数字）**
   任务：`main_thresh_ui_fast.py` 主循环里每帧发一次 `AA+flag+x+y+55`（7 字节）。把 UART2 波特率改成 `9600 / 38400 / 115200 / 460800` 各跑一次。
   **通过标准**：每个波特率记录 ① 屏幕 FPS 均值（30 次）；② 逻辑分析仪/串口助手实测收到的帧数与"应有帧数"之比（丢帧率）；③ 单帧在线上的传输耗时（`7 × 10 / baud`，自己算一遍再用示波器核对）。
   **判据**：找出"丢帧率 = 0 且 FPS 相比 460800 档下降 < 10%"的最低波特率，并说明**为什么波特率提高不一定让系统更快**（`uart2.flush()` 与 `time.sleep_ms(6)` 这类阻塞点在哪一行、各自花多少）。第 ③ 项不许只写公式——量出来的数与公式差多少，那个差值就是 `flush()` 的开销。

4. **（可选，做完前 3 题再考虑）把 `snippets/uart_rx_tx.c` 的差一 bug 修掉并证明修对了**
   任务：把 `GetLength()` 换成能区分空/满的写法（或按第 41~56 行注释掉的原版思路），把 `writeIndex + length < BUFFER_SIZE` 改成 `<=`。
   **通过标准**：写一个"灌 128 字节"的测试：主循环里一次性 `Command_Write(data, 128)`，然后**要求 `Command_GetLength()` 报告非 0**（改前它报 0 = 全部丢失）。把改前改后的 `GetLength()` 返回值都记下来。再加一组 127 字节与一组 129 字节（应被拒绝、返回 0）作为边界。三组数字齐了才算过。

# other_boards — 不是 CanMV K230 的代码

## 这个目录的划分依据只有一个问题

> **「这段代码能在 CanMV K230 上跑吗？」**

答案由**文件 import 了什么**决定，**不是**由它当初躺在哪个文件夹里决定。这就是本目录存在的理由：以前 OpenMV 的代码混在 `07_contest/2023_E_laser/sample_code/` 里、另一个人的 OpenMV 方案混在 `07_contest/2025_E_self_aiming/methods_reference/` 里、STM32 的 Keil 工程混在 `07_contest/reference/` 里 —— 它们看起来像 K230 代码，因为它们在 K230 赛题目录下面。

判定规则（照这个规则，任何新文件都能在 3 秒内归位）：

| 首行/导入出现 | 归到 | 在 K230 上会怎样 |
|---|---|---|
| `from maix import …` | [`maixpy/`](maixpy/README.md) | 第一条 import 就 `ModuleNotFoundError` |
| `import sensor, image, time` / `from pyb import …` | [`openmv/`](openmv/README.md) | K230 没有 `pyb`，也没有全局 `sensor` 模块 |
| `.c` / `.h` / `.ioc` / `.uvprojx` | [`stm32/`](stm32/README.md) | **不是 Python，本来就不该在 K230 上跑** —— 它是系统的另一半 |

## ⚠️ 这里没有任何一份是垃圾

移动这些文件时最容易产生的误解就是"被挪出去的 = 没用的 = 可以删的"。**不是。**

- **`stm32/` 是整套系统的一半。** K230 **只负责看**。它算出坐标、发一串字节出去，然后呢？云台谁转、步进电机谁走、闭环谁做？**是 STM32。** 没有这些工程，你的 K230 程序就只是一块会打印数字的摄像头。详见 [`stm32/README.md`](stm32/README.md)。
- **`openmv/nuedc_2025_e/` 是别人为同一道 2025 E 题写的完整解法**，MIT 许可，含作者自己的调参工具。它是"另一个队怎么做这道题"的实物参考，也是**全仓库最容易被误当成自己的代码抄走的东西**（它以前就无标注地躺在你的 2025 目录里）。
- **`maixpy/` 那份 124 行的脱机阈值调节器**是你自己 `06_practice/` 时期的作品（旧名 `平时练习/9,脱机调阈值.py`），只是目标平台换了。它的思路仍然有用，而且**K230 上的等价实现已经存在**：`06_practice/01_all_in_one.py` 第 128 行的 `handle_threshold_adjustment()`。

一句话：**这里的东西不该被删，只该被正确标注。**

## 目录内容

| 子目录 | 内容 | 文件数 |
|---|---|---|
| [`maixpy/`](maixpy/README.md) | Sipeed MaixPy（MaixCAM）的脱机阈值触摸屏调节器 | 1 个 `.py`（124 行） |
| [`openmv/`](openmv/README.md) | OpenMV 代码：`2023_laser/`（绿/红激光追踪 2 个）+ `nuedc_2025_e/`（程欢欢的 2025 E 题 OpenMV4 方案，含 MIT `LICENSE`、`.gitignore`、`激光矩形集中调参/` 工具） | 5 个 `.py` + 3 个辅助文件 |
| [`stm32/`](stm32/README.md) | STM32CubeMX + Keil MDK 工程：`oled_display/`、`serial_packet/`、`yahboom_2023_green/`、`yahboom_2023_red/` + `stm32/snippets/uart_rx_tx.c` | 4 个完整工程（各含 `.ioc` 与 `MDK-ARM/*.uvprojx`）+ 1 个 `.c` 片段 |

## 旧名 → 新名

全部搬迁由 **`28b5f40`**（"Separate non-K230 code into other_boards/, PC-side script into pc_tools/"）完成。下表列**跨目录**的搬迁；各子目录内部还有更完整的对照表。

| 旧路径 | 现在 |
|---|---|
| —（本目录由 `28b5f40` 新建） | `other_boards/` |
| `06_practice/09_offline_threshold_WIP.py` | `other_boards/maixpy/offline_threshold_tuner.py` |
| `07_contest/2023_E_laser/sample_code/green.py` | `other_boards/openmv/2023_laser/green.py` |
| `07_contest/2023_E_laser/sample_code/red.py` | `other_boards/openmv/2023_laser/red.py` |
| `07_contest/2025_E_self_aiming/methods_reference/NUEDC-2025-E-master/`（整目录，6 项） | `other_boards/openmv/nuedc_2025_e/` |
| `07_contest/reference/stm32/OLED/CODE/` | `other_boards/stm32/oled_display/CODE/` |
| `07_contest/reference/stm32/Serial port packet/` | `other_boards/stm32/serial_packet/` |
| `07_contest/2023_E_laser/yahboom_reference/2023 - green/2023 - green/` | `other_boards/stm32/yahboom_2023_green/2023 - green/` |
| `07_contest/2023_E_laser/yahboom_reference/2023 - red/2023 - red/` | `other_boards/stm32/yahboom_2023_red/2023 - red/` |
| `02_data_collection/04_uart_rx_tx.c` | `other_boards/stm32/snippets/uart_rx_tx.c` |

再往前追一层（`89e6ffc` 及更早）：
`reference/stm32/…` ← `电赛赛题K230/00_Reference/STM32/…`；
`2023_E_laser/sample_code/green.py` ← `电赛赛题K230/02_2023_E_Laser/示例代码/green.py` ← `赛题K230/02_2023_E_Laser/示例代码/green.py`（`f2aa2af` 初始提交）；
`06_practice/09_offline_threshold_WIP.py` ← `平时练习/9,脱机调阈值.py`；
`02_data_collection/04_uart_rx_tx.c` ← `02_Data_Collection/04_串口收发.c`。

## ⚠️ 全仓库串口协议：本目录是问题的另一半

`other_boards/stm32/` 里的 C 解析器和 `07_contest/` 里的 Python 发送端**说的是不同的方言**。完整表（实测 10 种互不兼容格式）在 [`../07_contest/README.md`](../07_contest/README.md)，本目录这边最需要知道的三条：

1. `stm32/snippets/uart_rx_tx.c` 与 `stm32/serial_packet/` 期望 `AA + 长度 + 数据 + 累加和校验`。
2. 而**本仓库每一个 K230 Python 脚本**发的都是 `AA + 类型 + x(2B) + y(2B) + 55`，**既没有长度字节，也没有校验和**。
3. 结论：**那个 C 解析器会把你的 Python 送来的每一帧都丢掉。** 不是"偶尔丢帧"，是 100% 丢。

唯一自洽的一对是 `yahboom_2023_green` / `_red` ↔ `../07_contest/2023_E_laser/yahboom_reference/`（`A3 … C3`，**大端**）。

## 练习建议

1. **证明"这段代码不是我这块板子的"——不许靠猜**
   任务：把 `maixpy/offline_threshold_tuner.py` 与 `openmv/2023_laser/red.py` 各拷一份到板上，在 CanMV IDE 里点运行。
   **通过标准**：能原样引用两条报错（哪个模块名、哪一行），并**用一句话说清这个模块属于哪个平台**。然后把 `maixpy` 那份与 `06_practice/01_all_in_one.py` 第 128 行的 `handle_threshold_adjustment()` 并排读，列出**它在 K230 上缺失的三样东西**（触摸读取 API、显示 API、二值化调用形式）。能列出这三样，你才算真的理解了"平台无关的只是算法"。

2. **把协议对拍做一遍（这道题必须上板，必须出计数）**
   任务：`07_contest/2023_E_laser/main_high_fps.py`（或任一发 `AA…55` 的脚本）连 UART2，STM32 侧烧 `stm32/serial_packet/`；先跑现状，再把 Python 端的 `struct.pack('<BHH', …)` 改成 C 端要的 `AA + len + payload + sum`。
   **通过标准**：现状必须**实测**到"K230 连发 ≥100 帧、STM32 侧 `Command_GetCommand()` 返回长度恒为 0"，并把这个 0 记进报告（不许只写"会失败"）；改完之后必须**实测**到 1000 帧全部接收、每帧解析值与发送值逐一相等。最后再故意把校验和加错一位，验证解析器确实丢弃了错帧（返回 0）。第三组数据是关键：**它证明你的校验和真的在起作用**，而不是碰巧没报错。

3. **盘一盘体积（决定要不要继续留 `.pack/`）**
   任务：在仓库根跑 `du -sh other_boards/stm32/*/`，再看 `.gitignore` 里 `Objects/`、`Listings/`、`*.pck` 这些规则。
   **通过标准**：报告要包含：① 四个工程的实测体积（本次核对：`yahboom_2023_green` 与 `_red` 各 **88 MB**，`oled_display` 与 `serial_packet` 各 **68 MB**）；② 指出大头在哪（两个 yahboom 工程各有 **78 MB** 的 `MDK-ARM/.pack/` 器件支持包缓存）；③ 说明 `.pack` 为什么可再生（Keil 会重新下载），以及"删"与"不删"各自的代价。**本仓库当前不删任何东西**，删除与否由仓库主人决定。

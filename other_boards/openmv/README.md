# openmv —— OpenMV 平台的代码（你的 K230 上不能跑）

两套东西：`2023_laser/` 是 2023 E 题的一对激光追踪主从；`nuedc_2025_e/` 是程欢欢的 OpenMV4 版 2025 E 题方案（MIT）。它们都建立在 `pyb` 和全局 `sensor` 上，与 CanMV 的 `Sensor(id=2)` 是两种架构。单独隔出来，是为了让"这不属于你的平台"先于"这题我见过"被看到。

## 这里有什么

### `2023_laser/`：绿/红一对

| 名字 | 平台 | 是什么 | 状态 |
| --- | --- | --- | --- |
| `green.py` | OpenMV（`import sensor, lcd` / `from pyb import UART`） | 一对主从里的被控端。每帧 `lens_corr(1.4)`，命中后只在中心 70×70 的 ROI 里找激光点 | 平台不符 |
| `red.py` | OpenMV | 主控端。`QQVGA` + `set_windowing`，逐帧发 `A1 02 flx dx fly dy 1A`，另有 `A1 33` / `A1 11` / `A1 44` 三种控制帧 | 平台不符 |

两份靠 `A1` 帧互发指令，**只留一个跑不起来**。坐标是 1 字节增量，变化超过 255 就溢出；帧布局见 [docs/06 第 2 节](../../docs/06_uart_protocol.md)。

### `nuedc_2025_e/`：程欢欢的 2025 E 题 OpenMV4 方案

| 名字 | 平台 | 是什么 | 状态 |
| --- | --- | --- | --- |
| `25电赛E题-OpenMV-图像识别示例-程欢欢-V1.py` | OpenMV4 / OpenMV4Plus | 131 行。黑框阈值找框，再在每个框的 `rect()` 里开 ROI 找白子 | 平台不符 |
| `25电赛E题-OpenMV-图像识别示例-程欢欢-V1.1.py` | 同上 | 97 行精简版，算法不变 | 平台不符 |
| `激光矩形集中调参/激光矩形集中调参.py` | 同上 | 195 行。参数集中区 + 两段式确认 + 圆形度筛选 | 平台不符 |
| `LICENSE` | — | MIT，Copyright (c) 2025 程欢欢，必须随代码保留 | 保留 |
| `.gitignore` | — | 原作者 Flash Builder 工程的规则，与 K230 无关 | 保留原状 |

文件头写着"例程序使用 OpenMV4 运行，OpenMV4Plus亦可"。三个 `.py` 的文件名一个都没改——改了就没法在原作者的仓库或视频里对上号。

MIT 允许修改与商用，唯一条件是保留版权声明。把 `LICENSE` 删了再抄，就从"合规借鉴"变成"违反许可"；借鉴了思路（尤其是嵌套 ROI 或参数集中区），在自己的文件头写一行来源，成本为零。

**最容易发生的事故是误抄。** 它和你的 2025 E 题题面一样，还带成型的阈值和调参区，看起来比 `result/` 那三份干净；但它不在你的平台上。看见 `pyb` 或全局 `sensor`，就不是 K230 代码。

### 平台证据（判断归属用）

| 文件 | 第一处标记 |
| --- | --- |
| `2023_laser/green.py` | `:1` `import time, sensor, lcd`，`:2` `from pyb import UART` |
| `2023_laser/red.py` | `:2` `from pyb import UART` |
| `nuedc_2025_e/…-V1.py` | `:6` `import sensor, image, time`，`:7` `from pyb import millis` |
| `nuedc_2025_e/…-V1.1.py` | `:4` `import sensor, image, time`，`:5` `from pyb import millis` |
| `激光矩形集中调参/激光矩形集中调参.py` | `:1` `from pyb import UART` |

### 可借鉴的三招

1. **嵌套 ROI。** 先 `find_blobs([黑框], merge=False)`，再对每个候选 `find_blobs([白], roi=blob.rect(), merge=False)`。第二遍的搜索面积被压到框内，候选数和误检一起降；CanMV 的 `find_blobs` 同样支持 `roi=`，`blob.rect()` 的顺序要对上 `(x, y, w, h)`（待上板确认）。
2. **`lens_corr(1.4)` 镜头畸变校正。** 广角镜头把画面边缘的直线拉弯，而矩形检测对直线最敏感。在 `find_rects()` 前调一次，往往比加大 `threshold` 更有效。CanMV 侧同名可用，`07_contest/reference/image_recognition/2，图像处理.py:88` 有一处 `src_img.lens_corr(3.0)` 可对照。
3. **参数集中在一个区域。** `激光矩形集中调参.py` 开头的调试参数区（第 6–35 行），每个参数都标了推荐范围；调参只改这一块，赛场不用全文 grep。它还区分"初始确认"与"持续跟踪"两套判据：确认时收紧，跟踪时放宽。

读代码时先看这几处：V1 的第 70–82 行是嵌套 ROI 的完整写法；`激光矩形集中调参.py` 的第 6–35 行是参数区，第 130–136 行是圆形度筛选；`green.py` 的第 40 行是 `lens_corr`，第 55 行是中心 70×70 ROI。

### 移植时只搬思路

1. **API 层。** `sensor.*` 与 `pyb.UART` 在 CanMV 里没有同名的全局对象，要换成 `Sensor(id=2)` 和 `machine.UART`。
2. **帧层。** `A1 …` 与 `DATA,…\r\n` 在仓库里都没有解析端，移植就得自己重写两端。
3. **参数层。** 阈值、ROI 尺寸、确认帧数要在 K230 的镜头上重扫；照抄数字不会得到同样的结果。

## 能不能跑

全部需要 OpenMV 固件（`pyb` + 全局 `sensor`），在你的 K230 上无法运行（读代码核实）。`2023_laser` 是主从一对，单份不成立；`nuedc_2025_e` 能否在 OpenMV 上跑，尚未验证（待上板确认）。`green.py:3-4` 把 `THRESHOLD_R` 连续赋值两次（[P3-23](../../docs/02_known_issues.md#p3-23)）；`A1` 帧没有任何 STM32 工程解析（[docs/06](../../docs/06_uart_protocol.md)）。

## 练习

1. 在 OpenMV 上跑一次 `lens_corr(1.4)`，和 K230 的 `find_rects` 对比校正前后的检出稳定性。
2. 把 `green.py` 的 `A1` 帧改成 `AA … 55`，同时写出 Python 打包和 C 解析两边的定义。
3. 借用 `激光矩形集中调参` 的思路，给 2025 主程序做一个"参数集中区"。

## 相关

- 串口族表：[docs/06](../../docs/06_uart_protocol.md)
- 本仓库的同题方案：[`07_contest/2025_E_self_aiming/`](../../07_contest/2025_E_self_aiming/)
- 执行端：[`other_boards/stm32/`](../stm32/README.md)
- 平台划分：[`other_boards/README.md`](../README.md)
- 官方入口：[docs/04](../../docs/04_official_resources.md)

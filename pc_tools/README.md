# pc_tools —— 跑在电脑上的工具脚本

目前一份：**串口模拟量实时曲线监视器**。它把 K230/MCU 通过 UART 发上来的数值画成滚动曲线，是"调控制环时不想每次都看串口里的数字"的那块拼图。
这一层的判定标准只有一条：**这个文件在 PC 上 `python xxx.py` 跑，还是在板子上跑**。`06_practice/` 原来把这类脚本和板子代码混在一起，导致有人以为拷上 SD 卡就能运行（它第一行 `import serial` 在板子上就没有）。
走完你应该能：把一个 115200 的串口数据流接成实时曲线；说清楚这份脚本要的数据格式在仓库里**为什么一个生产者都没有**、以及要接上它该由谁来发；以及用 `matplotlib` 的 `animation` 时那三个"自动缩放"开关为什么会互相打架。

## 文件清单

| 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `serial_plot_monitor.py` | 逐行读串口 → `float()` → 追加进定长缓冲 → 刷新一条红色曲线；解析失败的行只警告不退出 | `serial.Serial(port, baud, timeout=1)` `ser.in_waiting` `ser.readline()` `collections.deque(maxlen=…)` `matplotlib.animation.FuncAnimation` | 94 行；⚠️ **X 轴在 200 个点之后塌成一条竖线**，见下文 |

## 依赖与环境

```bash
pip install pyserial matplotlib
```

- `import serial` 来自 **pyserial**（注意 `pip install serial` 是另一个无关的包，装错了会 `AttributeError: module 'serial' has no attribute 'Serial'`）。
- 只有 Python 3；`matplotlib.animation` 需要能开窗口（Windows/Linux 桌面直接可用；SSH 或 WSL 里没图形转发就看不见窗口，只剩串口阻塞）。

## 这份脚本监控的发送端不在本仓库里

⚠️ **它等的是一条"每行一个浮点数"的 ASCII 流，而仓库里没有任何文件产生这种输出。**
电赛里模拟量（电池电压、电流、电位器、霍尔、红外阵列的模拟输出）**通常放在外部 MCU 上采**：K230 在系统里的角色是"那颗摄像头 + 一条 UART"，让它分心去轮询 ADC 一般不划算，而且 ADC 采样和舵机/电机控制要在同一个时基上。所以这条数据链的真实形状是：

```
传感器模拟量 ──> 外部 MCU（采 ADC）── UART ──> K230（视觉）
                        │
                        └──── UART ──> PC：serial_plot_monitor.py（本文件）
```

MCU 侧的工程在 [`../other_boards/stm32/`](../other_boards/stm32/)。K230 侧的 UART 用法看 [`../02_data_collection/03_uart_test.py`](../02_data_collection/03_uart_test.py) —— 那是本仓库唯一一份"K230 用 UART2 收发 ASCII"的样板：

```python
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)     # GPIO11 → UART2 TX
fpioa.set_function(12, FPIOA.UART2_RXD)     # GPIO12 → UART2 RX
uart2 = UART(UART.UART2, 115200)
uart2.write("Hello World\n")
```

但要清楚：**那份脚本发的是字面字符串 `"Hello World\n"`，本监控脚本会对它打印 `Warning: Could not parse value: Hello World` 并丢弃**（第 66–68 行走的是 `except ValueError`）。仓库里现存的另外两种发送格式也都不是它要的：`../06_practice/` 各文件发的是二进制帧 `AA + type + x + y + 55`（`float()` 一定失败）；`../04_number_classification/code/v1.2.2/cls_video_1_2_2.py:170` 发的是 `!<类别>@`。

**关于"K230 到底能不能直接读模拟量"——本仓库内部是矛盾的，别照任何一面之词下结论。**
仓库里存着立创·庐山派官方的 ADC 例程：[`../07_contest/reference/basic_gpio/9，获取电压ADC.py`](../07_contest/reference/basic_gpio/9，获取电压ADC.py)，32 行，用的是 `from machine import ADC` → `adc = ADC(0)` → `adc.read_u16()`（0–65535）/ `adc.read_uv()`（微伏），`time.sleep_ms(100)` 约 10 Hz 采样。这份例程存在，说明庐山派固件至少**给了 ADC 接口**。它能不能在你的固件版本上工作、通道 0 接到板上哪个引脚，**必须在你的板子上实测**（引脚定义以官方交互式查询工具为准，页面上没有静态表）。
顺带一条硬事实：**就算那个 ADC 能读，它现在也不能直接喂给本监控脚本** —— 那 28 行打印的是 `"ADC Value: %d, Voltage: %d uV, %.6f V"`，一行里有四个字段，`float()` 一样解析失败。要接上这条链，得把发送端改成只输出一个数加换行：`uart.write("%.3f\n" % (adc.read_uv() / 1e6))`。


## 旧名 → 新名（两次跳转）

| 阶段 | 路径 |
| --- | --- |
| 原始 | `平时练习/7.监控和可视化通过串口传输的模拟量数据.py` |
| 第一次（ASCII 化，`06_practice/`） | `06_practice/07_pc_serial_monitor.py` |
| 第二次（按平台归位，当前） | `pc_tools/serial_plot_monitor.py` |

原名里的"模拟量"三个字是本文件最重要的信息，也是判断"这东西跑不了在 K230 上"的依据 —— 所以在新名字里保留为 `serial_plot_monitor`，把"模拟量"这一层含义放回到上面那张数据链图里。

## 练习建议

1. **先不接板子，自己造一个发送端，证明监控脚本本身能工作。** PC 上开两个串口（一块 USB 转 TTL 对接，或 Windows 用 `com0com` 建虚拟串口对），另开一个 Python 窗口执行：
   ```python
   import serial, math, time
   s = serial.Serial('COM5', 115200, timeout=1)
   for i in range(10000):
       s.write(bytes(f"{2 + math.sin(i / 20):.3f}\n", 'ascii')); time.sleep(0.02)
   ```
   完成标准：曲线**前 200 个点**是一条正弦。这是这条练习的分水岭——200 点之后就是下面第 2 题要处理的东西。
2. **复现并解释 X 轴塌陷。** 让上面那个发送端跑超过 200 个点（10000 个点足够）。
   完成标准：看到曲线变成一条竖线，然后**不用改代码**就说出为什么：`MAX_DATA_POINTS = 200` 的 `deque` 一满，`len(data_buffer) - 1` 就永远等于 `199`，于是每个新点都落在同一个 X 坐标上；而 300 点之前 `len` 一直在涨，所以它看起来正常。再指出第二个后果：第 63 行 `ax.set_xlim(time_buffer[0], time_buffer[-1])` 此时变成 `set_xlim(199, 199)`，**窗口宽度为 0**。
3. **把三处坐标轴控制理清，只留一处。** 文件里同时存在三种"谁决定轴范围"的机制：第 29 行 `set_xlim(0, MAX_DATA_POINTS)`（固定的初始窗口）、第 58–59 行 `ax.relim()` + `ax.autoscale_view(True,True,True)`（**根据数据自动重算**）、第 63 行的滑动窗口 `set_xlim`。
   完成标准：解释清楚"每帧执行 `autoscale_view`"会让第 29 行和第 63 行的设置**在下一帧就被覆盖掉**，并给出你自己会保留哪一处、为什么（Y 轴 0–4V 是人为量程，`autoscale_view` 一开它也会跟着抖，这是同一个问题的另一半）。
4. **把它接到真实系统上。** 两条路任选：**(a)** 让 `../other_boards/stm32/` 那侧的 MCU 每 20 ms 发一行电压值（推荐给比赛用，K230 专心做视觉）；**(b)** 若你验证过 `ADC(0)` 在你的固件上可用，就让 K230 自己发——把发送端写成 `uart.write("%.3f\n" % (adc.read_uv() / 1e6))`，**不要**照官方例程那样一行打四个字段。改完 `SERIAL_PORT` 为实际端口。
   完成标准：能看到直流分量和噪声；顺手量一下"实际到达的点数 / 秒"，和你发送端的发送频率对比 —— 差得远就是 `interval=50`（每秒最多 20 帧刷新）与 `readline()` 每帧只读一行的组合限制了，这比曲线好不好看重要。

## 已知问题 / 注意事项

以下全部从代码核实（行号对应当前版本）。完整分级清单见 [docs/02_known_issues.md](../docs/02_known_issues.md)。

- ⚠️ **X 轴塌陷（功能性 bug，不是显示偏好）。** 第 52 行 `time_buffer.append(len(data_buffer) - 1)` 用"当前缓冲长度 - 1"当 X 坐标。`data_buffer` 是 `deque(maxlen=200)`（第 14 行），一旦满了长度恒为 200，**第 201 个点起 X 永远是 199**。表现：先看到 200 个点的正常曲线，然后它慢慢挤成一条竖线。前 200 个点看起来正常，是这个 bug 最难被发现的原因。
- ⚠️ **`ax.relim()` + `ax.autoscale_view()`（58–59 行）与显式的 `set_xlim`（29 行、63 行）互斥。** 前者每帧根据当前数据重算视口，后者每帧手动设视口，结果由执行顺序决定，Y 轴 `set_ylim(0, 4.0)`（28 行）同样会被 `autoscale_view` 覆盖。想固定视口就别调 `autoscale_view`；想自动就别写 `set_xlim`。
- ⚠️ **`SERIAL_PORT = 'COM4'` 硬编码在第 9 行**，且只在 `except serial.SerialException` 时打印提示后 `exit()`（第 35–38 行）。**端口被 CanMV IDE 占用时也是这个异常** —— 这是最常见的"打不开串口"原因：IDE 连着板子，PC 上的第二个程序就抢不到同一个 COM。用之前先断开 IDE 的串口连接。
- **`float(line_str)` 的语义很宽：它会接受 `nan` / `inf`。** 一个 `nan` 进 `data_buffer` 之后 matplotlib 会把曲线在那一段断掉，而 `relim()` 遇到全 `nan` 数据的行为不确定。真实串口链路一定会收到乱码（上电瞬间、拔插、波特率不对），所以生产用法是先过滤：`if not math.isfinite(voltage): return line,`。
- **每帧只读一行**（第 44–45 行 `if ser.in_waiting > 0: readline()`），而 `FuncAnimation` 的 `interval=50` 是每 50 ms 跑一次 `update`。发送端快于 20 行/秒时**数据会在系统串口缓冲里堆积**，曲线越来越滞后于现实；这不是丢数据（`deque` 只留最后 200 个），但看的是"过去"。要看得准就把发送频率降到 20 Hz 以下，或把 `readline` 换成 `while ser.in_waiting: …` 一次读干。
- `timeout=1`（第 33 行，秒）配合 `in_waiting > 0` 的判断，实际很少走到阻塞；但 `readline()` 在**最后一行没有 `\n`** 时会等到超时才返回半行，`float()` 失败 → 警告刷屏。发送端务必每帧带换行。
- `except serial.SerialException`（第 70–74 行）里 `plt.close(fig)` 后只 `return line,`，**主循环继续**：窗口关了但动画还在跑、串口已经不再读，程序变成"看起来卡住"。要么在这里退出，要么重连。
- **这份脚本没有 `if __name__ == '__main__':`，全部逻辑在模块顶层执行**，`import` 它就开始抢串口。作为一次性工具无所谓，想复用它的读串口部分时记得把 `update()` 抽出来。
- 代码里有多处行尾多余空格与全角/半角混排的缩进（第 6、16、30、39 行等，源文件是 CRLF 且部分续行缩进不是 4 的倍数）。Python 不报错，但会让 `git diff` 噪音很大。这是从聊天窗口/文档里粘贴出来的痕迹，也是这份文件没有 `.py` 项目常见的那套规范的证据 —— 复制走之前顺手 `black` 一下。

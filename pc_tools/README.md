# pc_tools —— 跑在电脑上的工具脚本

这一层只有一个文件，判定标准也只有一条：它在 PC 上用 `python` 启动，不烧到板子上。上游是别处发来的串口数据流，下游是屏幕上的实时曲线。`06_practice/` 里那些板子代码不能混进来——它们的 `import` 在 PC 上就过不去。

## 这里有什么

| 文件 | 做什么 | 关键 API / 来源 | 备注 |
| --- | --- | --- | --- |
| `serial_plot_monitor.py` | 逐行读串口 → `float()` → 追加进定长缓冲 → matplotlib 刷新一条曲线；解析失败只警告不退出 | `serial.Serial(port, baud, timeout=1)`、`ser.in_waiting`、`ser.readline()`、`collections.deque(maxlen=200)`（`:14`）、`FuncAnimation` | 94 行；X 轴 200 点后塌成竖线（[P3-7](../docs/02_known_issues.md#p3-7)） |

### 依赖与环境

```bash
pip install pyserial matplotlib
```

`import serial` 来自 pyserial（`pip install serial` 是另一个无关的包）；需要能开窗口的桌面环境，SSH / WSL 没有图形转发时看不到曲线。

### 它要的是文本行，不是二进制帧

每行一个浮点数，`float(line_str)` 解析（`:50`）。所以它接不上 `06_practice/` 的 `AA … 55` 二进制帧——`float()` 必然失败，只会在终端刷警告。仓库里没有这份脚本的发送端，要接上得自己写一个每帧输出一个数加换行的程序。K230 本身有 ADC，官方例程 [`reference/basic_gpio/9，获取电压ADC.py`](../07_contest/reference/basic_gpio/9，获取电压ADC.py) 就在用；但它打印一行四个字段，同样喂不进这个脚本。

数据链的整体形状是：模拟量在 MCU 侧采成数字，经 UART 变成文本行，到 PC 才成为曲线；虚线那一段要你自己补。

```mermaid
flowchart LR
    A["模拟量（外部传感器）"] --> B["MCU 采 ADC"]
    B --> C["UART 文本行<br/>每行一个浮点数"]
    C --> D["pc_tools/serial_plot_monitor.py"]
    D --> E["matplotlib 曲线"]
    C -.-> F["仓库里没有发送端"]
```

## 能不能跑

在 PC 上 `pip install pyserial matplotlib` 后，读代码核实启动路径完整（打开串口、建窗口、每 50 ms 刷新）；但默认等 `'COM4'`（`:9`），端口不对会走 `SerialException` 分支后 `exit()`。即使端口正确，没有发送端也只会是一条空坐标轴。X 轴在第 200 个点之后失真（[P3-7](../docs/02_known_issues.md#p3-7)），Y 轴量程（`:28`，0–4 V）与自动缩放互相覆盖。它只适合电池电压、电位器这类慢变量，高频信号看不出形状。数据链全通的状态尚未上板验证。

## 练习

1. **不接板子，用串口助手手动发 `0`、`1`、`2`。**
   任务：hex/文本模式下按行发送，每行末尾带换行。
   验收：曲线上依次出现三个点，终端不打印 `Warning: Could not parse value`；能解释为什么少了换行就会一直等到超时。
2. **把 `SERIAL_PORT = 'COM4'` 改成你自己的端口。**
   任务：先在设备管理器里确认端口号，再改 `:9`。
   验收：启动时终端打印 `Connected to <你的端口> at 115200 baud.`；若被 CanMV IDE 占用，能说出为什么两个程序抢不到同一个 COM。
3. **修 X 轴塌陷：给 `time_buffer` 换成真实时间戳。**
   任务：记录每个点到达的 `time.monotonic()`，用它替换 `len(data_buffer) - 1`。
   验收：跑满 200 点以上后曲线继续向左滚动，不再挤成竖线；同时只保留一处坐标轴控制（`set_xlim` 或 `autoscale_view` 二选一），并说明理由。
4. **把它改成能解析二进制帧。**
   任务：先写一个只认 `AA` 开头的读帧循环，再解出 `type, x, y`。
   验收：用 `struct.unpack('<BHH', buf)` 取字段，按 [docs/06](../docs/06_uart_protocol.md) 的帧格式校验帧头帧尾；喂入 `06_practice/` 的帧后能画出 `x` 或 `y` 的曲线，而不是刷解析警告。
5. **（可选）让发送端只发一个数。**
   任务：改发送端为每 20 ms 一行，单字段加换行。
   验收：曲线滞后不超过 2 秒；能解释 `interval=50` 与「每帧只读一行」（`:44`–`:45`）如何共同限制吞吐。

## 相关

- [matplotlib `FuncAnimation` 文档](https://matplotlib.org/stable/api/_as_gen/matplotlib.animation.FuncAnimation.html)
- [pySerial 文档](https://pyserial.readthedocs.io/en/latest/shortintro.html)
- [docs/06 串口协议](../docs/06_uart_protocol.md) · [docs/02 已知问题](../docs/02_known_issues.md)

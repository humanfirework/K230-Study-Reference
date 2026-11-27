# reference —— 厂商例程原件，用来对照「官方怎么写」

这一层放的是立创·庐山派与亚博（Yahboom）的例程原件，不是本仓库写的。它们按厂商的编号与文件名原样保留，唯一用途是查 API 的标准用法、或者怀疑自己那段代码写歪了时回来对照。自研代码在 `07_contest/` 的赛题目录与 `06_practice/`，这一层不承担赛题实现。官方资料的入口统一在 [docs/04](../../docs/04_official_resources.md)。

## 这里有什么

| 文件 | 做什么 | 关键 API / 来源 | 备注 |
| --- | --- | --- | --- |
| `basic_gpio/`（12 个） | 点灯、RGB、按键、蜂鸣器、串口收发、ADC、RTC、软件定时器、串口回环测试 | `Pin`、`PWM`、`UART`、`ADC`、`RTC`、`Timer`；立创·庐山派 LCKFB | 多数文件带立创版权头 |
| `image_recognition/`（12 个） | 绘制、图像处理、线段 / 矩形 / 圆形检测、颜色识别两讲、二维码、裁剪、YOLOv8n、OCR、离线调阈值 | `find_rects(threshold=5000)`（`4，矩形检测.py:89`）、`rotation_corr`（`2，图像处理.py:86`，被注释） | `9`、`10` 的文件头写的是 01Studio |
| `yahboom_ported/`（4 个） | 快速线性回归、物体计数、多颜色识别、K230 颜色巡线 | `get_regression`（`1.快速线性回归.py:52`） | 只有第 4 个需要 `ybUtils` |

### 每个子目录里有什么

- `basic_gpio/`：`1` 点灯、`2` 七色 RGB、`3` / `4` 按键、`5` / `6` 蜂鸣器、`7` / `8` 串口收发、`9` ADC、`10` RTC、`11` 软件定时器、`12` 串口回环。
- `image_recognition/`：`1` 绘制、`2` 图像处理、`3` 线段、`4` 矩形、`5` 圆形、`6` 与 `6（二）` 颜色识别、`7` 二维码、`8` 裁剪、`9` YOLOv8n、`10` OCR，外加 `离线调整阈值.py`。
- `yahboom_ported/`：`1` 快速线性回归、`2` 物体计数、`3` 多颜色识别、`4` K230 颜色巡线。

这些文件的版权归立创、01Studio、亚博各自所有，文件头的署名与版本信息原样保留；本仓库只调整了所在目录，没有改内容。

### 读之前要知道的四件事

- **`9`、`10` 缺模型。** 需要 3 个 `.kmodel` 加 `dict.txt`，都不在仓库（[P3-22](../../docs/02_known_issues.md#p3-22)）；`9` 的模型路径写在 `:185`。
- **两个「6，颜色识别」是两讲不同的课**，不是重名事故（[P3-22](../../docs/02_known_issues.md#p3-22)）。
- **串口例程只发 8 字节裸数据，没有帧格式。** 它能证明链路通，不能当通信协议用（[P3-22](../../docs/02_known_issues.md#p3-22)）；要定帧，看 [docs/06](../../docs/06_uart_protocol.md)。
- **中文文件名不要改。** 厂商教程按「编号 + 中文名」引用这些文件，改名会切断与外部资料的对应，见 [docs/07](../../docs/07_maintenance.md) 的「不能改名的位置」。

另外，`image_recognition/` 的显示初始化常带 HDMI / LCD / 虚拟屏多个分支（如 `4，矩形检测.py:26`–`:34` 的三套分辨率），照抄时要把 `DISPLAY_WIDTH/HEIGHT` 对齐你自己的配置，否则画面会被拉伸或只显示一角。

`yahboom_ported/` 里 `1`、`2`、`3` 只依赖 `media` 系列；`4.K230 颜色巡线.py` 在第 6 行 `from ybUtils.YbUart import YbUart`，需要亚博的 `ybUtils/` 包，这个包不在仓库。

### 一个例子：例程怎么变成自研代码

`image_recognition/离线调整阈值.py` 是一个纯调阈值工具；`../2023_E_laser/basic_part.py` 在它基础上加了步进电机的 `send_order()`（`:42`）。想学「触摸屏离线调阈值」这个技术，读前者；想看它怎么接到执行机构上，读后者。两份都保留，才能看出从厂商原件到自研之间动了哪些地方。

## 能不能跑

`basic_gpio/` 与 `image_recognition/` 的多数文件按固件自带的 `libs/`、`examples/` 组织，读代码核实没有语法级阻塞，但本目录没有一条已上板验证。`9`、`10` 缺资源，走到加载模型那一步会失败（[P3-22](../../docs/02_known_issues.md#p3-22)）。`yahboom_ported/1`–`3` 只依赖 `media`，`4` 需要 `ybUtils` 包。串口例程只负责验证链路，线上没有帧格式。

## 练习

1. **跑 `basic_gpio/12，串口测试.py` 确认链路。**
   任务：TX/RX 交叉、共地，先在 IDE 里跑通，再用串口助手复看一遍。
   验收：助手能收到板上发回的内容；能说出该文件用的波特率与引脚，并和 [docs/06](../../docs/06_uart_protocol.md) 的硬件参数对上。
2. **跑 `image_recognition/4，矩形检测.py`。**
   任务：对准一个边框清晰的靶标，再用 `find_rects` 的阈值看变化。
   验收：画出检测框与 `magnitude`；阈值从 5000 改到 2000 后，能说出你观察到的检出个数与误检变化，并给出原因。
3. **用 `离线调整阈值.py` 理解阈值。**
   任务：在触摸屏上现场调出一组 LAB 阈值，把区间抄下来。
   验收：三个通道的区间能让目标稳定框住；能说清它与设备端阈值常量的对应关系，以及为什么这一步不用连电脑。
4. **对比 `yahboom_ported/1.快速线性回归.py` 与 `01_basics/11_line_following.py`。**
   任务：只读这两个文件，找出同一算法的两种写法。
   验收：写出各自的输入、输出与「判断该往哪边转」的那一行；指出哪一个把直线拟合交给了库函数。

## 相关

- [庐山派 K230 快速上手](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/quick-start.html) · [使用摄像头](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/use-sensor.html)
- [01Studio CanMV K230 wiki](https://wiki.01studio.cc/docs/canmv_k230/)
- [docs/04 官方资源](../../docs/04_official_resources.md) · [docs/06 串口协议](../../docs/06_uart_protocol.md) · [docs/02 已知问题](../../docs/02_known_issues.md)

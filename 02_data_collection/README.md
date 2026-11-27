# 02_data_collection —— 采图与串口：把画面变成数据集，把结果送出去

这一层是整条链的上游：前面接 `01_basics` 的相机与绘图，后面接 `04_number_classification` 的训练集和 `06_practice` 的闭环。4 个文件按“单拍 → 分类连拍 → 串口收发”排，`05_data_collect.py` 是 `02` 的早期版本，留着对比改法。
串口帧格式与对端解析不在本目录定义，见 [docs/06](../docs/06_uart_protocol.md)；缺陷的现象与成因统一记在 [docs/02](../docs/02_known_issues.md)，这里只给结论。

## 这里有什么

| 文件 | 做什么 | 关键 API / 来源 | 备注 |
| --- | --- | --- | --- |
| `01_capture_single.py` | 按键单拍：上升沿 + 200 ms 消抖、三色 LED 提示、断点续编号 | `Pin(53, Pin.IN, Pin.PULL_DOWN)`、`Pin(62/20/63, Pin.OUT)`、`img.compress(quality=95)` | 立创版权头；800×480 RGB565，存 `/data/data/images/lckfb_00001_800x480.jpg` |
| `02_capture_burst.py` | 按键切类别 → 倒计时 → 每类连拍 100 张 | `os.mkdir`、`img.compress(95)`、`open(...,'wb')` | `class_lst` 10 类（`one`…`zero`）、`prefix="batch_1_"`；产出 800 张数据集 |
| `03_uart_test.py` | UART2 最小收发：按键发一行、回读打印 | `FPIOA.set_function(11/12, UART2_TXD/RXD)`、`UART(UART.UART2, 115200)` | `Sensor(width=…)` 已修（P0-3）；收尾只 `Display.deinit`（P1-5） |
| `05_data_collect.py` | `02` 的早期版本，英文提示 | 同 `02` | 1024×768、`finally` 完整；居中偏移按 800×480 算（P3-19） |

### 那 800 张数据集是怎么来的

`04_number_classification/data/dataset/1..8` 是 **8 类 × 100 张 = 800 张 480×320 JPEG**，文件名形如 `batch_1__one_1.jpg` … `batch_1__eight_100.jpg`。它由 `02_capture_burst.py` 产出，但脚本里写的是 10 个类别名（`one`…`zero`）；仓库里的 8 个数字文件夹是**板外手工改名**的结果，**没有改名脚本**。也就是说，`1..8` 这个目录结构来自一次人工操作，不是代码行为。

保存根路径 `/data/data/images/` 依固件而定：不同 CanMV 版本的根文件系统布局不一样。第一次用先 `print(os.listdir("/"))` 和 `print(os.listdir("/data"))` 确认，再决定要不要改 `save_folder`。

`01` 的断点续编号值得单独看：它扫一遍目录里以 `lckfb_` 开头、`.jpg` 结尾的文件，取最大编号往下续，而不是从 0 重来。这段逻辑和“目录存在就跳过创建”是同一个思路——先看现场，再决定动作。

### 采集链上的三个动作

- **按键消抖**：`01` 用“上次电平 + 当前电平”的上升沿判断，再配 200 ms 的 `time.ticks_diff` 窗口；直接读 `value()` 会在一次按下里触发多张。
- **JPEG 写出**：`img.compress(quality=…)` 返回压缩后的字节，再自己 `open(path, "wb")` 写盘；也可以直接 `img.save(path)`（嘉楠平台导出件里就是这种写法）。前者能控制压缩质量，后者少两行。
- **目录检查**：`01` 先 `os.stat()`、失败再 `os.mkdir()`；`02` 每次都直接 `mkdir`，所以重复进入同一类别会抛异常（P2-18）。这是两份脚本最值得对照的一处。

### 串口这一侧只到“能收发”

`03_uart_test.py` 演示的是引脚复用（GPIO11/12 → UART2）和最小读写，不定义帧格式。真正对外的协议、帧头、校验与对端解析，统一看 [docs/06](../docs/06_uart_protocol.md)；本目录发出去的字节序列不能直接当作通信协议使用。

## 能不能跑

4 个文件的入口都完整，`03` 的关键字已按官方手册修正；实际能否起画面**待上板确认**。`02` 的 FPS 覆盖层不显示（P3-19），第 11 次按键会因目录已存在而退出（P2-18）；`02`/`03` 中断后要断电才能再跑（P1-5）。

## 练习

1. **采一套自己的数据集**：每类 100 张、类别均衡、固定 480×320。
   建议验收：`os.listdir` 能看到 N 个类别目录、每个 100 个文件、`ls -l` 大小均不为 0。
2. **用板载 LED 当“正在采集”指示**：GPIO62 红 / GPIO20 绿 / GPIO63 蓝，共阳、低电平点亮。
   建议验收：按下按键到倒计时结束，LED 状态与采集状态一一对应；采完恢复熄灭。
3. **验证 JPEG 质量与分辨率对训练的影响**：同一目标分别用 `compress(95)` 与较低质量各采一小份，比较训练后的分错情况。
   建议验收：两份数据的文件体积有可测差异，且你能说出 kmodel 的输入尺寸（看 `deploy_config.json` 或平台导出说明）与采集 480×320 之间由谁重采样。
4. **先过 UART 回环这一关**：PC 串口工具接 GPIO11(TX)/12(RX)、115200-8N1，按键触发，并在 `03` 里把收到的字节回发。
   建议验收：PC 侧自发自收一致；这是接 `06_practice` 之前的最低门槛。

## 相关

- [CanMV Sensor 模块 API](https://www.kendryte.com/k230_canmv/zh/v1.3/api/mpp/K230_CanMV_Sensor%E6%A8%A1%E5%9D%97API%E6%89%8B%E5%86%8C.html)
- [CanMV UART 模块 API](https://www.kendryte.com/k230_canmv/zh/v1.3/api/machine/K230_CanMV_UART%E6%A8%A1%E5%9D%97API%E6%89%8B%E5%86%8C.html)
- 本仓：[docs/06 串口协议](../docs/06_uart_protocol.md) · [docs/02 已知问题](../docs/02_known_issues.md) · [docs/01 上手](../docs/01_getting_started.md)

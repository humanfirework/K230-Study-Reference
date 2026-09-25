# 02_data_collection —— 采图与串口：数据这条路的上游

这一层解决两个"上游"问题：**怎么在板子上把图像存成数据集**，以及**怎么把结果通过 UART 送出去**。
4 个文件按"单张 → 批量分类连拍 → 串口链路"排；最后一个 `05_data_collect.py` 是 `02` 的早期版本，保留是为了看得清改法演进。
走完之后你应该能：用一颗按键在板子上采出一个可以直接丢进训练平台的目录结构；知道 JPEG 是 `img.compress()` 之后手工 `open(...,'wb')` 写出去的（CanMV 没有 `img.save()`）；用 `FPIOA.set_function` 把 GPIO11/12 复用成 UART2 并收发字节；以及判断一份采集脚本写得是否规矩（看它的 `finally` 里有没有 `MediaManager.deinit()`）。

## 文件清单

| 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `01_capture_single.py` | 按键单拍：上升沿检测 + 200ms 消抖 + 板载三色灯闪烁提示 + 断点续编号 | `Pin(53, Pin.IN, Pin.PULL_DOWN)` `Pin(62/20/63, Pin.OUT, drive=7)` `img.compress(quality=95)` | 本目录**唯一写得完全正确**的一份；800×480 RGB565，存 `/data/data/images/lckfb_00001_800x480.jpg` |
| `02_capture_burst.py` | 分类连拍建数据集：按键切类别 → 倒计时 3 秒 → 每类 100 张 | `os.mkdir` `img.compress(95)` `open(path,'wb')` | ⚠️ 就是它产出了 `../04_number_classification/data/dataset/`；有 4 处问题见下 |
| `03_uart_test.py` | K230 ↔ 对端的最小串口链路：按键触发发一行文本，回读并打印 | `FPIOA.set_function(11/12, FPIOA.UART2_TXD/RXD)` `UART(UART.UART2, 115200)` `uart.write` `uart.read` | ⚠️ 当前 `TypeError` 起不来 |
| `05_data_collect.py` | `02` 的早期版本：同样的连拍逻辑，英文提示 | 同 `02` | 1024×768 + `midpoint_pool(2,2)`；`finally` 是完整的（和 `02` 正好相反） |

**`04_uart_rx_tx.c` 已经不在这里了**，现在在 [`../other_boards/stm32/snippets/uart_rx_tx.c`](../other_boards/stm32/snippets/uart_rx_tx.c)。
移出去的理由不是"它是 C"，而是**它是 MCU 侧的代码**：K230 只负责看见目标，云台/激光/电机是 STM32 在驱动。而且它解析的帧格式是 `AA + len + payload + checksum` 的循环缓冲区解析器，**和本目录 Python 发出的字节序列不匹配**——放在一起会让人误以为两端已经对上了，实际上没有（对端真正的解析格式见 [`../other_boards/stm32/`](../other_boards/stm32/) 与 `../06_practice/` 各文件的 `send_data()`）。

## 旧名 → 新名

原名在 `02_Data_Collection/`。

| 旧名 | 新名 |
| --- | --- |
| `01_拍摄单个照片.py` | `01_capture_single.py` |
| `02_连续拍摄100张照片.py` | `02_capture_burst.py` |
| `03_UART串口通信.py` | `03_uart_test.py` |
| `04_串口收发.c` | （已移出）`../other_boards/stm32/snippets/uart_rx_tx.c` |
| `05_数据收集.py` | `05_data_collect.py` |

## `02_capture_burst.py` 与那份 800 张数据集的关系

这条链在仓库里从来没被写下来过，但它是有据可查的。**代码侧**（`02_capture_burst.py`）：

- 69–74 行：`save_folder = "/data/data/images/"`、`class_lst = ["one","two","three","four","five","six","seven","eight","nine","zero"]`、`prefix = "batch_1_"`、`counter = 100`。
- 103 行：`file_name = "{}_{}_{}.jpg".format(prefix, class_lst[class_id], str(counter))` —— 因为 `prefix` 自带下划线、格式串又补了一个，所以是**双下划线**。
- 54–55 行：`set_framesize(width=480, height=320)` + `RGB888`，106 行 `img.compress(95)` 出 JPEG。

**数据集侧**（`../04_number_classification/data/dataset/`，实测）：8 个目录、每个正好 100 张，共 **800 张**，全部是 **480×320 的 baseline JPEG**。文件名逐个对得上：

| 目录 | 首张文件名 | 对应 `class_lst` |
| --- | --- | --- |
| `1/` | `batch_1__one_1.jpg` … `batch_1__one_100.jpg` | `one` |
| `2/` | `batch_1__two_1.jpg` | `two` |
| `3/` `4/` `5/` `6/` `7/` | `batch_1__three_…` … `batch_1__seven_…` | `three`…`seven` |
| `8/` | `batch_1__eight_1.jpg` | `eight` |

也就是说：类别序号 1–8 就是 `one`…`eight`，`nine`/`zero` 两类**没有采**（或者说没进最终数据集）。把 `<word>` 目录改名成 `<digit>` 是在板子之外做的，仓库里没有这一步的脚本 —— 这也解释了为什么 `04` 的 `deploy_config.json` 里 `categories` 是字符串 `"1".."8"` 而不是英文单词。

## 练习建议

1. **采一小份属于自己的数据集，并证明你知道每张图存在了哪里。** 用 `02_capture_burst.py` 的骨架采 2 类 × 20 张（把 `counter = 100` 改成 20、`class_lst` 留 2 项）。每次跑完**不给板子断电**，直接从 IDE 再运行一次。
   完成标准：`os.listdir("/data/data/images/")` 能看到你的两个类别目录、每个 20 个文件、`ls -l` 大小不为 0；第二次运行能立刻出画面。第二条做不到就说明你的 `finally` 没收尾干净——那是这份代码的现状，见已知问题。
2. **把 `01` 和 `02` 的存档策略对比一次。** 只读 `01_capture_single.py` 的 82–88 行和 145–160 行，然后回答：为什么 `01` 重复运行不会报 `OSError`，`02` 会？
   完成标准：能指出 `os.stat()` + `except OSError: os.mkdir()` 这个组合，以及 `02` 缺了它；并在 `02` 的循环里手工验证一次"切回已有类别就崩"。
3. **把串口链路打通到能被 PC 看见。** `03_uart_test.py` 修好 typo 后运行，用 PC 串口工具接 GPIO11(TX)/12(RX)、115200-8N1，按按键。
   完成标准：PC 侧收到 `Hello World`，且在 K230 侧 `uart2.write()` 的同一时刻收到（不要靠缓冲区攒着）。然后再反过来：**在 `03` 里加一行把收到的字节回发到 PC**，做成回环，这样你就有了"两端都在动"的证据。
4. **量一次 `fpioa.help()` 的代价。** 在 `02` 上分别开/关第 43 行，用 `fps.fps()` 记录从 `run()` 到第一帧的时间差和稳定帧率。
   完成标准：写出两个数字，并解释为什么它只影响启动而不影响帧率（提示：它只在 `try` 里跑一次，不在 `while True` 里）。

## 已知问题 / 注意事项

以下都是**当前代码的真实状态**，本仓库刻意保持代码原样不修。完整分级清单见 [docs/02_known_issues.md](../docs/02_known_issues.md)。

- ⚠️ **`03_uart_test.py:33` `Sensor(wihth = picture_width, height = picture_height, id = sensor_id)`** —— `wihth` 不是关键字，`TypeError`，**该文件当前无法启动**。它的 `finally`（69–79 行）只 `Display.deinit()`，**没有 `MediaManager.deinit()`**，所以就算修好 typo 跑通，每次也得重新上电。
- ⚠️ **`02_capture_burst.py` 和 `../01_basics/02_drawing.py` 的 `finally` 块被截断在同一处**：停在 `# 释放媒体缓冲区` 这行注释上，`MediaManager.deinit()` 根本没写。后果是**每次跑完都必须给板子断电重启**，否则第二次运行卡在 `MediaManager.init()`。
  更糟的是 `02` 第 142 行的注释写的是 `# 释放媒体缓冲区(自动处理)` —— 这句话是假的，而正是这句话让这个问题一整年没人去查第 143 行为什么什么都没有。
- **`02_capture_burst.py:119` 的 FPS 永远不会显示。** 同一行三处问题叠在一起：
  - `"FPS: ".format(fps.fps())` —— 字符串里**没有 `{}` 占位符**，`format()` 无事可做，画面上永远是字面的 `FPS: `。
  - `draw_string_advanced(0, 768, 32, …)` —— 帧是 480×320，y=768 在画面外。`01` 用的是 `DISPLAY_HEIGHT-32` 这种写法，是对的。
  - 同一行的 `fps` 和 65 行的 `clock` 是两个 `time.clock()`，只有 `fps.tick()` 被调用，`clock` 从头到尾没被用过。
- **`02_capture_burst.py:89` 的 `os.mkdir()` 没有保护。** 每按一次按键就无条件建目录；`class_lst` 有 10 项、按键是循环切换，所以**按满 10 次回到第一个类别时 `OSError: [EEXIST]`**，被 130 行的 `except BaseException` 吞掉后程序直接结束，采到一半的数据就那样停了。`05_data_collect.py:54` 是同一个问题。`01` 的 `os.stat()` + `except OSError` 才是该抄的写法。
- **`02_capture_burst.py:43` 的 `fpioa.help()`** 会把整颗 SoC 的引脚功能表打到串口上，几百行。调试期有用，采图时它是启动延迟的主要来源，建议注释掉。`03:26`、`05:21` 同样有。
- **`05_data_collect.py:72` 的居中偏移是硬编码且错的**：`Display.show_image(img, x=(800-480)//2, y=(480-400)//2)`。它的帧是 1024×768、屏是 800×480，这两个数既不是帧尺寸也不是屏尺寸（`480/400` 看不出对应哪个设备），结果就是画面被裁且偏下。同时它把 1024×768 的帧往 800×480 的显示上贴，本来就会溢出。
- **`05_data_collect.py` 与 `02_capture_burst.py` 是近重复**，保留理由是分辨率（1024×768 vs 480×320）、注释语言（英文 vs 中文）和 `finally` 完整性不同。要采数据集用 `02`（因为数据集就是它产出的），要抄一份干净的骨架用 `05`（它的收尾是对的）。
- **保存路径 `"/data/data/images/"` 依固件而定。** 不同 CanMV 版本根文件系统布局不一样。第一次用先 `print(os.listdir("/"))` 和 `print(os.listdir("/data"))` 确认；写到不存在的目录会得到 `OSError`，而被 `except BaseException` 打印出来时只有一行 `[Errno 2]`，看不出是哪个路径错了。
- **JPEG 质量与分辨率要在采之前定死。** `img.compress(95)` 的质量、`set_framesize` 的 480×320 一起决定了数据集的样子；训练完的 kmodel 输入是 224×224，和采集分辨率不是同一个数，中间的重采样由部署脚本的 `ai2d` 完成（见 `../04_number_classification/code/`）。采到一半改分辨率，前功尽弃。
- 本目录**只有 `01` 演示了板载 LED**（GPIO62 红 / GPIO20 绿 / GPIO63 蓝，共阳：**低电平点亮**，所以 34–36 行的 `.high()` 是熄灭）。比赛现场屏幕看不清时，一颗 LED 是最便宜的状态指示器。

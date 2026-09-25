# reference — 厂商例程（立创·庐山派 LCKFB + 亚博 Yahboom）

## 这是什么

三堆**别人写的官方/第三方例程**，原样保留，不做风格化改造。它们是查 API 用法的第一手材料，也是本仓库里**唯一"能确定是对的"的代码** —— 你自己那些赛题文件的缺陷，很多要反过来拿这里的例程当参照才能定位。

| 子目录 | 文件数 | 来源 | 用途 |
|---|---:|---|---|
| `image_recognition/` | **12** | 立创·庐山派 LCKFB 官方教程 | 图像处理主线：绘制、图像处理、线段/矩形/圆形检测、颜色识别、二维码、图像裁剪、YOLOv8n 物体检测、OCR 字符识别、离线调阈值 |
| `basic_gpio/` | **12** | 立创·庐山派 LCKFB 官方教程 | 外设基本功：点灯、RGB 灯、按键、蜂鸣器、串口收发、ADC、RTC、软件定时器 |
| `yahboom_ported/` | **4** | 亚博智能 K230 教程（移植版） | 线性回归、物体计数、多颜色识别、颜色巡线 |

（`STM32/` 子目录原先也在这里 —— 它不是 K230 代码，已在 `28b5f40` 移到 `../other_boards/stm32/`。）

## ⚠️ 为什么这里的文件保留中文文件名（不许改名）

`reference/` 是全仓库**唯一故意保留中文与全角标点文件名**的地方，这是有意为之，不是漏改：

**LCKFB 和亚博的官方教程按"编号 + 中文名"称呼这些文件**（论坛帖子、B 站视频、光盘目录里写的是「12，串口测试」，不是 `12_uart_test.py`）。一旦改名，你就再也无法把屏幕上跑的这份代码和网上那份教程对上 —— 找不到出处，就查不到作者后来修的 bug、看不到配套接线图、问不到技术支持。

同理，全角逗号 `，`、书名号 `【】`、括号 `（）` 都是**原样照抄**的：`6，颜色识别（二）.py` 里那个"（二）"是教程作者自己为了区分同名两讲加的，不是我们的重名冲突处理。

改名只发生在**我们自己写的**文件上（见 `../2025_E_self_aiming/README.md` 的旧名→新名表）。**不要顺手把这里也"英文化"。**

## 文件清单

### `image_recognition/`（12 个，LCKFB 官方）

| 文件 | 行数 | 作用 | 状态 |
|---|---:|---|---|
| `1，采集到的画面上绘制.py` | 100 | `snapshot` + `draw_*` 系列基础 | 可用 |
| `2，图像处理.py` | 118 | 图像处理算子总览；内含**被注释掉的** `src_img.rotation_corr(0.5)`（旋转校正）与 `binary([(120,255)], invert=False)` 示例，是仓库里 `rotation_corr` 唯一的出处 | 可用 |
| `3，线段检测.py` | 106 | `find_line_segments` | 可用 |
| `4，矩形检测.py` | 125 | `img.find_rects(threshold=5000)` —— **对照你自己的 `iterations/use_find_rects.py` 就明白 5000 这个默认值从哪来的** | 可用 |
| `5，圆形检测.py` | 103 | `find_circles` | 可用 |
| `6，颜色识别.py` | 111 | LAB 阈值 + `find_blobs` 第一讲 | 可用 |
| `6，颜色识别（二）.py` | 120 | ⚠️ **不是重复文件**。与上一行**从第 1 行起就不是同一份代码**（`diff` 显示前 34 行整体不同），是教程的第二讲。文件名相同只因为作者把两讲都叫"6，颜色识别" | 可用 |
| `7，二维码识别.py` | 60 | QR 码 | 可用 |
| `8，图像裁剪.py` | 61 | ROI 裁剪 | 可用 |
| `9，物体检测（YOLOv8n）.py` | 218 | COCO 80 类 YOLOv8n | **需要缺失文件**：第 185 行 `kmodel_path="/sdcard/examples/kmodel/yolov8n_320.kmodel"`，该模型不在仓库 |
| `10，字符识别（OCR）.py` | 283 | OCR 检测 + 识别两段网络串联 | **需要缺失文件**：第 250/252/254 行分别要 `/sdcard/examples/kmodel/ocr_det_int16.kmodel`、`/sdcard/examples/kmodel/ocr_rec_int16.kmodel`、`/sdcard/examples/utils/dict.txt`（注意 `dict.txt` 在 **`utils/`** 下，不是 `kmodel/`），都不在仓库 |
| `离线调整阈值.py` | 333 | **触摸屏离线调 LAB 阈值**，不用连电脑 —— 见下面与 `basic_part.py` 的关系 | 可用 |

### `basic_gpio/`（12 个，LCKFB 官方）

按编号 1~12 连续，无缺号：

| 文件 | 行数 | 对应你在赛题代码里会碰到的东西 |
|---|---:|---|
| `1，基础点灯试验.py` | 39 | `Pin(..., Pin.OUT)` 最小写法 |
| `2，点亮7种不同颜色的RGB灯.py` | 63 | **2024 年那份 RGB 灯指示本来该长什么样** —— 对比 `../2024_E_tic_tac_toe/main_tic_tac_toe.py` 里 `LED_R/G/B` 只在第 17~23 行被设成 `high()` 后再没动过 |
| `3，按键控制板载RGB灯亮灭.py` | 43 | 按键输入 |
| `4，用按键切换RGB灯状态.py` | 69 | 按键状态机 —— 2025 的 `KEY = Pin(53, …)` 切阈值模式就是这个思路 |
| `5，简单鸣叫一声.py` | 18 | **`PWM` 驱动蜂鸣器的正确写法**（对比 `../2023_E_laser/k230_full.py` 的 `beep_pwm` 从未实例化） |
| `6，播放【一闪一闪亮晶晶】.py` | 46 | 上面那个的进阶，多次改频率 |
| `7，用串口发送数据.py` | 54 | **本仓库 UART 的标准起点**：`fpioa.set_function(11, UART2_TXD)` / `(12, UART2_RXD)` + `UART(UART.UART2, 115200, bits=EIGHTBITS, parity=NONE, stop=ONE)` |
| `8，用串口接收数据.py` | 26 | 接收 |
| `9，获取电压ADC.py` | 31 | ADC |
| `10，RTC实时时钟.py` | 76 | RTC |
| `11，用软件定时器控制LED灯.py` | 62 | 软件定时器 |
| `12，串口测试.py` | 44 | 回环测试 —— **做控制题前先跑这个确认链路通** |

### `yahboom_ported/`（4 个，亚博移植）

| 文件 | 行数 | 作用 | 状态 |
|---|---:|---|---|
| `1.快速线性回归.py` | 63 | 线性回归（巡线的最小可用形态） | 需要缺失依赖 |
| `2.物体计数.py` | 118 | `find_blobs` 计数 | 需要缺失依赖 |
| `3.多颜色识别.py` | 86 | 多组 LAB 阈值 | 需要缺失依赖 |
| `4.K230 颜色巡线.py` | 124 | 颜色巡线 | 需要缺失依赖 |

⚠️ **四个都要 `ybUtils` 包**（`from ybUtils.YbKey import YbKey` / `YbUart` 等），本仓库没有这个包 → 直接跑第一行就 `ImportError`。它是亚博自己 SD 镜像里的辅助库。要跑就去亚博的资料包把 `ybUtils/` 整目录拷到 SD 卡的 `examples/`（或工作目录）下；**不要为了跑通它去改这几个 `.py` 的 import**，改了就和亚博教程对不上。
同样的 `ybUtils` 依赖也存在于 `../2023_E_laser/sample_code/`（2 个文件）和 `../2023_E_laser/yahboom_reference/` 里。

## 与你自己代码的重叠：`image_recognition/离线调整阈值.py` ↔ `../2023_E_laser/basic_part.py`

实测关系（不是"近乎重复"，是"母本 + 派生"）：

- 开头 2 行注释**逐字相同**（「视觉相关的题目受到光线干扰非常严重…所以，就有了这个解决方案」），`basic_part.py` 只是在最前面多加了一行来源标注「bilibili搜索学不会电磁场看教程 / 第14课」。
- `diff` 结果 **364 行**差异；行数 **333 → 518**（+185）。
- 关键分歧：`离线调整阈值.py` 里的 PID 是 `class PID`（`def __init__(self, kp, ki, input_value, target=320)`，给**舵机**用）；`basic_part.py` 换成了 `class PID_step_motor`（`def __init__(self, kp, ki, target=240)`），并新增 `uart2 = UART(UART.UART2, 115200)` 与 `send_order(number, dir_, steps)`（第 42~49 行）向**步进电机驱动器**发 `AA AA num dir steps_hi steps_lo sum FF FF`。

**该读哪份**：想学"触摸屏离线调阈值"这个纯 UI 技术，读 `离线调整阈值.py`（短 185 行、没有电机干扰）；想看它怎么接到 2023 E 题的执行机构上，读 `basic_part.py`。**两份都别删** —— 前者是后者的母本，删了就看不出你从厂商例程到自研之间动了哪些地方。

## 旧名 → 新名

`89e6ffc`：`电赛赛题K230/00_Reference/` → `07_contest/reference/`。**例程文件名本身一个都没改**（见上面「为什么不许改名」）。

| 旧路径 | `89e6ffc` 之后 | 现在 |
|---|---|---|
| `电赛赛题K230/00_Reference/` | `07_contest/reference/` | 同左 |
| `…/00_Reference/图像识别/` | `…/reference/image_recognition/` | 同左 |
| `…/00_Reference/基本GPIO/` | `…/reference/basic_gpio/` | 同左 |
| `…/00_Reference/亚博移植参考/` | `…/reference/yahboom_ported/` | 同左 |
| `…/00_Reference/STM32/OLED/CODE/` | `…/reference/stm32/OLED/CODE/` | **`other_boards/stm32/oled_display/CODE/`** ← `28b5f40` |
| `…/00_Reference/STM32/Serial port packet/` | `…/reference/stm32/Serial port packet/` | **`other_boards/stm32/serial_packet/`** ← `28b5f40` |

例程文件内部路径示例（`89e6ffc` 的提交说明）：`…/00_Reference/图像识别/离线调整阈值.py` → `…/reference/image_recognition/离线调整阈值.py`（**只有目录英文化，文件名保留原样**）。

更早：仓库根在最初提交 `f2aa2af` 叫 `赛题K230/`，`5b4dd92` 才改成 `电赛赛题K230/`。

## 已知问题

1. **`image_recognition/9，物体检测（YOLOv8n）.py` 与 `10，字符识别（OCR）.py` 开箱跑不了**：需要的 3 个 `.kmodel` + `dict.txt` 都不在仓库（具体路径见上表）。这些属于庐山派 SD 镜像的 `examples/` 目录，需自行获取。
2. **`yahboom_ported/` 全部 4 个文件缺 `ybUtils`**（见上）。
3. **两个都叫「6，颜色识别」的文件是真的两讲，不是重名事故。** 已用 `diff` 核对：`6，颜色识别.py`(111 行) 与 `6，颜色识别（二）.py`(120 行) 从第 1 行起内容就不同。**别把其中一个当重复文件删。**
4. ⚠️ **`basic_gpio/` 与 `image_recognition/` 用的 UART 只有 8 字节裸数据（`uart.write("...")`），没有任何帧格式。** 而本仓库 `../README.md` 的协议表列出了 **10 种互不兼容的帧格式**。也就是说：例程能证明"链路通"，**不能**直接当你的通信协议用。别拿 `7，用串口发送数据.py` 去接 `../../other_boards/stm32/` 里的工程，会解析不出任何东西。
5. `image_recognition/` 多数例程的显示分辨率/HDMI/LCD 分支比我们的赛题代码更宽松（如 `../2023_E_laser/error/error1.py` 那种 VIRT/LCD/HDMI 三选一写法源自这里）。**照抄时记得对齐你自己的 `DISPLAY_WIDTH/HEIGHT`**，2023/2025 三个 main 统一是 ST7701 800×480、采集 400×240。

## 练习建议

1. **把例程和你自己的代码做一次"接口对照"（不许打开赛题文件，只看例程）**
   任务：只读 `basic_gpio/5，简单鸣叫一声.py` + `basic_gpio/2，点亮7种不同颜色的RGB灯.py` + `basic_gpio/7，用串口发送数据.py` 三个，然后**不看任何赛题代码**，手写一个 60 行以内的程序：初始化 UART2、PWM 蜂鸣器、RGB 灯，主循环每 500 ms 换一色、蜂鸣一声、发一帧 `AA <flag> <counter:H> 55`。
   **通过标准**：串口助手收到 5 帧且 `counter` 递增、字节序正确；写完后再打开 `../2023_E_laser/k230_full.py`，用你自己的版本去解释它为什么炸（缺陷 1、2 见该目录 README）。**能凭例程独立写对，才算真的会用这两个 API。**

2. **量 `find_rects` 的 threshold 参数敏感度（必须出数字）**
   用 `image_recognition/4，矩形检测.py`（第 89 行 `img.find_rects(threshold=5000)`）。
   任务：同一个矩形靶标，固定光照与距离，把 `threshold` 依次设 `2000 / 5000 / 10000 / 20000 / 50000`，每个值记录：① 检出的矩形个数；② 目标那个矩形的 `magnitude()`；③ FPS 均值（30 帧）。然后把靶标倾斜 15°、30° 各重复一遍。
   **通过标准**：交出「threshold × 倾角 → 检出个数」的表格，并明确指出**你选的阈值在多大角度内还能检出**。这正是 `../2025_E_self_aiming/methods_reference/iterations/use_find_rects.py` 当年放弃 `find_rects` 的原因 —— 你要用自己的数据复现那个结论，或者推翻它。

3. **验证 `rotation_corr` 能不能救你的斜靶标**
   `image_recognition/2，图像处理.py` 第 86 行那句被注释掉的 `src_img.rotation_corr(0.5)` 是仓库里唯一的旋转校正入口（`find_blobs`/`find_rects` **不做**旋转不变）。
   任务：把一张写着数字/带方框的纸旋转约 20° 放置，分别在启用与不启用 `rotation_corr` 两种情况下跑 `find_blobs`，比较同一目标的 `w*h` 面积与 `corners()` 位置。
   **通过标准**：报告里给出两次检出的 blob 面积比（`有校正 / 无校正`）与 FPS 差值。**必须解释为什么"面积变了"** —— 因为这直接影响 `../2025_E_self_aiming/` 里那套按面积（5000 / 20000）分档的阈值逻辑：如果旋转会让面积跨档，那条流水线在你的斜靶标下就会选错阈值。这一条想通了，你就理解了为什么"去抖 + 分档阈值"是一整套耦合设计，而不是一堆可拆的参数。

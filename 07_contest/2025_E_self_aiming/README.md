# 2025_E_self_aiming — 2025 年 E 题「简易自行瞄准装置」（本仓库作者的原创）

这是整个仓库里分量最重、也是**唯一一份自己从零写**的赛题代码。同时它也是缺陷最多的一份 —— 下面「已知问题」很长，那是因为它三个主程序**实际上没有一个真正跑通过完整闭环**，而把这些年没被发现的东西一次写清楚，比留着下次再踩有用。读之前请先读 [`../README.md`](../README.md) 的目录更正表。

## 题目要求与本目录的做法

2025 E 题「简易自行瞄准装置」要求：用视觉识别一个靶标（本题靶标是画在 A4 幅面上的矩形/方框标志），实时算出它在画面中的位置，驱动瞄准机构让激光/指针**自动对准**该目标，并在满足对准判据时执行打击/指示动作；题目对响应时间、对准误差、以及抗干扰（目标被移动、有干扰图形）都有分档要求。

本目录的做法是一条**纯视觉 + 一条 UART 出帧 + 一个 GPIO 打激光**的极简闭环：摄像头只出 400×240 灰度图，二值化 + 开运算后把白色连通域当矩形候选，按面积/长宽比过滤并做帧间连续性选择，再往前外推一帧作为预测点；预测点离屏幕中心足够近就把 GPIO48 拉高点亮激光模块，同时把坐标以 `AA | type | x(2B) | y(2B) | 55` 发给 STM32 让电控自己闭环。`result/` 里三个 main 是同一条流水线的三个取舍版本（高帧率 / 高精度 / 多判据），`find_rect/` 是"改用训练好的检测模型找矩形"的备选路线，`methods_reference/iterations/` 是走到最终方案之前的 9 个中间版本。

## 题目 PDF

`E题_简易自行瞄准装置.pdf`（本目录内，保留原中文名）。
同一份题面也在 `../../NUEDC_TOPIC-master/真题/2025/`。

## 目录结构与文件清单

```
2025_E_self_aiming/
├── E题_简易自行瞄准装置.pdf
├── result/                  三个主程序（本目录的核心）
├── find_rect/               备选路线：训练好的 AnchorBaseDet kmodel + 4 个部署脚本
└── methods_reference/
    ├── iterations/          9 个中间迭代版本
    └── error/               2 个废弃版本
```

（原 `methods_reference/NUEDC-2025-E-master/` 已确认是 **OpenMV** 代码，在 `28b5f40` 移到 `../../other_boards/openmv/nuedc_2025_e/`。）

### `result/` — 三个主程序

| 文件 | 行数 | 大小 | 作用 | 状态 |
|---|---:|---:|---|---|
| `main_thresh_ui_fast.py` | **655** | 26,734 B | 高帧率版：`find_blobs` + 手写 `find_best_rect()`，带触摸屏阈值调节 UI、按键切换阈值模式、UART 状态机 | **可用（最接近能跑的一份）**，但含下面 B/C/D/共 4 类缺陷 |
| `main_thresh_ui_accurate.py` | **987** | 38,806 B | 高精度版：改用 `cv_lite` 的 Canny + `findContours` + `approxPolyDP` 做几何筛选，再加自写的 3×3 透视变换矩阵映射 | **需要缺失依赖**（`import cv_lite`），且 fallback 路径自身有 3 处崩溃（E/F 类） |
| `main_multi_constraint.py` | **451** | 17,931 B | 多限制条件版：嵌套矩形（外框+内框）判据 + 一维卡尔曼滤波平滑坐标。**无触摸屏 UI、无 UART 状态机**（没有 `TOUCH`、没有 `Situation`，主循环每帧直跑） | 不完整 —— **它名字里那个"多限制条件"功能从未执行过一次**（见缺陷 G） |

### `find_rect/` — 备选路线（模型检测矩形）

| 文件 | 行数 | 大小 | 作用 | 状态 |
|---|---:|---:|---|---|
| `find_rect/mp_deployment_source/best_AnchorBaseDet_can2_5_s_20250803004720.kmodel` | — | 7,552,016 B | 自己训练的 AnchorBaseDet 检测模型（文件名时间戳 20250803） | 可用（但见下面「缺文件」） |
| `det_image_1_2_2.py` | 149 | 5,558 B | CanMV **v1.2.2** 固件下单图推理：手写 `nncase_runtime` + `ai2d` 预处理，结果存 `/sdcard/mp_deployment_source/det_result.jpg` | 需要缺失依赖 + 3 处缺陷 |
| `det_video_1_2_2.py` | 188 | 7,375 B | 同上的实时视频版，`display_mode="lcd"` → `Display.ST7701`（800×480） | 需要缺失依赖 + 4 处缺陷 |
| `det_image_1_3.py` | 70 | 3,143 B | CanMV **v1.3+** 固件下单图版：走 `libs.PlatTasks.DetectionApp` 高层封装 | 需要缺失依赖 + 1 处路径缺陷 |
| `det_video_1_3.py` | 80 | 3,625 B | 同上的视频版，`display_mode = "lt9611"`（HDMI 1080p） | 需要缺失依赖 + 2 处缺陷 |
| `README.pdf` | — | 156,800 B | 厂商/工具链的部署说明文档，**读这个而不是猜 API** | 可用 |

⚠️ **本目录缺两个脚本运行必需的文件**（实测 `find . -name "deploy_config.json" -o -name "test.jpg"` 全仓库无结果）：

- `deploy_config.json` —— 四个脚本都读 `/sdcard/mp_deployment_source/deploy_config.json`，字段用到 `kmodel_path` / `categories` / `confidence_threshold` / `nms_threshold` / `img_size` / `nms_option` / `model_type` / anchors。**它不在仓库里，这是有意的**：仓库根 `.gitignore` 第 13~14 行显式写了 `deploy_config.json` 与 `det_results/`（连同第 12 行的 `cls_results/`）—— 它们是 nncase 每次导出时重新生成的产物，不该入库。要用就在导出模型时一并生成，再和 `.kmodel` 一起拷到 SD 卡的 `mp_deployment_source/`。
- `test.jpg` —— 而且两个单图脚本找的位置**不一样**：`det_image_1_2_2.py:17` 是 `root_path + "test.jpg"` = `/sdcard/mp_deployment_source/test.jpg`；`det_image_1_3.py:29` 硬编码 `/sdcard/test.jpg`。
- 旧版 README 还提到 `det_results/` 目录 —— **不存在**。
- 四个脚本还依赖 `libs.PlatTasks` / `libs.PipeLine` / `libs.Utils` / `aicube` / `nncase_runtime` / `ulab`，这些由庐山派固件与 SD 镜像提供，不在本仓库。`.kmodel` 要放到 **SD 卡根的 `mp_deployment_source/`** 下（`/sdcard/mp_deployment_source/…`），不是仓库里的相对路径。

### `methods_reference/iterations/` — 9 个中间版本

每个都独立可跑（除 `cvlite_variant.py` 需 `cv_lite`），共用同一套硬件配置（UART2 引脚 11/12、`LED = Pin(48)`、400×240 GRAYSCALE、发 `AA|<BHH>|x|y|55`）。列成表看演进最清楚：

| 文件 | 行数 | 旧名 | 在试什么 | 结局 |
|---|---:|---|---|---|
| `use_find_rects.py` | 246 | `25-master（find_rect）.py` | 不写候选筛选，直接用固件内置 `img.find_rects(threshold=5000)`；`Display.VIRT` | **放弃**。`find_rects` 对细线方框不稳，最终改用 `find_blobs` + 手写几何过滤 |
| `custom_rect_check.py` | 266 | `25-master1（自定义矩形判断）.py` | 改回 `find_blobs` + `min_corners()` + 面积/长宽比过滤；**还没有帧间连续性、没有预测**；`Display.VIRT` | 思路**被采纳**，进 `result/`；无预测这一点被后面补上 |
| `custom_rect_check_dup.py` | 266 | `25-master（自定义矩形判断）.py` | ⚠️ **与上一行字节完全相同**（`git hash-object` 同为 `7291c245735014a82214f34c5f07030f46a821fc`）。旧名一个是 `25-master1（…）` 一个是 `25-master（…）`，靠"1"区分，其实是同一份存了两次 | 新名里的 `_dup` 就是在说这件事 |
| `gimbal_rect_roi.py` | 288 | `云台找矩形（矩形ROI框定）.py` | 加 **A4 长宽比过滤**（`A4_ASPECT_RATIO = 1.414`、容差 `0.2`），形态学用的是 `close(1)` 而不是 `open(1)`；阈值 `rect_binart = [(84, 200)]`。⚠️ 文件名里的 "roi" 在代码里**找不到对应实现**（无 `roi=` 用法），实质区别是 A4 比例过滤 + 闭运算 | **部分采纳**：A4 比例过滤没进 `result/`（会漏识别非 A4 靶标），`open(1)` 最终胜出 |
| `gimbal_rect_voting.py` | 342 | `云台找矩形（投票选矩形）.py` | 多帧**滑动窗口投票**：`SLIDING_WINDOW_SIZE = 5`、`MIN_DETECTION_COUNT = 3`、`rect_history`，5 帧里同一位置出现 ≥3 次才认。长宽比放宽到 0.3~3.0；`Display.VIRT` | **放弃**。5 帧窗口引入 5 帧延迟，与"响应时间"要求冲突；替代方案是更便宜的"连续 N 帧距离 ≤50 px"计数（进了 `result/`） |
| `gimbal_rect_predict.py` | 298 | `云台找矩形（激光点的预测）.py` | 首次引入**一帧速度外推**（`velocity = center − previous_target`；`predicted = center + velocity`）+ 稳定计数 | **采纳**，是 `result/` 三个 main 的直接形态 |
| `gimbal_rect_predict_v2.py` | 322 | `云台找矩形（激光点的预测） copy.py` | 在 predict 之上把阈值拆成**三档按面积自适应**（`rect_binary_default/small/large` + `get_binary_threshold()`） | **采纳**。三个 main 全部继承这套三档阈值（以及它的边界 bug，见缺陷 A） |
| `gimbal_rect_opening.py` | 307 | `云台找矩形（开运算） copy.py` | 用 `cv_lite.rgb888_open(...)` 自己做开运算，而不是 `img_binary.open(1)` | **放弃**。固件原生 `open(1)` 更快更省事（`result/` 用的是原生） |
| `cvlite_variant.py` | 500 | `25电赛E题3(1).py` | 第一版完整的 `cv_lite` 管线（GaussianBlur → Canny → findContours → approxPolyDP → isContourConvex → boundingRect）+ **自写 3×3 透视变换矩阵** `get_perspective_matrix()` / `transform_points()` / `sort_corners()` / `get_rectangle_orientation()` | **采纳为 `result/main_thresh_ui_accurate.py` 的骨架**（accurate 文件里那几处「来自25电赛E题3(1).py」注释就是它）。同时它也是 `cv_lite` 依赖被引进的地方 |

> 关于 " copy" 后缀的两条重要提醒：
> 1. **`gimbal_rect_opening.py` 没有不带 " copy" 的同伴** —— 它是那一对里唯一幸存的文件，**不是重复文件，不许当"副本"删**。
> 2. `gimbal_rect_predict_v2.py` 与 `gimbal_rect_opening.py` 的旧名**都**带 " copy"，但**这不代表它们互为副本** —— 一个改预测+阈值，一个改形态学实现，实测内容完全不同。" copy" 只是浏览器重复下载时的自动后缀，只说明"和当时的某个文件同名"，不说明内容重复。
> 3. `cvlite_variant.py` 的旧名 `25电赛E题3(1).py` 里的 `(1)` 同样是浏览器下载后缀，改名成 `cvlite_variant` 是为了让"它依赖 cv_lite"这件事写在脸上。
> 4. 该文件此前在工作区里是**只读**属性。本次核对：当前 `stat` 为 `-rw-r--r--`、git 索引模式 `100644`，**已不是只读**。

### `methods_reference/error/` — 2 个废弃版本

| 文件 | 行数 | 旧名 | 说明 |
|---|---:|---|---|
| `error1.py` | 384 | `方法及参考/ERROR/ERROR1.py` | 抬头写的是「激光瞄准打靶装置 —— 识别 A4 幅面紫外感光纸上的靶标：红色靶心(直径≤0.1cm) + 5 个同心圆(半径 2~10cm，间隔 2cm)」，即**把靶标理解成同心圆**的那一版；发 `AA\|<BHHHB>\|x\|y\|score\|hit_type\|55` 帧。语法通过，方案被放弃（同心圆对识别的实时要求太高） |
| `error2.py` | 576 | `方法及参考/ERROR/ERROR2.py` | 发 `AA\|<BHHHH>\|laser_x\|laser_y\|target_x\|target_y\|55`（打点+目标点同帧）的那一版；语法通过，接口与最终 STM32 约定不符，废弃 |

## 共享流水线（逐条在代码里核对过）

下面每一条都在三个 main 里验证过具体数值，可直接当作答题时的"我到底做了什么"清单：

| 环节 | 具体实现 | 出处（fast / accurate / multi） |
|---|---|---|
| 采集 | `Sensor(id=2)`，`set_framesize(width=400, height=240, chn=CAM_CHN_ID_0)`，`set_pixformat(Sensor.GRAYSCALE, …)` | 13~14、458~459 / 16~17 / 11~12、289~290 |
| 显示 | `Display.init(Display.ST7701, 800×480, to_ide=True)` | 461 / 同 / 293 |
| 二值化阈值分档 | `get_binary_threshold(area)`：**`area < 5000` → small**；**`5000 < area < 20000` → default**；**其余 → large**。边界值 5000 / 20000 | 27~33 / 31~37 / 25~31 |
| 三档阈值实际值 | fast：default `(103,255)`、small `(127,216)`、large `(85,200)`；accurate：`(95,255)`、`(110,216)`、`(80,200)`；multi：`(100,255)`、`(127,216)`、`(81,200)` | 22~24 / 26~28 / 20~22 |
| 用上一帧面积选档 | 上一帧 `max_rect.area()` 决定本帧阈值，首帧用 `rect_binary_default` | 507~513 / 798~806 |
| 形态学 | `img_binary.open(1)`（开运算 = 先腐蚀后膨胀），梯度运算那 6 行注释掉保留着 | 517 / 808 / 325 |
| 找矩形 | `find_blobs([(255,255)], x_stride=2, y_stride=2, area_threshold=100)` → `min_corners()` → 面积 `MIN_RECT_AREA=500`/`MAX_RECT_AREA=50000`、长宽比 `0.5`~`2.5` 过滤 → 帧间连续性优选（上一帧中心 50 px 内优先，否则取最大面积） | 358~430（fast）；accurate 换成 `cv_lite` Canny 管线（594~722）；multi 先试 `find_nested_rects()` 再回退 `find_best_rect()`（338~340） |
| 一帧速度外推 | `velocity = center − previous_target`；`predicted = center + velocity` | 548~553 / 873~878 / 358 之后 |
| 稳定判定 | `TARGET_STABILITY_THRESHOLD = 3`；距 `last_valid_target` `< 50` px 计数 +1；`> 100` px 视为误检只减不增；`50~100` 之间计数重置为 1 | 61、557~568 / 65、885~895 / multi 同 |
| UART 出帧 | UART2 @115200，`fpioa` 11=TXD、12=RXD；帧 = `b'\xAA' + struct.pack('<BHH', flag, x, y) + b'\x55'`（**6 字节，小端**）；`flag` 0=未检出、1=检出；整帧共 **7 字节**（`AA` 1 + `BHH` 5 + `55` 1），**小端** | 37~38、45、436/442（其余同） |
| 打激光 | `fpioa.set_function(48, FPIOA.GPIO48)`；`LED = Pin(48, Pin.OUT, pull=Pin.PULL_NONE, drive=15)`；判据 `distance((200,120), predicted_target) < 30` → `LED.value(1)` | 39、46、610~615 / 936~941 / 35~37、418~423 |
| 屏幕中心 | `SCREEN_CENTER_X = 200`、`SCREEN_CENTER_Y = 120`（即 400×240 的正中） | 49~50 / 52~53 / 42~43 |
| 调试出图 | `draw_string_advanced` 打 FPS、中心坐标、`dist_to_target`、当前阈值 | 618~621 / 944~947 |
| 收尾 | `except BaseException: print(f"异常: {e}")` + `finally` 停 sensor / `Display.deinit()` / `os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)` / `MediaManager.deinit()` | 642~655 / 976~987 / 440~451 |

## 旧名 → 新名

第一次改名：`89e6ffc`（`电赛赛题K230` → `07_contest`）。第二次：`28b5f40`（非 K230 代码移出）。

| 旧名（`89e6ffc` 之前） | `89e6ffc` 之后 | 现在 |
|---|---|---|
| `电赛赛题K230/04_2025_E_SelfAiming/` | `07_contest/2025_E_self_aiming/` | 同左 |
| `…/Result/` | `…/result/` | 同左 |
| `…/Result/main（可阈值调节高帧）.py` | `…/result/main_thresh_ui_fast.py` | 同左 |
| `…/Result/main（可阈值调节高识别）.py` | `…/result/main_thresh_ui_accurate.py` | 同左 |
| `…/Result/main（多限制条件）.py` | `…/result/main_multi_constraint.py` | 同左 |
| `…/find_rect/`（含 `mp_deployment_source/`、`README.pdf`、4 个 `det_*.py`） | 同名保留 | 同左 |
| `…/方法及参考/` | `…/methods_reference/` | 同左 |
| `…/方法及参考/迭代版本/` | `…/methods_reference/iterations/` | 同左 |
| `…/方法及参考/迭代版本/25-master（find_rect）.py` | `…/iterations/use_find_rects.py` | 同左 |
| `…/方法及参考/迭代版本/25-master1（自定义矩形判断）.py` | `…/iterations/custom_rect_check.py` | 同左 |
| `…/方法及参考/迭代版本/25-master（自定义矩形判断）.py` | `…/iterations/custom_rect_check_dup.py` | 同左（与上一行内容**完全相同**） |
| `…/方法及参考/迭代版本/25电赛E题3(1).py` | `…/iterations/cvlite_variant.py` | 同左 |
| `…/方法及参考/迭代版本/云台找矩形（开运算） copy.py` | `…/iterations/gimbal_rect_opening.py` | 同左（**无同名非 copy 版本**，别当副本） |
| `…/方法及参考/迭代版本/云台找矩形（投票选矩形）.py` | `…/iterations/gimbal_rect_voting.py` | 同左 |
| `…/方法及参考/迭代版本/云台找矩形（激光点的预测） copy.py` | `…/iterations/gimbal_rect_predict_v2.py` | 同左 |
| `…/方法及参考/迭代版本/云台找矩形（激光点的预测）.py` | `…/iterations/gimbal_rect_predict.py` | 同左 |
| `…/方法及参考/迭代版本/云台找矩形（矩形ROI框定）.py` | `…/iterations/gimbal_rect_roi.py` | 同左 |
| `…/方法及参考/ERROR/ERROR1.py`、`ERROR2.py` | `…/methods_reference/error/error1.py`、`error2.py` | 同左 |
| `…/方法及参考/NUEDC-2025-E-master/` | 同名保留 | **`other_boards/openmv/nuedc_2025_e/`** ← `28b5f40` 移出，因为它 `from pyb import …`，是 OpenMV4 的代码 |
| `…/E题_简易自行瞄准装置.pdf` | 同名（不改） | 同左 |

⚠️ 改名时**没有**改动的东西：`find_rect/` 下的 4 个 `det_*.py` 文件名、`.kmodel` 文件名、赛题 PDF 中文名。旧版 README 提到的 `04_2025_E_SelfAiming/Result`、`方法及参考/`、`mp_deployment_source/`（作为 `find_rect/` 直接子级的说法）**均为历史路径**。

## 已知问题（逐条实测；这份代码不干净）

### A. 三个 main 共有：`area == 5000` 会掉进"大面积"档

```
if area < 5000:                 return rect_binary_small
elif area > 5000 and area < 20000: return rect_binary_default
else:                           return rect_binary_large
```

`area` 恰好等于 5000 时，第一个条件假、第二个（`> 5000`）也假，于是落到 `else` → **用大面积阈值去处理中等面积的目标**。三个文件一模一样（fast 27~33、accurate 31~37、multi 25~31）。面积是整型，`5000` 是会被撞上的。
正确写法应把第二个分支写成 `elif area < 20000`。

### B. `main_thresh_ui_fast.py` / `main_thresh_ui_accurate.py`：**"开始识别"命令是空操作**

`Situation` 的注释（fast 第 469 行、accurate 对应位置）写得很清楚：

```
Situation = 0  # 0:未初始化, 1:开始识别, 2:停止识别, 3:阈值调节
```

UART 收到 `55 01 FF FF` 时把 `Situation = 1`（fast 491~493，打印「识别矩形，校准激光」）。
但分发逻辑（fast 502~637）是：

```
if Situation == 0:      # ← 真正干活的是 0（"未初始化"）
    …整套流水线…
elif Situation == 2:    pass
elif Situation == 3:    handle_threshold_adjustment()
else:                   pass   # ← Situation == 1 落到这里，什么都不做
```

**后果**：电控发"开始识别"，K230 反而停手；K230 一上电（`Situation=0`）却立刻开始识别和发帧。也就是说串口这条"开始"指令**从来没起过作用**，现场只能靠"上电即识别"来配合。
**正确写法看同一仓库的 [`../2023_E_laser/main_high_fps.py`](../2023_E_laser/main_high_fps.py) 第 198 行 —— 它的祖先写的是 `if Situation == 1:`，是对的。** 把 `== 0` 改成 `== 1` 即可（本仓库不代为修改）。

顺带两处不一致，改的时候一并注意：
- 收包长度：`main_high_fps.py` 与 `main_thresh_ui_fast.py` 用 `bytearray(4)` / 要求 `== 4`，而 `main_thresh_ui_accurate.py` 用 `bytearray(5)` / 要求 `== 5`（第 778、780 行）。同一个电控发同一帧 `55 01 FF FF`，只有 4 字节的版本收得到。
- `multi_constraint.py` 完全没有 `Situation` 状态机，也就没有这个问题（也没有"电控让开始/停止"的能力）。

### C+D. fast / accurate 共有：进阈值调节界面会**篡改你调好的阈值**（这是最危险的一条）

`init_slider_values(mode)`（fast 95~103、accurate 107~114）：

```
def init_slider_values(mode):          # ← mode 参数从头到尾没被读过
    if threshold_mode == 0:  return [82, 212]     # ← 读的是全局 threshold_mode
    elif threshold_mode == 1: return [85, 220]
    else:                     return [75, 200] / [85, 200]
```

三件事叠在一起：

1. **参数被忽略**：形参 `mode` 一次都没用，函数实际读全局 `threshold_mode`。调用点写的还是 `init_slider_values(current_mode)`（fast 105、326；accurate 117、338），传进去的是显示模式字符串 `'gray_rect'`，函数根本不看。
2. **硬编码值和同文件的默认值不一致**：fast 自己的 `rect_binary_default/_small/_large` 是 `(103,255)`、`(127,216)`、`(85,200)`（第 22~24 行），accurate 的是 `(95,255)`、`(110,216)`、`(80,200)`（第 26~28 行）—— 而滑块初始值给的是 `[82,212]`、`[85,220]`、`[75,200]`/`[85,200]`。**没有一组对得上。**
3. **两个文件之间这组硬编码值还彼此不同**（大面积档 fast 是 `[75,200]`，accurate 是 `[85,200]`）。

**必须说清后果**：`save_thresholds()`（fast 284~304、accurate 296~316）做的是
`rect_binary_*.clear(); rect_binary_*.extend([tuple(slider_values)])` —— 直接覆写全局。
于是：

> 你进场馆，把阈值在真实光照下一点点调到能识别（此刻内存里是调好的值）。按了一下 KEY(GPIO53) 或电控发了 `55 03 FF FF`，界面打开 —— **滑块立刻跳到那三个硬编码值之一，不是你调的值**。你只要顺手按下「保存」，你在赛场灯光下调出来的那组阈值就被无声覆盖成一组和现场毫无关系的数字，屏幕上还会礼貌地打出「保存成功!」。

**这个功能存在的目的正是防止"阈值被现场光照毁掉"，而它自己就是最大的毁阈值来源。** ⚠️ 现场调试前务必先修这条，或者干脆不要按「保存」。
修法方向（不代为修改）：`init_slider_values` 应 `return list(当前全局 rect_binary_xxx[0])`，即以文件自己的真实值为初值，并真正使用它收到的档位。

### E. `main_multi_constraint.py`：它的招牌功能**从未执行过一次**

`find_nested_rects()` 第 81~86 行：

```
outer_points = outer_blob.min_corners()
if len(outer_points) < 4:
    continue
# 新增：检查轮廓近似多边形顶点数，只有8个顶点才是目标矩形
if len(outer_points) != 8:
    continue
```

`min_corners()` 返回的是**最小外接面积矩形**的角点，**恒为 4 个点**，永远不可能等于 8。所以第 86 行这条 `continue` 对**每一个** blob 都成立，函数遍历完所有候选后 `return None`。
主循环（第 338~340 行）：

```
max_rect = find_nested_rects(img_binary)
if max_rect is None:
    max_rect = find_best_rect(img_binary, is_first_frame, last_frame_center)
```

于是每帧都走 fallback，`main_multi_constraint.py` **实际上和 `main_thresh_ui_fast.py` 跑的是同一套 `find_best_rect()`**，只是多了卡尔曼平滑。它不报错、不打日志、结果看着也正常 —— 这类"静默失效"是三个 main 里最难自己发现的。

**真正的判别器在下面几行，而且逻辑是对的**（第 90~98 行）：

```
outer_area = outer_w * outer_h                  # 外接矩形面积
area_ratio = outer_area / outer_blob.area()     # ÷ 实际白色像素数
if area_ratio < 1.5:
    continue
```

双层方框（空心框）的**外接面积远大于像素面积**（框只占周长那几个像素带），比值会明显 > 1；而实心块或误检的比值接近 1。这才是区分"这是一个空心方框"和"这是一坨白色"的正确判据。

**删掉第 85~87 行那个死判据，`area_ratio` 这条路才第一次真的开始跑。** ⚠️ 但请注意：
- 这条路径**从来没运行过**，行为完全未知，不能当作"只是解除注释、肯定能用"来处理；
- 它外面套着一个 `for i, outer_blob in enumerate(blobs): for inner_blob in blobs[i+1:]:` 的双重循环 —— 以前每帧都在**第一次迭代就被 `!= 8` 短路掉**，几乎不花时间；放开后变成对面积排序后的 blob 列表做真正的 **O(n²)** 遍历，帧率会掉多少**必须实测**；
- 内框判据（`inner_area` 在 `MIN_RECT_AREA/4` ~ `outer_area/2`、且四边内切于外框）也是没验证过的假设；
- 换到 800×480 或不同靶标距离时，`1.5` 这个阈值几乎肯定要重调。
**改完必须上板验证，不能只在 IDE 里看图。**

### F. `main_multi_constraint.py`：文件头注释与代码不一致

第 21~22 行注释写「面积小于**500**像素时的二值化阈值」「面积大于**10000**像素时的二值化阈值」，而第 25~31 行 `get_binary_threshold()` 用的是 **5000** 和 **20000**。fast / accurate 的注释与代码是一致的，只有这个文件错。按 500/10000 去理解分档，会把阈值调档的时机理解错整整一个数量级。

### G. `main_thresh_ui_accurate.py` 的三连崩 + 静默退出

1. **`import cv_lite`（第 14 行）—— 本仓库没有这个模块。** 它由庐山派固件/SD 镜像提供，不在代码里。板子上有没有，最直接的检查就是在 CanMV IDE 的终端里执行一次 `import cv_lite`。同仓库需要它的还有 `methods_reference/iterations/cvlite_variant.py`（第 4 行）和 `../laser_drawing/02_triangle_exposure.py`（第 11 行）。
   顺带：`import ulab.numpy as np`（第 15 行）也是固件提供。
2. **fallback 的 `RectLike` 没有 `corners()`，但主循环无条件调它。** 第 678~690 行定义的 `RectLike` 只有 `rect()` / `center()` / `area()` 三个方法（`find_nested_rectangles()` 里第 535~552 行那个**有** `corners()`，两处不同名同形，很容易看错）。而主循环第 829 行 `corners = max_rect.corners()` → **AttributeError**。
3. **`matrix` 只在 `len(corners) == 4` 分支里赋值（第 850 行），却在第 950 行每帧被读**（`if matrix is not None:` 用来决定屏幕显示 `Perspective: OK` / `FAIL`）。首次进入若那个分支没走到 → **NameError**；若走到了但后续某帧没走到 → 显示的是**上一帧留下的旧值**，屏幕上那句 "Perspective: OK" 就成了谎话。

**为什么这三条谁都没发现**：`except BaseException as e: print(f"异常: {e}")`（第 976~977 行）**只打印一行异常文本、不打印 traceback**。程序从哪一行崩的、调用栈是什么，全部丢失，现场只看到"跑了半秒就安静退出了"。
**修法（记录，不动手）**：在那个 `except` 里加 `sys.print_exception(e)`（`sys` 第 1 行已经导入了）。同样适用于 fast（644~645）与 multi（440~441），以及 2023 的 `k230_full.py` 和 2024 的 `main_tic_tac_toe.py` —— **全仓库的 `except BaseException` 都在吞 traceback，这是本目录大量缺陷长年潜伏的共同原因。**

## 练习建议

按顺序做，前两道是"把这份代码变成真的能跑"，后两道是"逼你量数字"。

1. **拆掉吞异常的壳，把三个 main 各自的真实死因找出来**
   在临时副本里，把三个 main 的 `except BaseException as e: print(f"异常: {e}")` 换成 `sys.print_exception(e)`，逐个上板跑。
   **通过标准**：交出一张「文件 × 第一条 traceback 的文件名:行号 × 异常类型 × 异常消息」表，三行都要有，且行号**能对上本文「已知问题」里的编号**（accurate 应对上 G 组，fast 应对上 B 或 C，multi 若报 `find_nested_rects` 相关则说明你手动删过 E 里的死判据）。任何一格写"没报错"但程序又确实没出结果，说明你换的 `except` 没生效 —— 回去检查是不是只改了其中一个分支。

2. **修 B + C 两处，并用串口对拍验证**
   - B：把干活分支的 `if Situation == 0:` 改成 `== 1`，并解释 `Situation = 0` 时应该做什么。
   - C：让 `init_slider_values()` 真正以当前全局阈值为初值。
   **通过标准**：(a) 上电后 K230 **不**发任何 `AA…55` 帧（用逻辑分析仪或 USB 串口助手抓），电控发 `55 01 FF FF` 后**开始**发帧，发 `55 02 FF FF` 后**停止**；(b) 阈值界面里滑块初值 == 文件头 `rect_binary_default` 的两个数（把两处数值并排抄下来核对）；(c) 先在 A 光照下调到阈值 T1 并保存，进界面、不碰滑块、直接按保存，再打印当前生效值 —— **必须仍是 T1**。做不到 (c) 就是 C 还没修好。

3. **量化三档自适应阈值的收益（必须出数字，不许用"更稳了"）**
   同一靶标、同一距离，做三组：全用 `rect_binary_default` / 全用 `small` / 用带 A 缺陷的三档自适应。每组记录：
   ① 屏幕上 `FPS:` 读数连续 30 帧的均值与最小值；② 把靶标沿水平方向匀速移动，统计"进入视野 → 首次发出 `flag=1` 帧"的**帧数**（20 次，取中位数）；③ 故意在画面里放一张白纸作为干扰，统计误检发帧次数 / 100 帧。
   **通过标准**：三组 × 三项指标的表格齐全，并明确指出**在什么面积区间内自适应才带来正收益**（用 `find_blobs` 打出的实际 area 数值来定区间，而不是"大概"）。顺手验证一次 A 缺陷：把靶标缩放到 `area` 正好 5000 附近，看它有没有掉进 large 档 —— 从屏幕 `阈值:(…)` 那行读数就能判断。

4. **打开 E 的死判据，然后测你到底付出了什么**
   删掉（或在副本里注释掉）`main_multi_constraint.py` 第 85~87 行的 `if len(outer_points) != 8: continue`，让 `area_ratio ≥ 1.5` 这条真正生效。
   **通过标准**：报告必须包含三件事：(a) 帧率变化 —— 改前/改后各 30 次采样的 FPS 均值，**给出下降百分比**；(b) 有效性 —— 摆一个真·双层方框和一个实心色块，各测 20 次，写清 `find_nested_rects()` 分别返回了什么（不是 `None` 才算生效）；(c) 稳定性 —— 连续跑 60 秒，记录 `hit rate`（`dist_to_target < 30` 且 `LED.value(1)` 为真的帧数 / 总帧数），改前改后各一组。**如果 (a) 的下降超过一半，或者你无法解释为什么，就把它标为"不上赛场"并写回原样。** 这道题的重点是让你习惯"解除一段死代码 = 引入一条从未运行过的路径 = 必须重新测全部指标"。

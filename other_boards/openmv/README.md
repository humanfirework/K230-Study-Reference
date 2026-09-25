# openmv — OpenMV 平台的代码（K230 上不能跑）

## 这里放什么

**判定标准**：文件里出现 `from pyb import …`，或者用了 OpenMV 那套全局 `sensor` 模块（`import sensor, image, time` + `sensor.reset()` + `sensor.snapshot()`）。

CanMV K230 **没有 `pyb` 这个模块**（那是 MicroPython 为 STM32 硬件抽象出来的旧式 API），也没有 OpenMV 那种"import 完就能 `sensor.reset()`"的全局单例 —— K230 要 `from media.sensor import *` 然后 `Sensor(id=2)` 显式构造、显式 `set_framesize` / `set_pixformat` / `run()`。

所以这些文件在本仓库里的定位是：**算法参考 + 别人的解法**，不是能跑的代码。

> ⚠️ 本目录**不是"你自己写的东西"**。里面除 `2023_laser/` 那两份之外，`nuedc_2025_e/` 是**另一位作者（B 站 @程欢欢的智能控制集）的完整方案，带 MIT 许可**。抄之前先读下面「许可与出处」那一节。

## 文件清单

### `nuedc_2025_e/` — 别人写的 2025 E 题 OpenMV4 方案（5 项）

| 文件 | 行数 | 大小 | 作用 | 状态 |
|---|---:|---:|---|---|
| `25电赛E题-OpenMV-图像识别示例-程欢欢-V1.py` | 131 | 6,770 B | 2025 E 题「简易自行瞄准装置」视觉部分第一版。**核心思路：先用黑色阈值 `find_blobs([thr_black], merge=False)` 找黑框，再在**每个黑框的 `rect()` 里**开一个 ROI，用白色阈值 `find_blobs([thr_write], area_threshold=2, roi=single_black_blob.rect(), merge=False)` 找里面的白子** —— "嵌套 ROI 二道筛选"。VGA 采集后 `set_windowing([200,120,240,240])` 只取中央 240×240（换取帧率） | 需要 pyb（OpenMV 专用） |
| `25电赛E题-OpenMV-图像识别示例-程欢欢-V1.1.py` | 97 | 4,886 B | 同一份代码的精简版（131→97 行，注释大幅删减），算法不变（第 55、64 行仍是那两个嵌套 `find_blobs`） | 需要 pyb |
| `激光矩形集中调参/激光矩形集中调参.py` | 195 | 8,732 B | ⭐ **本目录最有工程价值的一份**。不是"另一个解法"，而是一个**参数集中管理 + 两段式确认**的范本，见下面专门一节 | 需要 pyb |
| `LICENSE` | — | 1,066 B | **MIT License，Copyright (c) 2025 程欢欢** | 必须保留，不许删/改 |
| `.gitignore` | — | 350 B | 原作者工程的 gitignore（Flash Builder / Eclipse 风格，`bin-debug/`、`[Oo]bj/` 等），**与 K230 无关**，随包一起搬进来的 | 保留（属于原作者的工程原状） |

### `2023_laser/` — 2023 E 题的 OpenMV 视觉端（2 项）

| 文件 | 行数 | 大小 | 作用 | 状态 |
|---|---:|---:|---|---|
| `green.py` | 122 | 3,820 B | 绿色激光追踪端。`QQVGA(160×120)` + `set_windowing((120,120))`，每帧 `img.lens_corr(1.4)` 做**镜头畸变校正**，红/绿两模式分支；`THRESHOLD_R = [(0, 255, 15, 255, -8, 61)]`（⚠️ 第 3、4 行**重复赋值了同一个变量两次**） | 需要 pyb |
| `red.py` | 204 | 6,028 B | 红色激光端，是**主控端**：会**逐帧向另一端下发指令** `uart.read(1)` 收 `task`，回 `A1 33 1A`（应答）、`A1 11 1A`（完成）、`A1 44 1A`（标定完成）三帧；追踪时发 `A1 02 flx dx fly dy 1A`（**带符号的增量**，不是绝对坐标）。含标定流程与 `DIV_TASK_2 = 10` / `DIV_TASK_3 = 6` 分频参数 | 需要 pyb |

## 许可与出处（⚠️ 抄之前先看这段）

- `nuedc_2025_e/` 三份 `.py` 是 **B 站 @程欢欢的智能控制集** 的代码，第 1 行注释可查：`#By B站@程欢欢的智能控制集 20250730` / `#例程序使用OpenMV4运行，OpenMV4Plus亦可`。许可是 **MIT**（见 `nuedc_2025_e/LICENSE`，`Copyright (c) 2025 程欢欢`）。
- **`LICENSE` 文件必须跟着代码走，不许删。** MIT 允许商用与修改，唯一条件就是保留版权声明 —— 把 `LICENSE` 删了再抄，就从"合规借鉴"变成"违反许可"。
- 电赛对代码来源的态度请以当年规程为准。**保守做法**：如果你借鉴了它的思路（尤其是那个"嵌套 ROI 二道筛选"或"参数集中管理"），在你自己的文件头写一行来源注释，成本为零、事后无争议。
- 这份代码以前**无标注地**躺在 `07_contest/2025_E_self_aiming/methods_reference/NUEDC-2025-E-master/` 里，和你自己写的 `result/`、`iterations/` 混在同一个赛题目录下 —— 那是全仓库最容易误抄的位置。`28b5f40` 把它移出来，就是为了让它**先自报平台（OpenMV）再谈内容**。

## 值得移植的算法与 CanMV 对应 API

这一节是本目录存在的实际理由。**移植的是思路，逐行照抄是不可能的（API 不通用）。**

### 1. 从 `nuedc_2025_e/25电赛E题-OpenMV-图像识别示例-程欢欢-V1.py`：嵌套 ROI 二道筛选 ⭐ 最该抄的一招

OpenMV 写法（V1 第 70~82 行）：
```
black_blobs = img.find_blobs([thr_black], merge=False)        # 先找所有黑框
for single_black_blob in black_blobs:
    write_blobs = img.find_blobs([thr_write],
                    area_threshold=2,
                    roi=single_black_blob.rect(),              # ← 只在黑框内部找白的
                    merge=False)
```
为什么有效：第二遍搜索的面积被压到黑框那么大，**噪声候选数量断崖式下降**，帧率和准确率同时变好；而且"白东西在黑框里"本身就是一条强先验，不需要额外几何判据。

CanMV K230 对应：`find_blobs()` **同样支持 `roi=`**，`blob.rect()` 同样可用。写法几乎一致，只是要把 `img` 换成 `sensor.snapshot(chn=CAM_CHN_ID_0)` 拿到的帧，且注意 CanMV 的 `find_blobs` 阈值是"每组 6 元组一个列表"，格式相同。

**对照你自己的实现**：你 2025 年走的是另一条路 —— `main_multi_constraint.py` 里用 `area_ratio = 外接矩形面积 / 实际像素面积 ≥ 1.5` 来判断"空心双层框"。那是一条**更聪明但从未生效**的路（`min_corners()` 恒返回 4 点导致前面的判据把整条分支短路了，详见 `../../07_contest/2025_E_self_aiming/README.md` 的缺陷 E）。**嵌套 ROI 是它的可直接替代品，而且已经被人验证过。**

### 2. 从 `2023_laser/green.py`：`lens_corr` 畸变校正 + 跟随式小 ROI

- `img.lens_corr(1.4)` —— 广角/短焦镜头在画面边缘把直线拉弯，而**矩形检测对直线最敏感**。CanMV/OpenMV 系同样有 `img.lens_corr(strength)`，在 `find_rects()` 之前调一次往往比加大 `threshold` 更有效。
  （本仓库目前**没有**任何一处用 `lens_corr`。参考目录里 `2，图像处理.py` 只演示了 `rotation_corr(0.5)` 且是注释状态。）
- `green.py` 第 55 行：`img.find_blobs(THRESHOLD_R, roi=(CENTER_X-35, CENTER_Y-35, 70, 70), …)` —— **只在中心 70×70 里找激光点**。目标已经在中心附近时，把搜索域缩到 70×70（=4900 px）而不是全屏 160×120（=19200 px），是白送的 4 倍加速。这个"上一帧命中 → 下一帧缩域，连续 N 帧不中 → 恢复全屏"的模式，本仓库 2023/2025 都没做，只有 `../../07_contest/2023_E_laser/variants/` 里的 A4 过滤思路接近。

### 3. 从 `nuedc_2025_e/激光矩形集中调参/`：见下一节

## ⭐ `激光矩形集中调参.py` 的三个工程做法（建议直接学走）

这份 195 行的代码本身跑不了（`from pyb import UART`），但它的**组织方式**比仓库里任何一份自己的代码都规范：

**(a) 参数全部集中在文件开头一个「调试参数区」，每个参数都写清推荐范围。**
```
RECT_THRESHOLD = 12000     # 矩形检测阈值（越小越灵敏，推荐10000~20000）
RECT_GRADIENT = 10         # 边缘梯度（越小检测越灵敏，推荐8~15）
MAX_HISTORY = 3            # 矩形历史记录帧数（越多跟踪越稳，推荐2~5）
INIT_CONFIRM_THRESH = 3    # 初始识别确认帧数（连续N帧才确认，推荐2~5）
RECT_INIT_DIST = 20        # 初始识别允许的中心距离（像素，推荐15~30）
RECT_TRACK_DIST = 30       # 跟踪阶段允许的中心距离（像素，推荐25~40）
LASER_STABLE_THRESH = 2    # 激光稳定帧数（连续N帧才确认，推荐2~4）
LASER_CIRCULARITY = 0.5    # 圆形度阈值（越小允许形状越不规则，推荐0.5~0.7）
```
对比一下：你自己的 `main_thresh_ui_fast.py` 里 `TARGET_STABILITY_THRESHOLD = 3`、`dist < 50`、`< 30`、`area > 5000`、`< 20000` 这些数字**全部散在代码里、没有一处写推荐范围**。赛场上你要重调，就得全文 grep。

**(b) "初始确认"和"持续跟踪"用两套不同的判据。**
`INIT_CONFIRM_THRESH = 3` + `RECT_INIT_DIST = 20`（收紧，防误认）→ 一旦确认，转成 `RECT_TRACK_DIST = 30` + `MAX_HISTORY = 3`（放宽，跟得上）。你的 2025 流水线只有**一套** `TARGET_STABILITY_THRESHOLD = 3` / `50 px`，从头用到尾 —— 首帧容易误捕、跟快了又容易丢，两个阶段被同一组数字卡住。

**(c) 手写圆形度筛掉非圆斑。**
第 135~136 行：`circularity = 4 * 3.14159 * blob.area() / (perimeter ** 2)`，`if circularity > LASER_CIRCULARITY:`
这是区分"激光点（圆斑）"和"反光条/灯丝（长条）"最省事的判据 —— 只看面积永远分不开。本仓库**没有任何一处**用到圆形度或 `elongation()`，而这恰好是 2023/2025 现场最常见的误检来源。

⚠️ 移植提醒：`perimeter` 那个变量在上述文件里由 blob 属性算出，CanMV 的 `find_blobs` 返回对象**不一定有同名属性**。别照抄表达式，自己确认 CanMV 侧 `blob` 对象暴露了什么（`corners()` / `pixels()` / `w()` / `h()` / `area()` / `density()` / `rotation()`），必要时用 `4π·area / 周长²` 的等价形式自己算周长。

**(d) 顺带一个通信做法值得学**：它用 ASCII 协议 `DATA,<激光x>,<激光y>,<矩形中心x>,<矩形中心y>\r\n`（第 33、180~190 行），**未检出的字段一律填 `-1`**。四个字段永远齐全、换行结尾、肉眼可读、STM32 侧用 `sscanf` 就能解。
对比本仓库那 **10 种互不兼容的帧格式**（绝大多数是二进制，见 [`../../07_contest/README.md`](../../07_contest/README.md)）：调试期用 ASCII，跑起来再换二进制 —— 你会省下大量"到底是视觉没识别到还是串口丢帧了"的扯皮时间。

## 旧名 → 新名

**这些文件以前都在 `07_contest/` 里面**，这是本次搬迁最重要的部分（改名 = `89e6ffc`，搬家 = `28b5f40`）：

| 旧路径（`28b5f40` 之前） | 更早的旧名（`89e6ffc` 之前） | 现在 |
|---|---|---|
| `07_contest/2023_E_laser/sample_code/green.py` | `电赛赛题K230/02_2023_E_Laser/示例代码/green.py` ← `赛题K230/…`（`f2aa2af`） | `other_boards/openmv/2023_laser/green.py` |
| `07_contest/2023_E_laser/sample_code/red.py` | `电赛赛题K230/02_2023_E_Laser/示例代码/red.py` | `other_boards/openmv/2023_laser/red.py` |
| `07_contest/2025_E_self_aiming/methods_reference/NUEDC-2025-E-master/` | `电赛赛题K230/04_2025_E_SelfAiming/方法及参考/NUEDC-2025-E-master/` | `other_boards/openmv/nuedc_2025_e/` |
| `…/NUEDC-2025-E-master/25电赛E题-OpenMV-图像识别示例-程欢欢-V1.py` | 同名保留 | `other_boards/openmv/nuedc_2025_e/25电赛E题-OpenMV-图像识别示例-程欢欢-V1.py` |
| `…/NUEDC-2025-E-master/25电赛E题-OpenMV-图像识别示例-程欢欢-V1.1.py` | 同名保留 | `…/nuedc_2025_e/25电赛E题-OpenMV-图像识别示例-程欢欢-V1.1.py` |
| `…/NUEDC-2025-E-master/激光矩形集中调参/激光矩形集中调参.py` | 同名保留 | `…/nuedc_2025_e/激光矩形集中调参/激光矩形集中调参.py` |
| `…/NUEDC-2025-E-master/LICENSE` | 同名保留 | `…/nuedc_2025_e/LICENSE` |
| `…/NUEDC-2025-E-master/.gitignore` | 同名保留 | `…/nuedc_2025_e/.gitignore` |

`NUEDC-2025-E-master` 这个名字里的 `-master` 是 GitHub 下载 zip 的默认后缀（`仓库名-master/`），**不是"母程序"的意思** —— 与 `../07_contest/2024_E_tic_tac_toe/` 里那个同样被 `-master` 误导过的文件是同一类事故。

**三个 `.py` 文件名一个都没改**，因为它们不是本仓库作者写的：改了文件名，就没法在 B 站评论区/原作者仓库里对上号。**只有目录名从 `NUEDC-2025-E-master` 改成 `nuedc_2025_e`**，因为那是下载产物、无语义。

## 已知问题（实测核对）

1. **`2023_laser/green.py` 第 3、4 行把 `THRESHOLD_R` 连续赋值了两次，同一个值。** 无害（后一次覆盖前一次，值相同），但是"这份代码在别处被改过、忘了删"的痕迹。**别照着这个结构抄多组阈值的写法。**
2. **`green.py` / `red.py` 的帧格式与全仓库其他所有代码都不同。** 它们发 `A1 02 flx dx fly dy 1A`（`flx`/`fly` 是符号位，`dx`/`dy` 是**增量**且只有 1 字节 → 坐标变化超过 255 就溢出），还夹着 `A1 33 1A` / `A1 11 1A` / `A1 44 1A` 三种控制帧。全仓库**没有任何 STM32 工程**解析这一族（`../../other_boards/stm32/` 里那 4 个各解析别的格式）。**移植时只能移植算法，通信部分要整个重做。**
3. **`green.py` 与 `red.py` 是一对**，靠 `A1` 帧互发指令；**只留一个跑不起来**（`red.py` 是主控、`green.py` 是被控）。要参考就两份一起看，别单独拿一份当完整方案。
4. **`nuedc_2025_e/.gitignore` 是 Flash Builder / Eclipse 的规则**（`bin-debug/`、`[Oo]bj/`、`*.air`、`.project` 等），跟 K230 或 MicroPython 一点关系都没有 —— 它是随原作者工程包一起搬进来的。**不要**把它当成本仓库的 `.gitignore` 参考，仓库根那份才是（后者显式排除了 `deploy_config.json`、`det_results/`、`cls_results/`、`Objects/`、`Listings/`、`*.pck`）。
5. ⚠️ **最容易发生在这里的事故：误抄。** `nuedc_2025_e/` 的三份代码解决的就是**你自己那道 2025 E 题**，题面一模一样、还带了成型的阈值和调参区，看起来比 `../07_contest/2025_E_self_aiming/result/` 那三份"更干净"（因为缺陷少的代码本来就容易显得干净 —— 它连"能不能跑"都还没被验证过，因为它根本不在你的平台上）。**它以前就无标注地躺在你的 2025 目录里。** 现在它挪到了 `other_boards/`，路径本身就是提示：**看见 `pyb` 或 `import sensor` 开头，那就不是 K230 的代码。**

## 练习建议

1. **先证明它跑不了，并说清"缺的是哪一层"**
   把 `nuedc_2025_e/25电赛E题-OpenMV-图像识别示例-程欢欢-V1.py` 原样拷到 K230 上点运行。
   **通过标准**：引用报错原文（模块名 + 行号）；然后回答一个判断题并给理由 —— "把 `from pyb import millis` 删掉、`millis()` 换成 `time.ticks_ms()`，这个文件就能在 K230 上跑了吗？"（**不能**。`import sensor` 与后面 `sensor.reset()` / `sensor.set_framesize(sensor.VGA)` / `sensor.set_windowing([200,120,240,240])` 这一整套**全局模块式 API** 在 CanMV 里根本不存在，要换成 `Sensor(id=2)` 对象 + `set_framesize(width=…, height=…, chn=CAM_CHN_ID_0)`。能把这条差异说清楚，才算理解两个平台的架构差别，而不只是记住几个函数名。）

2. **把嵌套 ROI 那招搬到 K230 上，然后量它到底省了多少（必须出数字）**
   任务：在 `../../07_contest/2025_E_self_aiming/result/main_thresh_ui_fast.py` 之外**另存**一份副本，把 `find_best_rect()` 改成 V1 那两遍结构：第一遍 `find_blobs(黑框阈值, merge=False)`，第二遍对每个候选用 `roi=blob.rect()` 再 `find_blobs(白阈值, …)`。
   **通过标准**：交出三行实测 —— ① 原版 FPS 均值（30 次采样）；② 两遍版 FPS 均值；③ 两遍版第一遍的候选 blob 个数均值与第二遍总搜索面积（`Σ roi 的 w*h`）占全屏 400×240 = 96000 px 的百分比。
   **判据**：若准确率提升但 FPS 掉超过 30%，说明你第二遍没被 `roi` 真正限住（最常见原因是 CanMV 里 `blob.rect()` 返回元组，而 `find_blobs(roi=…)` 要的是 `(x, y, w, h)` 顺序 —— 打印出来核对）。这道题的重点是让你习惯"**换算法必须重新测帧率**"，而不是"看起来更准就用它"。

3. **把「调试参数区」这件事做成你自己的规范**
   任务：从 `激光矩形集中调参.py` 的 8 个带推荐范围的参数里挑出对应物，为你 2025 那份 `main_thresh_ui_fast.py` **另存**一个"参数区"版本：把所有散落的魔数（`5000` / `20000` / `50` / `100` / `3` / `30` / `500` / `50000` / `0.5` / `2.5`）收到文件开头，**每个都用注释写上实测出来的推荐范围**。
   **通过标准**：① 原文件与参数区版本的输出必须逐帧一致（同一输入下 `AA…55` 帧字节完全相同，抓 ≥20 帧比对）；② 每个参数的"推荐范围"必须来自**你自己扫出来的边界**，做法是对该参数至少扫 3 个值、各测 ≥20 次、记录"开始失效"的那一档；③ 参数区版本要能在**只改开头那一块**的前提下，把整条流水线从"高帧率优先"调到"高准确优先"（判据：FPS 下降不超过 40% 且误检帧数下降 ≥50%）。
   这道题不产出新算法，但产出的那份"参数 + 实测边界"清单，就是你赛场上一张能用的调参表 —— 比任何"我记得大概是 5000 左右"都可靠。

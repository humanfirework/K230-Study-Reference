# K230 电赛视觉资料库

嘉楠 **K230**（CanMV / MicroPython）机器视觉代码集，为**全国大学生电子设计竞赛**积累而成。
里面既有从零写的赛题方案，也有基础教程、数据采集、AI 模型部署，以及历年电赛真题原文。

| | |
| --- | --- |
| **开发板** | 立创·庐山派 K230-CanMV（`LCKFB-LSPI-K230-1G`，1GB） |
| **固件** | CanMV **v1.3+**（`developer.canaan-creative.com` 已迁至 `kendryte.com`） |
| **读者** | 自己 + 队友 + 学弟学妹。所以每个目录都有 README，每份 README 都写"旧名对照"和练习 |
| **代码语言** | 板子上是 MicroPython；`other_boards/` 里另有 STM32 的 C、OpenMV、MaixPy |

---

## 整体框架：一个赛题视觉系统是怎么拼起来的

这个仓库不是"一堆脚本"，而是按下面这条链组织的。**每个目录对应链上的一环**，
看清这条链，就知道为什么有九个目录、以及自己卡在哪一环。

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  [镜头]  GC2093，代码里一律 sensor_id = 2                        │
   └───────────────────────────┬─────────────────────────────────────┘
                               ↓
   ┌────────────────────────────────────────────────────────┐  ← 01_basics
   │ 采集   Sensor() → reset() → set_framesize() →           │     12 个最小可用示例
   │        set_pixformat(GRAYSCALE / RGB565) → snapshot()   │
   └───────────────────────────┬─────────────────────────────┘
                               ↓
   ┌────────────────────────────────────────────────────────┐  ← 05_cv_lite
   │ 预处理  二值化 binary() · 形态学 open/close/erode/      │     27 个 cv_lite 示例
   │        dilate/tophat/blackhat · 曝光 · 白平衡 · 直方图   │     （零拷贝 ndarray）
   └───────────────────────────┬─────────────────────────────┘
                               ↓
   ┌────────────────────────────────────────────────────────┐  ← 01_basics
   │ 判据   find_blobs(色块) · find_rects(矩形) ·            │     形状/码制/巡线
   │        find_line_segments(线段) · find_circles ·        │     08–12 是码制类
   │        get_regression(巡线) · find_qrcodes · AprilTag   │
   └───────────────────────────┬─────────────────────────────┘
                               ↓
   ┌────────────────────────────────────────────────────────┐  ← 06_practice
   │ 决策   状态机（复位/任务1-3/调参/暂停）· 稳定计数        │     可直接当赛题骨架
   │        连续 N 帧才认 · 面积/长宽比过滤 · 嵌套框判别      │     用，含触摸调参 UI
   │        速度外推 predicted = c + (c - prev) · PID         │
   └───────────────────────────┬─────────────────────────────┘
                               ↓
              ┌────────────────┴────────────────┐
              ↓                                 ↓
   ┌────────────────────────┐      ┌──────────────────────────────┐
   │ 显示/记录               │      │ 输出  UART2 GPIO11=TX         │ ← 02_data_collection
   │ Display ST7701         │      │       GPIO12=RX @115200       │   串口与采图
   │ 800×480 / LT9611 HDMI  │      │       GPIO48 点火             │   + other_boards/stm32
   │ / VIRT(仅 IDE)         │      │  帧：AA|type:B|x:H|y:H|55     │
   └────────────────────────┘      └───────────────┬──────────────┘
                                                   ↓
                                  ┌────────────────────────────────┐ ← other_boards/stm32
                                  │ 对端 STM32F103 解析帧 →        │   系统的另一半，
                                  │ 驱动云台舵机 / 电机 / 激光      │   不是"多余的东西"
                                  └────────────────────────────────┘
```

**另一条支线：AI 模型。** 上面那条链是"手工判据"，遇到形状复杂、光照多变的目标就不够了。
仓库里还有完整的第二条路：

```
采图 02_data_collection/02_capture_burst.py（按键切类别，每类连拍 100 张）
  ↓  产出 04_number_classification/data/dataset/：8 类 × 100 张 = 800 张 480×320 JPEG
训练  嘉楠在线训练平台 / AI Cube —— ⚠️ 仓库里没有训练脚本，这一段完全没有文档
  ↓  产出 *.kmodel + deploy_config.json（平台导出件）
部署 04_number_classification/code/  · 07_contest/2025_E_self_aiming/find_rect/
  ↓
推理 03_ai_demos/（人脸 8 / 手势 6 / 人体 3 / 跟踪 1）—— ⚠️ 全是 v1.2 API
```

> 一句话：**视觉只是 4 天赛制里的一个子系统。** 这条链跑通之后，结构、电源、MCU 联调
> 还要占掉一半天数。别把第三天全花在调一个阈值上。

---

## 九个目录

| 目录 | 是什么 | 什么时候看 |
| --- | --- | --- |
| `01_basics/` | 12 个最小可用示例：开摄像头、绘制、矩形/线段/圆形、颜色追踪、一维码/二维码/Apriltag、巡线 | 第一次摸板子；忘了某个 API 怎么调 |
| `02_data_collection/` | 单拍 / 连拍建数据集 / 串口收发测试 | 要训练自己的模型之前 |
| `03_ai_demos/` | 人脸、人体、手势、目标跟踪的 kmodel 推理示例（18 个） | 做 AI 题；⚠️ 见下方"能不能跑" |
| `04_number_classification/` | 一个**完整**的数字分类工程：800 张数据集 + 训好的 kmodel + 两代固件的部署脚本 | 想走通"数据→模型→上板"整条路 |
| `05_cv_lite/` | 27 个 `cv_lite` 图像处理器示例：二值化、曝光、腐蚀膨胀、开闭、顶帽黑帽、形态学梯度、模糊、直方图、白平衡、find_blobs/circles/edges/rectangles | 手工判据不稳、要做预处理调优时 |
| `06_practice/` | 状态机框架、内外框/三角形/多边形识别、颜色巡线、LVGL 屏、曲线识别 | 开始写自己的赛题程序时，**直接拿 `01_all_in_one.py` 改** |
| `07_contest/` | 2021 / 2023 / 2024 / 2025 四年的赛题代码 + 题目原文 PDF + 厂商参考例程 | 备战具体某一年 |
| `other_boards/` | **跑不了这块板子的代码**：MaixPy、OpenMV、STM32 Keil 工程 | 找对端实现；或想知道某个算法的原型写法 |
| `pc_tools/` | 跑在电脑上的脚本（串口曲线监控） | 调试上位机 |

`NUEDC_TOPIC-master/` —— 1994–2026 全部电赛真题原文（150 个 PDF），已纳入版本控制。

---

## ⚠️ 哪些能直接跑，哪些不能

**照这张表判断，比看文件名靠谱。** 详细原因写在各目录 README 里。

| 路径 | 状态 | 原因 |
| --- | --- | --- |
| `01_basics/` | 🟡 大部分可跑 | 有 3 个文件当前有致命 typo，见 [已知问题](docs/02_known_issues.md) |
| `02_data_collection/` | 🟡 大部分可跑 | 保存路径 `/data/data/images` 依固件而定；`03_uart_test.py` 有 typo 起不来 |
| `05_cv_lite/` | 🟡 需 `cv_lite` | `cv_lite` 由庐山派固件/SD 镜像提供，不在仓库。全仓库 **33 个文件**依赖它 |
| `06_practice/` | 🟡 可跑但有硬伤 | 四个文件的 `struct.pack` 参数个数不对，串口那条路从来没通过 |
| `07_contest/2025_E_self_aiming/result/` | 🔴 未验证 | 三个主程序各有一到三处必崩点；其中一个还依赖缺失的 `cv_lite` |
| `07_contest/2024_E_tic_tac_toe/main_tic_tac_toe.py` | 🔴 **跑不起来** | 用了 `os.exitpoint()` 但全文没 `import os`，第一次进主循环就 NameError |
| `03_ai_demos/` | 🔴 大概率不行 | 18 个文件全是 v1.2 时代 API（`libs.PipeLine`/`libs.AIBase`），v1.3+ 上不保证；且需要 **26 个模型文件**，一个都不在仓库 |
| `07_contest/reference/yahboom_ported/` | 🔴 缺依赖 | 8 个文件要 `ybUtils` 包（亚博固件自带） |
| `06_practice/lvgl/` | 🔴 缺资源 | 要 `/sdcard/examples/15-LVGL/data/` 的字体和图，以及思源黑体 ttf |
| `other_boards/` | ⚫ 不是这块板子 | MaixPy / OpenMV / STM32，按平台区分，别照抄 |

**怎么自查一个文件为什么跑不了**（30 秒）：

```python
# 在 CanMV IDE 里逐条试，第一条报错的就是原因
import cv_lite          # 庐山派固件自带；失败说明固件不对或没烧官方 SD 镜像
import ybUtils          # 亚博固件自带；本仓库没有
from libs.PipeLine import PipeLine     # v1.2 写法；v1.3 改成了 libs.PlatTasks
import os               # 如果某文件用了 os.exitpoint() 却没有这一行，它一定崩
```

---

## 五分钟跑到第一帧画面

1. 从[庐山派快速上手](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/quick-start.html)下载官方固件镜像，
   按页面说明烧录（也支持 Web IDE，Chrome 86+）。
2. 打开 CanMV IDE，连上板子的串口。
3. 新建脚本，粘 `01_basics/01_camera_open.py` 的内容并运行。
   ⚠️ 该文件目前有一处 `Sensor(channe = ...)` 拼错，改成 `Sensor(id=sensor_id)` 才有画面 ——
   这是仓库现状，已记进[已知问题清单](docs/02_known_issues.md)。
4. 看到实时画面即成功。
5. **再做一次关键验证**：按 IDE 的停止按钮，然后不重启板子直接再运行一次。
   如果第二次卡住、必须断电才能恢复，说明这个脚本缺 `os.exitpoint()` 或
   `MediaManager.deinit()` —— 这正是 `05_cv_lite/` 全部 27 个文件的现状。
   这条"停止后能不能直接再跑"是判断一份 CanMV 脚本写得是否规矩的最快方法。

---

## 学习顺序

摘要在这里，完整版（每阶段的时间预算、对应文件、练习和验收标准）在
**[docs/03_learning_roadmap.md](docs/03_learning_roadmap.md)**。

```
阶段 0  环境            2–4h   01_basics/01      → 会烧固件、会看生命周期契约
阶段 1  图像基础        6–10h   01_basics/02–07   → 阈值、色彩空间、形态学
                                  05_cv_lite/          ★ 核心一课：同一物体在三种
                                                       光照下要三组不同阈值
阶段 2  特征与几何     10–16h   01_basics/08–12   → 从像素到"判断"
                                  06_practice/02–06
阶段 3  串口 + 闭环     8–12h   02_data_collection → K230 是控制环里的一个传感器，
                                  06_practice/01,08   不是一台独立相机
                                  other_boards/stm32
阶段 4  AI / kmodel   12–20h   04_number_classification → 数据→训练→部署走通一遍
                                  03_ai_demos（当 API 参考看）
阶段 5  赛题实战      20–40h   07_contest/        → 端到端做完一道题
```

阶段 0–3 约 30 小时，是**最低可用**的备赛量。阶段 4–5 才区分冲奖与否。

**练法比练什么更重要**（理由见学习路线里那一条）：

- 永远要有**实体目标**。仿真器只能建立直觉，传感器噪声和曝光才是真正的课题。
- **一次只改一个变量并记下来**。仓库里有一处 bug 就是因为没人记录哪组阈值是真的。
- **先读 `iterations/` 和 `error/`，再读 `result/`。** 只读最终版学到的是照搬。
- 调试卡住 30 分钟，第一件事是加 `sys.print_exception(e)`，不是改逻辑。
  这份代码里三个崩溃点就是被一个只打印异常文本、不带 traceback 的
  `except BaseException` 藏了一整年。
- **练"重新标定"，而不只是练"识别"。** 赛场上你没时间调算法，有时间调阈值。
  练到三分钟以内。

---

## 官方资源（精选）

全清单带"每条解决什么问题"见 **[docs/04_official_resources.md](docs/04_official_resources.md)**。

| 资源 | 什么时候用它 |
| --- | --- |
| [CanMV-K230 官方文档](https://www.kendryte.com/k230_canmv/zh/main/index.html) | 首选权威来源。⚠️ **左侧有 v1.2–v1.7 版本选择器**，`main` 是开发分支且明说"可能包含尚未在发布版本中提供的功能" —— 你在 v1.3，务必切到对应版本再抄 |
| [image 图像处理 API 手册](https://www.kendryte.com/k230_canmv/en/v1.2/api/openmv/image.html) | 任何函数签名争议以它为准。比如 `find_line_segments([roi[, merge_distance=0[, max_theta_difference=15]]])` —— **roi 就在第一个参数**，本仓库的写法是对的，网上很多帖子说不是 |
| [庐山派快速上手](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/quick-start.html) | 烧固件、装 IDE |
| [庐山派引脚查询](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/pinout-tutorial.html) | ⚠️ 是**交互式查询工具，页面上没有静态引脚表**。所以本仓库不画引脚图，只列代码实际用到的脚并标出处，具体以这个工具为准 |
| [01Studio CanMV K230 wiki](https://wiki.01studio.cc/docs/canmv_k230/) | 讲得比嘉楠参考手册更入门友好；`03_ai_demos/` 的 18 个文件就是抄自这里 |
| [在线模型训练](https://wiki.01studio.cc/docs/canmv_k230/machine_vision/train/) + [AI Cube](https://www.kendryte.com/ai_docs/zh/main/%E4%BD%BF%E7%94%A8AI_Cube%E5%BC%80%E5%8F%91.html) | **补本仓库最大的空白**：有 800 张图和训好的 kmodel，却没有任何一份文档讲模型是怎么训出来的 |

旧域名 `developer.canaan-creative.com` 现在 301 跳到 `kendryte.com`。
仓库里厂商 PDF 和网上老帖子引用的都是旧地址，搜不到就换域名。

---

## 关于"重复文件"和"废弃代码"

**这个仓库里刻意保留了不少看起来该删的东西。删之前请先读对应目录的 README。**

| 保留物 | 为什么 |
| --- | --- |
| `07_contest/*/iterations/`、`variants/` | 一条**单变量实验序列**。8 个文件共享同一骨架、彼此只在一个环节上不同；删掉任何一份就丢掉那个变量的一次对照 |
| `07_contest/*/error/` | 被放弃的**另一条题解路线**，不是残次品。换成圆靶或感光纸介质时，里面的思路仍然值得翻出来 |
| `02_data_collection/05_data_collect.py` | 和 `02_capture_burst.py` 近重复，但分辨率和注释不同，是早期版本 |
| `01_basics/10_find_apriltag_basic.py` + `12_..._full.py` | 两个 AprilTag 示例，差在采集分辨率（320×240 / 800×480），各有用处 |
| `07_contest/laser_drawing/01–06` | 5 个图形程序约 80% 重复，差别在曝光处理、坐标来源、有无 UI |
| `laser_drawing/05_digits_EMPTY.py` | **0 字节**，占位从未实现。留着是为了让教程序列上的这个缺口可见，而不是被悄悄重编号掉 |
| `07_contest/2021_F_drug_car/` | **空目录**。这一题从来没写过 K230 代码。根 README 以前声称有 2021 资料，那是错的 |

两个**名字不能改**的地方，改了会静默失效：
`mp_deployment_source/`（CanMV 部署代码硬编码去 `/sdcard/mp_deployment_source/` 找它）、
`cls_*_1_3.py` / `det_*_1_2_2.py`（嘉楠平台导出件的命名约定，保持原样才能和新导出的包直接 diff）。

---

## 文档索引

| | |
| --- | --- |
| [docs/README.md](docs/README.md) | 文档总入口 |
| [docs/01_getting_started.md](docs/01_getting_started.md) | 固件、IDE、SD 卡目录结构、v1.2 与 v1.3 的差异 |
| [docs/02_known_issues.md](docs/02_known_issues.md) | **按严重度分级的 bug 清单**。只归类不修，每条给文件/行号/成因/建议改法 |
| [docs/03_learning_roadmap.md](docs/03_learning_roadmap.md) | 六阶段、时间预算、每阶段练习与验收标准 |
| [docs/04_official_resources.md](docs/04_official_resources.md) | 官方文档与优秀案例全清单 |
| [docs/05_competition_checklist.md](docs/05_competition_checklist.md) | 可打印一页，出发前 / 到场第一小时 / 比赛中 |
| `*/README.md` | 每个目录一份，含"旧名对照"表和练习建议 |

---

## 目录命名约定

自己写的代码和文档用 ASCII 名（这些文件要拷到 FAT32 SD 卡、用 CanMV IDE 打开，
两者对非 ASCII 路径的支持都不稳；纯 ASCII 也避开 Windows 路径长度问题）。
**文件内容里的中文注释、文档正文一律保留中文。**
文档文件名同样走 ASCII（理由一样：链接和路径在工具链里更稳），
标题用中文写在文件第一行。

以下三类**保持中文原名不动**：官方题目 PDF（`E题_三子棋游戏装置.pdf` 等，标题本身是信息）、
立创/亚博的厂商例程原件（其教程按中文编号引用它们）、`NUEDC_TOPIC-master/` 真题库。

## 许可与来源

本仓库原创代码 MIT。以下内容有各自许可，请连同其 `LICENSE` 一起保留：

- `other_boards/openmv/nuedc_2025_e/` —— OpenMV4 平台的他人赛题方案
- `07_contest/2023_E_laser/yahboom_reference/` —— 亚博 K230 参考包
- `07_contest/reference/{image_recognition,basic_gpio}/` —— 立创·庐山派官方例程
- `NUEDC_TOPIC-master/` —— 第三方整理的电赛真题档案（MIT）
- `*/mp_deployment_source/`、`code/firmware_v*/`、`find_rect/det_*` —— 嘉楠在线训练平台导出件

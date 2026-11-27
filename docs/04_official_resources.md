# 官方资源与优秀案例

> 这份文件是**链接的唯一来源**。其它文档提到官方资料时，只给一句结论，链接到这里。
> 下面每个地址都在 2026-11 整理时访问过；标注「未核实」的除外。

## 0. 该以哪个为准

冲突时的优先级：

**嘉楠官方 API 手册（对应你固件版本的那一版）> 庐山派 / 01Studio 官方教程 > 本仓库的代码 > CSDN / 博客 / 论坛帖子**

本仓库的代码不是"最佳实践样本" —— 它是备赛过程中长出来的东西，带着一批[已知问题](02_known_issues.md)。它是"可参考的实现"，不是"权威的写法"。

---

## 1. 嘉楠官方（CanMV K230）

### [CanMV-K230 文档主页](https://www.kendryte.com/k230_canmv/zh/main/index.html)

侧栏有完整例程索引：外设、多媒体、网络、AI 推理。⚠️ 左侧有 **v1.2 → v1.7** 的版本选择器；你烧的是 v1.3 就切到 v1.3。`main` 是开发分支，页面自己写着"可能包含尚未在发布版本中提供的功能"，别照 `main` 抄。

### 三个最常用的 API 手册（v1.3）

| 手册 | 什么时候用 |
| --- | --- |
| [Sensor 模块](https://www.kendryte.com/k230_canmv/zh/v1.3/api/mpp/K230_CanMV_Sensor%E6%A8%A1%E5%9D%97API%E6%89%8B%E5%86%8C.html) | `Sensor(id, [width, height, fps])` 的构造参数、`set_framesize`、`set_pixformat`、`snapshot` |
| [UART 模块](https://www.kendryte.com/k230_canmv/zh/v1.3/api/machine/K230_CanMV_UART%E6%A8%A1%E5%9D%97API%E6%89%8B%E5%86%8C.html) | 串口编号、引脚、参数；**方法只有 init / read / readline / readinto / write / deinit** |
| [image 图像处理](https://www.kendryte.com/k230_canmv/zh/v1.3/api/openmv/image.html) | `find_blobs` / `find_line_segments` / `get_regression` / `find_rects` / `draw_*` 的权威签名 |

下面几条争论，最终都以 image 手册裁定：

| 争议 | 手册结论 |
| --- | --- |
| `find_line_segments` 的 roi 在前还是在后 | **在前**：`find_line_segments([roi[, merge_distance=0[, max_theta_difference=15]]])`。网上不少帖子说在后，照着"修"会把正确代码改坏 |
| `find_blobs` 的 `margin` 是不是合并开关 | 不是。`margin` 是"色块向外扩多少像素"的整数；**合并是 `merge`** |
| `compressed_for_ide()` 改不改原图 | 返回新的 JPEG 图像对象，**不改原图**（所以丢弃返回值的那几行确实是空操作） |
| `draw_string_advanced` 有没有 `scale` | 手册签名里没有，但庐山派官方例程自己在用 `scale=2` → **冲突未决**，见[澄清](02_known_issues.md#澄清这些不是-bug) |

### [使用 AI Cube 开发](https://www.kendryte.com/ai_docs/zh/main/%E4%BD%BF%E7%94%A8AI_Cube%E5%BC%80%E5%8F%91.html)

嘉楠的模型转换 / 训练工具链文档。本仓库两处 `mp_deployment_source/` 的 `*.kmodel` 就是这条链路的产物。

### `cv_lite` 的文档在哪

[`cv_lite` 手册](https://www.kendryte.com/k230_canmv/zh/v1.5/api/cv_lite/cv_lite.html)（v1.4–v1.7 与 main 都有，**v1.3 文档树里没有**）。页面注明"请烧录 daily_build 固件实现 cv_lite 支持"，示例在 `/sdcard/examples/23-CV_Lite/` —— `05_cv_lite/` 那 27 个文件就是这批例程。

⚠️ 这是**嘉楠官方模块**，不是庐山派专有的扩展。本仓库"v1.3+"的固件前提与它 33 个文件的依赖不匹配，见 [docs/01 §1](01_getting_started.md#1-烧固件) 的依赖表。

---

## 2. 嘉立创 / 立创·庐山派（你手上这块板子）

| 页面 | 用途 |
| --- | --- |
| [快速上手](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/quick-start.html) | 固件下载与烧录，Web IDE（Chrome 86+） |
| [使用摄像头](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/use-sensor.html) | `Sensor(id=2)` 的默认 CSI2 说明；四个完整例程；`sensor.run` 条目的顺序说明 |
| [串口教程](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/uart.html) | UART2 = GPIO11 TX / GPIO12 RX @115200；交叉连接、共地 |
| [引脚查询工具](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/pinout-tutorial.html) | ⚠️ 是**交互式查询页，页面上没有静态引脚表**。本仓库因此不画引脚图，只列代码实际用到的脚并标出处 |
| [K230 与 K230D 的区别](https://openkits-wiki.easyeda.com/zh-hans/lushan-pi-k230/k230vsk230d.html) | 买卡/查资料前确认型号 |

需要查具体电气连接时，看[立创开源广场 · 立创开发板](https://oshwhub.com/li-chuang-kai-fa-ban)（庐山派原理图开源处）。

---

## 3. 其他厂商的同类资料

### [01Studio CanMV K230 wiki](https://wiki.01studio.cc/docs/canmv_k230/)

它的 API 讲解比嘉楠参考手册更入门；示例按"机器视觉 / 图像处理"分类组织。

⚠️ **出处要分清**：本仓库 `03_ai_demos/` 的 18 个文件里，**17 个来自庐山派 wiki 的 AI Demo 页，只有 `05_object_tracking.py` 来自 01Studio**（文件头写着"实验平台：01Studio CanMV K230"）。

### [亚博（Yahboom）K230 学习资料](https://www.yahboom.com/study/K230)

对应本仓库：`07_contest/2023_E_laser/yahboom_reference/`、`sample_code/`，以及 `reference/yahboom_ported/` 的 4 个例程。

⚠️ `ybUtils` 这个包由**亚博固件**自带、不在本仓库。全仓有 **8 个文件**导入它，分布在这 4 个子目录里（不是"8 个都在 `yahboom_ported/`"）。想跑要先补包。

### [嘉楠 K230 自定义数据集模型训练与部署（B 站）](https://m.bilibili.com/video/BV1cRzuYvETq/)

视频走一遍分类/检测的训练 + 部署。外部视频，未逐帧核对。

---

## 4. 本仓库最大的空白：训练这一步

`04_number_classification/` 有 800 张图（8 类 × 100，480×320）和一个训好的 `can2_10.0l_*.kmodel`，但**没有任何一份文档讲模型是怎么从前者变成后者的**。训练是在嘉楠在线训练平台上做的，仓库里只留了导出的产物。

⚠️ 旧版文档说 `deploy_config.json` 里能读到 `model_type: can2`、`nncase_version: 2.9.0` —— **这个文件不在仓库里，磁盘上也没有**，那些字段无法核实。新克隆只有 kmodel，没有配置；8 个部署脚本读它会立刻失败（[P3-2](02_known_issues.md#p3-2)）。

要补这一格，按这个顺序读：

1. [01Studio 在线模型训练](https://wiki.01studio.cc/docs/canmv_k230/machine_vision/train/) —— 平台操作流程
2. [使用 AI Cube 开发](https://www.kendryte.com/ai_docs/zh/main/%E4%BD%BF%E7%94%A8AI_Cube%E5%BC%80%E5%8F%91.html) —— 本地/工具链侧
3. `04_number_classification/docs/README.pdf` —— 平台导出包自带的部署说明（通用说明，不含"数字分类"这件事本身）
4. 那个 30 分钟视频

然后从[阶段 4 练习 4.2](03_learning_roadmap.md)开始：先采一套自己的数据集，再训。

---

## 5. 竞赛本身

`NUEDC_TOPIC-master/`（已随仓库纳入版本控制）：1994–2026 的电赛题目原文，**150 个 PDF = 真题 136 + 综合测评 12 + 参考资料 2**。另有 Multisim/Matlab 模型和两本 TI 手册。离线可用，赛场没网时是唯一的题目原文来源。

⚠️ 这 150 个 PDF 里，真题只有 136 个；该目录**没有 LICENSE 文件**（见 [docs/07](07_maintenance.md#7-许可与出处)）。

---

## 6. 两个必须知道的坑

### 6.1 版本选择器

同一份文档有 v1.2 到 v1.7 多个版本，函数签名会变。`main` 是最新开发分支，不等于你板子上的版本。**抄任何 API 之前先看左上角版本号。**

### 6.2 两份官方说法冲突的两处

| 事项 | 嘉楠 v1.3 | 庐山派 wiki | 本仓库怎么处理 |
| --- | --- | --- | --- |
| `sensor.run()` 与 `MediaManager.init()` 的顺序 | 官方例程：`Display.init → MediaManager.init → sensor.run` | `sensor.run` 条目写"**必须在 `MediaManager.init()` 之前执行**" | 代码跟嘉楠例程；文档两说并列，**待上板对照**（[docs/01 §3](01_getting_started.md#3-看到第一帧画面)） |
| `find_line_segments` 第三个形参名 | 手册：`max_theta_difference` | 图像识别栏目的特征检测例程：`max_theta_diff` | 不猜关键字，建议改位置传参；见 [P2-12](02_known_issues.md#p2-12) |

---

## 7. 查阅时的一条建议

网上关于 K230 视觉的中文帖子质量参差，而且**相当一部分在讲 OpenMV 或 MaixPy 的 API**（`pyb`、`maix` 这两个 import 是识别标志）。本仓库历史上就因此混进过 OpenMV 和 MaixPy 的代码，还因此写错过注释。

**抄之前先确认那份代码跑在哪块板子上。** 这也是本仓库把 `other_boards/` 单独隔出来的原因。

# 官方资源与优秀案例

> 这里只收**实际访问验证过**的地址，每条写清"讲什么"和"对应本仓库哪一块"。
> 不堆链接。全清单之外还值得知道的，归在最后。

## 该以哪个为准

冲突时的优先级：

```
嘉楠官方 API 手册（对应你固件版本的那一版）
   >  庐山派 / 01Studio 官方教程
   >  本仓库的代码
   >  CSDN / 博客 / 论坛帖子
```

本仓库的代码**不是最佳实践样本** —— 它是备赛过程中长出来的东西，带着一批
[已知问题](02_known_issues.md)。它是"可参考的实现"，不是"权威的写法"。

---

## 一、嘉楠官方（CanMV K230）

### [CanMV-K230 快速入门指南](https://www.kendryte.com/k230_canmv/zh/main/index.html)

官方文档主页。侧栏有完整例程索引：外设控制、多媒体处理、网络、AI 推理
（含颜色追踪、YOLOv8 目标检测、云端模型部署）。

⚠️ **两个必须知道的坑**：

1. **左侧有版本选择器，覆盖 v1.2 一直到 v1.7。** 你烧的是 v1.3，
   那就该看 v1.3 那一版。
2. `zh/main` 这个地址本身写着「这是最新开发分支的文档，可能包含尚未在发布版本中提供的功能」。
   **别照 `main` 抄**，先切到你对应的版本。

对应本仓库：这是所有 API 问题的第一出处；`03_ai_demos/`（v1.2 API）和
`04_number_classification/code/firmware_v1_3/`（v1.3 API）的差别，也要靠版本选择器来对照看。

### [image 图像处理 API 手册](https://www.kendryte.com/k230_canmv/en/v1.2/api/openmv/image.html)

`find_blobs` / `find_line_segments` / `get_regression` / `find_rects` /
`draw_string_advanced` 这些函数的**权威签名**。

本仓库有几处争论最终以它裁定了，值得记住：

| 争议 | 手册结论 |
| --- | --- |
| `find_line_segments` 的 roi 在前还是在后 | **在前**：`find_line_segments([roi[, merge_distance=0[, max_theta_difference=15]]])`。网上不少帖子说在后，照着"修"会把正确代码改坏 |
| `find_blobs` 的 `margin` 是不是合并开关 | 不是。`margin` 是"色块向外扩多少像素"的整数；**合并是 `merge`** |
| `compressed_for_ide()` 改不改原图 | 返回新的 JPEG 图像对象，**不改原图**（所以丢弃返回值的那几行确实是空操作） |
| `draw_string_advanced` 有没有 `scale` | 手册签名里没有，但庐山派官方例程自己在用 `scale=2` → 冲突未决，见[已知问题](02_known_issues.md)澄清一节 |

### [使用 AI Cube 开发](https://www.kendryte.com/ai_docs/zh/main/%E4%BD%BF%E7%94%A8AI_Cube%E5%BC%80%E5%8F%91.html)

嘉楠的模型转换/训练工具链文档。

对应本仓库：`04_number_classification/mp_deployment_source/` 和
`07_contest/2025_E_self_aiming/find_rect/mp_deployment_source/` 那两套
`*.kmodel + deploy_config.json` 就是这条链路的产物。

### ⚠️ 旧域名已迁移

`developer.canaan-creative.com` 现在 **301 跳到 `www.kendryte.com`**。
仓库里厂商自带 PDF、以及网上大量 2024–2025 年的帖子引用的都是旧地址。
搜不到东西就换域名，不要以为文档下线了。

---

## 二、嘉立创 / 立创·庐山派官方（你手上这块板子）

### [庐山派 K230 / Lite-K230D CanMV 快速上手](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/quick-start.html)

固件下载与烧录。也支持 Web IDE（Chrome 86+）。
**这块板子的固件是该从这里拿** —— `cv_lite` 等扩展模块随官方固件/SD 镜像提供，
不在本仓库里（全仓库 33 个文件依赖它）。

### [引脚查询工具](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/pinout-tutorial.html)

⚠️ **这是一个交互式查询页面，页面上没有静态引脚表**（我确认过：它只是查询工具的入口说明，
并提示"红色感叹号表示该引脚被板载硬件占用（如 LED、蜂鸣器）"，并说明 UART2 用户可用）。

**所以本仓库刻意不画引脚图，也不抄一份静态表。** 一张 GPIO 标错但看起来很权威的图
比没有图更糟 —— 它会被相信，然后有人把激光接到 LED 脚上。

本仓库各 README 里的引脚信息一律：
- 只写**代码里实际用到的**，并给出出处文件（例如 GPIO48 点火，见
  `07_contest/2025_E_self_aiming/result/` 三个主程序的 `Pin(48, ...)`）
- 明确标注"完整/电气定义以这个官方查询工具为准"

需要查具体电气连接时，看[立创开源广场 · 立创开发板](https://oshwhub.com/li-chuang-kai-fa-ban)
（庐山派硬件原理图开源处）。

### [串口教程](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/uart.html)

对应本仓库：`02_data_collection/03_uart_test.py`，以及[已知问题 P3-1](02_known_issues.md)
里那个"仓库内有 4 套互不兼容帧格式、且没有任何重同步"的问题。

### [K230 与 K230D 的区别](https://openkits-wiki.easyeda.com/zh-hans/lushan-pi-k230/k230vsk230d.html)

两款板子共享同一颗 K230/K230D SoC，但外设和内存配置有差别。
买卡/查资料前先确认自己是哪一款。

---

## 三、其他厂商的同类资料（值得参考的优秀案例）

### [01Studio CanMV K230 wiki](https://wiki.01studio.cc/docs/canmv_k230/)

**本仓库 `03_ai_demos/` 那 18 个文件就是抄自这套教程** ——
`05_object_tracking.py` 的文件头至今写着「实验平台：01Studio CanMV K230 / 教程：wiki.01studio.cc」。

它的 API 讲解比嘉楠参考手册更适合入门，示例按"机器视觉 / 图像处理"分类组织。
需要某个具体检测函数的通俗解释时，先查它。

### [亚博（Yahboom）K230 学习资料](https://www.yahboom.com/study/K230)

对应本仓库：`07_contest/2023_E_laser/yahboom_reference/` 那一包，
以及 `07_contest/reference/yahboom_ported/` 的 4 个例程。

⚠️ 这也是 `ybUtils` 这个包的来源 —— 它由亚博固件自带、**不在本仓库**，
所以那 8 个文件现在直接 import 就失败。想跑要先补包。

### [嘉楠 K230 自定义数据集模型训练与部署：30 分钟实操（B站）](https://m.bilibili.com/video/BV1cRzuYvETq/)

视频版走一遍分类/检测的训练 + 部署。**配合上面两篇文档看比只看文档快。**

---

## 四、本仓库最大的空白，正好由上面这些补

`04_number_classification/` 有 800 张图（8 类 × 100，480×320）和一个训好的
`can2_10.0l_*.kmodel`，但**没有任何一份文档讲模型是怎么从前者变成后者的** ——
训练是在嘉楠在线训练平台上做的，仓库里只留了导出的产物（`deploy_config.json` 里
`model_type: can2`、`nncase_version: 2.9.0` 就是那个平台的签名）。

要补这一格，按这个顺序读：

1. [01Studio 在线模型训练](https://wiki.01studio.cc/docs/canmv_k230/machine_vision/train/) —— 平台操作流程
2. [使用 AI Cube 开发](https://www.kendryte.com/ai_docs/zh/main/%E4%BD%BF%E7%94%A8AI_Cube%E5%BC%80%E5%8F%91.html) —— 本地/工具链侧
3. `04_number_classification/docs/README.pdf` —— 嘉楠导出包自带的 2 页部署说明
   （注意它是**通用**说明，不含数字分类这件事本身）
4. 那个 30 分钟视频

然后自己从[阶段 4 练习 4.2](03_learning_roadmap.md)开始：先采一套自己的数据集，再训。

---

## 五、竞赛本身

### `NUEDC_TOPIC-master/`（已随本仓库纳入版本控制）

1994–2026 全部电赛真题原文，150 个 PDF，另有综合测评的 Multisim/Matlab 模型和两本 TI 手册。
离线可用，赛场没网时是唯一的题目原文来源。

---

## 六、查阅时的一条建议

网上关于 K230 视觉的中文帖子质量参差，而且**相当一部分是在讲 OpenMV 或 MaixPy 的 API**
（`pyb`、`maix` 这两个 import 是识别标志）。本仓库历史上就因此混进过
OpenMV 和 MaixPy 的代码，还因此写错过注释（`06_practice/06_curve_recognition_WIP.py`
里有一行注释在 CanMV 文件上写着"使用正确的 MaixPy API"）。

**抄之前先确认那份代码跑在哪块板子上。**这也是本仓库把 `other_boards/` 单独隔出来的原因。

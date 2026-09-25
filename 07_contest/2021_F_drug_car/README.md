# 2021_F_drug_car — 2021 年 F 题「智能送药小车」

## 这个目录里有什么

**什么都没有。** 本目录当前是一个空目录，`.py` / `.pdf` / 图片一个都没有，唯一的文件就是这份 README。

这不是搬家时丢的。实测：

- `git log --all -- 电赛赛题K230/01_2021_F_DrugCar 07_contest/2021_F_drug_car` 只返回一个分支上的提交（`78cdb53`，`wip/restructure-2026-09-24`），**main 分支上这两个路径从未被 git 跟踪过**。原因很简单：git 不跟踪空目录。
- `git ls-tree 89e6ffc^:电赛赛题K230` 的输出是 `00_Reference`、`02_2023_E_Laser`、`03_2024_E_ThreePieceChess`、`04_2025_E_SelfAiming`、`README.md`、`绘制图像` —— **没有 `01_2021_F_DrugCar`**。它在磁盘上是个空壳，所以改名提交里没有它的重命名记录。
- 改名提交 `89e6ffc` 的说明文字里明确写了：「`01_2021_F_DrugCar` is empty - no code, no topic PDF - which the root README nonetheless claims holds 2021 material.」旧名 `01_2021_F_DrugCar` 就是从这里来的（commit message 记录，不是 rename 记录）。

也就是说，2021 F 题**从来没做过**。这个目录是个待办占位，不是归档。它的价值是提醒你和队友：别在 README 里写「本仓库整理了 2021 年资料」。

## 题目 PDF 在哪

题目正文不在本目录，在题库里（仓库根相对路径）：

- `NUEDC_TOPIC-master/真题/2021/F_智能送药小车.pdf` ← 题面
- `NUEDC_TOPIC-master/真题/2021/F_智能送药小车数字字模.pdf` ← 题目要求识别的**数字字模**（要打印出来对着练）

从本目录出发是 `../../NUEDC_TOPIC-master/真题/2021/`。2021 年其余 11 道题（A~K）也在同一目录。

## 代码文件表

| 文件 | 作用 | 状态 |
|---|---|---|
| `README.md` | 本说明 | 可用 |

没有代码可列。

## 旧名 → 新名

| 旧路径 | 新路径 | 出处 |
|---|---|---|
| `赛题K230/01_2021_F_DrugCar/`（磁盘上，未被 git 跟踪） | `电赛赛题K230/01_2021_F_DrugCar/` | `5b4dd92` 改了仓库根目录名 |
| `电赛赛题K230/01_2021_F_DrugCar/` | `07_contest/2021_F_drug_car/` | 名称见 `89e6ffc` 提交说明；因目录为空，`git show --name-status -M 89e6ffc` 里**查不到这一行** |

`89e6ffc` 与 `28b5f40` 两次改名提交中，与本目录相关的**唯一**记录就是提交说明里那句「它是空的」。**不要**在别的文档里编造本目录的旧文件名——它历史上就没有文件。

## 如果要把这道题做出来（练习建议）

2021 F 题的视觉部分是「识别轨道旁的数字字模 + 找巡线」，正好能复用自己仓库里现成的三块积木，所以是个不错的补全目标。

1. **字模识别：先量准确率，别只看"认出来了"**
   用 `NUEDC_TOPIC-master/真题/2021/F_智能送药小车数字字模.pdf` 打印 0~9 各一张，贴在墙上，用手机屏当参照物。
   从 `reference/image_recognition/10，字符识别（OCR）.py` 起步（注意它要 `/sdcard/examples/kmodel/ocr_det_int16.kmodel`、`ocr_rec_int16.kmodel`、`/sdcard/examples/utils/dict.txt`，仓库里没有，得从庐山派固件包取），或者退一步用 `04_number_classification/` 里那个已训练的 `.kmodel`。
   **通过标准**：距离 1.5 m，每个数字连续测 20 次，**识别正确 ≥ 18 次（90%）**，并把每次的耗时写下来。达不到就把分辨率/阈值改成三组对照，记录哪组最好。低于 90% 不许进下一步。

2. **巡线：量化转向延迟**
   复用 `06_practice/08_color_line_following.py` 或 `reference/yahboom_ported/4.K230 颜色巡线.py` 的思路（后者需要仓库外的 `ybUtils`）。
   **通过标准**：直线段跑满 2 m 不出线，且屏幕左上角打印的 FPS 稳定 ≥ 15；记录「进弯 → 首次反向打舵」的帧数，≤ 3 帧算通过。

3. **UART 发帧：先定协议再动手**
   ⚠️ 见 [`../README.md`](../README.md) 的协议表：仓库里 9 种帧格式互不兼容，**不要**随手抄一段就发。为这道题单独写一份帧定义（帧头、字段、字节序、有没有校验和），Python 和 STM32 两边都按它实现。
   **通过标准**：连续发 1000 帧，STM32 侧收到的帧数 = 1000，且每帧字段解析值与发送值逐一相等（用 `print(frame.hex().upper())` 和 C 侧的 `printf` 对拍）。少一帧就算不通过，并去查是不是掉进了 `../../other_boards/stm32/snippets/uart_rx_tx.c` 的环形缓冲区 bug（见 [`other_boards/stm32/README.md`](../../other_boards/stm32/README.md)）。

## 已知问题

- **本目录为空，却曾长期在 README 里被描述成"有 2021 年整理资料"。** 这条虚假陈述已在 `07_contest/README.md` 的更正表里记入，若再看到同类说法请回来更新这里。
- 保留空目录是有意的：它让「2021 没做」这件事可见，而不是被悄悄删掉、变成"仓库里没有 2021"这种更容易误读成"2021 做过但资料丢了"的状态。

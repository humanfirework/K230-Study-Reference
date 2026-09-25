# 文档索引

入口在仓库根 [README.md](../README.md)（那里有整体框架图和"哪些能直接跑"对照表）。
这里是从那里进的具体文档。

## 我该看哪一篇

| 你的情况 | 看这个 |
| --- | --- |
| 刚拿到板子，连不上 / 没画面 | [01_getting_started.md](01_getting_started.md) |
| 不知道按什么顺序学、要学多久 | [03_learning_roadmap.md](03_learning_roadmap.md) |
| 程序跑不起来 / 静默退出 / 要断电重启 | [02_known_issues.md](02_known_issues.md) |
| 忘了某个函数怎么调、参数顺序是什么 | [04_official_resources.md](04_official_resources.md) → 官方 API 手册 |
| 想知道模型的 `deploy_config.json` 是哪来的 | [04_official_resources.md](04_official_resources.md) 第四节 |
| 要比赛了 | [05_competition_checklist.md](05_competition_checklist.md) |
| 想知道某段代码是不是这个板子的 | `other_boards/README.md` |

## 各目录自己的 README

写清了每个文件做什么、**旧中文名 → 新英文名对照表**、练习建议和本目录特有的坑。

| | |
| --- | --- |
| [01_basics](../01_basics/README.md) | 12 个最小可用示例：摄像头、绘制、矩形/线段/圆形、颜色、码制、巡线 |
| [02_data_collection](../02_data_collection/README.md) | 采图建数据集、串口测试 |
| [03_ai_demos](../03_ai_demos/README.md) | 人脸/人体/手势/跟踪 ⚠️ v1.2 API + 缺 26 个模型文件 |
| [04_number_classification](../04_number_classification/README.md) | 数字分类完整部署工程：800 张图 + kmodel + 两代固件脚本 |
| [05_cv_lite](../05_cv_lite/README.md) | 27 个图像处理器示例 ⚠️ 依赖固件自带的 `cv_lite` |
| [06_practice](../06_practice/README.md) | 状态机框架、形状识别、颜色巡线、LVGL |
| [07_contest](../07_contest/README.md) | 2021 / 2023 / 2024 / 2025 赛题 |
| [other_boards](../other_boards/README.md) | **不是这块板子的代码**：MaixPy / OpenMV / STM32 |
| [pc_tools](../pc_tools/README.md) | 跑在电脑上的脚本 |

`NUEDC_TOPIC-master/` —— 1994–2026 电赛真题原文（150 个 PDF，已纳入版本控制）。

## 三条贯穿全部文档的结论

如果只记三件事，记这三条：

1. **阈值是环境量，不是配置量。** 靶纸、光照、距离任何一项变了就得重标，
   而且标好的值**重启就没了**（只在内存里，不落盘）。所以调参 UI 必须好用 ——
   而它目前恰好有个会静默覆盖你标定结果的 bug
   （[已知问题 P1-2](02_known_issues.md)）。

2. **`os.exitpoint()` + `try/finally` + `MediaManager.deinit()` 是 CanMV 的生存契约。**
   缺它的直接后果是"每次中断都要给板子断电重启"，这在 4 天赛制里是实打实的时间损失。
   `05_cv_lite/` 全部 27 个文件现在都缺。

3. **抄代码之前先确认它跑在哪块板子上。** 本仓库历史上混进过 OpenMV（`from pyb`）
   和 MaixPy（`from maix`）的代码，和 K230 主程序并排摆放、毫无标记 ——
   那是最容易误抄的东西。现在它们被隔离进 `other_boards/`，
   但网上帖子仍然混着三家生态写。

## 关于这份文档本身

- 所有代码目前**保持原样，未做任何修复**。问题只归类、不修改 ——
  这是有意的决定，因为改行为的东西必须上板验证，而没有板子时"看起来对"的修复本身也是风险。
  要动手就按 [02_known_issues.md](02_known_issues.md) 末尾的建议顺序，逐条改、逐条验证。
- 文档里的行号基于当前 HEAD。改过代码之后请重新定位。
- 所有外链都在 [04_official_resources.md](04_official_resources.md) 里说明过"讲什么、对应哪一块"，
  且都实际访问验证过。嘉楠旧域名 `developer.canaan-creative.com` 已 301 迁到 `kendryte.com`。

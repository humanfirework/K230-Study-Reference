K230 电赛视觉资料库 · 2026-11

CanMV / MicroPython 机器视觉代码集，为全国大学生电子设计竞赛整理。
A K230 (CanMV/MicroPython) vision library for NUEDC, built on the LCKFB Lushan Pi board.

## 先看这里

| 你的情况 | 从这里开始 |
| --- | --- |
| 第一次摸板子 | `docs/01_getting_started.md` + `01_basics/01_camera_open.py` |
| 不知道按什么顺序学 | `docs/03_learning_roadmap.md`（阶段 0–3 约 26–42 小时） |
| 要比赛了 | `docs/05_competition_checklist.md`（本页附可打印 PDF） |
| 找某一年的题 | `07_contest/<年份>/README.md`；题面在 `NUEDC_TOPIC-master/真题/` |
| 程序跑不起来 | `docs/02_known_issues.md`（按症状查，每条标了证据等级） |

## 这一版做了什么

- 根 README 重画系统架构图；各目录 README 统一成“这里有什么 / 能不能跑 / 练习 / 相关”。
- 16 张流程图改为 **PNG**（源在 `docs/assets/diagrams/src/`）。任何阅读器都能看，不再依赖 Mermaid 渲染。
- 缺陷清单重构：每条标“已上板验证 / 读代码核实 / 待上板确认”；当前没有一条已上板验证。
- 新增 `docs/06_uart_protocol.md`：10 族帧布局、STM32 解析流程、一份可用的重同步实现。
- 新增 `docs/07_maintenance.md`：命名、保留物、旧名总表、许可与出处。
- 代码只改两处 `Sensor` 关键字拼写（有官方手册依据）；其余缺陷只记录、不修改。
- 修掉一批会说错的事实：`cv_lite` 归属、`03_ai_demos` 出处、2021 空目录、`magnitude()` 方向等。

## 重要提醒

- 这是教学 / 参考资料，不是“拿去就能拿奖”的成品；厂商例程与平台导出件保持原样。
- **没有一条运行结论经过上板验证**；请按 `docs/02` 的证据等级使用。
- 两处官方文档互相冲突（`sensor.run()` 顺序、`find_line_segments` 形参名），已在 `docs/04` 并列记录。
- 题库与厂商代码各有许可，见 `docs/07`；题目版权归命题方，仅作备赛查阅。

## 附件

| 文件 | 是什么 |
| --- | --- |
| `nuedc_papers_1994-2026.zip` | 1994–2026 全部真题 PDF（136 份，42 MB） |
| `nuedc_paper_index.md` | 年份 / 文件名索引，先查再下 |
| `checklist_A4.pdf` | 赛前检查清单的可打印版（2 页，双面打印带走） |
| `2025_E_self_aiming.zip` | 2025 E 题工程（`result/` + `find_rect/` + 题面 + README） |

> 源码 zip 用 GitHub 页面上的 “Source code (zip)” 即可；旧 release `25-code` 停在 2026-01 的初始提交，不要用它。

对应 tag：`v2026.11`。附件由 GitHub Actions 在打 tag 时从仓库内生成（见 `publish/`）。

# 文档索引

仓库根 [README.md](../README.md) 是入口：系统架构图、目录表、"能不能跑"状态表都在那里。这里是从那里进来的具体文档。

| 你的情况 | 看这个 |
| --- | --- |
| 刚拿到板子；连不上、没画面 | [01_getting_started.md](01_getting_started.md) |
| 不知道按什么顺序学、要学多久 | [03_learning_roadmap.md](03_learning_roadmap.md) |
| 程序跑不起来、静默退出、每次都要断电 | [02_known_issues.md](02_known_issues.md)（按"症状"查） |
| 忘了某个函数怎么调、参数顺序是什么 | [04_official_resources.md](04_official_resources.md) → 官方 API 手册 |
| 要定 K230 和对端 MCU 的串口协议 | [06_uart_protocol.md](06_uart_protocol.md) |
| 要比赛了 | [05_competition_checklist.md](05_competition_checklist.md) |
| 想知道某段代码是不是这块板子的 | [`../other_boards/README.md`](../other_boards/README.md) |
| 要改这个仓库（命名、旧名、保留物、出处） | [07_maintenance.md](07_maintenance.md) |

## 关于这些文档

- **代码除 [P0-3](02_known_issues.md#p0-3) 的两处拼写外，保持原样。** 其余缺陷只记录、不修改。
- **运行状态只有三档**：已上板验证 / 读代码核实 / 待上板确认。当前**没有一条**已上板验证 —— 所有"跑不起来"的结论都是读代码推断的，不是实测。
- **每个事实只写一处。** 目录 README 只写"这里有什么、能不能跑、练什么"，细节链到 `docs/`。

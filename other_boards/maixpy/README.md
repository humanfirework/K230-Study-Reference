# maixpy —— MaixCAM 上的离线阈值调节器（不是 K230 代码）

一份 124 行的触摸屏调参工具，跑在 Sipeed MaixPy（MaixCAM）上。单独隔出来，是因为它的 `from maix import …` 与 CanMV 是两套 API；留在这里的价值是 API 对照和交互设计，不是"拿过来就能跑"。

## 这里有什么

| 名字 | 平台 | 是什么 | 状态 |
| --- | --- | --- | --- |
| `offline_threshold_tuner.py` | MaixCAM（Sipeed MaixPy） | 124 行离线 LAB 阈值调节器：按键切换六个分量，`+`/`-` 改值，`Change` 进验证页，`app.need_exit()` 退出 | 平台不符；读代码核实 |

### API 对照（MaixPy → CanMV）

只列这份文件实际用到的四个模块：

| 用途 | 本文件的写法 | CanMV K230 对应 |
| --- | --- | --- |
| 图像处理 | `maix.image` | `image` |
| 显示 | `maix.display` | `Display` |
| 摄像头 | `maix.camera` | `Sensor` |
| 触摸 | `maix.touchscreen` | `TOUCH` |

K230 上的等价物已经存在：`06_practice/01_all_in_one.py:128` 的 `handle_threshold_adjustment()`，做的是同一件事（触摸、左右分屏、滑块、保存），只是 API 换成了 CanMV 那套。两份的交互不同：这份用"按钮命中区 + 分量索引"，K230 那份用滑块映射。小屏（320×240）上按钮式更容易按准，值得对照。

读这份代码时，按钮表在 `:10-21`，初始阈值在 `:24`，`Change` 的分支在 `:51` 和 `:112`。

## 能不能跑

不能。第一行 `from maix import touchscreen, display, image, app, time, camera` 在 CanMV K230 上就失败（读代码核实）。**不要改 import 让它"跑起来"**——改了也不是这份代码的原意，直接用上面那份 K230 实现。

已知问题：`current_threshold_index` 未初始化（[P2-17](../../docs/02_known_issues.md#p2-17)）；`thresholds1` 是从未被读过的复制；`flag` 只有 0/1 两条路，进了验证页只能靠 IDE 停止退出。后两条为读代码核实。

## 练习

把这份的交互和 `06_practice/01_all_in_one.py` 的调参界面对照，列出 MaixPy 有而 CanMV 没有的调用点。

建议验收：在 K230 上用 `TOUCH(0)` 复刻一个"三分量选择 + 保存"的最小版本；上电后先按 `+`/`-` 不报错，且保存的值与屏幕显示一致（待上板确认）。

## 相关

- K230 实现：[`06_practice/01_all_in_one.py`](../../06_practice/01_all_in_one.py)
- 缺陷：[P2-17](../../docs/02_known_issues.md#p2-17)
- 平台划分：[`other_boards/README.md`](../README.md)
- 官方入口：[docs/04](../../docs/04_official_resources.md)

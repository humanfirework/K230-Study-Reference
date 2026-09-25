# maixpy — Sipeed MaixPy（MaixCAM）代码

## 这里放什么

**判定标准只有一条**：文件里出现 `from maix import …`。

MaixPy 是 Sipeed 为 MaixCAM / Maix系列做的 Python 运行时，API 与 CanMV（乐鑫式 `machine` + `media.sensor`）**完全是两套**。在 CanMV K230 上，这个 import 就是**第一条报错**：`ImportError` / `ModuleNotFoundError: No module named 'maix'` —— 程序连一行你的逻辑都没执行到。

本目录只有 1 个文件。

## 文件清单

| 文件 | 行数 | 大小 | 作用 | 状态 |
|---|---:|---:|---|---|
| `offline_threshold_tuner.py` | 124 | 4,309 B | MaixCAM 上的**脱机触摸屏 LAB 阈值调节器**：`touchscreen.TouchScreen()` + `display.Display()` + `camera.Camera(552, 368)`，屏幕上画 9 个按钮（`EXIT` / `-` / `+` / `Lmin` / `Lmax` / `Amin` / `Amax` / `Bmin` / `Bmax` / `Change`），按 `-`/`+` 改当前选中的那个阈值分量，按 `Change` 从"调参页"切到"验证页"（`img.find_blobs([Threshold], pixels_threshold=500)` 把色块框出来）。第 1 行有作者标记 `#ltxdysl` | 需要缺失依赖（`maix`），在 CanMV 上不可运行 |

## 它的 K230 等价物**已经存在**

不要在 K230 上重写这个功能 —— 你已经有了两份：

| 位置 | 说明 |
|---|---|
| `../../06_practice/01_all_in_one.py` 第 128 行 `handle_threshold_adjustment()` | **同一件事的 CanMV 实现**：`TOUCH(0)` 读触摸、左右分屏（左半实时二值化画面 / 右半按钮+滑块）、按 `-`/`+` 分量调、保存回全局阈值 |
| `../07_contest/2025_E_self_aiming/result/main_thresh_ui_fast.py` 第 74 行 | 上面那个函数在你 2025 赛题里的落地版本（**但它有"进界面会篡改阈值"的严重缺陷，见该目录 README 的 C/D 条**） |
| `../07_contest/reference/image_recognition/离线调整阈值.py` | 更早的 LCKFB 例程母本，333 行 |

MaixPy 这份**保留价值**在于：它是三种不同触摸调参 UI 思路里唯一"按钮命中区 + 分量索引"式的设计（另外两份用滑块映射 0~255），当你在 K230 上做小屏幕（比如 320×240）时，按钮式比滑块式更值得抄。

## API 对照（MaixPy → CanMV）

要移植时，缺的就是下面这三样，别的一个一个试：

| 这件事 | MaixPy（本文件里的写法） | CanMV K230 对应 |
|---|---|---|
| 取一帧 | `img = cam.read()`（`camera.Camera(552, 368)`） | `sensor = Sensor(id=2)` → `sensor.reset()` → `set_framesize(width=…, height=…)` → `set_pixformat(...)` → `sensor.run()` → `img = sensor.snapshot(chn=CAM_CHN_ID_0)` |
| 出图 | `disp.show(img)`（`display.Display()`） | `Display.init(Display.ST7701, width=800, height=480, to_ide=True)` → `Display.show_image(img)`（+ 收尾 `Display.deinit()` / `MediaManager.deinit()`） |
| 读触摸 | `x, y, pressed = ts.read()`（`touchscreen.TouchScreen()`） | `tp = TOUCH(0)` → `points = tp.read()` → 判 `len(points) > 0`，取 `points[0].x` / `.y` |
| 退出条件 | `while not app.need_exit():` | `while True: os.exitpoint()`（⚠️ 必须 `import os`，见 `../07_contest/2024_E_tic_tac_toe/README.md` 的缺陷 1） |
| 睡眠 | `time.sleep_ms(50)` | 同名可用（`from maix import time` vs `import time`） |
| 二值化 / 找块 | `img.binary([thresholds])`、`img.find_blobs([T], pixels_threshold=500)` | **名字一致**，但 CanMV 要显式 `to_grayscale()` 且阈值列表格式与颜色空间需对齐 |

画图的 `draw_rect` / `draw_string` 两边签名接近，但 CanMV 里带中文/放大字号一般用 `img.draw_string_advanced(x, y, height, text, color=…)`。

## 旧名 → 新名

| 旧路径 | 中间路径 | 现在 |
|---|---|---|
| `平时练习/9,脱机调阈值.py`（`f2aa2af` 初始提交） | `06_practice/09_offline_threshold_WIP.py`（`f2d0a64` 改目录名 + 英文化） | **`other_boards/maixpy/offline_threshold_tuner.py`**（`28b5f40` 移出） |

关于中间那个名字：`_WIP`（work in progress）当时被加上去，是因为它在 K230 上跑不起来、看起来像半成品。**这个判断是错的** —— 它对 MaixCAM 是完整可跑的，跑不起来纯粹是平台不对。`28b5f40` 把它改名成 `offline_threshold_tuner.py`，语义变成"离线阈值调参器"（描述它做什么），而不是"未完成"（描述它对你不值）。

`../07_contest/` 与 `../../06_practice/` 里**不再有任何一份 MaixPy 代码**：这份是当时唯一一个混在那两个目录体系里的（它挂在 `06_practice/` 名下，看起来就是普通练习文件）。

## 已知问题（实测核对）

1. **`current_threshold_index` 在使用之前从未赋值。**
   第 30 行 `global current_threshold_index`，但全文**没有任何模块级初始化**（`grep current_threshold_index` 的 12 处结果里，赋值只发生在 `button_clicked()` 的 `Lmin…Bmax` 分支，第 36~46 行）。
   而第 49 行 `if current_threshold_index is not None:`、第 59 行、第 62~63 行**直接读它**。
   后果：上电后**第一个按下的按钮如果是 `+` 或 `-`**（没先点 `Lmin` 之类选分量），第 49 行就 `NameError: name 'current_threshold_index' is not defined`。
   作者显然**本想**写 `current_threshold_index = None`（因为下面三处都在防 `None`），只是漏了这一行。
   修法（不代为修改）：在文件顶部 `thresholds = [...]` 旁边补 `current_threshold_index = None`。

2. **`thresholds1` 是一个从未被读过的复制。** 第 78 行 `thresholds1 = [thresholds[0], …, thresholds[5]]` —— 逐元素抄了一遍 `thresholds`，此后全文再没出现过 `thresholds1`（`grep -c` 只有这一处）。
   从上下文（紧跟着 `img.binary([thresholds])` 与那段整体注释掉的"显示当前阈值"代码）看，作者原本大概是想"画面上显示原始值、实际用修改后的值"，但没做完。
   顺带第 85~88 行也有一整块注释掉的旧显示逻辑（里面 `for threshold_name, threshold_value in thresholds.items():` 用的是 `.items()` —— 而 `thresholds` 现在是 **list 不是 dict**，说明这份代码是从"字典版"改到"列表版"的，注释里留了上一个版本的遗迹）。

3. **`flag` 只有 0 和 1 两条路，`Change` 按钮按下去无法回到调参页。** 第 112 行 `elif flag ==1:` 分支里没有再读按钮（它只 `cam.read()` + `find_blobs` + `show`，**没有 `ts.read()`**），所以进了验证页之后，屏幕上那个 `EXIT` 按钮和任何按钮都点不动，只能靠 `app.need_exit()`（IDE 停止）退出。**这是交互设计的缺口，不是崩溃。**

4. ⚠️ 本文件的**平台**问题不算"缺陷"，是它出现在这里的理由：`from maix import touchscreen, display, image, app, time, camera`（第 2 行）在 CanMV K230 上必然失败。**不要为了让它跑起来去改 import** —— 该做的是看上面那张 API 对照表，用 `06_practice/01_all_in_one.py` 那份。

## 练习建议

1. **先证明它跑不了，再证明你能定位到"哪一行、为什么"**
   拷一份到 K230 上点运行，**不许改代码**。
   **通过标准**：原样引用报错文本，指明是第几行的哪个模块名；并解释为什么这个报错**必然发生在你自己写的任何一行之前**（提示：模块顶层的 `ts = touchscreen.TouchScreen()` 在第 5 行，而 `import` 在第 2 行）。

2. **把缺陷 1 改掉，然后按"最坏按序"验证**
   在临时副本里补 `current_threshold_index = None`（或等价的初始化）。
   **通过标准**：因为本文件跑不了，这道题**在 K230 的对应实现上做** —— 给 `../../06_practice/01_all_in_one.py` 的 `handle_threshold_adjustment()` 设计同样的最坏情形，并在**真机**上执行：上电后**第一步就按 `+`/`-`**，重复 10 次。要求 10 次都不崩（无 traceback、无退出），并且屏幕上当前分量值不变化。**通过判据是"10/10 次无异常"，不是"我看了一次没事"。** 记下单次按下的最短间隔（你手动能按多快它就得多快响应，这就是 UI 的最低响应时间要求）。

3. **量一次移植代价（唯一需要出数字的题）**
   把本文件的"按钮命中区 + 分量索引"这套 UI 思路，改成能在 K230 上跑的 300×240 小屏版本（**只改 UI，不动识别部分**）。
   **通过标准**：报告里给出① 你在 MaixPy 版与 K230 版之间**必须改写**的调用点个数（逐条列出，别估算）；② 新 UI 的触摸响应延迟 —— 从 `tp.read()` 拿到点到画面上的数字发生变化，**用屏幕录制逐帧数**，给出毫秒中位数（≥20 次采样）；③ 按钮最小可命中尺寸（多少 px 你还能稳定按对）。第 ③ 项的意义：`offline_threshold_tuner.py` 里按钮是 `80×35`、`90×50` 这一档，戴手套/屏幕小了就按不准，这个数字决定了你赛场上的 UI 该画多大。

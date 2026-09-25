# 上手与环境

面向第一次摸这块板子的人。已用过 CanMV 的可以只看
[SD 卡目录结构](#sd-卡目录结构)和[v1.2 与 v1.3 的区别](#v12-与-v13-的区别)两节。

## 0. 先确认你的硬件

| | |
| --- | --- |
| 板子 | 立创·庐山派 K230-CanMV（`LCKFB-LSPI-K230-1G`，1GB） |
| SoC | 嘉楠 K230（庐山派另有一款 Lite-K230D，两者共享同一颗 SoC，外设和内存配置不同） |
| 摄像头 | GC2093，**代码里一律 `sensor_id = 2`** |
| 屏幕 | 板载 **ST7701** 800×480；可外接 **LT9611** MIPI 转 HDMI |

确认自己是哪一款：[K230 与 K230D 的区别](https://openkits-wiki.easyeda.com/zh-hans/lushan-pi-k230/k230vsk230d.html)

> ⚠️ 本仓库**只有立创·庐山派这一块板的引脚信息可靠**。代码里出现过的
> 01Studio、亚博的例程用的是各自板子的引脚定义，换板要重新核对。

## 1. 烧固件

从[庐山派快速上手](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/quick-start.html)
下载官方 `.img` 镜像，按页面说明烧录。

**为什么必须用官方镜像而不是自己拼**：本仓库有大量文件依赖固件自带东西 ——

| 依赖 | 谁需要 | 从哪来 |
| --- | --- | --- |
| `cv_lite` 扩展模块 | **33 个文件**（`05_cv_lite/` 全部 27 个 + 2025 高精版主程序 + 其它） | 庐山派固件 / 官方 SD 镜像 |
| `/sdcard/examples/kmodel/*.kmodel` | `03_ai_demos/` 需要 18 个 | 官方 SD 镜像 |
| `/sdcard/examples/utils/*.bin` | `03_ai_demos/` 需要 8 个 | 官方 SD 镜像 |
| `ybUtils` 包 | 8 个亚博例程 | **亚博**固件，庐山派上没有 |
| `/sdcard/examples/15-LVGL/data/` + 思源黑体 ttf | `06_practice/lvgl/` | 官方镜像，可能需自备 |

**30 秒自查你卡上有什么**（在 CanMV IDE 里逐条跑）：

```python
import cv_lite; print("cv_lite OK")           # 失败 = 固件不对，05_cv_lite/ 全部跑不了
import ybUtils                                 # 失败 = 正常，庐山派没有这个包
from libs.PipeLine import PipeLine             # 成功 = 你是 v1.2 时代 API
from libs.PlatTasks import ClassificationApp   # 成功 = 你是 v1.3+ 时代 API

# MicroPython 没有 os.listdir，用 ilistdir；目录不存在会抛 OSError，所以要包起来
import os
def ls(p):
    try:
        return [e.name for e in os.ilistdir(p)]
    except OSError:
        return "<不存在: %s>" % p
print(ls('/sdcard'))
print(ls('/sdcard/examples/kmodel'))           # 数有哪些模型
```

## 2. 连上 IDE

三种方式，任选：

1. **CanMV IDE**（桌面版）—— 最常用，有帧缓冲显示和帧率显示
2. **VS Code + CanMV 插件**
3. **Web IDE**（Chrome 86+，免安装）

用 USB 线连板子，在 IDE 里选对串口号。Windows 上是 `COMx`，
Linux 是 `/dev/ttyACM0` 或 `/dev/ttyUSB0`。

## 3. 看到第一帧画面

跑 `01_basics/01_camera_open.py`。

⚠️ **这个文件当前跑不起来**：第 13 行写的是 `Sensor(channe = sensor_id)`，
`channe` 不是合法关键字，会抛 `TypeError`。改成 `Sensor(id=sensor_id)` 即可。
这是仓库现状，已记在[已知问题 P0-3](02_known_issues.md)。

一份最小的能跑代码长这样（**这份是好的**，可以直接用）：

```python
import time, os, sys
from media.sensor import *
from media.display import *
from media.media import *

sensor = None
try:
    sensor = Sensor(id=2)                    # ← 庐山派的摄像头是 id=2
    sensor.reset()
    sensor.set_framesize(width=800, height=480, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    Display.init(Display.ST7701, width=800, height=480, to_ide=True)
    MediaManager.init()
    sensor.run()

    clock = time.clock()
    while True:
        os.exitpoint()                        # ← 少了这行，IDE 停止按钮无效
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        Display.show_image(img)
except KeyboardInterrupt as e:
    print("用户停止:", e)
except BaseException as e:
    print("异常:", e)
    sys.print_exception(e)                    # ← 一定带 traceback，否则查不到东西
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()                      # ← 少了这行，跑完必须断电
```

## 4. 生命周期契约：为什么"停止后要不要断电"是第一件事

上面三个标了 ← 的地方，是 CanMV 上唯一真正影响体验的三行：

| 缺什么 | 后果 |
| --- | --- |
| 循环里的裸 `os.exitpoint()` | **IDE 停止按钮无效**，只能靠串口 Ctrl+C |
| `finally` 里的 `MediaManager.deinit()` | 媒体缓冲区不释放，**必须给板子断电**才能再跑一次 |
| `except` 里没有 `sys.print_exception(e)` | 程序静默退出，只留一行文字，看不出错在哪 |

**规矩**：任何 `while True:` 的主程序，都必须被 `try/finally` 包住，
且 `finally` 里走完整套 `sensor.stop() → Display.deinit() → exitpoint(ENABLE_SLEEP) →
sleep_ms(100) → MediaManager.deinit()`。

⚠️ 注意区分两个 `os.exitpoint`：**循环里的是无参的裸调用**（检查是否请求退出），
`finally` 里的是 `os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)`（改变退出时的休眠行为）。
它们是两个不同的东西，不能互相替代 —— 批量"补 exitpoint"时最容易搞混。

**本仓库现状**：`05_cv_lite/` 全部 27 个文件三样都缺，所以每中断一次就要断电重启；
另有 3 个文件的 `finally` 被截断在注释处。见[已知问题 P1-4、P1-5](02_known_issues.md)。

**学会自查**（10 秒）：

```bash
grep -L "MediaManager.deinit()" $(grep -l "MediaManager.init()" 0*/*/*.py)   # 缺 deinit 的
grep -L "os.exitpoint()" $(grep -l "while True:" 0*/*/*.py)                   # 缺 exitpoint 的
```

## <a name="sd-卡目录结构"></a>5. SD 卡目录结构

板子从 `/sdcard/` 读代码和资源。本仓库的代码/文档里出现的这些路径**都是板子上的路径**，
不是仓库里的：

```
/sdcard/
├── <你的脚本>.py                     ← 从仓库拷过来，建议放根目录或 /sdcard/xxx/
├── mp_deployment_source/             ← ⚠️ 目录名固定，不能改
│   ├── *.kmodel                      模型本体
│   ├── deploy_config.json            部署脚本读它拿参数
│   └── test.jpg                      ⚠️ 不在仓库，跑单图脚本前要自己放
├── test.jpg                          ⚠️ det_image_1_3.py 找的是这里，和上面那个不一样
└── examples/                         ← 官方镜像自带
    ├── kmodel/                       18 个 .kmodel 都在这里
    ├── utils/                        prior_data_320.bin、方向图标 .bin 等
    ├── libs/                         PipeLine / AIBase / AI2D / Utils
    └── 15-LVGL/data/                 LVGL 示例的字体和图片
```

**两个路径陷阱**：

- `mp_deployment_source/` 这个名字是**承重的**。CanMV 部署代码硬编码
  `root_path = "/sdcard/mp_deployment_source/"`。本仓库做英文化改名时刻意没动它，
  同理也没动 `cls_image_1_3.py` / `det_video_1_2_2.py` 这些嘉楠导出件的名字
  （保持原样才能和平台新导出的包直接 diff）。
- ⚠️ `deploy_config.json` 被仓库 `.gitignore` 的一条规则匹配住了，**所以它没进版本控制**。
  新克隆会拿到 kmodel 但拿不到配置，而脚本开头就读它 → 立刻失败。
  见[已知问题 P3-3](02_known_issues.md)。

**拷贝建议**：直接拷整个 `.py` 文件，或在 IDE 里运行（IDE 会传给板子）。
⚠️ 仓库用 ASCII 文件名正是为此 —— FAT32 + CanMV IDE 对非 ASCII 路径的支持
在不同版本上表现不一致，中文名拷卡上容易出各种问题。

## <a name="v12-与-v13-的区别"></a>6. v1.2 与 v1.3 的区别

**这件事决定你哪些文件能跑。**

| | v1.2.x 写法 | v1.3+ 写法 |
| --- | --- | --- |
| AI 推理 | `from libs.PipeLine import PipeLine`<br>`from libs.AIBase import AIBase`<br>`from libs.AI2D import Ai2d`<br>`import nncase_runtime as nn` | `from libs.PlatTasks import ClassificationApp`<br>`from libs.PlatTasks import DetectionApp`<br>预处理/后处理都封在固件里 |
| 代码量 | 手写 ai2d + kpu + softmax，冗长但看得清每一步 | 短约 10 倍，但内部过程看不见 |
| 本仓库哪里用 | **`03_ai_demos/` 全部 18 个**、`04_number_classification/code/firmware_v1_2_2/`、`find_rect/det_*_1_2_2.py` | `code/firmware_v1_3/`、`det_*_1_3.py` |

⚠️ **`03_ai_demos/` 大概率在你的 v1.3 固件上跑不了** —— 那是整个目录级别的坏消息，
不是个别文件。所以：

- 想**学 API 和推理流程** → 读 `03_ai_demos/`（它的结构仍然有参考价值）
- 想**真的跑 AI** → 用官方 v1.3 例程，或走 `04_number_classification/code/firmware_v1_3/` 这条路
- 想**看懂 ai2d/kpu 每一步在干什么** → 反而该读 v1.2.2 那份，它把细节都摊开了

判断自己的版本用第 1 节那两行 `import`。

## 7. 读官方文档时的版本坑

[CanMV-K230 文档](https://www.kendryte.com/k230_canmv/zh/main/index.html) 左侧有
**v1.2 → v1.7** 的版本选择器，而 `main` 是开发分支（页面自己写着"可能包含尚未在发布版本中
提供的功能"）。你在 v1.3 就切到 v1.3，别照 `main` 抄。

另外 `developer.canaan-creative.com` 已 301 跳到 `www.kendryte.com`；
厂商 PDF 和老帖子引用的都是旧域名，搜不到就换域名而不是放弃。

## 8. 下一步

- 不知道按什么顺序学 → [03_学习路线.md](03_learning_roadmap.md)
- 想知道哪里会咬人 → [02_已知问题.md](02_known_issues.md)
- 要去比赛了 → [05_赛前检查清单.md](05_competition_checklist.md)

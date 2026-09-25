# 01_basics —— K230 视觉最小可用示例

这一层是"从零到第一帧结果"的 12 个最小可用示例，覆盖一条完整链路：**开摄像头 → 画东西 → 找形状（矩形/线段/圆）→ 找色块 → 读码（一维码/二维码/AprilTag）→ 巡线**。
它们都只用固件自带的 `media.sensor` / `media.display` / `media.media`，不依赖 `cv_lite`，也不依赖 `libs.PipeLine`，所以是排查"到底是板子的问题还是我的代码的问题"时最干净的参照物。
逐个敲一遍之后你应该能：不看例程独立写出一份带 `try/except/finally` 的采集脚本；知道 `DISPLAY_MODE` 三个分支各自对应什么硬件；说出 `find_rects` / `find_line_segments` / `find_circles` / `find_blobs` / `get_regression` 各自该传什么、返回值怎么取坐标；以及判断一个示例值不值得抄进赛题程序。

## 文件清单

| 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `01_camera_open.py` | 最小采集管线；全文件逐行注释，是生命周期契约的教材 | `Sensor()` → `reset()` → `set_framesize()` → `set_pixformat()` → `MediaManager.init()` → `run()` | ⚠️ 当前起不来，见已知问题 |
| `02_drawing.py` | 绘制原语全家桶：文字 / 线 / 矩形 / 关键点 / 填充圆 | `draw_string_advanced` `draw_line` `draw_rectangle` `draw_keypoints` `draw_circle` | 1920×1080 FHD + VIRT；`finally` 块被截断 |
| `03_find_rectangles.py` | 灰度→二值化→找最大矩形→用 `corners()` 连四条边 + 画十字中心 | `to_grayscale(copy=True)` `binary()` `find_rects(threshold=5000)` `rect.corners()` | 二值化阈值 `(101, 183)`；显示分支是死的 |
| `04_find_line_segments.py` | LSD 线段检测，最简形态 | `find_line_segments(roi, merge_distance, max_theta_diff)` | ⚠️ 参数顺序是**对的**，别照网上改，见下 |
| `05_find_circles.py` | 霍夫圆检测 | `find_circles(threshold=6000)` `circle.circle()` | 400×240，`draw_circle` 直接吃 `circle()` 四元组 |
| `06_color_blobs_and_lines.py` | 同一帧上同时做线段 + 色块；下采样加速线段检测 | `midpoint_pool(2, 2)` 后坐标 `*2` 还原、`find_blobs` | HDMI `LT9611`，1024×768；`margin=True` 的注释是错的 |
| `07_color_tracking.py` | LAB 阈值色块追踪 + FPS 反馈 | `find_blobs(threshold, invert, roi, x_stride, y_stride, pixels_threshold)` | 阈值 `(29, 42, -10, 34, -16, 39)`，`x/y_stride=5`，`pixels_threshold=3000` |
| `08_find_barcode.py` | 一维码：码制中文名、payload、旋转角、质量 | `find_barcodes()` `code.rect()` `code.payload()` `code.rotation()` `code.quality()` | GRAYSCALE 640×480；文件顶部 `barcode_name()` 是码制查表 |
| `09_find_qrcode.py` | 二维码：画框 + 把 payload 写在框上 | `find_qrcodes()` | GRAYSCALE 800×480；`barcode_name()` 从 08 抄来但没被调用 |
| `10_find_apriltag_basic.py` | AprilTag **低分辨率档** | `find_apriltags(families=...)` `tag.rect/cx/cy/id/family` | 320×240，绿框 `thickness=5` |
| `11_line_following.py` | **巡线的正确做法**：线性回归 | `binary()` + `get_regression([(255, 255)])` `line.line()` | ⚠️ 有 NameError，且 `Display.init()` 调了两次 |
| `12_find_apriltag_full.py` | AprilTag **高分辨率档** | 同 `10` | 800×480，红框默认线宽；尾部多了焦距注释 |

**两个 AprilTag 示例是刻意都留的**，不是重复文件：`10` 用 320×240、`12` 用 800×480，除分辨率外只有绘制颜色和一段注释不同。
低分辨率档帧率高、适合小车运动中的粗定位；高分辨率档能在同样距离上解出更小的 tag。赛题里先跑 `10`，确认帧率有余量再换 `12`。

## 旧名 → 新名

原名在 `01_Basic_Learning/`。**旧编号是坏的**：`05_` 前缀被两个文件同时占用（`05_圆形识别.py` 和 `05_色块追踪与线段识别.py`），所以文件浏览器里第 5 项会出现两次、而 `06_` 之后全部错位。新编号 01–12 连续。

| 旧名 | 新名 |
| --- | --- |
| `01_打开摄像头.py` | `01_camera_open.py` |
| `02_绘制图像.py` | `02_drawing.py` |
| `03_矩形识别.py` | `03_find_rectangles.py` |
| `04_线段识别.py` | `04_find_line_segments.py` |
| `05_圆形识别.py` | `05_find_circles.py` |
| `05_色块追踪与线段识别.py` | `06_color_blobs_and_lines.py` |
| `06_颜色追踪.py` | `07_color_tracking.py` |
| `07_识别一维码.py` | `08_find_barcode.py` |
| `08_识别二维码.py` | `09_find_qrcode.py` |
| `09_识别机器码.py` | `10_find_apriltag_basic.py` |
| `10_巡线路径.py` | `11_line_following.py` |
| `11_识别机器码（AprilTag）.py` | `12_find_apriltag_full.py` |

## 为什么 `11_line_following.py` 是这一层最重要的文件

赛道线、管道、边框这类**连续曲线**的目标，正确工具是 `img.get_regression()`，不是 `find_line_segments()` 后在 Python 里拼。
`get_regression()` 把逐像素的拟合放在固件的 C 里做，Python 只拿一条线的对象；`find_line_segments()` 给你一堆离散线段，然后你要自己写循环排序、合并、拟合——`06_practice/05_polygon_from_lines.py` 用了 100 多行做这件事，`06_practice/06_curve_recognition_WIP.py` 死在这条路上。
返回值对象提供 `x1() y1() x2() y2() length() theta() rho() magnitude()`；`magnitude()` 是拟合优度，范围 `(0, INF]`，越接近 0 说明像素越贴合一条直线。这条注释就在 `11` 的 82–87 行里，是中文注释中少见的准确描述。

## 练习建议

1. **把 `01_camera_open.py` 跑起来并证明你理解了生命周期。** 只做已知问题里那一处改动（不改别的），运行；然后按 IDE 停止按钮，**不重启板子**直接再运行一次。
   完成标准：第二次能立刻出画面。做不到就说明你没跑通 `finally` 里的清理顺序，回去读 45–59 行。
2. **给 `03_find_rectangles.py` 定一组能用的阈值。** 拿一张 A4 白纸或一个纸盒，改变房间光照（开灯 / 关灯 / 侧光），只在 IDE 里改 `rect_binart` 和 `find_rects(threshold=…)`。
   完成标准：三种光照下都能稳定框出目标矩形，且记录下的三组阈值写在注释里；如果必须三组完全不同才算过——这一条就算过了，因为你亲测了"阈值不可跨光照复用"。
3. **用 `04` 的 `find_line_segments` 和 `11` 的 `get_regression` 做同一件事：量一条 3cm 宽黑胶带的倾角。** 一个用 `line.theta()`，一个用回归对象的 `theta()`。
   完成标准：两种方法读数在同一帧上的差值 ≤ 3°，并且 `get_regression` 版帧率不低于 `find_line_segments` 版。做不到就去查 `merge_distance` 在合并什么。
4. **把 `07_color_tracking.py` 改成一个能报"目标在第几象限"的程序。** 用 `blob[5], blob[6]`（中心坐标）和图像宽高做比较，`draw_string_advanced` 输出 `LU/RD` 之类的象限码。
   完成标准：把色块放到画面四角，程序各报对 5 次不间断；把色块移出画面时报"无目标"而不是崩。

## 已知问题 / 注意事项

以下是**当前代码的真实状态**，本仓库刻意保持代码原样不修，只归类。逐条完整清单见 [docs/02_known_issues.md](../docs/02_known_issues.md)。

- ⚠️ **`01_camera_open.py:13` `Sensor(channe = sensor_id)`** —— 不存在的关键字，`TypeError`，**该文件当前无法启动**。改成 `Sensor(id=sensor_id)` 即可，这也是本目录唯一的致命 typo（其余文件用 `Sensor(id=…)` 都对）。
- ⚠️ **`11_line_following.py:63` `THRESHOLD = D(90, 23)`** —— `D` 从未定义，`NameError`，进不了主循环。看字面意图是灰度阈值，应为 `(90, 23)` 形式的一个二元组（注意后者比前者小，需自己确认区间方向）。
- **`11_line_following.py` 调了两次 `Display.init()`**（56 行走分支、64 行硬编码 `Display.ST7701`）。第二次会覆盖上面 `DISPLAY_MODE` 的选择：你把 `DISPLAY_MODE` 改成 `"VIRT"` 或 `"HDMI"` 也仍然按 LCD 初始化。这是"改了没反应"的经典现场。
- **`03_find_rectangles.py` 的 `DISPLAY_MODE` 分支是死代码。** 14–31 行按模式算出 `DISPLAY_WIDTH/HEIGHT`，但 51 行无条件 `Display.init(Display.VIRT, width=1920, height=1080)`。默认 `DISPLAY_MODE = "LCD"` 时算出的是 480×320，于是 121 行的居中偏移 `x=int((480-480)/2), y=0` 把 480×320 的图贴在 1920×1080 画布的左上角。另外 LCD 分支写的 480×320 与庐山派 ST7701 屏的 800×480 不符——同目录 `04/05/08/09/10/11/12` 的 LCD 分支都是 800×480，只有 `03` 是 480×320。
- ⚠️ **`find_line_segments(roi, merge_distance, max_theta_diff)` 的参数顺序是对的，不要改。** 官方签名 `find_line_segments([roi[, merge_distance=0[, max_theta_difference=15]]])`，`roi` 就在第一位；`04`（第 74 行）和 `06`（第 59 行）都按位置传参，都是对的。网上大量帖子声称第一个参数是 `merge_distance`，照它们改会把 `roi` 和 `merge_distance` 对调，检测直接失效。
- **`04_find_line_segments.py:71` `roi = (0, 0, 480, 240)` 超出画面。** 该文件 `picture_width = 400`，roi 宽度写了 480，是从别的分辨率改过来时的残留。想验证 LSD 就把它改成 `(0, 0, 400, 240)` 或干脆去掉 roi。
- **`06_color_blobs_and_lines.py:64` 关于 `margin` 的注释是错的。** 注释写 `margin(是否合并)`，实际 `find_blobs` 的 `margin` 是**整数像素外扩量**（把每个 blob 的边界框向外撑几像素），合并开关是 `merge=True`。第 67 行传的 `margin=True` 会被当成 `margin=1`，能跑，但语义和注释都不对。
- **`img.compressed_for_ide()` 在 `03`（118 行）和 `06`（72 行）里是空操作。** 它**返回一张新图**，不修改原图；这两个文件都没接返回值。要压缩显示得写成 `img = img.compressed_for_ide()`。其余文件的 `Display.show_image(img)` 是正常路径，不受影响。
- **`02_drawing.py` 的 `finally` 块被截断**：57 行停在 `# 释放媒体缓冲区` 注释，后面的 `MediaManager.deinit()` 没写。后果是每跑一次就得给板子重新上电。同样的缺失在 `02_data_collection/02_capture_burst.py`，那份还把它写在注释里说"自动处理"。
- **`09_find_qrcode.py:34` 有从 `08` 复制来的 `barcode_name()`，全文未被调用。** 无害，但别以为二维码也有码制名可查。
- **`12_find_apriltag_full.py:132–141` 尾部关于 `fx/fy/cx/cy` 的注释是 OpenMV OV7725 的资料**（"标准 OpenMV Cam 的值为 ((2.8 / 3.984) × 656)"），焦距 6mm、靶面 5.76mm 都是那个模组的参数，**不适用于本板的 GC2093**。AprilTag 的 3D 位姿计算要另找 K230 的内参。
- **`06/07` 是每帧 `print` 的文件**，串口打印会实打实吃掉帧率；在 IDE 里看 FPS 用 `draw_string_advanced` 就够了，别在 `while True` 里加 `print`。
- 本目录**每帧 `find_rects()` 都算一遍**、没有"连续 N 帧才认"的稳定化逻辑。赛题程序里这一点必须补，写法见 `../06_practice/03_nested_rect.py` 和 `04_triangle.py`。

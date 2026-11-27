# 01_basics —— 最小可用示例（12 个）

这一层是"从零到第一帧结果"的 12 个最小脚本，覆盖一条完整链路：**开摄像头 → 画东西 → 找形状（矩形/线段/圆）→ 找色块 → 读码（一维码/二维码/AprilTag）→ 巡线**。
它们只用固件自带的 `media.sensor` / `media.display` / `media.media`，不依赖 `cv_lite`，也不依赖 `libs.PipeLine` —— 排查"到底是板子的问题还是我的代码的问题"时，这一层是最干净的参照物。

学完你应该能：不看例程独立写出一份带 `try/except/finally` 的采集脚本；知道 `DISPLAY_MODE` 三个分支各自对应什么硬件；说出 `find_rects` / `find_line_segments` / `find_circles` / `find_blobs` / `get_regression` 各该传什么、返回值怎么取坐标；判断一个示例值不值得抄进赛题程序。

## 这里有什么

| 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `01_camera_open.py` | 最小采集管线，逐行注释，是生命周期契约的教材 | `Sensor(id=2)` → `reset()` → `set_framesize()` → `set_pixformat()` → `MediaManager.init()` → `run()` | VIRT 1920×1080；关键字拼写已按官方手册修正（[P0-3](../docs/02_known_issues.md#p0-3)） |
| `02_drawing.py` | 绘制原语全家桶：文字 / 线 / 矩形 / 关键点 / 填充圆 | `draw_string_advanced` `draw_line` `draw_rectangle` `draw_keypoints` `draw_circle` | `finally` 块被截断（[P1-5](../docs/02_known_issues.md#p1-5)） |
| `03_find_rectangles.py` | 灰度 → 二值化 → 找最大矩形 → `corners()` 连四条边 + 画中心 | `to_grayscale(copy=True)` `binary()` `find_rects(threshold=5000)` `rect.corners()` | 显示分支是死的（[P2-4](../docs/02_known_issues.md#p2-4)） |
| `04_find_line_segments.py` | LSD 线段检测，最简形态 | `find_line_segments(roi, merge_distance, max_theta_diff)` | ⚠️ 参数顺序是**对的**，别照网上改；roi 越界（[P2-3](../docs/02_known_issues.md#p2-3)） |
| `05_find_circles.py` | 霍夫圆检测 | `find_circles(threshold=6000)` `circle.circle()` | 400×240；`draw_circle` 直接吃 `circle()` 四元组 |
| `06_color_blobs_and_lines.py` | 同一帧上做线段 + 色块；下采样加速 | `midpoint_pool(2, 2)` 后坐标 `*2` 还原、`find_blobs` | HDMI 1024×768；`margin` 的注释写错了（见[澄清](../docs/02_known_issues.md#澄清这些不是-bug)） |
| `07_color_tracking.py` | LAB 阈值色块追踪 + FPS 反馈 | `find_blobs(threshold, invert, roi, x_stride, y_stride, pixels_threshold)` | 阈值 `(29, 42, -10, 34, -16, 39)`，`x/y_stride=5`，`pixels_threshold=3000` |
| `08_find_barcode.py` | 一维码：码制中文名、payload、旋转角、质量 | `find_barcodes()` `code.rect()` `code.payload()` `code.rotation()` `code.quality()` | GRAYSCALE 640×480；文件顶部的 `barcode_name()` 是码制查表 |
| `09_find_qrcode.py` | 二维码：画框 + 把 payload 写在框上 | `find_qrcodes()` | `barcode_name()` 从 08 抄来但没被调用 |
| `10_find_apriltag_basic.py` | AprilTag **低分辨率档** | `find_apriltags(families=...)` `tag.rect/cx/cy/id/family` | 320×240，绿框 |
| `11_line_following.py` | 巡线的正确做法：线性回归 | `binary()` + `get_regression([(255, 255)])` `line.line()` | ⚠️ 起不来：`D(90, 23)`（[P0-4](../docs/02_known_issues.md#p0-4)）；`Display.init` 调了两次 |
| `12_find_apriltag_full.py` | AprilTag **高分辨率档** | 同 `10` | 800×480；尾部焦距注释是 OpenMV OV7725 的资料（[P3-8](../docs/02_known_issues.md#p3-8)） |

**两个 AprilTag 示例是刻意都留的**：`10` 用 320×240、`12` 用 800×480，除分辨率外只有绘制颜色和一段注释不同。低分辨率档帧率高，适合运动中的粗定位；高分辨率档能在同样距离上解出更小的 tag。赛题里先跑 `10`，确认帧率有余量再换 `12`。

### 巡线为什么用 `get_regression`，而不是 `find_line_segments` 拼

赛道线、管道、边框这类**连续曲线**的目标，正确工具是 `img.get_regression()`。它把逐像素拟合放在固件的 C 里做，Python 只拿一条线的对象；`find_line_segments()` 给你一堆离散线段，然后你要自己写循环排序、合并、拟合 —— `06_practice/05_polygon_from_lines.py` 用了 100 多行做这件事，`06_curve_recognition_WIP.py` 死在这条路上。

返回值对象提供 `x1() y1() x2() y2() length() theta() rho() magnitude()`。`magnitude()` 是**线性拟合的强度**，范围 `(0, INF]`：**0 表示点更像一个圆，数值越大表示越接近一条直线**（`11_line_following.py:86-87` 的注释就是这么写的）。别把它当"误差越小越好" —— 方向正好相反。

## 能不能跑

- 12 个文件里，11 个没有启动级问题；`11_line_following.py` 因 `D(90, 23)` 起不来（P0-4），`01` 的关键字已修（P0-3）。
- 能启动 ≠ 结果对：`03` 的 LCD/HDMI 分支无效（P2-4），`04` 的 roi 超出画面（P2-3），`02` 的 `finally` 截断（P1-5，中断后要断电）。
- **没有一条上板验证过。** 状态按"读代码核实 / 待上板确认"标注，见[已知问题](../docs/02_known_issues.md)。

## 练习

1. **把 `01_camera_open.py` 跑起来，证明你理解了生命周期。** 运行 → 按 IDE 停止 → **不重启板子**直接再运行。
   完成标准：第二次能立刻出画面；做不到就回去看 `finally` 里的清理顺序。
2. **给 `03_find_rectangles.py` 定一组能用的阈值。** 拿一张 A4 白纸或纸盒，改变房间光照（开灯 / 关灯 / 侧光），只改 `rect_binart` 和 `find_rects(threshold=…)`。
   完成标准：三种光照下都能稳定框出目标，并把三组阈值写进注释 —— 你会发现它们不可能相同。
3. **用 `04` 的 `find_line_segments` 和 `11` 的 `get_regression` 做同一件事：量一条 3 cm 宽黑胶带的倾角。** 一个用 `line.theta()`，一个用回归对象的 `theta()`。
   完成标准：同一帧上两种读数差 ≤ 3°，且 `get_regression` 版帧率不低于 `find_line_segments` 版。
4. **把 `07_color_tracking.py` 改成报"目标在第几象限"。** 用中心坐标和图像宽高比较，`draw_string_advanced` 输出 `LU/RD` 之类的象限码。
   完成标准：色块放四角各报对 5 次；移出画面时报"无目标"而不是崩。

## 相关

- [上手与环境](../docs/01_getting_started.md) —— 唯一的生命周期模板在那一篇
- [已知问题](../docs/02_known_issues.md) —— 本目录的问题集中在 P0-3、P0-4、P1-5、P2-3、P2-4、P3-8
- 官方：[image API 手册 v1.3](https://www.kendryte.com/k230_canmv/zh/v1.3/api/openmv/image.html) · [庐山派使用摄像头](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/use-sensor.html)

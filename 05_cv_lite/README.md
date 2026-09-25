# 05_cv_lite —— 用 `cv_lite` 做实时预处理（27 个示例）

这一层解决"手工判据在真实光照下不稳"的问题。`01_basics/` 的 `binary()` / `find_rects()` 全在 Python 层一帧一帧地调 image 对象方法，帧率上不去；`cv_lite` 是庐山派固件里的一个 C 扩展，把二值化、形态学、模糊、直方图、白平衡、以及 blobs/circles/edges/rectangles 四类检测都放到固件里对 **ndarray 原地**做，所以同一颗板子上能跑出可用帧率。
27 个示例每个只演示**一个函数**，参数全部摊在文件顶部当常量，是很好的"扫一眼就知道接口形状"的参考。走完这一层你应该能：判断某个预处理该不该用 `cv_lite` 版本；写出零拷贝的 `to_numpy_ref()` → 处理 → `ALLOC_REF` 回包这条链；并且清楚为什么**这一层的每个文件跑一次就要断一次电**（这是本目录最大的痛点，最后有解法）。

## 先搞懂那三行零拷贝套路

27 个文件全都长这样：

```python
import cv_lite                          # 庐山派固件提供，不在本仓库
img = sensor.snapshot()
img_np = img.to_numpy_ref()             # 拿到指向摄像头缓冲区的 ndarray 引用（不是副本）
out_np = cv_lite.<something>(image_shape, img_np, ...params)
img_out = image.Image(image_shape[1], image_shape[0], image.RGB888,
                      alloc=image.ALLOC_REF, data=out_np)
Display.show_image(img_out)
```

注意参数顺序：`image.Image()` 收的是 **(宽, 高, 像素格式)**，而 `image_shape = [480, 640]` 是 **高在前**，所以那句 `image.Image(image_shape[1], image_shape[0], …)` 是**先取 `[1]` 再取 `[0]`**、不是写反了。这个反直觉的下标用法是本目录最容易抄错的地方，务必记住：`image_shape[0]` 是高、`image_shape[1]` 是宽。

为什么这样快：`to_numpy_ref()` **不复制**，`ALLOC_REF` **也不复制**。整条链上没有任何一次 480×640×3 的内存搬运，C 侧读写的是传感器那块 buffer。
副作用一定要理解清楚：**对 `img_np` 的原地修改，就是对你屏幕上的那一帧的修改**；反过来，`img.draw_rectangle()` 画上去的东西也会出现在你交给 `cv_lite` 的数据里。所以下面这 27 个文件里，凡是 `Display.show_image(img)`（画在 `img` 上、显示 `img`）的 `find_*` 系列，都是在往相机 buffer 上直接涂鸦——这在演示里没问题，在赛题程序里你要清楚自己是这个语义。

`image` 这个名字在 27 个文件里**都没有显式 `import image`**，它从 `from media.sensor import *` 里带进来。别把那一行的星号导入删掉。

## 编号系列 `01_`–`16_`

| 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `01_grayscale_binary.py` | 灰度图定阈值二值化（本目录唯一的 GRAYSCALE 编号文件） | `cv_lite.grayscale_threshold_binary(shape, np, thresh, maxval)` | `thresh=130, maxval=255` |
| `02_rgb888_binary.py` | 同上，RGB888 输入 | `cv_lite.rgb888_threshold_binary` | 同样 `130 / 255` |
| `03_rgb888_exposure.py` | 手动增益调曝光 | `cv_lite.rgb888_adjust_exposure(shape, np, gain)` | `exposure_gain = 2.5`，注释给的推荐区间 0.2~3.0 |
| `04_rgb888_exposure_fast.py` | 快速版曝光 | `cv_lite.rgb888_adjust_exposure_fast` | 同一参数；注释写"增强亮度 1.5 倍"但值是 2.5，注释和代码不符 |
| `05_rgb888_erode.py` | 腐蚀 | `cv_lite.rgb888_erode(shape, np, ksize, iter, th)` | `3 / 1 / 100` |
| `06_rgb888_dilate.py` | 膨胀 | `cv_lite.rgb888_dilate` | `3 / 1 / 100` |
| `07_rgb888_open.py` | 开运算（去噪点） | `cv_lite.rgb888_open` | `threshold_value = 0` → 走 **Otsu 自动阈值**，和 05/06 的 100 不一样，别以为是同一个 |
| `08_rgb888_close.py` | 闭运算（补断线） | `cv_lite.rgb888_close` | `3 / 1 / 100` |
| `09_rgb888_tophat.py` | 顶帽 | `cv_lite.rgb888_tophat` | `3 / 1 / 100` |
| `10_rgb888_blackhat.py` | 黑帽 | `cv_lite.rgb888_blackhat` | `3 / 1 / 100` |
| `11_rgb888_morph_gradient.py` | 形态学梯度 | `cv_lite.rgb888_gradient` | ⚠️ 文件名是 `morph_gradient`，**函数名没有 `morph_` 前缀** |
| `12_rgb888_mean_blur.py` | 均值模糊 | `cv_lite.rgb888_mean_blur_fast` | `kernel_size = 3` |
| `13_rgb888_gaussian_blur.py` | 高斯模糊 | `cv_lite.rgb888_gaussian_blur_fast` | `kernel_size = 3` |
| `14_rgb888_histogram.py` | RGB 三通道直方图（**不是图像，是 3×256 数组**） | `cv_lite.rgb888_calc_histogram` + `np.argmax` | 通道顺序是 `hist[0]=B, hist[1]=G, hist[2]=R`；每 30 帧打一次三通道峰值索引；显示的是 `img` 原图 |
| `15_rgb888_wb_gray_world.py` | 灰度世界白平衡（**带参版**） | `cv_lite.rgb888_white_balance_gray_world_fast_ex(shape, np, gain_clip, brightness_boost)` | `gain_clip=2.5, brightness_boost=1.25` |
| `16_rgb888_wb_white_patch.py` | 白补丁白平衡（**带参版**） | `cv_lite.rgb888_white_balance_white_patch_ex(shape, np, top_percent, gain_clip, brightness_boost)` | `5.0 / 2.5 / 1.1` |

## 灰度检测系列 `grayscale_*`

| 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `grayscale_find_blobs.py` | 灰度阈值连通域 | `cv_lite.grayscale_find_blobs(shape, np, th_min, th_max, min_area, ksize)` | `[230,255] / 10 / 1`；返回 `[x,y,w,h,...]` 平铺列表 |
| `grayscale_find_circles.py` | 灰度霍夫圆 | `cv_lite.grayscale_find_circles(shape, np, dp, minDist, param1, param2, minR, maxR)` | 返回 `[x,y,r,...]`，`range(0, len(circles), 3)` 步进解包 |
| `grayscale_find_edges.py` | 灰度 Canny | `cv_lite.grayscale_find_edges(shape, np, t1, t2)` | `50 / 80`；返回的是**新的灰度 ndarray**，要重新包成 `image.GRAYSCALE` |
| `grayscale_find_rectangle.py` | 灰度矩形（Canny + 轮廓逼近） | `cv_lite.grayscale_find_rectangles(shape, np, c1, c2, eps, area_ratio, angle_cos, blur)` | `50/150/0.04/0.001/**0.3**/5`；**本目录唯一动模拟增益的文件**：`gain = k_sensor_gain(); gain.gain[0] = 20; sensor.again(gain)` |

## RGB 检测系列 `rgb888_*`

| 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `rgb888_find_blobs.py` | RGB 空间色块 | `cv_lite.rgb888_find_blobs(shape, np, threshold, min_area, ksize)` | ⚠️ 阈值是 **`[Rmin,Rmax,Gmin,Gmax,Bmin,Bmax]`**，不是 `01_basics/07` 那套 LAB！`[120,255,0,50,0,50]` = 找红色 |
| `rgb888_find_circles.py` | RGB 霍夫圆 | `cv_lite.rgb888_find_circles(shape, np, dp, minDist, p1, p2, minR, maxR)` | `1/30/80/20/10/50` |
| `rgb888_find_edges.py` | RGB Canny | `cv_lite.rgb888_find_edges(shape, np, t1, t2)` | `50/80`，输出仍是灰度图 |
| `rgb888_find_rectangles.py` | RGB 矩形 | `cv_lite.rgb888_find_rectangles(shape, np, c1, c2, eps, area_ratio, angle_cos, blur)` | 与 grayscale 版**只差一个参数**：`max_angle_cos = **0.5**`（grayscale 版是 0.3），越大越宽松 |
| `rgb888_calc_histogram_1.py` | 与 `14_` 功能相同的早期版本 | `cv_lite.rgb888_calc_histogram` | ⚠️ 摄像头初始化自相矛盾，见已知问题 |
| `rgb888_white_balance_gray_world_fast.py` | 灰度世界白平衡（**无参版**） | `cv_lite.rgb888_white_balance_gray_world_fast(shape, np)` | 与 `15_` 是**不同接口**，不是同一函数的不同写法 |
| `rgb888_white_balance_white_patch.py` | 白补丁白平衡（**无参版**） | `cv_lite.rgb888_white_balance_white_patch(shape, np)` | 与 `16_` 同上；结尾 `print("white patch wb fast:")` 里那个 `fast` 是复制粘贴残留 |

## ⚠️ 两套系列已经分叉了：该抄哪一份

编号系列（`01_`–`16_`）和命名系列（`grayscale_*` / `rgb888_*`）覆盖**同一批算法**，是同一个教程里两个阶段留下的产物。它们**不是**彼此的别名，行为有实质差异：

| 算法 | 编号文件 | 命名文件 | 差异 |
| --- | --- | --- | --- |
| 灰度世界白平衡 | `15_` 调 `..._gray_world_fast_ex(shape, np, gain_clip, brightness_boost)` | `rgb888_white_balance_gray_world_fast.py` 调 `..._gray_world_fast(shape, np)` | **两个不同的入口点**。带参版给你亮度上限和整体提亮两个旋钮；无参版把这两个值烧在 C 里 |
| 白补丁白平衡 | `16_` 调 `..._white_patch_ex(shape, np, top_percent, gain_clip, brightness_boost)` | `rgb888_white_balance_white_patch.py` 调 `..._white_patch(shape, np)` | 同上 |
| 矩形检测 | —（编号系列无） | `grayscale_find_rectangle.py` 用 `max_angle_cos=0.3`；`rgb888_find_rectangles.py` 用 `0.5` | 同一算法、两份文件、两个默认值 |
| 直方图 | `14_rgb888_histogram.py` | `rgb888_calc_histogram_1.py` | 除了摄像头初始化那行，**其余逐字相同**（`count += 1` / `if count == 30` 都在 44/50/62/70 行） |

**建议**：白平衡一律用编号版（`15_` / `16_`），因为现场一定要调增益上限，`_ex` 是唯一能调的入口；其余算法以命名版为准（`find_*` 系列命名版参数更完整、注释更全）。

真正的风险是**跨系列复制**：把 `rgb888_white_balance_gray_world_fast.py` 的那一行 `balanced_np = cv_lite.rgb888_white_balance_gray_world_fast(image_shape, img_np)` 粘进你的项目，编译运行都不报错、画面也出来了、帧率也正常 —— 只是颜色偏，而且**没有任何参数可以调**。从 `15_` 粘就没这个问题，因为它多两个参数，粘错了会当场 `TypeError`。这一条是本目录最需要警惕的"静默改变行为"。

## 旧名 → 新名

旧路径 `05_OpenCV_Porting/23-CV_Lite/`。**"23" 是厂商教程系列的章节号**，脱离那套教程就毫无意义，而且白白把 27 个文件埋深一层，所以这次直接把中间两段压平成 `05_cv_lite/`。
命名版文件本来就是 ASCII，原名保留；只有 `rgb888_find_rectangels.py` 的拼写错误在这次改掉。

| 旧名（`05_OpenCV_Porting/23-CV_Lite/` 下） | 新名 |
| --- | --- |
| `01_灰度图像中进行二值化处理.py` | `01_grayscale_binary.py` |
| `02_RGB888图像中进行二值化处理.py` | `02_rgb888_binary.py` |
| `03_RGB888图像中调整曝光度.py` | `03_rgb888_exposure.py` |
| `04_RGB888图像中快速调整曝光度.py` | `04_rgb888_exposure_fast.py` |
| `05_RGB888图像中进行腐蚀操作.py` | `05_rgb888_erode.py` |
| `06_RGB888图像中进行膨胀操作.py` | `06_rgb888_dilate.py` |
| `07_RGB888图像进行开运算.py` | `07_rgb888_open.py` |
| `08_RGB888图像进行闭运算.py` | `08_rgb888_close.py` |
| `09_RGB888图像进行顶帽运算.py` | `09_rgb888_tophat.py` |
| `10_RGB888图像进行黑帽运算.py` | `10_rgb888_blackhat.py` |
| `11_RGB888图像进行形态学梯度运算.py` | `11_rgb888_morph_gradient.py` |
| `12_RGB888图像进行均值模糊.py` | `12_rgb888_mean_blur.py` |
| `13_RGB888图像进行高斯模糊.py` | `13_rgb888_gaussian_blur.py` |
| `14_RGB888图像的直方图.py` | `14_rgb888_histogram.py` |
| `15_RGB888图像中使用灰度世界算法快速进行白平衡.py` | `15_rgb888_wb_gray_world.py` |
| `16_RGB888图像中使用白色补丁算法进行白平衡.py` | `16_rgb888_wb_white_patch.py` |
| `grayscale_find_blobs.py` | 原名保留 |
| `grayscale_find_circles.py` | 原名保留 |
| `grayscale_find_edges.py` | 原名保留 |
| `grayscale_find_rectangle.py` | 原名保留（注意：文件名单数 `rectangle`，函数名复数 `grayscale_find_rectangles`） |
| `rgb888_calc_histogram_1.py` | 原名保留 |
| `rgb888_find_blobs.py` | 原名保留 |
| `rgb888_find_circles.py` | 原名保留 |
| `rgb888_find_edges.py` | 原名保留 |
| `rgb888_find_rectangels.py` | `rgb888_find_rectangles.py`（改掉拼写错误） |
| `rgb888_white_balance_gray_world_fast.py` | 原名保留 |
| `rgb888_white_balance_white_patch.py` | 原名保留 |

## 练习建议

1. **先给一个文件装上"能反复运行"的能力，再开始这一层的其它练习。** 按下面"关于断电"一节的模板改 `01_grayscale_binary.py`。
   完成标准：在 IDE 里连续运行 5 次，**中途不给板子断电**，每次都能出画面；第 5 次的帧率和第 1 次相差 < 10%。做不到就别往下做——后面 26 个文件是同一个病。
2. **量化每个预处理对你的帧率的代价。** 挑一个固定目标（比如一个红杯子），依次跑 `02_`(二值化) → `12_`(均值模糊) → `13_`(高斯) → `05_`(腐蚀) → `07_`(开) → `15_`(白平衡)，每个记下 `print` 出来的 fps。
   完成标准：交出一张 6 行的"算法 → fps"表，并指出最慢的那个慢在哪（必须给一个可验证的理由，比如"它每帧多分配了一块 640×480×3 的 ndarray"，而不是"感觉慢"）。
3. **证明 `ALLOC_REF` 是共享内存而不是拷贝。** 在 `grayscale_find_blobs.py` 的主循环里，在 `cv_lite.grayscale_find_blobs(...)` **之前**加一行 `img_np[0:8, 0:8] = 0`（把左上角 8×8 涂黑）。
   完成标准：屏幕左上角出现一个黑方块。若出现，说明你写的就是相机 buffer；然后删掉那行，确认它消失。（做完这一条，你就永久理解了为什么 `draw_rectangle` 会污染喂给算法的数据。）
4. **把 `rgb888_find_blobs.py` 改成找蓝色，再改成 LAB 版。** 蓝色阈值按 `[Rmin,Rmax,Gmin,Gmax,Bmin,Bmax]` 自己填；第二步把它换成 `01_basics/07_color_tracking.py` 的 `img.find_blobs` 写法对比。
   完成标准：同一张图、同一个目标，`cv_lite` 版和 image 版都稳定框出，且 `cv_lite` 版 fps ≥ image 版；同时你手里有**两套不通用的阈值格式**，这一点必须写在你自己项目 README 里，否则一定会有人把 LAB 阈值粘进 RGB 接口。

## 关于"跑一次就要断电"——本目录最烦人的地方

这是实打实测出来的：**27 个文件里 `try:` 的数量都是 0**（`grep -c "try:" 05_cv_lite/*.py` → 全为 0），主循环都是模块级裸 `while True:`，`os.exitpoint()` **一次都没在循环体里出现过**。
于是每个文件末尾那五行清理代码：

```python
while True:
    ...                     # ← 永远不退出

sensor.stop()               # ↓ 这五行全是死代码
Display.deinit()
os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
time.sleep_ms(100)
MediaManager.deinit()
```

`Display.deinit()` 和 `MediaManager.deinit()` 永远执行不到，`MediaManager` 的 buffer 就一直被占着 —— 你在 IDE 里点停止之后，第二次运行会卡在 `MediaManager.init()`，只能拔电。这就是这一层写代码-看效果的迭代循环特别慢的原因，也是本目录体验最差的一点。

**修法是模式化的**（本仓库不改代码，请自己动手套到你正在看的那个文件上）：

```python
sensor = None
try:
    sensor = Sensor(id=2, width=image_shape[1], height=image_shape[0])
    sensor.reset()
    sensor.set_framesize(width=image_shape[1], height=image_shape[0])
    sensor.set_pixformat(Sensor.RGB888)
    Display.init(Display.VIRT, width=image_shape[1], height=image_shape[0], to_ide=True, quality=50)
    MediaManager.init()
    sensor.run()
    clock = time.clock()
    while True:
        os.exitpoint()          # ← 关键：循环体第一行的裸 exitpoint()
        clock.tick()
        img = sensor.snapshot()
        ...                     # 原来的处理逻辑
except KeyboardInterrupt as e:
    print("用户停止:", e)
except BaseException as e:
    print(f"异常: {e}")          # 想要 traceback 用 sys.print_exception(e)
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()       # ← 少了这一行，仍然要断电
```

三个点缺一不可：**循环里 `os.exitpoint()`**（否则 IDE 的停止按钮打不断它）、**`finally`**（否则异常路径不收尾）、**`MediaManager.deinit()` 放在最后**（顺序错了会 `MediaManager` 还占着 buffer）。参考实现看 `02_data_collection/01_capture_single.py` 和 `../01_basics/01_camera_open.py`，它们这条链是完整的。

## 已知问题 / 注意事项

以下都从代码里核实过。完整分级清单见 [docs/02_known_issues.md](../docs/02_known_issues.md)。

- ⚠️ **`cv_lite` 不在本仓库**，由立创庐山派固件 / 官方 SD 镜像提供。自查方法就一行：在 CanMV IDE 的终端里 `import cv_lite`。全仓库有 **33 个文件** `import cv_lite`，这条不过，那 33 个文件一个都跑不了。
- ⚠️ **全部 27 个文件缺 `try/finally` 与循环内 `os.exitpoint()`**，见上一节。这是本目录的系统性问题，不是个别文件的疏忽。
- ⚠️ **`rgb888_calc_histogram_1.py:23` 摄像头初始化自相矛盾**：`Sensor(id=2, width=1280, height=720, fps=90)` 建了个 720p/90fps 的传感器，紧接着第 25 行 `sensor.set_framesize(width=640, height=480)` 又改回 VGA。到底哪个生效取决于固件里 `set_framesize` 的实现，代码本身没有表达清意图；而且 `fps=90` 这个参数在本仓库其它 26 个文件里一次都没出现过。以 `14_` 的写法为准：`Sensor(id=2, width=image_shape[1], height=image_shape[0])`，构造尺寸和 `set_framesize` 用的是同一组数，不会自相矛盾。
- ⚠️ **`rgb888_find_blobs.py:41–42` 的阈值格式和 `01_basics/07` 不是一回事。** 这里的注释写得很明白：`[Rmin, Rmax, Gmin, Gmax, Bmin, Bmax]`，是**通道极值**；`01_basics` 的 `find_blobs` 用 LAB 的 `(Lmin, Lmax, Amin, Amax, Bmin, Bmax)`。数值范围还不同（LAB 的 A/B 是 -128~127）。这两套阈值**互相粘过去一定不工作**，而编译器不会拦你。
- **`11_rgb888_morph_gradient.py` 的文件名和函数名不一致**：文件叫 `morph_gradient`，调的是 `cv_lite.rgb888_gradient`。在固件里搜符号时用后者。
- **`grayscale_find_rectangle.py`（单数）里的函数是 `cv_lite.grayscale_find_rectangles`（复数）**；`rgb888_find_rectangles.py` 文件名与函数名一致。所以文件名带不带 s 和函数带不带 s 没有对应关系，别靠文件名猜 API。
- **`07_rgb888_open.py:49` 的 `threshold_value = 0`，而 `05_/06_/08_/09_/10_/11_` 都是 `100`。** 注释说 `0 = 使用 Otsu 自动阈值`。也就是说"开运算"这一份文件跑出来的输入图和它的三个邻居（腐蚀/膨胀/闭）**不是同一张二值图**，把 07 的结果和 05/06 对比时这是首要变量。
- **`04_rgb888_exposure_fast.py:51` 的注释与值不符**：`exposure_gain = 2.5  # 示例：增强亮度 1.5 倍`。以值为准。
- **`rgb888_white_balance_white_patch.py:48` 打印 `"white patch wb fast:"`**，但它调的是**没有** `fast` 后缀的 `cv_lite.rgb888_white_balance_white_patch`。看串口输出判断自己在跑哪个文件时会被骗到。
- **每帧 `print(..., clock.fps())` + `gc.collect()` 是有代价的**，27 个文件全部如此（`print` 各 1 次、`gc.collect()` 各 1 次，都在循环里）。MicroPython 的 `print` 走 UART，640×480 的循环里它还每帧触发一次全堆扫描。想把 fps 数字做准，就把这两行注释掉再测；想复现示例给的帧率，就别注释。两种做法都对，但**不能混着比较数字**。
- **`from machine import Pin` 在 27 个文件里全都有，但 0 个文件用到 `Pin(`**；`import _thread` 出现在 21 个文件里，也 0 处使用；`ulab.numpy as np` 只有两个直方图文件真正用到（`np.argmax`）。这些是从同一个模板复制来的死导入，无害，但别以为这些文件里有多线程或 GPIO 逻辑。
- **`Display.init(Display.VIRT, ...)` 27 个文件全部一致**，也就是**只能看 IDE 缓冲区，接 LCD 不显示**。想在庐山派的 800×480 屏上看，得换成 `Display.init(Display.ST7701, width=800, height=480, to_ide=True)`，同时注意 `image_shape` 仍是 640×480，画面会偏左上（居中偏移的写法见 `../01_basics/04_find_line_segments.py:87`）。
- **`Display.init` 的 `quality=` 三种写法并存**：`06_`–`11_` 这 6 个文件**不写 `quality`**（走固件默认值）、`12_ 13_ 14_` + `rgb888_calc_histogram_1.py` + `rgb888_find_circles.py` 是 `quality=100`、其余 16 个是 `quality=50`。`quality` 只影响你在 IDE 里看到的画面压缩质量，**不影响算法耗时**，但它确实会改变"目视流畅度"，所以对比帧率时要知道自己在看的是哪一档。想对比公平，就把它统一成同一个值。

# 03_ai_demos —— 18 个 kmodel 推理示例（当 API 参考用）

⚠️ **先说结论：这 18 个文件在 CanMV v1.3+ 上大概率跑不起来，请当 API 参考而不是可运行示例。**
它们整体是 v1.2 时代的技术栈：`libs.PipeLine` + `libs.AIBase` + `libs.AI2D` + `nncase_runtime`，全部 18 个文件一字不差地按这套写。v1.3 把这些收进了 `libs.PlatTasks`（对照 `../04_number_classification/code/v1.3/` 只有 63–75 行、而这 18 个是 127–611 行，就知道接口面变了多少）。
再加上**它们需要的 26 个模型/先验文件一个都不在本仓库**（见下面的资产表），所以实际可用的路径只有两条：**真要用 AI 能力，去看嘉楠官方为 v1.3 写的示例**（<https://www.kendryte.com/k230_canmv/zh/main/index.html>，注意左侧版本选择器要切到你自己的固件版本）；**要理解一个 kmodel 任务在 K230 上是怎么被组织起来的**（ai2d 预处理 → kpu 推理 → `aidemo`/`aicube` 后处理 → OSD 绘制），这个目录是目前手上最完整的一份说明，读完比看任何二手帖子都快。
走完之后你应该能：说清 `AIBase` 子类必须实现哪几个方法、`rgb888p_size` 和 `model_input_size` 分别由谁决定、后处理为什么不在 Python 里做，以及怎么判断某个官方例程是不是又换了 API。

## 技术栈（18 个文件全部一致）

| 依赖 | 用在哪 | 来源 | v1.3 现状 |
| --- | --- | --- | --- |
| `from libs.PipeLine import PipeLine, ScopedTiming` | 建管线、`pl.get_frame()` / `pl.show_image()` / `pl.osd_img` | 官方 SD 镜像 `/sdcard/libs/`（部分文件注释里直接写 `/sdcard/app/libs/AI2D.py`） | 已被 `libs.PlatTasks` 一层的封装取代 |
| `from libs.AIBase import AIBase` | 所有任务的基类；`kmu.load_kmodel` 与前后处理编排在它里面 | 同上 | 同上 |
| `from libs.AI2D import Ai2d` | 硬件做 resize/格式转换 | 同上 | 同上 |
| `import nncase_runtime as nn` | `nn.kpu()` / `nn.ai2d()` / `nn.from_numpy()` | 固件内置 | v1.3 走 `LiteEvaluator` |
| `import aidemo`（10 个文件） | `face_det_post_process` `face_parse_post_process` `nanotracker_postprocess` `polylines` `contours` `invert_affine_transform` | 固件内置 | ⚠️ 函数名/参数需按你的固件核对 |
| `import aicube`（8 个文件） | `anchorbasedet_post_process`（手/人体检测那批） | 固件内置 | 同上 |
| `import ulab.numpy as np` `import ujson` `import image` | 全部 18 个 | 固件内置 | 稳定 |

**18 个文件里有 17 个的公共配置都是 `display_mode="lcd"` + `rgb888p_size=[1920,1080]` + `display_size=[800,480]`。**
也就是说它们把 **1920×1080 的 RGB888P 帧**送给 NPU 前端，而模型输入只有 320×320 或 512×512，屏幕上也没有超过 800×480。唯一的例外 `05_object_tracking.py` 用的是 `rgb888p_size=[1280,720]`。这是这份代码最值得记住的一条**性能教训**：`rgb888p_size` 是 sensor→AI 那条通道的尺寸，调小它是免费的帧率，很多人只调 `model_input_size`（那个改不了，模型已固化）。
`01_face_detection.py:88` 上面那行注释写着"k230保持不变，k230d可调整为[640,360]"—— 记一下这个数，`[640,360]` 是同一份逻辑能跑到的合理量级。

## 文件清单

| 组 | 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- | --- |
| 人脸 | `face_analysis/01_face_detection.py` | **只做检测**：出框 + 置信度 | `AIBase` 子类 + `aidemo.face_det_post_process` | 127 行，本目录最短，最适合先读；`anchors` 从 `prior_data_320.bin` 读（`anchor_len=4200, det_dim=4`，99–103 行） |
| 人脸 | `face_analysis/02_face_segmentation.py` | 检测 + 人脸 Parsing（区域分割） | + `aidemo.face_parse_post_process` | 两个 kmodel 串联 |
| 人脸 | `face_analysis/03_face_landmark.py` | 检测 + 五官关键点 | `aidemo.invert_affine_transform` `polylines` `contours` | 先仿射对齐把脸摆正再提特征点 |
| 人脸 | `face_analysis/04_face_3d.py` | 检测 + 3D 网络（网格/姿态/表情） | `aidemo.face_mesh_post_process` `face_draw_mesh` | 3 个 kmodel：`face_alignment` + `face_alignment_post` + 检测 |
| 人脸 | `face_analysis/05_face_orientation.py` | 检测 + 朝向（正视/侧脸/低头/仰头） | + `face_pose.kmodel` | 判断"人有没有在看屏幕"很有用 |
| 人脸 | `face_analysis/06_face_register.py` | **人脸注册**（门禁/打卡）：特征向量写进数据库 | `FaceRegistrationApp`，`utils/db/`、`utils/db_img/` | ⚠️ 主循环**没有 `os.exitpoint()`**；它读的是**磁盘样图**（`image.Image(full_img_file)`）而不是实时帧 |
| 人脸 | `face_analysis/07_face_detect_recognize.py` | 检测 + **识别**（认 `06` 注册过的人） | 双模型串联 + 数据库比对 | 与 `01` 的区别就是这一份才做识别 |
| 人脸 | `face_analysis/08_eye_gaze.py` | 视线方向 | `aidemo.eye_gaze_post_process(results)` | 后处理只吃一个参数，这批里最简 |
| 手 | `hand_inspection/01_hand_detection.py` | 手掌框检测 | `aicube.anchorbasedet_post_process(...)` | 单模型；`model_input_size=[512,512]`、`strides=[8,16,32]` |
| 手 | `hand_inspection/02_dynamic_gesture.py` | **动态手势**：检测 + 关键点 + 时序分类三段串联 | 3 kmodel + 4 个方向 `.bin` | 611 行，本目录最长的一份 |
| 手 | `hand_inspection/03_hand_keypoint.py` | 手部关键点（带手指连线） | `hand_det` + `handkp_det` | |
| 手 | `hand_inspection/04_hand_keypoint_classify.py` | 关键点 → 静态手势分类 | 同上 + 分类器 | |
| 手 | `hand_inspection/05_gesture_recognition.py` | 与 `04` 同套，换 `hand_reco.kmodel`，**不再画手指连线** | `hand_det` + `hand_reco` | 文件头自己说了"和上一章是差不多的" |
| 手 | `hand_inspection/06_rock_paper_scissors.py` | 剪刀石头布：关键点 + 三类模板比对 | 3 个 `.bin`（`fist/five/shear`）当模板 | 完整可演示的小项目 |
| 人体 | `human_detection/01_person_detection.py` | 人体框检测 | `person_detect_yolov5n.kmodel` | 入侵检测/人数统计的起点 |
| 人体 | `human_detection/02_body_keypoint.py` | 人体 17 关键点姿态 | `yolov8n-pose.kmodel`，`[320,320]` | 170 行，比手部那批短，好读 |
| 人体 | `human_detection/03_fall_detection.py` | 跌倒检测 | `yolov5n-falldown.kmodel` | 老人看护场景；**电赛最可能直接用到的一类** |
| 跟踪 | `05_object_tracking.py`（根目录） | **视觉跟踪（NanoTracker）**：给初始框，之后每帧回归目标位置 | `aidemo.nanotracker_postprocess(...)`；3 kmodel | 422 行；⚠️ **主循环没有 `os.exitpoint()`、整个文件没有 `try/finally`** |

**为什么 `05_object_tracking.py` 孤零零一个 `05_` 摆在根目录、没有 `01_`–`04_`。** 因为它不是本仓库自己组织的示例，是从 **01Studio 的教程里整份抄过来的**——那份教程把 AI 例子按 01–05 平铺在同一个列表里，这里的编号是抄来的时候带上的。它文件头至今还写着：

```
实验名称：目标跟踪
实验平台：01Studio CanMV K230
教程：wiki.01studio.cc
```

（庐山派和 01Studio 用的是同一套 CanMV 固件，所以这段抬头不用改也能看懂。）
它和那三个子目录并列是有道理的：**跟踪是第四类任务**，不是"检测的一种"。检测输出的是"这一帧有什么"，跟踪输出的是"我盯着的那个东西现在在哪"，所以它需要三个模型协同（backbone 提特征、head 回归位移、crop 取模板），也所以它的 `display_mode` 走的是 `'st7701'`（`display="lcd3_5"` 分支），和 800×480 的庐山派屏正好对得上——**这是全目录唯一一个默认配置就适合本板的文件**。

## 模型资产表：26 个文件，0 个在仓库里

⚠️ 下面每一项都得来自**官方 CanMV SD 镜像**，路径分别是 `/sdcard/examples/kmodel/` 和 `/sdcard/examples/utils/`。本仓库一个都没有（已实测：`find . -name "*.kmodel" -o -name "*.bin"` 只找到 `../04_number_classification/` 和 `../07_contest/2025_E_self_aiming/` 各一个 kmodel，与这 18 个文件无关）。
自查：`print(os.listdir("/sdcard/examples/kmodel/"))`。

**18 个 `.kmodel`**

| 模型 | 用途 | 被哪些文件用 |
| --- | --- | --- |
| `face_detection_320.kmodel` | 人脸检测（**8 个文件共用的前置**） | face_analysis 的 `01`–`08` 全部 |
| `face_parse.kmodel` | 人脸区域分割 | `02` |
| `face_landmark.kmodel` | 人脸关键点 | `03` |
| `face_alignment.kmodel` | 3D 对齐 | `04` |
| `face_alignment_post.kmodel` | 3D 对齐后处理 | `04` |
| `face_pose.kmodel` | 头部姿态 | `05` |
| `face_recognition.kmodel` | 人脸特征向量 | `06` `07` |
| `eye_gaze.kmodel` | 视线方向 | `08` |
| `hand_det.kmodel` | 手掌检测（6 个文件共用的前置） | hand_inspection 的 `01`–`06` |
| `handkp_det.kmodel` | 手部关键点 | `02` `03` `04` `06` |
| `hand_reco.kmodel` | 手势识别 | `05` |
| `gesture.kmodel` | 动态手势分类 | `02` |
| `person_detect_yolov5n.kmodel` | 人体检测 | human `01` |
| `yolov8n-pose.kmodel` | 人体关键点 | human `02` |
| `yolov5n-falldown.kmodel` | 跌倒检测 | human `03` |
| `nanotrack_backbone_sim.kmodel` | 跟踪主干 | `05_object_tracking` |
| `nanotracker_head_calib_k230.kmodel` | 跟踪头 | `05_object_tracking` |
| `cropped_test127.kmodel` | 跟踪模板 crop | `05_object_tracking` |

**8 个 `.bin`**（先验框 / 手势模板，`np.fromfile(path, dtype=np.float)` 读进来后 `reshape`）

- `utils/prior_data_320.bin` —— 320×320 检测的 anchor 先验。face `01`–`08` **全部 8 个** + hand `03` `04` `05` `06`，共 12 个文件引用，是这批里被用得最多的一个文件。
- `utils/fist.bin` `five.bin` `shear.bin` —— 石头 / 布 / 剪刀 模板，hand `06` 用。
- `utils/shang.bin` `xia.bin` `you.bin` `zuo.bin` —— 上 / 下 / 右 / 左 四个方向的动态手势模板，hand `02` 用。

另有两个**目录**：`utils/db/`（人脸特征数据库）和 `utils/db_img/`（注册样图），`face_analysis/06` `07` 用；这两个是运行时会被程序**写**的，第一次跑要先确认它们存在且可写。

**合计 18 kmodel + 8 bin = 26 个资产文件，加 2 个可写目录。** 一个都不在仓库里 —— 这就是"这个目录只能当参考"的第二条理由。

## 旧名 → 新名

旧根目录 `03_AI_Demo/`，子目录 `Face_Analysis/` `Hand_Inspection/` `Human_Detection/` → 全小写 `face_analysis/` `hand_inspection/` `human_detection/`。

| 旧名（`03_AI_Demo/` 下） | 新名 |
| --- | --- |
| `05_目标跟踪.py` | `05_object_tracking.py` |
| `Face_Analysis/01_人脸识别.py` | `face_analysis/01_face_detection.py` |
| `Face_Analysis/02_人脸分割.py` | `face_analysis/02_face_segmentation.py` |
| `Face_Analysis/03_人脸特征点识别.py` | `face_analysis/03_face_landmark.py` |
| `Face_Analysis/04_人脸3D网络.py` | `face_analysis/04_face_3d.py` |
| `Face_Analysis/05_人脸朝向检测.py` | `face_analysis/05_face_orientation.py` |
| `Face_Analysis/06_人脸注册.py` | `face_analysis/06_face_register.py` |
| `Face_Analysis/07_人脸检测识别.py` | `face_analysis/07_face_detect_recognize.py` |
| `Face_Analysis/08_人眼注视方向.py` | `face_analysis/08_eye_gaze.py` |
| `Hand_Inspection/01_人手检测.py` | `hand_inspection/01_hand_detection.py` |
| `Hand_Inspection/02_人手动态手势识别.py` | `hand_inspection/02_dynamic_gesture.py` |
| `Hand_Inspection/03_手部关键点检测.py` | `hand_inspection/03_hand_keypoint.py` |
| `Hand_Inspection/04_手部关键点分类.py` | `hand_inspection/04_hand_keypoint_classify.py` |
| `Hand_Inspection/05_手势识别.py` | `hand_inspection/05_gesture_recognition.py` |
| `Hand_Inspection/06_剪刀石头布游戏.py` | `hand_inspection/06_rock_paper_scissors.py` |
| `Human_Detection/01_人体检测.py` | `human_detection/01_person_detection.py` |
| `Human_Detection/02_人体关键点检测.py` | `human_detection/02_body_keypoint.py` |
| `Human_Detection/03_人体跌倒检测.py` | `human_detection/03_fall_detection.py` |

**`01_人脸识别.py` → `01_face_detection.py` 是有意的改名**：读代码就知道它只加载 `face_detection_320.kmodel`、只画框、不做任何身份比对，"识别"是原名的误导。真正做识别的是 `07`（检测 + `face_recognition.kmodel`）和 `06`（把人脸注册进库）。这三个词的区分在人脸这条链上是**功能边界**，不是措辞差异。

## 练习建议

1. **确认你的固件到底缺什么。** 在 IDE 终端里逐条执行，把**第一条报错的**记下来。
   ```python
   import nncase_runtime              # 固件内置
   import aidemo, aicube             # 固件内置；v1.3 上可能已经改名或挪位置
   from libs.PipeLine import PipeLine # v1.2 写法
   import os; print(os.listdir("/sdcard/examples/kmodel"))
   ```
   完成标准：交出一张四行表——每一项"成功 / ImportError / 其它异常 + 原文"，并明确回答"`03_ai_demos` 在我的固件上是缺 API 还是缺模型文件"。（很可能两个都缺，那这个目录就真的只能读。）
2. **拿 `face_analysis/01_face_detection.py` 做纯阅读练习，画出它的调用图。** 不要运行，只读。
   完成标准：在一张纸上写清 `PipeLine.create()` → `AIBase.__init__` → `config_preprocess()` → `run()` → `post_process()` → `draw_result()` 每一步**谁把什么交给谁**（图像格式、ndarray 形状、坐标是相对 `rgb888p_size` 还是 `display_size`）。第五步那个坐标换算（`x * display_size[0] / rgb888p_size[0]`）说不清楚，就是还没读懂。
3. **把 `rgb888p_size` 从 `[1920,1080]` 降到 `[640,360]`，做纸面预算。** 不需要能跑；算的是面积比、以及 `ai2d` 每帧要搬的字节数比值。
   完成标准：给出一个数字（大约几倍），并用 `04_number_classification/code/v1.2.2/cls_video_1_2_2.py` 里 `OUT_RGB888P_WIDTH/HEIGH = 640/360` 这个官方自己的选择作为对照，解释为什么它是 640×360 而不是 1920×1080。
4. **挑一个真正能落地的：`human_detection/03_fall_detection.py`（或 `01_person_detection.py`），列出上板还差的每一样东西。**
   完成标准：清单包括（a）API 版本差异（去官方 v1.3 示例里找同任务的现在写法）、（b）所需模型文件的确切路径与获取方式、（c）`display_mode` 要不要改、（d）`rgb888p_size` 该定多少。四条都有出处（文件+行号或官方链接）才算完成。

## 已知问题 / 注意事项

- ⚠️ **全 18 个文件都是 v1.2 技术栈，v1.3+ 上不保证能跑。** 判定方法就是练习 1 那三行 import。**不要花时间"修"这个目录**；同样的任务在官方 v1.3 示例里有更短的写法。
- ⚠️ **26 个模型/先验资产全部缺失**（见资产表）。这是比 API 更硬的墙：API 能改，模型文件得从官方 SD 镜像或官方仓库拿。
- ⚠️ **`05_object_tracking.py` 的主循环既没有 `os.exitpoint()` 也没有 `try/finally`**（全文 0 处 `try:`、0 处 `exitpoint`、0 处 `KeyboardInterrupt`），IDE 点停止**打不断它**，只能断电，收尾本来就没有。`face_analysis/06_face_register.py` 的循环里也没有 `os.exitpoint()`（它有 `try/except/finally`，异常路径能收尾，但停止按钮打不断循环）。其余 16 个文件都有。
- **18 个文件里 `KeyboardInterrupt` 出现 0 次**：它们统一用 `except Exception as e: sys.print_exception(e)`，所以 Ctrl-C 会被当成普通异常处理， traceback 会打出来。这一点其实比本仓库其它目录的 `except BaseException as e: print(f"异常: {e}")`（只有一行、没有 traceback）更规矩 —— 值得学过去。
- **`05_object_tracking.py` 每帧打两次串口**：循环里 `print(output)` + `print(clock.fps())`。跟踪任务本来就吃紧，这两行是白送的延迟；测帧率前先注释掉。
- **`rgb888p_size=[1920,1080]` 在 17/18 个文件里是默认值，对 800×480 的庐山派屏是浪费**（见前面专节）。这不是"必须这样"，`01_face_detection.py:87` 的注释已经告诉你合理值是 `[640,360]`。
- **`aidemo` / `aicube` 是固件内置模块、不在仓库**，而且这两个模块的函数签名是这批代码里最容易随版本变的部分。`aidemo.face_det_post_process` 在 `01`（`self.model_input_size[1]` 当第三参）和 `02`（`self.model_input_size[0]`）里传的下标还不一样 —— 抄的时候认准一个文件，别混。
- **`06_face_register.py` 是离线批处理式的**：从 `utils/db_img/` 读静态图逐张注册（`image.Image(full_img_file)` → `fr.image2rgb888array(img)` → `fr.run(...)`），不是实时视频流；把它当"注册界面"看会误解。而 `utils/db/` 与 `utils/db_img/` 都是**会被程序写入**的目录 —— SD 卡只读挂载、或目录不存在时报的是 `OSError`，和"模型文件找不到"混在一起分不清。第一次跑之前先 `os.listdir` 确认这两个目录存在。
- **子目录里各文件用同一份 `PipeLine` 配置但 `model_input_size` 不同**：人脸检测 `01`–`08` 是 `[320,320]`、手 `01` 是 `[512,512]`、人体关键点 `02` 是 `[320,320]`。**改模型必须同时改 `prior_data_*.bin` 的 `anchor_len/det_dim`**（`01_face_detection.py:99–103` 那五行），只改一个数会让后处理把先验框解释错，表现是"框全在乱跳"而不是报错。

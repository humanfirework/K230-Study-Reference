# 03_ai_demos —— 18 个 kmodel 推理示例：读调用结构，不当可运行样板

这一层在 `01_basics` 的图像处理之后、`04_number_classification` 的完整工程之前，用 18 个文件展示“ai2d 预处理 → kpu 推理 → `aidemo`/`aicube` 后处理 → OSD 绘制”这条链如何被组织起来。
出处要分清：17 个来自**庐山派 wiki 的 AI Demo 页**，只有根目录的 `05_object_tracking.py` 来自 **01Studio**（文件头写着“实验平台：01Studio CanMV K230”）。
与 `04` 的分工：`04` 是能部署的最小闭环，本目录是任务种类的索引和 API 形状的参考。

## 这里有什么

| 文件 | 做什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `face_analysis/01_face_detection.py` | 只做检测：出框 + 置信度 | `AIBase` + `aidemo.face_det_post_process` | 127 行，本目录最短，适合先读 |
| `face_analysis/02_face_segmentation.py` | 检测 + 人脸区域分割 | + `aidemo.face_parse_post_process` | 两个 kmodel 串联 |
| `face_analysis/03_face_landmark.py` | 检测 + 五官关键点 | `invert_affine_transform`、`polylines`、`contours` | 先仿射对齐再提点 |
| `face_analysis/04_face_3d.py` | 检测 + 3D 网格/姿态 | `face_mesh_post_process`、`face_draw_mesh` | 3 个 kmodel |
| `face_analysis/05_face_orientation.py` | 检测 + 头部朝向 | `face_pose.kmodel` | 判断“有没有看屏幕” |
| `face_analysis/06_face_register.py` | 人脸注册：特征写进库 | `FaceRegistrationApp`、`utils/db/` | 离线读磁盘样图，不是实时流 |
| `face_analysis/07_face_detect_recognize.py` | 检测 + 识别已注册的人 | 双模型 + 数据库比对 | 与 `01` 的分界在“认人” |
| `face_analysis/08_eye_gaze.py` | 视线方向 | `aidemo.eye_gaze_post_process` | 后处理只吃一个参数 |
| `hand_inspection/01_hand_detection.py` | 手掌框检测 | `aicube.anchorbasedet_post_process` | `model_input_size=[512,512]` |
| `hand_inspection/02_dynamic_gesture.py` | 动态手势：检测 + 关键点 + 时序分类 | 3 kmodel + 4 个方向 `.bin` | 611 行，本目录最长 |
| `hand_inspection/03_hand_keypoint.py` | 手部关键点（带连线） | `hand_det` + `handkp_det` | |
| `hand_inspection/04_hand_keypoint_classify.py` | 关键点 → 静态手势 | 同上 + 分类器 | |
| `hand_inspection/05_gesture_recognition.py` | 换 `hand_reco`，不画连线 | `hand_det` + `hand_reco` | 与 `04` 同套 |
| `hand_inspection/06_rock_paper_scissors.py` | 剪刀石头布 | `fist/five/shear.bin` 当模板 | 完整小项目 |
| `human_detection/01_person_detection.py` | 人体框检测 | `person_detect_yolov5n.kmodel` | 人数统计的起点 |
| `human_detection/02_body_keypoint.py` | 人体 17 关键点 | `yolov8n-pose.kmodel` | 170 行，比手部那批好读 |
| `human_detection/03_fall_detection.py` | 跌倒检测 | `yolov5n-falldown.kmodel` | 老人看护场景 |
| `05_object_tracking.py` | NanoTracker 视觉跟踪 | `aidemo.nanotracker_postprocess` | 来自 01Studio；裸循环（P1-4） |

### 技术栈

| 依赖 | 用在哪 | 现状 |
| --- | --- | --- |
| `libs.PipeLine` | 建管线、`get_frame()` / `show_image()` / `osd_img` | v1.3 文档树仍有手册 |
| `libs.AIBase` | 所有任务的基类，`load_kmodel` 与前后处理编排 | 同上 |
| `libs.AI2D` | 硬件 resize / 格式转换 | 同上 |
| `nncase_runtime as nn` | `nn.kpu()` / `nn.ai2d()` / `nn.from_numpy()` | 接口面随固件变 |
| `aidemo` / `aicube` | 人脸/手/人体的后处理 | 函数签名最易随版本变（P3-18） |

这套 API 在 v1.3 文档树里仍有手册（PipeLine、Ai2D、AIBase、Utils），所以“老 API”本身不是硬阻塞；真正的墙是资产。

### 读一个文件的顺序

`face_analysis/01_face_detection.py` 只有 127 行，适合当模板。读的时候沿着这条线走，每一步只问“谁把什么交给谁”：

1. `PipeLine.create()` 建出 `pl`，确定 `rgb888p_size` 与 `display_size`。
2. `FaceDetectionApp(...)` 继承 `AIBase`，在 `__init__` 里 `load_kmodel`、建 `Ai2d`。
3. `config_preprocess()` 把模型输入尺寸、mean/scale、resize 方式写进 ai2d。
4. `run()` 取一帧 → ai2d → kpu → `post_process()`。
5. `draw_result()` 把坐标从 `rgb888p_size` 换算到 `display_size` 再画。

### `rgb888p_size` 为什么值得单独记

它是 sensor→AI 那条通道的尺寸，不是模型输入尺寸。模型输入由 kmodel 固化（320×320、512×512 等），改不了；`rgb888p_size` 可以调小，而且调小几乎白送帧率。17/18 个文件默认 `[1920,1080]`，而屏幕只有 800×480，中间的搬运是纯开销（P3-18）。`01_face_detection.py:87` 的注释给了同逻辑下的合理量级 `[640,360]`。

### 为什么 `05_object_tracking.py` 单独编号

它来自 01Studio 的教程，那份教程把 AI 例子平铺成 01–05，编号是抄来时带上的。跟踪是第四类任务：检测回答“这一帧有什么”，跟踪回答“我盯着的那个东西现在在哪”，所以它要三个模型协同（backbone、head、crop）。它默认 `display="lcd3_5"`（映射到 `st7701`），和 800×480 屏对得上。

### 这些示例能给你什么

- **调用结构**：一个 AI 任务在 K230 上被拆成哪几层，类与类之间传什么。
- **坐标换算**：后处理输出相对 `rgb888p_size`，画到屏幕要乘 `display_size / rgb888p_size` 的比例。
- **多模型串联**：人脸 `01`–`08`、手 `02`、跟踪都用两个以上 kmodel，能看清“前一个模型的输出怎么变成后一个的输入”。
- **任务边界**：检测、识别、跟踪各需要什么模型，哪些步骤在 Python、哪些在 `aidemo`/`aicube`。

### 资产表：26 个文件，仓库里一个都没有

18 个 `.kmodel` 全部在官方 SD 镜像的 `/sdcard/examples/kmodel/`；8 个 `.bin` 在 `/sdcard/examples/utils/`。自查：`print(os.listdir("/sdcard/examples/kmodel/"))`。

| 资产 | 用途 | 被谁用 |
| --- | --- | --- |
| `face_detection_320.kmodel` | 人脸检测（8 个文件共用的前置） | face `01`–`08` |
| `face_pose.kmodel` | 头部姿态 | face `05` |
| `face_parse.kmodel` | 人脸区域分割 | face `02` |
| `face_landmark.kmodel` | 人脸关键点 | face `03` |
| `face_alignment.kmodel` | 3D 对齐 | face `04` |
| `face_alignment_post.kmodel` | 3D 对齐后处理 | face `04` |
| `face_recognition.kmodel` | 人脸特征向量 | face `06` `07` |
| `eye_gaze.kmodel` | 视线方向 | face `08` |
| `hand_det.kmodel` | 手掌检测（6 个文件共用的前置） | hand `01`–`06` |
| `handkp_det.kmodel` | 手部关键点 | hand `02` `03` `04` `06` |
| `hand_reco.kmodel` | 手势识别 | hand `05` |
| `gesture.kmodel` | 动态手势分类 | hand `02` |
| `person_detect_yolov5n.kmodel` | 人体检测 | human `01` |
| `yolov8n-pose.kmodel` | 人体关键点 | human `02` |
| `yolov5n-falldown.kmodel` | 跌倒检测 | human `03` |
| `cropped_test127.kmodel` | 跟踪模板 crop | `05_object_tracking` |
| `nanotrack_backbone_sim.kmodel` | 跟踪主干 | `05_object_tracking` |
| `nanotracker_head_calib_k230.kmodel` | 跟踪头 | `05_object_tracking` |

8 个 `.bin`：`prior_data_320.bin`（anchor 先验，face `01`–`08` 与 hand `03`–`06` 共用）；`shang/xia/you/zuo.bin`（动态手势四方向，hand `02`）；`fist/five/shear.bin`（石头/布/剪刀，hand `06`）。人脸注册另需 `utils/db/`、`utils/db_img/` 两个可写目录。

这些资产随官方 CanMV SD 镜像提供；也可以按 [docs/04](../docs/04_official_resources.md) 的训练/导出链接，为同任务重新导出。先确认资产齐全，再谈 API 版本。

## 能不能跑

18 个都缺资产，没有一个能直接跑（P3-3）。`05_object_tracking.py` 是裸循环、无收尾（P1-4）；17/18 个默认 `rgb888p_size=[1920,1080]`，对 800×480 屏是浪费（P3-18）。全部**未上板验证**。

## 练习

1. **在官方 SD 镜像上跑通一个人脸 demo**（建议从 `01_face_detection.py` 开始）。
   建议验收：画面出框，IDE 或串口有置信度输出，并且你说得出这次用了哪几个 kmodel 与 `.bin`。
2. **读一个文件，列出它与 v1.3 的 API 差异**（只列，不迁移）。
   建议验收：至少覆盖 `PipeLine` / `AIBase` / `Ai2d` / `nncase_runtime` 四项，每条附文件行号或官方链接。
3. **对照 `04_number_classification/code/v1.3/`，看 `PlatTasks` 封掉了哪些步骤**。
   建议验收：把“取帧 / 预处理 / 推理 / 判定 / 显示”逐项标注为“仍在脚本里”或“被 cfg/run 吞掉”，每项有对照行号。

## 相关

- [CanMV-K230 文档主页](https://www.kendryte.com/k230_canmv/zh/main/index.html)（左侧切到你的固件版本）
- [庐山派 wiki](https://wiki.lckfb.com/zh-hans/lushan-pi-k230/quick-start.html)
- 本仓：[docs/03 学习路线](../docs/03_learning_roadmap.md) · [docs/04 官方资源](../docs/04_official_resources.md) · [docs/02 已知问题](../docs/02_known_issues.md)

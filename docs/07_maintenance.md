# 维护说明：命名、保留物、旧名与出处

> 这份文件是给**以后要改这个仓库的人**（包括作者自己）看的，读者不需要读。
> 它回答四件事：东西该放哪、什么不能改名、哪些"看起来该删"的东西为什么还在、每一段的出处是什么。

## 1. 六条维护规则

### 1.1 一个事实只写一处

| 事实类型 | 唯一位置 | 其它地方怎么写 |
| --- | --- | --- |
| 目录/文件清单、每个文件做什么 | 各目录 `README.md` | 根 README 只给一行 |
| 能不能跑 | 根 README 一行 + 目录 README 一节 + `docs/02` 一条 | 只给结论和链接 |
| 缺陷（现象/成因/改法） | `docs/02_known_issues.md` | 只给条目号和链接 |
| 串口协议 | `docs/06_uart_protocol.md` | 只给结论 |
| 官方链接 | `docs/04_official_resources.md` | 目录 README 最多 1–2 条 |
| 命名、旧名、保留物、许可 | 本文件 | — |
| 学习方法与阶段 | `docs/03_learning_roadmap.md` | 根 README 5 行摘要 |

### 1.2 新增一个目录

建 `NN_ascii_name/` → 文件名用 ASCII → README 用固定四段（这里有什么 / 能不能跑 / 练习 / 相关）→ 根 README 目录表加一行 → 本文件 §5 旧名表加一行（如果是从旧目录改来的）。

### 1.3 新增一个文件

在目录 README 的"这里有什么"表里加一行：做什么 + 来源。有缺陷就在 `docs/02` 加一条（带"核实方式"和"状态"）。厂商原件不要改名，也不要"顺手修"。

### 1.4 改代码前的五步

1. 读该文件上下文，确认它是**自写**还是**厂商/平台导出/他人方案**。
2. 厂商件、平台导出件、他人方案：**只记录，不改**。
3. 自写件：在嘉楠 CanMV-K230 文档（切到 v1.3）或庐山派 wiki 找到对应原文。
4. 只改"字面错误"（拼写、补显式导入），不改语义；拿不准就不改。
5. 改完 `ast.parse`，在 `docs/02` 记下依据 URL、改前 `文件:行号`，并在提交说明里写清。

### 1.5 图的规则

一张图只讲一件事；图上方必须有一句文字摘要（CanMV IDE 和部分 Markdown 阅读器不渲染 Mermaid）；每个节点都要能指到代码行或官方页面原句。画不出来的环节写"仓库内无脚本"，不要补想象。

### 1.6 每次改完跑三条检查

```python
# 1) 断链：保存为 check_links.py，在仓库根运行
import os, re, urllib.parse
bad = 0
for dp, dn, fn in os.walk("."):
    dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
    for f in fn:
        if not f.endswith(".md"):
            continue
        p = os.path.join(dp, f)
        text = open(p, encoding="utf-8", errors="replace").read()
        for i, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(r"\]\(([^)\s]+)", line):
                t = urllib.parse.unquote(m.group(1).split("#")[0])
                if not t or t.startswith(("http", "mailto:", "#")):
                    continue
                q = t.lstrip("/") if t.startswith("/") else os.path.join(os.path.dirname(p), t)
                if not os.path.exists(os.path.normpath(q)):
                    print(f"{p}:{i} -> {t}")
                    bad += 1
print("断链:", bad)
```

```bash
# 2) 文件:行号 引用是否越界
grep -rhoE '`[^`]+\.py:[0-9]+' --include="*.md" . | sort -u
# 3) 计数（改完目录后核对文档里的数字）
find . -name "*.py" -not -path "./.git/*" | wc -l
grep -rl "^import cv_lite\|^from cv_lite" --include="*.py" . | wc -l   # 当前 33
```

## 2. 命名约定

- **自己写的代码、文档文件名一律 ASCII**：这些文件要拷到 FAT32 SD 卡、用 CanMV IDE 打开，两者对非 ASCII 路径的支持都不稳；纯 ASCII 也避开 Windows 路径长度问题。
- **文件内容里的中文注释、文档正文一律保留中文。**
- 文档文件名同样 ASCII，标题用中文写在第一行。
- 编号用 `NN_` 前缀，保证在文件浏览器和 SD 卡上排序唯一。旧仓库里混用过 `1.`（点号）、`8,`（ASCII 逗号）、`1，`（全角逗号），三种写法排序结果不同，这是当年那次重命名的直接原因。
- 以下三类**保持中文原名不动**：官方题目 PDF（`E题_三子棋游戏装置.pdf`，标题本身是信息）、立创/亚博的厂商例程原件（其教程按中文编号引用它们）、`NUEDC_TOPIC-master/` 真题库。

## 3. 不能改名的位置

| 位置 | 为什么 |
| --- | --- |
| `04_number_classification/mp_deployment_source/`<br>`07_contest/2025_E_self_aiming/find_rect/mp_deployment_source/` | CanMV 部署脚本硬编码 `root_path = "/sdcard/mp_deployment_source/"`，改名后板子上找不到 |
| `cls_image_1_2_2.py` / `cls_video_1_2_2.py` / `cls_*_1_3.py` / `det_*_1_2_2.py` / `det_*_1_3.py` | 嘉楠在线训练平台导出件的命名约定；保持原样才能和新导出的包直接 diff |
| `07_contest/reference/basic_gpio/`、`image_recognition/` 的中文文件名 | 立创/01Studio 教程按这些名字引用 |
| 亚博工程内部（`2022.ioc`、`bsp_uart.c`、`pid_motor.h` 等） | 第三方便件，改名会让它和亚博教程对不上 |

## 4. 刻意保留的文件（实测后的真实情况）

| 保留物 | 真实情况 | 处理建议 |
| --- | --- | --- |
| `07_contest/2025_E_self_aiming/methods_reference/iterations/`（9 个） | 共享同一骨架，但差异 30–495 行不等；其中 `custom_rect_check_dup.py` 与 `custom_rect_check.py` **逐字节相同** | 当成"阶段存档"，不要当"单变量对照"；dup 可删（git 里有） |
| `07_contest/2023_E_laser/variants/`（6 个） | 两两差 60–370 行，阈值、发帧格式、函数集都不同；`yedan.py` 是立创例程，不属于这条序列 | 同上，按"阶段存档"读 |
| `03_E_laser/error/`、`2025/methods_reference/error/` | 被放弃的另一条路线，不是残次品 | 保留，README 里说明它是什么路线 |
| `07_contest/laser_drawing/05_digits_EMPTY.py` | **0 字节**，全仓唯一 | 保留，它是"这一格没做"的可见标记；补做时从它起步 |
| `02_data_collection/05_data_collect.py` | 与 `02_capture_burst.py` 近重复：1024×768、英文提示、`finally` 完整 | 早期版本，保留 |
| `01_basics/10` 与 `12` | 同一件事的两档分辨率（320×240 / 800×480） | 都留，用途不同 |
| `06_practice` 的编号空号（缺 07、两个 08） | 07 移到 `pc_tools/`，09 移到 `other_boards/maixpy/`；两个 08 是"脚本 + 它的仿真器" | 不重编号，位置本身是信息 |
| `06_practice/lvgl/first.py` | 不是 LVGL 代码，是两份脚本首尾拼接，后一份覆盖前一份的函数定义 | 留作"复制粘贴事故"的样本 |
| `07_contest/2021_F_drug_car/` | 只有一个 README，没有代码 | 保留目录，让"2021 没做"可见 |
| `05_cv_lite/` 两套命名 | 16 个编号文件（`01_`–`16_`）+ 11 个原名文件 | 两套都保留，对应固件例程原貌 |
| `reference/image_recognition/6，颜色识别.py` 与 `6，颜色识别（二）.py` | 两份不同的课，不是重名事故 | 都留 |
| `variants/k230_basic_variant2.py` | 旧名带"副本"，但与 `k230_basic.py` 差 192 行（105 增 / 87 删），阈值和载荷都不同 | 不是副本，别删 |
| `07_contest/2023_E_laser/yahboom_reference/` | 第三方方案（Apache-2.0，署名 Kongcheng） | 保留 LICENSE 与署名，代码不改 |

## 5. 旧名 → 现名（全库总表）

> 用途只有一个：你用旧名字找文件时查得到。新读者不需要。git 里用 `git log --follow -- 路径` 也能追。

### 5.1 目录级

| 旧目录 | 现目录 |
| --- | --- |
| `01_Basic_Learning/` | `01_basics/` |
| `02_Data_Collection/` | `02_data_collection/` |
| `03_AI_Demo/`（含 `Face_Analysis/` `Hand_Inspection/` `Human_Detection/`） | `03_ai_demos/`（`face_analysis/` `hand_inspection/` `human_detection/`） |
| `04_Number_Classification/`（`Data/` `Code/` `Docs/`） | `04_number_classification/`（`data/` `code/` `docs/`） |
| `05_OpenCV_Porting/23-CV_Lite/` | `05_cv_lite/` |
| `平时练习/`（含 `LVGL屏幕/`） | `06_practice/`（`lvgl/`） |
| `电赛赛题K230/` | `07_contest/` |
| `电赛赛题K230/00_Reference/` | `07_contest/reference/` |
| `赛题K230/01_2021_F_DrugCar/` | `07_contest/2021_F_drug_car/` |
| `02_2023_E_Laser/参考/` | `07_contest/2023_E_laser/reference_gimbal/` |
| `02_2023_E_Laser/示例代码/` | `07_contest/2023_E_laser/sample_code/` |
| `02_2023_E_Laser/合集/` | `07_contest/2023_E_laser/variants/` |
| `02_2023_E_Laser/K230参考/` | `07_contest/2023_E_laser/yahboom_reference/` |
| `03_2024_E_ThreePieceChess/` | `07_contest/2024_E_tic_tac_toe/` |
| `04_2025_E_SelfAiming/`（`Result/` `方法及参考/`） | `07_contest/2025_E_self_aiming/`（`result/` `methods_reference/`） |
| `绘制图像/` | `07_contest/laser_drawing/` |
| `04_2025_E_SelfAiming/方法及参考/NUEDC-2025-E-master/` | `other_boards/openmv/nuedc_2025_e/` |
| `00_Reference/STM32/OLED/CODE/` | `other_boards/stm32/oled_display/CODE/` |
| `00_Reference/STM32/Serial port packet/` | `other_boards/stm32/serial_packet/` |
| `2023 - green/2023 - green/`（在 `K230参考/` 下） | `other_boards/stm32/yahboom_2023_green/2023 - green/` |
| `2023 - red/2023 - red/`（在 `K230参考/` 下） | `other_boards/stm32/yahboom_2023_red/2023 - red/` |
| `06_practice/07_pc_serial_monitor.py` | `pc_tools/serial_plot_monitor.py` |
| `06_practice/09_offline_threshold_WIP.py` | `other_boards/maixpy/offline_threshold_tuner.py` |
| `02_data_collection/04_uart_rx_tx.c` | `other_boards/stm32/snippets/uart_rx_tx.c` |

### 5.2 文件级

#### `01_basics/`

| 旧名 | 现名 |
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

#### `02_data_collection/`

| 旧名 | 现名 |
| --- | --- |
| `01_拍摄单个照片.py` | `01_capture_single.py` |
| `02_连续拍摄100张照片.py` | `02_capture_burst.py` |
| `03_UART串口通信.py` | `03_uart_test.py` |
| `05_数据收集.py` | `05_data_collect.py` |

#### `03_ai_demos/`

| 旧名 | 现名 |
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

#### `04_number_classification/`

| 旧名 | 现名 |
| --- | --- |
| `Data/Number image/1.png`…`8.png` | `data/test_images/1.png`…`8.png` |
| `Data/dataset/` | `data/dataset/` |
| `Code/` | `code/` |
| `Docs/README.pdf` | `docs/README.pdf` |
| `mp_deployment_source/` | 原名保留（硬编码路径） |
| `Code/v1.2.2/cls_{image,video}_1_2_2.py`、`Code/v1.3/cls_{image,video}_1_3.py` | 原名保留（平台导出件） |

#### `05_cv_lite/`

| 旧名 | 现名 |
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
| `rgb888_find_rectangels.py`（拼写错） | `rgb888_find_rectangles.py` |
| `grayscale_find_*.py`、`rgb888_{calc_histogram_1,find_blobs,find_circles,find_edges,white_balance_*}.py` | 原名保留（11 个） |

#### `06_practice/`

| 旧名 | 现名 |
| --- | --- |
| `1.Module.py` | `01_all_in_one.py` |
| `2.按键控制切换界面.py` | `02_key_switch_ui.py` |
| `3.内外框矩形识别.py` | `03_nested_rect.py` |
| `4.三角形识别.py` | `04_triangle.py` |
| `5.多边形识别_基于线段.py` | `05_polygon_from_lines.py` |
| `6.曲线识别（有问题）.py` | `06_curve_recognition_WIP.py` |
| `8,颜色巡线.py` | `08_color_line_following.py` |
| `颜色巡线仿真.html` | `08_line_following_sim.html` |
| `LVGL屏幕/1，LVGL demo.py` | `lvgl/01_lvgl_demo.py` |
| `LVGL屏幕/2，LVGL touch demo.py` | `lvgl/02_lvgl_touch.py` |
| `LVGL屏幕/3，LVGL touch demo freetype.py` | `lvgl/03_lvgl_freetype.py` |
| `LVGL屏幕/first.py` | `lvgl/first.py`（原名保留） |

#### `07_contest/2021_F_drug_car/`

| 旧名 | 现名 |
| --- | --- |
| `赛题K230/01_2021_F_DrugCar/`（未被 git 跟踪） | `07_contest/2021_F_drug_car/` |

#### `07_contest/2023_E_laser/`

| 旧名 | 现名 |
| --- | --- |
| `2023年E题基础部分.py` | `basic_part.py` |
| `K230.py` | `k230_full.py` |
| `main（高帧率）.py` | `main_high_fps.py` |
| `ERROR/ERROR1.PY`…`ERROR4.py` | `error/error1.py`…`error4.py` |
| `参考/main.py` | `reference_gimbal/main.py` |
| `参考/云台驱动.py` | `reference_gimbal/gimbal_driver.py` |
| `参考/发挥部分.py` | `reference_gimbal/advanced_part.py` |
| `参考/基础34题.py` | `reference_gimbal/basic_tasks_34.py` |
| `参考/摄像头追踪测试代码.py` | `reference_gimbal/camera_track_test.py` |
| `示例代码/get_square.py` | `sample_code/get_square.py` |
| `示例代码/red_light.py` | `sample_code/red_light.py` |
| `示例代码/green.py` | `other_boards/openmv/2023_laser/green.py` |
| `示例代码/red.py` | `other_boards/openmv/2023_laser/red.py` |
| `合集/K230 基本.py` | `variants/k230_basic.py` |
| `合集/K230 基本 - 副本.py` | `variants/k230_basic_variant2.py`（不是副本） |
| `合集/K230（基础题完成）.py` | `variants/k230_basic_done.py` |
| `合集/K230 （初级）.py` | `variants/k230_entry.py` |
| `合集/K230 （铅笔激光标点）.py` | `variants/k230_pencil_mark.py` |
| `合集/yedan.py` | `variants/yedan.py` |

#### `07_contest/2024_E_tic_tac_toe/`

| 旧名 | 现名 |
| --- | --- |
| `Three-piece chess.py` | `main_tic_tac_toe.py` |
| `2024-E-master.py` | `skeleton_incomplete.py`（名字带 master，实为空壳） |

#### `07_contest/2025_E_self_aiming/`

| 旧名 | 现名 |
| --- | --- |
| `Result/main（可阈值调节高帧）.py` | `result/main_thresh_ui_fast.py` |
| `Result/main（可阈值调节高识别）.py` | `result/main_thresh_ui_accurate.py` |
| `Result/main（多限制条件）.py` | `result/main_multi_constraint.py` |
| `方法及参考/迭代版本/25-master（find_rect）.py` | `methods_reference/iterations/use_find_rects.py` |
| `方法及参考/迭代版本/25-master1（自定义矩形判断）.py` | `methods_reference/iterations/custom_rect_check.py` |
| `方法及参考/迭代版本/25-master（自定义矩形判断）.py` | `methods_reference/iterations/custom_rect_check_dup.py` |
| `方法及参考/迭代版本/25电赛E题3(1).py` | `methods_reference/iterations/cvlite_variant.py` |
| `方法及参考/迭代版本/云台找矩形（开运算） copy.py` | `methods_reference/iterations/gimbal_rect_opening.py` |
| `方法及参考/迭代版本/云台找矩形（投票选矩形）.py` | `methods_reference/iterations/gimbal_rect_voting.py` |
| `方法及参考/迭代版本/云台找矩形（激光点的预测） copy.py` | `methods_reference/iterations/gimbal_rect_predict_v2.py` |
| `方法及参考/迭代版本/云台找矩形（激光点的预测）.py` | `methods_reference/iterations/gimbal_rect_predict.py` |
| `方法及参考/迭代版本/云台找矩形（矩形ROI框定）.py` | `methods_reference/iterations/gimbal_rect_roi.py` |
| `方法及参考/ERROR/ERROR1.py`、`ERROR2.py` | `methods_reference/error/error1.py`、`error2.py` |

#### `07_contest/laser_drawing/`

| 旧名 | 现名 |
| --- | --- |
| `1.画三角形.py` | `01_triangle.py` |
| `1.画三角形（调整曝光后）.py` | `02_triangle_exposure.py` |
| `2.绘制圆形.py` | `03_circle.py` |
| `3.五角星.py` | `04_pentagram.py` |
| `4.绘制数字.py` | `05_digits_EMPTY.py`（0 字节） |
| `5.贝塞尔曲线.py` | `06_bezier.py` |
| `6,UI界面调试.py` | `07_ui_debug.py` |
| `ui_simulation.html` | `ui_simulation.html`（原名保留） |

#### `other_boards/`

| 旧名 | 现名 |
| --- | --- |
| `06_practice/09_offline_threshold_WIP.py` | `maixpy/offline_threshold_tuner.py` |
| `07_contest/2023_E_laser/sample_code/{green,red}.py` | `openmv/2023_laser/{green,red}.py` |
| `07_contest/2025_E_self_aiming/methods_reference/NUEDC-2025-E-master/` | `openmv/nuedc_2025_e/` |
| `07_contest/reference/stm32/OLED/CODE/` | `stm32/oled_display/CODE/` |
| `07_contest/reference/stm32/Serial port packet/` | `stm32/serial_packet/` |
| `07_contest/2023_E_laser/yahboom_reference/2023 - green/2023 - green/` | `stm32/yahboom_2023_green/2023 - green/` |
| `07_contest/2023_E_laser/yahboom_reference/2023 - red/2023 - red/` | `stm32/yahboom_2023_red/2023 - red/` |
| `02_data_collection/04_uart_rx_tx.c` | `stm32/snippets/uart_rx_tx.c` |

## 6. 提交哈希与历史

- **正文里不再写提交哈希。** 旧文档里有 60 处引用了 `89e6ffc`、`28b5f40`、`f2d0a64`、`78cdb53`，这些都不在当前 `main` 上（在前两个整理分支里），照抄会在本地 `git show` 时报 `unknown revision`。
- 要追一个文件的历史，用 `git log --follow --oneline -- 路径`；要看某次改名的完整差异，用 `git log --follow --stat`。
- 仓库当前历史里，与结构整理相关的是 `8d83380`…`35da7a7` 这一串（目录改名）和 `7a590a3`（根 README + docs 初版）；后续修改以 `git log` 为准，不在文档里枚举。

## 7. 许可与出处

| 内容 | 来源 | 许可 / 要求 |
| --- | --- | --- |
| 作者自写代码 | 本仓库作者 | 根 README 声明 MIT；**仓库根目录还没有 `LICENSE` 文件**，要正式发布建议补一份 |
| `03_ai_demos/` 17 个 | 立创庐山派 wiki 的 AI Demo 页 | 保留出处；`05_object_tracking.py` 例外，来自 01Studio |
| `05_cv_lite/` 27 个 | 嘉楠官方 `/sdcard/examples/23-CV_Lite/` 例程 | 保留出处；模块文档自 v1.4 起，v1.3 文档树里没有 |
| `04_number_classification/code/*`、两处 `mp_deployment_source/` | 嘉楠在线训练平台导出件 | 保留文件名，勿改 |
| `07_contest/reference/basic_gpio/`（12 个） | 立创·庐山派官方例程 | 保留文件头 |
| `07_contest/reference/image_recognition/`（12 个） | 10 个立创 + 2 个 01Studio（`9，物体检测`、`10，字符识别`，文件头写明） | 保留文件头 |
| `07_contest/reference/yahboom_ported/`（4 个） | 亚博例程 | 其中 1 个需要 `ybUtils` 包 |
| `07_contest/2023_E_laser/sample_code/` | 亚博 | 需要 `ybUtils` |
| `07_contest/2023_E_laser/yahboom_reference/` | 第三方方案，署名 Kongcheng，Apache-2.0 | **保留 `LICENSE` 与 `ReadMe.txt` 署名** |
| `07_contest/2023_E_laser/basic_part.py` | B 站教程「学不会电磁场」 | 文件头保留署名 |
| `07_contest/2023_E_laser/reference_gimbal/main.py` | 文件头署「立创·庐山派-K230-CanMV（最终版）」 | 是否官方例程**未核实**，按"不改"处理 |
| `other_boards/openmv/nuedc_2025_e/` | 程欢欢，MIT | 保留 `LICENSE` |
| `other_boards/openmv/2023_laser/` | 未署名 | 来源**未核实** |
| `NUEDC_TOPIC-master/` | 左岚整理的电赛真题档案 | 其 README 声明 MIT，但**目录里没有 `LICENSE` 文件**；引用时注明来源 |
| `04_number_classification/data/dataset/`（800 张） | 作者自采（`02_capture_burst.py` 产出） | 自己拍的，可自由使用 |

## 8. `.gitignore` 与仓库体积

| 现象 | 影响 | 建议 |
| --- | --- | --- |
| `deploy_config.json` 被忽略（`.gitignore:13`） | 新克隆只有 kmodel、没有配置，8 个部署脚本读它会立刻失败 | 要么 `git add -f` 两份配置，要么在目录 README 里写清"自己从平台导出" |
| `det_results/`、`cls_results/` 被忽略 | `det_results/` 在磁盘上并不存在 | 文档里不要再引用"35 张检测结果图" |
| `!Data/Number image/*.png`、`!Data/dataset/**/*.jpg` | 目录已改成 `data/`，这两条**谁也不匹配** | 改成实际路径，或删掉（目前没有 `*.jpg` 忽略规则，数据集才没丢） |
| `other_boards/stm32/**/.pack/` | 1310 个文件、约 156 MB，全部在版本库里 | 不影响正确性；要瘦身可单独处理，别顺手 `git rm` |
| `*.kmodel`（2 个） | 04 的 2.6 MB + 2025 的 7.2 MB，已被跟踪 | 保持跟踪：没有它们，部署脚本无从验证 |

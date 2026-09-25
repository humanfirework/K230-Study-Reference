# 04_number_classification —— 一个完整的"数据 → 模型 → 上板"工程

这是全仓库唯一一条**闭环走通了的** AI 路：800 张自己采的图 → 一个训好的 2.6 MB kmodel → 四个部署脚本（覆盖 v1.2.2 与 v1.3 两代固件）。它值钱不在于识别 8 个数字有多难，而在于**它是完整的**，你能在这一个目录里把整条链看完，不用在四个目录之间跳。
走完你应该能：把一份 kmodel + `deploy_config.json` 部署上板并解释配置里每个字段被谁读；说清 `ai2d → kpu → softmax` 这三步在 v1.2.2 脚本里各自的手续；判断官方给的"高度封装版"和"完整代码版"该读哪个、该跑哪个；以及——最重要的一件——**知道这条路里"训练"那一环本仓库是空的**，并且知道去哪儿补。

## ⚠️ 仓库最大的内容缺口：训练这一步没有任何文档

这条链的三环，现状是：

| 环节 | 状态 | 依据 |
| --- | --- | --- |
| **采数据** | ✅ 有据可查 | `../02_data_collection/02_capture_burst.py` 的 `prefix`/`class_lst`/`compress(95)`/480×320 与 `data/dataset/` 里 800 张图的文件名、格式、分辨率逐项对得上（对照过程见 `../02_data_collection/README.md`） |
| **训练** | ❌ **完全没有** | 目录里搜不到任何训练脚本、超参记录、数据集划分、训练曲线、混淆矩阵。`*.pt` / `*.onnx` / `train.py` / `nncase.*` 一个都没有 |
| **部署** | ✅ 完整 | `code/` 四个脚本 + `mp_deployment_source/` + `docs/README.pdf`（嘉楠官方部署教程，2 页） |

kmodel 是在**嘉楠的在线训练平台**上训出来的，不是本地训的。三条证据：
1. `mp_deployment_source/can2_10.0l_20250704203609.kmodel` 这个文件名是平台的导出命名格式（模型族 `can2` + 精度/轮次标记 `10.0l` + 导出时间戳 `20250704 2036:09`），手写脚本不会产出这种名字。
2. `docs/README.pdf` 开头就写着"部署包内包括转换的 kmodel、部署配置文件 deploy_config.json 以及对应任务的部署脚本" —— 这正是平台导出包的三件套，README.pdf 本身也是包内自带文件。
3. 四个脚本一律从 `deploy_config.json` 读 `kmodel_path` / `categories` / `confidence_threshold` / `img_size` / `num_classes` 这五个键（`code/v1.3/cls_video_1_3.py:40–44`、`code/v1.2.2/cls_video_1_2_2.py:63–67`），这个键集就是平台的导出约定，不是自己设计的。

所以 `deploy_config.json`（记录着 `model_type: can2`、`nncase_version 2.9.0`、8 个类别 `"1".."8"`、输入 224×224）就是**那份训练记录的唯一残留** —— 而它恰好因为 `.gitignore` 没进版本库，见下面的已知问题第一条。**这份配置现在既不在盘上也不在库里，等于这个工程丢掉了它自己唯一的元数据。**

补这一段要看外部资源：
- 嘉楠官方文档 <https://www.kendryte.com/k230_canmv/zh/main/index.html>（⚠️ 左侧版本选择器切到你的固件版本再抄）
- 01Studio 的在线训练教程 <https://wiki.01studio.cc/docs/canmv_k230/machine_vision/train/>
- AI Cube（本地导出 nncase 工具链）：<https://www.kendryte.com/ai_docs/>

## 文件清单

| 文件 | 演示什么 | 关键 API | 备注 |
| --- | --- | --- | --- |
| `code/v1.2.2/cls_image_1_2_2.py` | **单张图分类，全程手写**：读图→HWC 转 CHW→ai2d→kpu→softmax→画图→存结果 | `image.Image(path)` `to_numpy_ref()` `reshape/transpose/copy` `nn.ai2d()` `nn.kpu()` | 145 行；结果写回 `/sdcard/mp_deployment_source/cls_result.jpg` |
| `code/v1.2.2/cls_video_1_2_2.py` | **视频流分类，全程手写**，双通道 + OSD 层 + UART 上报 | `Sensor` chn0→VO / chn2→`PIXEL_FORMAT_RGB_888_PLANAR`、`sensor.bind_info()` `Display.bind_layer()` `image.ARGB8888` OSD、`uart2.write('!'+label+'@')` | 191 行；含 `softmax()` / `sigmoid()` 两个手写函数；**这份是本目录的教学价值顶点** |
| `code/v1.3/cls_image_1_3.py` | 同一件事的 v1.3 写法 | `from libs.PlatTasks import ClassificationApp` `read_image()` `cls_app.config_preprocess()` `cls_app.run(img_chw)` `cls_app.draw_result()` | **63 行**（对比 v1.2.2 的 145 行） |
| `code/v1.3/cls_video_1_3.py` | 视频版 v1.3 | `PipeLine(rgb888p_size=…, display_mode=…)` + `ClassificationApp` | **75 行**（对比 191 行）；`display_mode = "lt9611"`（HDMI），只有屏的要先改成 `"lcd"` |
| `mp_deployment_source/can2_10.0l_20250704203609.kmodel` | 训好的分类模型，2,676,264 字节（约 2.6 MB） | —— | ⚠️ **所在目录名不能改**，见下文 |
| `mp_deployment_source/deploy_config.json` | 平台导出的部署配置 | —— | ⚠️ **不在版本库里**，见已知问题第一条 |
| `data/dataset/1..8/` | 训练集：8 类 × 100 张 = **800 张**，实测全部 **480×320 baseline JPEG** | —— | 文件名 `batch_1__one_1.jpg` … 见下 |
| `data/test_images/1..8.png` | 8 张**单图推理的自检输入**，文件名就是类别标签 | `cls_image_1_3.py` 之类的输入 | 实测尺寸 419×554 ~ 482×576 的 **RGBA PNG**：既不是 480×320、也不是 JPEG，**和训练集不是一套东西** |
| `docs/README.pdf` | 嘉楠官方《MicroPython 部署教程》，2 页 | —— | 平台导出包自带的原件；**只讲部署，不讲训练** |

## 数据集事实（全部实测）

- `data/dataset/` 下 8 个目录 `1/`…`8/`，**每个正好 100 张，合计 800 张**。
- 每张都是 **480×320** JPEG（`file` 与 PIL 两种方法核对过）。
- 文件名是 `batch_1__<英文数词>_<1..100>.jpg`（**双下划线**：`prefix = "batch_1_"` 自带一个，格式串 `"{}_{}_{}.jpg"` 又补一个）。目录号 ↔ 数词：`1=one`、`2=two`、`3=three`、`4=four`、`5=five`、`6=six`、`7=seven`、`8=eight`。
- 采集脚本 `class_lst` 里其实有 10 项（还有 `nine`、`zero`），**这两类没进最终数据集** —— 8 这个数字是最终选定值，不是采到的上限。
- `data/test_images/` 那 8 张是**从别处来的**（尺寸、长宽比、色彩模式、文件格式全都不一致），它们只是"拿一张干净的数字图去戳一下模型"的自检输入。旧名 `Data/Number image/`，改名成 `test_images` 就是为了让这件事写在路径里。

## 该读哪一版，该跑哪一版

**读 v1.2.2，跑 v1.3。** 这不是偏好，`docs/README.pdf` 官方自己就是这么定位的（原文）：

> 以 1_2_2 结尾的脚本为 1.2.2 以后固件使用，该代码包含完整的步骤，但代码比较冗长，**扩展性较好**；
> 以 1_3 结尾的脚本为 1.3 以后固件使用，该代码**高度封装**，代码简单易用，但**扩展性较差**。

具体差别在哪，看同一件事的两种写法：

| 步骤 | `cls_video_1_2_2.py`（191 行，看得见） | `cls_video_1_3.py`（75 行，看不见） |
| --- | --- | --- |
| 取 AI 输入帧 | 自己开 chn2、设 `PIXEL_FORMAT_RGB_888_PLANAR`、判 `rgb888p_img.format() == image.RGBP888` | `pl.get_frame()` |
| 预处理 | 自己 `nn.ai2d()` + `set_dtype(NCHW, NCHW, uint8, uint8)` + `set_resize_param(tf_bilinear, half_pixel)` + `ai2d.build([1,3,360,640], [1,3,H,W])` | `cls_app.config_preprocess()` |
| 显示 | 自己 `sensor.bind_info(chn=CAM_CHN_ID_0)` + `Display.bind_layer(**info, layer=LAYER_VIDEO1)` + 单独建一张 `ARGB8888` 的 `osd_img` 画在 `LAYER_OSD3` | `pl.show_image()` |
| 推理 | `kpu.set_input_tensor()` → `kpu.run()` → 遍历 `kpu.outputs_size()` 取 `get_output_tensor(i).to_numpy()` | `cls_app.run(img)` |
| 判定 | **手写** `softmax()`（多类，`num_classes > 2`）和 `sigmoid()`（二分类），再 `np.argmax` | 在 `ClassificationApp` 里面 |
| 输出 | 自己 `uart2.write('!' + label + '@')` | 无（只有画面） |

v1.2.2 那份是**赛题里真正要用的形状**：你要改后处理（比如加"连续 N 帧一致才认"）、要改上报协议、要把输入换成 640×360 省帧率，全都得看得见她替 `ClassificationApp` 做掉的那些事。v1.3 那份扩展性差，改不动的时候你只能整个换掉。
一句话：**v1.2.2 是课本，v1.3 是壳**。手上是 v1.3+ 固件就照 `docs/README.pdf` 跑 `1_3`，遇到"它替我做了什么"就回 `1_2_2` 里查同名步骤。

## ⚠️ `mp_deployment_source/` 这个名字不能改

CanMV 的部署代码是按**硬编码约定**找它的：四个脚本里第一行路径就是 `root_path = "/sdcard/mp_deployment_source/"`（`cls_image_1_3.py:31`、`cls_video_1_3.py:36`、两个 `1_2_2` 的 `29`/`11` 行）。`docs/README.pdf` 也明写"将 `mp_deployment_source` 文件夹拷贝到盘符 `CanMV/sdcard/` 目录下"。
**改名不会有任何报错，只会 `FileNotFoundError`，而且报错的行是读 json 那一行，看不出是目录名的锅。** 这正是本仓库在这一个目录里停止英文化的原因：`mp_deployment_source/`、`cls_image_1_3.py` 这类名字是平台导出件的一部分，保持原样才能让"新导出的包"和"仓库里这份"直接 diff。
（同理 `data/dataset/1..8` 的目录名也不能动 —— 数字目录名就是 8 个类别标签。）

## 旧名 → 新名

⚠️ **先读一条事实**：这次重命名把 `04_Number_Classification` 改成 `04_number_classification`（外加 `Code/`→`code/`、`Data/`→`data/`、`Docs/`→`docs/`）在 Windows 上**只改到了一半** —— 这台机器 `git config core.ignorecase = true`，纯大小写的目录改名 Git 看不见。实测 `git ls-tree -r HEAD` 里这个目录仍然记作 `04_Number_Classification/Code/…`、`…/Data/…`、`…/Docs/…`。
所以：**在 Linux/macOS 上 clone 出来会是旧的大小写**，`code/` 打不开、脚本里那些相对路径引用也会断。下面表格右列是本仓库磁盘上的现状（也是你想要的目标），左列是 git 记录。

`04_Number_Classification/` → `04_number_classification/`。四个脚本文件名与 `mp_deployment_source/` 本次**未改名**（理由见上一节）。

| 旧名 | 新名（磁盘现状 / git 索引记录） |
| --- | --- |
| `Data/Number image/1.png` … `8.png` | `data/test_images/1.png` … `8.png`（**唯一真正落到 git 的重命名**） |
| `Data/dataset/` | `data/dataset/`（git 仍记作 `Data/dataset/`） |
| `Code/` | `code/`（git 仍记作 `Code/`） |
| `Docs/README.pdf` | `docs/README.pdf`（git 仍记作 `Docs/README.pdf`） |
| `mp_deployment_source/` | 原名保留（**有意**） |
| `Code/v1.2.2/cls_{image,video}_1_2_2.py`、`Code/v1.3/cls_{image,video}_1_3.py` | 原名保留（平台导出件的命名约定） |

## 练习建议

1. **先做一次"配置字段 → 代码行"的对账。** 拿官方包（或自己随便导一个）的 `deploy_config.json`，逐个字段在 `code/` 里找到读它的那一行。
   完成标准：五张卡片 —— `kmodel_path` `categories` `confidence_threshold` `img_size` `num_classes`，每张写上"被哪个文件的哪一行读、读进哪个变量、这个变量最后被谁用"。`img_size` 那两个下标谁当宽谁当高必须说清（`cls_video_1_2_2.py:78` 里 `[1, 3, model_input_size[1], model_input_size[0]]` —— NCHW 是**高在前**，`img_size` 是**宽在前**，这里做了一次互换，抄错了就是推理结果全乱）。
2. **在 v1.2.2 视频版里插一行 UART，把分类结果送出去。** 板子 115200 接 PC，`docs/README.pdf` 的上板流程走完，让 `cls_video_1_2_2.py` 跑起来（`display_mode` 是 `"lcd"`，本板可直接用）。
   完成标准：PC 串口助手上能看到 `!<数字>@` 形式的帧（`cls_video_1_2_2.py:170`），且换数字时字段跟着变。这一条做完，你就拥有了一份"K230 → MCU 的分类结果协议"，`../other_boards/stm32/` 那半边能直接接。
3. **用 `data/test_images/` 那 8 张做端到端自检。** 逐张拷成 `/sdcard/test.jpg`（v1.3 读的是这个路径，见 `cls_image_1_3.py:27`），跑 `cls_image_1_3.py`。
   完成标准：8 张至少对 7 张，并且**能对每张说出 `score` 数量级**。少于 7 张先怀疑预处理，别怀疑模型 —— 这 8 张是 RGBA PNG、尺寸和训练集完全不同（见文件清单），这是一个真实的分布偏移测试，不是模型不行。
4. **给这个工程补一份它最缺的东西：`TRAINING.md`。** 只写你自己复现出来的部分：在哪个平台、数据集怎么上传（800 张目录结构原样打包？要不要重命名成数字目录？）、类别数怎么填、输入分辨率、导出的 `deploy_config.json` 长什么样。
   完成标准：另开一份 `deploy_config.json` 和现有的 `can2_10.0l_…kmodel` 的字段结构一致（键名一个不多一个不少），并且你写清了"**采图脚本里的英文数词目录名是怎么变成 1..8 数字目录名的**"——那是当前唯一没有任何文档记录的一步。

## 已知问题 / 注意事项

- ⚠️⚠️ **`deploy_config.json` 不在版本库里，因此按本目录说明跑任何一步都会立刻失败。** 根 `.gitignore` 的 `# K230 specific` 段里有一条 `deploy_config.json`（同段还有 `cls_results/` `det_results/`），所以它是**被忽略规则排掉**的：`git ls-files | grep deploy_config` 无结果，全盘 `find` 也搜不到这个文件。
  后果：四个脚本第一句都是读它（`root_path + "/deploy_config.json"` 或 `root_path + "deploy_config.json"`），文件不在 → 立刻 `OSError`，连模型都不会被加载。
  **一行修法**：删掉 `.gitignore` 里那一条，或者 `git add -f 04_number_classification/mp_deployment_source/deploy_config.json`。本仓库刻意没动 `.gitignore`（规则改了会影响别的目录），请自己动手 —— **并且先自己造一份这个 json**，因为仓库里也没有它的原件可恢复。
- ⚠️ **`mp_deployment_source/` 目录名硬编码，不能改**（专节讲过）。同一条约定还牵连两个测试图路径，它们**不一致**：
  - `cls_image_1_3.py:27` 读 `/sdcard/test.jpg`（与 `docs/README.pdf` 的说明一致）；
  - `cls_image_1_2_2.py:13` 读 `root_path + "test.jpg"`，即 `/sdcard/mp_deployment_source/test.jpg`（**和 PDF 的说明差一层目录**）。
  同一份导出包里两代脚本要求图放在不同位置，`README.pdf` 只写了其中一种。照 PDF 放图，v1.2.2 那份会报文件找不到。
- ⚠️ **四个脚本都没有 `os.exitpoint()`，也都没有顶层 `try/finally`。** 两个 `1_2_2` 里的 `try:`（`cls_image:33`、`cls_video:38`）是包在 `read_deploy_config()` 的 JSON 解析外面的局部 try，不是主循环的。于是和 `../05_cv_lite/` 完全同样的病：`cls_video_1_2_2.py` 的收尾（`sensor.stop()` / `Display.deinit()` / `MediaManager.deinit()` / `nn.shrink_memory_pool()`，175–186 行）全在裸 `while True:` 之后，**永远执行不到**，IDE 停止一次就得断电一次。修法模板见 [../05_cv_lite/README.md](../05_cv_lite/README.md) 的"关于跑一次就要断电"一节。
- **`cls_video_1_3.py:30` 的 `display_mode = "lt9611"` 是 HDMI**（1920×1080）。只有庐山派那块 800×480 MIPI 屏的话必须改成 `"lcd"`，否则要么黑屏要么报分辨率不支持。同一份 v1.3 的注释（28–29 行）已经把可选值列全了：`'hdmi' 'lcd' 'lt9611' 'st7701' 'hx8399'`，并且说明 `'lcd'` 默认就是 `'st7701'` 800×480 —— 和 `../01_basics/` 里那批 `DISPLAY_MODE` 分支是自洽的。
- **`cls_video_1_2_2.py:166` 藏了一个写死的判定阈值 `score >= 0.7`。** OSD 上显不显示结果、UART 发不发消息，用的是这个 0.7，**不是** `deploy_config.json` 里的 `confidence_threshold`（后者只在 143 行决定 `cls_idx` 是不是 -1）。也就是说改配置里的置信度门限，会出现"图上有字但 UART 不发消息"或反之的怪现象。这是全目录最值得注意的一处双阈值。
- **`cls_image_1_2_2.py` 一张图读了四遍。** 每个分支都重新 `image.Image(image_path).to_rgb565()`（99、117、127 行），加上开头 `read_img(image_path)` 里那次解码，一张图共四次；结果图还会 `image_draw.save(root_path + "cls_result.jpg")`（108、122、136 行）**写进 `mp_deployment_source/`**。想干净一点就自己把 `image_draw` 提到分支外面。
- **`read_deploy_config()` 里的 `except ValueError` 有问题**（`cls_image_1_2_2.py` / `cls_video_1_2_2.py` 各一处）：JSON 解析失败只 `print("JSON 解析错误:", e)`，然后 `return config` —— 而 `config` 此时**根本没被赋值**，于是抛 `UnboundLocalError`，把真正的错因盖掉。想快速判断 json 是不是坏了，直接看串口打出来的是哪个异常名。
- **`.gitignore` 里还有两条针对旧路径的失效豁免**：`!Data/Number image/*.png`（目录已改名 `data/test_images/`）和 `!Data/dataset/**/*.jpg`（用的是旧大小写）。这两行现在**匹配不到任何文件**。目前没造成损失，因为 `.gitignore` 从头到尾没有一条规则忽略 `*.jpg` / `*.png`，那 808 个图像文件是靠"没人忽略它们"而不是靠这两行豁免被跟踪的 —— 哪天你加了 `*.png` 之类的规则，这两行不会救你。
- **v1.2.2 那两份依赖 `nncase_runtime` 的 `nn.kpu()` 老式接口，v1.3 已换 `LiteEvaluator`。** 所以严格说：**"读 v1.2.2"这件事在 v1.3+ 固件上也是跑不动的**，它是设计参考而不是可执行参考。真要在 v1.3 上做定制后处理，去官方文档里找 v1.3 版的 `kpu` 等价写法（`03_ai_demos/` 那份技术栈是 v1.2 的，别拿它当 v1.3 的答案）。
- **2.6 MB 的 kmodel 被 Git 当文本处理不了，但也没被忽略**，`git ls-files` 里能看到它。想缩小仓库体积可以考虑 Git LFS —— 但**先确认 clone 之后 `/sdcard/mp_deployment_source/` 里还有没有那个文件**，这份工程的可用性全押在它和那份（缺失的）json 上。

# -*- coding: utf-8 -*-
'''
Script: deploy_det_image.py
脚本名称：deploy_det_image.py

Description:
    This script performs object detection on a single image.
    It loads an image, performs inference using a pre-trained Kmodel,
    and displays the detection results (bounding boxes, class labels).

    The model configuration is loaded from the Canaan online training platform via a JSON config file. Please prepare the test image yourself.

脚本说明：
    本脚本对单张图像执行目标检测。它加载图像，使用预训练的 Kmodel 进行推理，并显示检测结果（边界框、类别标签）。

    模型配置文件通过 Canaan 在线训练平台从 JSON 文件加载。 请自行准备测试图片。

Author: Canaan Developer
作者：Canaan 开发者
'''


import os, gc
from libs.PlatTasks import DetectionApp
from libs.Utils import *

# Load image in CHW format for inference and RGB888 for display
# The image dimensions are used for setting the input size for the inference model
img_chw, img_rgb888 = read_image("/sdcard/test.jpg")
rgb888p_size = [img_chw.shape[2], img_chw.shape[1]]

# Set root directory path for model and config
root_path = "/sdcard/mp_deployment_source/"

# Load deployment configuration
deploy_conf = read_json(root_path + "/deploy_config.json")
kmodel_path = root_path + deploy_conf["kmodel_path"]              # KModel path
labels = deploy_conf["categories"]                                # Label list
confidence_threshold = deploy_conf["confidence_threshold"]        # Confidence threshold for filtering boxes
nms_threshold = deploy_conf["nms_threshold"]                      # NMS threshold for box suppression
model_input_size = deploy_conf["img_size"]                        # Model input size
nms_option = deploy_conf["nms_option"]                            # NMS strategy,Intra-class(True) NMS,Inter-class NMS(False)
model_type = deploy_conf["model_type"]                            # Detection model type
anchors = []                                                      # Load anchor settings if the model type requires them
if model_type == "AnchorBaseDet":
    anchors = deploy_conf["anchors"][0] + deploy_conf["anchors"][1] + deploy_conf["anchors"][2]

# Inference configuration
inference_mode = "image"                                          # Inference mode: 'image'
debug_mode = 0                                                    # Debug mode flag

# Initialize object detection application
det_app = DetectionApp(inference_mode,kmodel_path,labels,model_input_size,anchors,model_type,confidence_threshold,nms_threshold,rgb888p_size,rgb888p_size,debug_mode=debug_mode)

# Configure preprocessing for the model
det_app.config_preprocess()

# Run inference on the loaded image
res = det_app.run(img_chw)

# Draw detection results (bounding boxes and labels) on the image
det_app.draw_result(img_rgb888, res)

# Prepare image for IDE display
img_rgb888.compress_for_ide()

# Cleanup: De-initialize detection app and Run garbage collection to free memory
det_app.deinit()
gc.collect()


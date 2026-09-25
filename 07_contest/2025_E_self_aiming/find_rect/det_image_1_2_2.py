import gc
import os

import aicube
import image
import nncase_runtime as nn
import ujson
import ulab.numpy as np
from libs.PipeLine import ScopedTiming
from libs.Utils import *
from media.display import *
from media.media import *
from media.sensor import *

root_path = "/sdcard/mp_deployment_source/"  # root_path要以/结尾
config_path = root_path + "deploy_config.json"
image_path = root_path + "test.jpg"
deploy_conf = {}
debug_mode = 1


def read_img(img_path):
    img_data = image.Image(img_path)
    img_data_rgb888 = img_data.to_rgb888()
    img_hwc = img_data_rgb888.to_numpy_ref()
    shape = img_hwc.shape
    img_tmp = img_hwc.reshape((shape[0] * shape[1], shape[2]))
    img_tmp_trans = img_tmp.transpose()
    img_res = img_tmp_trans.copy()
    img_return = img_res.reshape((shape[2], shape[0], shape[1]))
    return img_return


def two_side_pad_param(input_size, output_size):
    ratio_w = output_size[0] / input_size[0]  # 宽度缩放比例
    ratio_h = output_size[1] / input_size[1]  # 高度缩放比例
    ratio = min(ratio_w, ratio_h)  # 取较小的缩放比例
    new_w = int(ratio * input_size[0])  # 新宽度
    new_h = int(ratio * input_size[1])  # 新高度
    dw = (output_size[0] - new_w) / 2  # 宽度差
    dh = (output_size[1] - new_h) / 2  # 高度差
    top = int(round(dh - 0.1))
    bottom = int(round(dh + 0.1))
    left = int(round(dw - 0.1))
    right = int(round(dw - 0.1))
    return top, bottom, left, right, ratio


# 读取deploy_config.json文件
def read_deploy_config(config_path):
    with open(config_path, "r") as json_file:
        try:
            config = ujson.load(json_file)
        except ValueError as e:
            print("JSON 解析错误:", e)
    return config


def detection():
    print("--------------start-----------------")
    # 使用json读取内容初始化部署变量
    deploy_conf = read_deploy_config(config_path)
    kmodel_name = deploy_conf["kmodel_path"]
    labels = deploy_conf["categories"]
    confidence_threshold = deploy_conf["confidence_threshold"]
    nms_threshold = deploy_conf["nms_threshold"]
    model_input_size = deploy_conf["img_size"]
    num_classes = deploy_conf["num_classes"]
    color_four = get_colors(num_classes)
    nms_option = deploy_conf["nms_option"]
    model_type = deploy_conf["model_type"]
    if model_type == "AnchorBaseDet":
        anchors = deploy_conf["anchors"][0] + deploy_conf["anchors"][1] + deploy_conf["anchors"][2]
    strides = [8, 16, 32]

    # ai2d输入输出初始化
    ai2d_input = read_img(image_path)
    frame_size = [ai2d_input.shape[2], ai2d_input.shape[1]]
    ai2d_input_tensor = nn.from_numpy(ai2d_input)
    ai2d_input_shape = ai2d_input.shape
    data = np.ones((1, 3, model_input_size[1], model_input_size[0]), dtype=np.uint8)
    ai2d_output_tensor = nn.from_numpy(data)

    # kpu初始化并加载模型
    kpu = nn.kpu()
    kpu.load_kmodel(root_path + kmodel_name)
    # ai2d初始化
    ai2d = nn.ai2d()
    ai2d.set_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT, np.uint8, np.uint8)
    top, bottom, left, right, ratio = two_side_pad_param(frame_size, model_input_size)
    ai2d.set_pad_param(True, [0, 0, 0, 0, top, bottom, left, right], 0, [114, 114, 114])
    ai2d.set_resize_param(True, nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
    ai2d_builder = ai2d.build(
        [1, 3, ai2d_input_shape[1], ai2d_input_shape[2]], [1, 3, model_input_size[1], model_input_size[0]]
    )
    with ScopedTiming("total", debug_mode > 0):
        # 使用ai2d实现预处理
        ai2d_builder.run(ai2d_input_tensor, ai2d_output_tensor)
        # 设置模型的输入tensor
        kpu.set_input_tensor(0, ai2d_output_tensor)
        # 模型推理
        kpu.run()
        # 获取模型输出
        results = []
        for i in range(kpu.outputs_size()):
            data = kpu.get_output_tensor(i)
            result = data.to_numpy()
            del data
            results.append(result)
        # 后处理
        det_boxes = aicube.anchorbasedet_post_process(
            results[0],
            results[1],
            results[2],
            model_input_size,
            frame_size,
            strides,
            num_classes,
            confidence_threshold,
            nms_threshold,
            anchors,
            nms_option,
        )
        # 绘制结果
        image_draw = image.Image(image_path).to_rgb565()
        if det_boxes:
            for det_boxe in det_boxes:
                x1, y1, x2, y2 = det_boxe[2], det_boxe[3], det_boxe[4], det_boxe[5]
                x, y, w, h = int(x1), int(y1), int(x2 - x1), int((y2 - y1))
                image_draw.draw_rectangle(x, y, w, h, color=color_four[det_boxe[0]][1:])
                label = labels[det_boxe[0]]
                score = str(round(det_boxe[1], 2))
                image_draw.draw_string_advanced(
                    int(x1), int(y1) - 30, 20, label + " " + score, color=color_four[det_boxe[0]][1:]
                )
                print("\n" + label + " " + score)
            image_draw.compress_for_ide()
            image_draw.save(root_path + "det_result.jpg")
        else:
            print("No objects were identified.")
    del ai2d_input_tensor
    del ai2d_output_tensor
    print("---------------end------------------")
    nn.shrink_memory_pool()
    gc.collect()


if __name__ == "__main__":
    detection()

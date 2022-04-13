import os
import time
import json

import torch
from torchvision import transforms
import numpy as np
from PIL import Image

# from src import deeplabv3_resnet50
import torchvision.models as models

from torch.profiler import profile, record_function, ProfilerActivity


def time_synchronized():
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    return time.time()


def main():
    aux = False  # inference time not need aux_classifier
    classes = 20
    # weights_path = "./save_weights/model_29.pth"
    img_path = "./test.jpeg"
    # palette_path = "./palette.json"
    # assert os.path.exists(weights_path), f"weights {weights_path} not found."
    assert os.path.exists(img_path), f"image {img_path} not found."
    # assert os.path.exists(palette_path), f"palette {palette_path} not found."
    # with open(palette_path, "rb") as f:
    #     pallette_dict = json.load(f)
    #     pallette = []
    #     for v in pallette_dict.values():
    #         pallette += v

    # get devices
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print("using {} device.".format(device))

    # create model
    # model = deeplabv3_resnet50(aux=aux, num_classes=classes+1)
    model = models.segmentation.deeplabv3_resnet50(pretrained=True)

    # delete weights about aux_classifier
    # weights_dict = torch.load(weights_path, map_location='cpu')['model']
    # for k in list(weights_dict.keys()):
    #     if "aux" in k:
    #         del weights_dict[k]

    # # load weights
    # model.load_state_dict(weights_dict)
    model.to(device)

    # load image
    original_img = Image.open(img_path)

    # from pil image to tensor and normalize
    data_transform = transforms.Compose([transforms.Resize(520),
                                         transforms.ToTensor(),
                                         transforms.Normalize(mean=(0.485, 0.456, 0.406),
                                                              std=(0.229, 0.224, 0.225))])
    img = data_transform(original_img)
    # expand batch dimension
    img = torch.unsqueeze(img, dim=0)

    model.eval()  # 进入验证模式
    with torch.no_grad():
        with profile(activities=[ProfilerActivity.CPU], record_shapes=True, with_modules=True) as prof:
            with record_function("model_inference"):
                # init model
                img_height, img_width = img.shape[-2:]
                init_img = torch.zeros((1, 3, img_height, img_width), device=device)
                model(init_img)

                t_start = time_synchronized()
                output = model(img.to(device))
                t_end = time_synchronized()
                print("inference+NMS time: {}".format(t_end - t_start))

                prediction = output['out'].argmax(1).squeeze(0)
                prediction = prediction.to("cpu").numpy().astype(np.uint8)
                mask = Image.fromarray(prediction)
                # mask.putpalette(pallette)
                mask.save("test_result.png")
        print(prof.key_averages().table(sort_by="cpu_time_total", row_limit=10))
        print(prof.key_averages(group_by_input_shape=True).table(sort_by="cpu_time_total", row_limit=10))
        print(prof.key_averages().table(sort_by="self_cpu_memory_usage", row_limit=10))
        print(prof.key_averages().table(sort_by="cpu_memory_usage", row_limit=10))
        
        prof.export_chrome_trace("trace.json")


if __name__ == '__main__':
    main()

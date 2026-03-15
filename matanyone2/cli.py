import os
from typing import Annotated

import cv2
import tqdm
import typer
import imageio
import numpy as np
from PIL import Image

import torch
import torch.nn.functional as F

from matanyone2.utils.download_util import load_file_from_url
from matanyone2.utils.inference_utils import gen_dilate, gen_erosion, read_frame_from_videos
from matanyone2.inference.inference_core import InferenceCore
from matanyone2.utils.get_default_model import get_matanyone2_model
from matanyone2.utils.device import get_default_device, safe_autocast_decorator

import warnings
warnings.filterwarnings("ignore")

app = typer.Typer(help="MatAnyone2 video matting inference")


@torch.inference_mode()
@safe_autocast_decorator()
def run_inference(input_path, mask_path, output_path, ckpt_path, n_warmup=10, r_erode=10,
                  r_dilate=10, suffix="", save_image=False, max_size=-1):
    device = get_default_device()

    # download ckpt for the first inference
    pretrain_model_url = "https://github.com/pq-yang/MatAnyone2/releases/download/v1.0.0/matanyone2.pth"
    ckpt_path = load_file_from_url(pretrain_model_url, 'pretrained_models')

    # load MatAnyone model
    matanyone2 = get_matanyone2_model(ckpt_path, device)

    # init inference processor
    processor = InferenceCore(matanyone2, cfg=matanyone2.cfg)

    # inference parameters
    r_erode = int(r_erode)
    r_dilate = int(r_dilate)
    n_warmup = int(n_warmup)
    max_size = int(max_size)

    # load input frames
    vframes, fps, length, video_name = read_frame_from_videos(input_path)
    repeated_frames = vframes[0].unsqueeze(0).repeat(n_warmup, 1, 1, 1)
    vframes = torch.cat([repeated_frames, vframes], dim=0).float()
    length += n_warmup

    # resize if needed
    if max_size > 0:
        h, w = vframes.shape[-2:]
        min_side = min(h, w)
        if min_side > max_size:
            new_h = int(h / min_side * max_size)
            new_w = int(w / min_side * max_size)
            vframes = F.interpolate(vframes, size=(new_h, new_w), mode="area")
            print(f'Resize to {new_h}x{new_w} for processing...')

    # set output paths
    os.makedirs(output_path, exist_ok=True)
    if suffix != "":
        video_name = f'{video_name}_{suffix}'
    if save_image:
        os.makedirs(f'{output_path}/{video_name}', exist_ok=True)
        os.makedirs(f'{output_path}/{video_name}/pha', exist_ok=True)
        os.makedirs(f'{output_path}/{video_name}/fgr', exist_ok=True)

    # load the first-frame mask
    mask = Image.open(mask_path).convert('L')
    mask = np.array(mask)

    bgr = (np.array([120, 255, 155], dtype=np.float32) / 255).reshape((1, 1, 3))
    objects = [1]

    # [optional] erode & dilate
    if r_dilate > 0:
        mask = gen_dilate(mask, r_dilate, r_dilate)
    if r_erode > 0:
        mask = gen_erosion(mask, r_erode, r_erode)

    mask = torch.from_numpy(mask).float().to(device)

    if max_size > 0:
        mask = F.interpolate(mask.unsqueeze(0).unsqueeze(0), size=(new_h, new_w), mode="nearest")
        mask = mask[0, 0]

    # inference start
    phas = []
    fgrs = []
    for ti in tqdm.tqdm(range(length)):
        image = vframes[ti]
        image_np = np.array(image.permute(1, 2, 0))
        image = (image / 255.).float().to(device)

        if ti == 0:
            output_prob = processor.step(image, mask, objects=objects)
            output_prob = processor.step(image, first_frame_pred=True)
        else:
            if ti <= n_warmup:
                output_prob = processor.step(image, first_frame_pred=True)
            else:
                output_prob = processor.step(image)

        mask = processor.output_prob_to_mask(output_prob)

        pha = mask.unsqueeze(2).cpu().numpy()
        com_np = image_np / 255. * pha + bgr * (1 - pha)

        if ti > (n_warmup - 1):
            com_np = np.round(np.clip(com_np * 255.0, 0, 255)).astype(np.uint8)
            pha = np.round(np.clip(pha * 255.0, 0, 255)).astype(np.uint8)
            fgrs.append(com_np)
            phas.append(pha)
            if save_image:
                cv2.imwrite(f'{output_path}/{video_name}/fgr/{str(ti - n_warmup).zfill(4)}.png',
                            com_np[..., [2, 1, 0]])
                cv2.imwrite(f'{output_path}/{video_name}/pha/{str(ti - n_warmup).zfill(4)}.png',
                            pha)

    phas = np.array(phas)
    fgrs = np.array(fgrs)

    imageio.mimwrite(f'{output_path}/{video_name}_fgr.mp4', fgrs, fps=fps, quality=7)
    imageio.mimwrite(f'{output_path}/{video_name}_pha.mp4', phas, fps=fps, quality=7)


@app.command()
def main(
    input_path: Annotated[str, typer.Option("-i", "--input-path",
        help="Path of the input video or frame folder.")],
    mask_path: Annotated[str, typer.Option("-m", "--mask-path",
        help="Path of the first-frame segmentation mask.")],
    output_path: Annotated[str, typer.Option("-o", "--output-path",
        help="Output folder.")] = "results/",
    ckpt_path: Annotated[str, typer.Option("-c", "--ckpt-path",
        help="Path of the MatAnyone2 model.")] = "pretrained_models/matanyone2.pth",
    warmup: Annotated[int, typer.Option("-w", "--warmup",
        help="Number of warmup iterations for the first frame alpha prediction.")] = 10,
    erode_kernel: Annotated[int, typer.Option("-e", "--erode-kernel",
        help="Erosion kernel size on the input mask.")] = 10,
    dilate_kernel: Annotated[int, typer.Option("-d", "--dilate-kernel",
        help="Dilation kernel size on the input mask.")] = 10,
    suffix: Annotated[str, typer.Option(
        help="Suffix to specify different target when saving.")] = "",
    save_image: Annotated[bool, typer.Option("--save-image",
        help="Save output frames.")] = False,
    max_size: Annotated[int, typer.Option(
        help="Downsamples if min(w, h) exceeds this value. -1 means no limit.")] = -1,
):
    """Run MatAnyone2 video matting inference."""
    run_inference(
        input_path=input_path,
        mask_path=mask_path,
        output_path=output_path,
        ckpt_path=ckpt_path,
        n_warmup=warmup,
        r_erode=erode_kernel,
        r_dilate=dilate_kernel,
        suffix=suffix,
        save_image=save_image,
        max_size=max_size,
    )


if __name__ == '__main__':
    app()

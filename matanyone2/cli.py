import os
from typing import Annotated

import typer

import torch

from matanyone2 import MatAnyone2
from matanyone2.inference.inference_core import InferenceCore
from matanyone2.utils.device import safe_autocast_decorator

import warnings
warnings.filterwarnings("ignore")

app = typer.Typer(help="MatAnyone2 video matting inference")


@torch.inference_mode()
@safe_autocast_decorator()
def run_inference(input_path, mask_path, output_path, n_warmup=10, r_erode=10,
                  r_dilate=10, suffix="", save_image=False, max_size=-1):
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    model = MatAnyone2.from_pretrained("PeiqingYang/MatAnyone2")
    processor = InferenceCore(model, device=device)

    os.makedirs(output_path, exist_ok=True)
    processor.process_video(
        input_path=input_path,
        mask_path=mask_path,
        output_path=output_path,
        n_warmup=n_warmup,
        r_erode=r_erode,
        r_dilate=r_dilate,
        suffix=suffix,
        save_image=save_image,
        max_size=max_size,
    )


@app.command()
def main(
    input_path: Annotated[str, typer.Option("-i", "--input-path",
        help="Path of the input video or frame folder.")],
    mask_path: Annotated[str, typer.Option("-m", "--mask-path",
        help="Path of the first-frame segmentation mask.")],
    output_path: Annotated[str, typer.Option("-o", "--output-path",
        help="Output folder.")] = "results/",
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
        n_warmup=warmup,
        r_erode=erode_kernel,
        r_dilate=dilate_kernel,
        suffix=suffix,
        save_image=save_image,
        max_size=max_size,
    )


if __name__ == '__main__':
    app()

<div align="center">
<div style="text-align: center;">
    <img src="./assets/matanyone2_logo.png" alt="MatAnyone Logo" style="height: 52px;">
    <h2>Scaling Video Matting via a Learned Quality Evaluator</h2>
</div>

<div>
    <a href='https://pq-yang.github.io/' target='_blank'>Peiqing Yang</a><sup>1</sup>&emsp;
    <a href='https://shangchenzhou.com/' target='_blank'>Shangchen Zhou</a><sup>1†</sup>&emsp;
    <a href="https://www.linkedin.com/in/kai-hao-794321382/" target='_blank'>Kai Hao</a><sup>1</sup>&emsp;
    <a href="https://scholar.google.com.sg/citations?user=fMXnSGMAAAAJ&hl=en/" target='_blank'>Qingyi Tao</a><sup>2</sup>&emsp;
</div>
<div>
    <sup>1</sup>S-Lab, Nanyang Technological University&emsp; 
    <sup>2</sup>SenseTime Research, Singapore&emsp; 
    <br>
    <sup>†</sup>Project lead
</div>


<div>
    <h4 align="center">
        <a href="https://pq-yang.github.io/projects/MatAnyone2/" target='_blank'>
        <img src="https://img.shields.io/badge/😈-Project%20Page-blue">
        </a>
        <a href="https://arxiv.org/abs/2512.11782" target='_blank'>
        <img src="https://img.shields.io/badge/arXiv-2501.14677-b31b1b.svg">
        </a>
        <a href="https://www.youtube.com/watch?v=tyi8CNyjOhc&lc=Ugw1OS7z5QbW29RZCFZ4AaABAg" target='_blank'>
        <img src="https://img.shields.io/badge/Demo%20Video-%23FF0000.svg?logo=YouTube&logoColor=white">
        </a>
        <a href="https://huggingface.co/spaces/PeiqingYang/MatAnyone" target='_blank'>
        <img src="https://img.shields.io/badge/Demo-%F0%9F%A4%97%20Hugging%20Face-blue">
        </a>
        <img src="https://api.infinitescript.com/badgen/count?name=sczhou/MatAnyone2&ltext=Visitors&color=3977dd">
    </h4>
</div>

<strong>MatAnyone 2 is a practical human video matting framework that preserves fine details by avoiding segmentation-like boundaries, while also shows enhanced robustness under challenging real-world conditions.</strong>

<div style="width: 100%; text-align: center; margin:auto;">
    <img style="width:100%" src="assets/teaser.jpg">
</div>

:movie_camera: For more visual results, go checkout our <a href="https://pq-yang.github.io/projects/MatAnyone2/" target="_blank">project page</a>

---
</div>


## 📮 Update
- [2026.03] Release inference codes, evaluation codes, and gradio demo.
- [2025.12] This repo is created.


## 🏄🏻‍♀️ TODO
- [x] Release inference codes and gradio demo. 
- [x] Release evaluation codes.
- [ ] Release training codes for video matting model.
- [ ] Release checkpoint and training codes for quality evaluator model.
- [ ] Release real-world video matting dataset **VMReal**.


## 🔎 Overview
![overall_structure](assets/matanyone1vs2.jpg)

## 🔧 Installation
1. Clone Repo
    ```bash
    git clone https://github.com/pq-yang/MatAnyone2
    cd MatAnyone2
    ```

2. Create Conda Environment and Install Dependencies
    ```bash
    # create new conda env
    conda create -n matanyone2 python=3.10 -y
    conda activate matanyone2

    # install python dependencies
    pip install -e .
    # [optional] install python dependencies for gradio demo
    pip3 install -r hugging_face/requirements.txt
    ```

### Windows `.venv` Setup For Internal Web App
If you are running the internal web app on a Windows workstation, a local `.venv` is the most reliable setup path:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -e .
```

The gradio demo keeps its extra dependencies in [`hugging_face/requirements.txt`](./hugging_face/requirements.txt), so install those separately only when you need the demo UI.

## 🔥 Inference

### Download Model
Download our pretrained model from [MatAnyone 2](https://github.com/pq-yang/MatAnyone2/releases/download/v1.0.0/matanyone2.pth) to the `pretrained_models` folder (pretrained model can also be automatically downloaded during the first inference).

The directory structure will be arranged as:
```
pretrained_models
   |- matanyone2.pth
```

### Quick Test
We provide some examples in the [`inputs`](./inputs) folder. **For each run, we take a video and its first-frame segmenatation mask as input.** <u>The segmenation mask could be obtained from interactive segmentation models such as [SAM2 demo](https://huggingface.co/spaces/fffiloni/SAM2-Image-Predictor)</u>. For example, the directory structure can be arranged as:
```
inputs
   |- video
      |- test-sample1          # folder containing all frames
      |- test-sample2.mp4      # .mp4, .mov, .avi
   |- mask
      |- test-sample1.png      # mask for targer person(s)
      |- test-sample2.png    
```
Run the following command to try it out:

```shell
# intput format: video folder
python inference_matanyone2.py -i inputs/video/test-sample1 -m inputs/mask/test-sample1.png

# intput format: mp4
python inference_matanyone2.py -i inputs/video/test-sample2.mp4 -m inputs/mask/test-sample2.png

```
The results will be saved in the `results` folder, including the foreground output video and the alpha output video. 
- If you want to save the results as per-frame images, you can set `--save_image`.
- If you want to set a limit for the maximum input resolution, you can set `--max_size`, and the video will be downsampled if min(w, h) exceeds. By default, we don't set the limit.

## 🎪 Interactive Demo
To get rid of the preparation for first-frame segmentation mask, we prepare a gradio demo on [hugging face](https://huggingface.co/spaces/PeiqingYang/MatAnyone2) and could also **launch locally**. Just drop your video/image, assign the target masks with a few clicks, and get the the matting results!

*We integrate MatAnyone Series in the demo. [MatAnyone 2](https://github.com/pq-yang/MatAnyone2) is the default model. You can also choose [MatAnyone](https://github.com/pq-yang/MatAnyone) as your processing model in "Model Selection".*

```shell
cd hugging_face

# install python dependencies
pip3 install -r requirements.txt # FFmpeg required

# launch the demo
python app.py
```

By launching, an interactive interface will appear as follow.

![overall_teaser](assets/teaser_demo.gif)

## 🧪 Internal Web App
The repository now also includes a lightweight internal-web-app scaffold for the planned queue-based workflow.

Run the web server:

```shell
python scripts/run_internal_webapp.py
```

Run the worker in a separate process:

```shell
python scripts/run_internal_worker.py
```

Run an end-to-end smoke test that launches the web app, launches the worker, submits two back-to-back jobs, and verifies queueing plus artifact export:

```shell
python scripts/smoke_internal_webapp.py --copies 2
```

## 📊 Evaluation
Please refer to the [evaluation documentation](docs/EVAL.md) for details.

## 🛠️ Data Pipeline
![data_pipeline](assets/data_pipeline.jpg)


## 📑 Citation

   If you find our repo useful for your research, please consider citing our paper:

   ```bibtex
  @InProceedings{yang2026matanyone2,
      title     = {{MatAnyone 2}: Scaling Video Matting via a Learned Quality Evaluator},
      author    = {Yang, Peiqing and Zhou, Shangchen and Hao, Kai and Tao, Qingyi},
      booktitle = {CVPR},
      year      = {2026}
      }

  @inProceedings{yang2025matanyone,
      title     = {{MatAnyone}: Stable Video Matting with Consistent Memory Propagation},
      author    = {Yang, Peiqing and Zhou, Shangchen and Zhao, Jixin and Tao, Qingyi and Loy, Chen Change},
      booktitle = {CVPR},
      year      = {2025}
      }
   ```

## 📝 License

This project is licensed under <a rel="license" href="./LICENSE">NTU S-Lab License 1.0</a>. Redistribution and use should follow this license.

## 👏 Acknowledgement

This project is built upon [MatAnyone](https://github.com/pq-yang/MatAnyone) and [Cutie](https://github.com/hkchengrex/Cutie), with matting dataset files adapted from [RVM](https://github.com/PeterL1n/RobustVideoMatting). The interactive demo is adapted from [ProPainter](https://github.com/sczhou/ProPainter), leveraging segmentation capabilities from [Segment Anything Model](https://github.com/facebookresearch/segment-anything) and [Segment Anything Model 2](https://github.com/facebookresearch/sam2). Thanks for their awesome works!

## 📧 Contact

If you have any questions, please feel free to reach us at `peiqingyang99@outlook.com`. 

# Evaluation Documentation

This document shows the way to reproduce the quantitative results in our paper on two synthetic benchmarks ([YouTubeMatte](https://github.com/pq-yang/MatAnyone/tree/main?tab=readme-ov-file#youtubematte-dataset) and [VideoMatte](https://github.com/PeterL1n/RobustVideoMatting/blob/master/documentation/training.md#evaluation)) and one real benchmark ([CRGNN](https://github.com/TiantianWang/VideoMatting-CRGNN)).

*If the link for CRGNN expires, we save a local copy for research purposes [here](https://drive.google.com/drive/folders/1OGIOcPwCekp26F2crQ8sx370crJSOtKN?usp=drive_link).*

## YouTubeMatte

**📦 We provide the inference results with MatAnyone 2 on the YouTubeMatte benchmark [here](https://drive.google.com/drive/folders/1fgPAx4pRGyxGIYW4NeBevDM8PpA0TG9I?usp=sharing).**

### Preparation
* [YouTubeMatte.zip (6.24G)](https://drive.google.com/file/d/1IEH0RaimT_hSp38AWF6wuwNJzzNSHpJ4/view?usp=drive_link)
* [YouTubeMatte_first_frame_seg_mask.zip (310K)](https://drive.google.com/file/d/1Zpa7SB7VZmkvRDiehVC-c_0dmFWXdfzK/view?usp=drive_linkk)

To run the inference scripts, your files should be arranged as:
```
data
   |- YouTubeMatte_first_frame_seg_mask   # for inference only
   |- YouTubeMatte
        |- youtubematte_512x288
        |- youtubematte_1920x1080
```

### Batch Inference
Empirically, for low-resolution (`youtubematte_512x288`) and high-resolution (`youtubematte_1920x1080`) data, we set **different** hyperparameter values for `--warmup`, `--erode_kernel`, and `--dilate_kernel`.

```shell
# lr: youtubematte_512x288
bash evaluation/infer_batch_lr_yt.sh

# hr: youtubematte_1920x1080
bash evaluation/infer_batch_hr_yt.sh
```

### Evaluation
To run the evaluation scripts, your files should be arranged as:

```
data
   |- YouTubeMatte
        |- youtubematte_512x288
        |- youtubematte_1920x1080

   |- results
        |- youtubematte_512x288
        |- youtubematte_1920x1080
```

```shell
# lr: youtubematte_512x288
python evaluation/eval_lr.py \
    --pred-dir ./data/results/youtubematte_512x288 \
    --true-dir ./data/YouTubeMatte/youtubematte_512x288 

# hr: youtubematte_1920x1080
python evaluation/eval_hr.py \
    --pred-dir ./data/results/youtubematte_1920x1080 \
    --true-dir ./data/YouTubeMatte/youtubematte_1920x1080 
```

## VideoMatte

**📦 We provide the inference results with MatAnyone 2 on the VideoMatte benchmark [here](https://drive.google.com/drive/folders/12QM-_kyerE1tQfINoR17zYIFtrcwCK04?usp=sharing).**

### Preparation
* [videomatte_512x512.tar (1.8G)](https://robustvideomatting.blob.core.windows.net/eval/videomatte_512x288.tar)
* [videomatte_1920x1080.tar (2.2G)](https://robustvideomatting.blob.core.windows.net/eval/videomatte_1920x1080.tar)
* [VideoMatte_first_frame_seg_mask.zip (416K)](https://drive.google.com/file/d/1kN5gX4NAEa4HG-k2ir8kPcEp_18DbDHt/view?usp=drive_link)

To run the inference scripts, your files should be arranged as:
```
data
   |- VideoMatte_first_frame_seg_mask   # for inference only
   |- VideoMatte
        |- videomatte_512x288
        |- videomatte_1920x1080
```

### Batch Inference
Empirically, for low-resolution (`videomatte_512x288`) and high-resolution (`videomatte_1920x1080`) data, we set **different** hyperparameter values for `--warmup`, `--erode_kernel`, and `--dilate_kernel`.

```shell
# lr: videomatte_512x288
bash evaluation/infer_batch_lr_vm.sh

# hr: videomatte_1920x1080
bash evaluation/infer_batch_hr_vm.sh
```

### Evaluation
To run the evaluation scripts, your files should be arranged as:

```
data
   |- VideoMatte
        |- videomatte_512x288
        |- videomatte_1920x1080

   |- results
        |- videomatte_512x288
        |- videomatte_512x288
```

```shell
# lr: videomatte_512x288
python evaluation/eval_lr.py \
    --pred-dir ./data/results/videomatte_512x288 \
    --true-dir ./data/VideoMatte/videomatte_512x288 

# hr: videomatte_1920x1080
python evaluation/eval_hr.py \
    --pred-dir ./data/results/videomatte_1920x1080 \
    --true-dir ./data/VideoMatte/videomatte_1920x1080 
```

## CRGNN

**📦 We provide the inference results with MatAnyone 2 on the CRGNN benchmark [here](https://drive.google.com/file/d/1JJyE4uPymEcijNa1Ok8ME_BY6oxJ3EXJ/view?usp=sharing).**

### Preparation
* [real_human_data](https://www.dropbox.com/sh/23uvsue5we7e7b5/AAB4GSSWIaKiSouvN3wuWiwWa?dl=0)
* [CRGNN_first_frame_seg_mask.zip (151K)](https://drive.google.com/file/d/1cDSf1kO_tdWy-q3CuX4IfuZ16ZYEER-d/view?usp=sharing)

To run the inference scripts, your files should be arranged as:
```
data
   |- crgnn   
     |- alpha
     |- image_allframe
     |- mask              # first frame seg mask
```

### Batch Inference

```shell
bash evaluation/infer_batch_crgnn.sh
```

### Evaluation
To run the evaluation scripts, your files should be arranged as:

```
data
   |- crgnn
        |- alpha

   |- results
        |- crgnn
```

```shell
python evaluation/eval_crgnn.py \
    --pred-dir ./data/results/crgnn \
    --true-dir ./data/crgnn/alpha 
```

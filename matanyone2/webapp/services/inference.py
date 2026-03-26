from pathlib import Path
import shutil

from matanyone2.webapp.models import InferenceResult


class InferenceService:
    def __init__(self, model_name: str = "MatAnyone 2"):
        self.model_name = model_name

    def run_job(
        self,
        *,
        source_video_path: Path,
        mask_path: Path,
        job_dir: Path,
        template_frame_index: int,
    ) -> InferenceResult:
        foreground_path, alpha_path = self._run_model(
            source_video_path=Path(source_video_path),
            mask_path=Path(mask_path),
            job_dir=Path(job_dir),
            template_frame_index=template_frame_index,
        )
        return InferenceResult(
            foreground_video_path=foreground_path,
            alpha_video_path=alpha_path,
        )

    def _run_model(
        self,
        *,
        source_video_path: Path,
        mask_path: Path,
        job_dir: Path,
        template_frame_index: int,
    ) -> tuple[Path, Path]:
        del template_frame_index
        from inference_matanyone2 import main as run_inference

        job_dir.mkdir(parents=True, exist_ok=True)

        run_inference(
            input_path=str(source_video_path),
            mask_path=str(mask_path),
            output_path=str(job_dir),
            ckpt_path="pretrained_models/matanyone2.pth",
        )

        stem = source_video_path.stem
        generated_foreground = job_dir / f"{stem}_fgr.mp4"
        generated_alpha = job_dir / f"{stem}_pha.mp4"
        foreground_path = job_dir / "foreground.mp4"
        alpha_path = job_dir / "alpha.mp4"
        shutil.move(generated_foreground, foreground_path)
        shutil.move(generated_alpha, alpha_path)
        return foreground_path, alpha_path

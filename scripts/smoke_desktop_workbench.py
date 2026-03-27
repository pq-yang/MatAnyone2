from datetime import datetime
from pathlib import Path
import argparse

import cv2
import numpy as np
from PIL import Image

from _path_bootstrap import ensure_project_root_on_path

PROJECT_ROOT = ensure_project_root_on_path(__file__)

from matanyone2.desktop_app.app import build_controller, build_desktop_config
from matanyone2.webapp.services.masking import MaskingService


def _create_sample_video(video_path: Path) -> Path:
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        4.0,
        (320, 192),
    )
    for index in range(24):
        frame = np.zeros((192, 320, 3), dtype=np.uint8)
        frame[:, :] = (18, 24, 32)
        x0 = 60 + (index * 3)
        cv2.rectangle(frame, (x0, 32), (x0 + 72, 176), (208, 184, 132), thickness=-1)
        writer.write(frame)
    writer.release()
    return video_path


class FakeController:
    def first_frame_click(self, image, points, labels, multimask=True):
        mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
        for x, y in points.tolist():
            x0 = max(0, x - 32)
            y0 = max(0, y - 48)
            x1 = min(image.shape[1], x + 32)
            y1 = min(image.shape[0], y + 48)
            mask[y0:y1, x0:x1] = 1
        return mask, np.zeros_like(mask, dtype=np.float32), Image.fromarray(image)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, default=None)
    parser.add_argument("--start-frame", type=int, default=2)
    parser.add_argument("--end-frame", type=int, default=14)
    parser.add_argument("--anchor-frame", type=int, default=6)
    args = parser.parse_args()

    config = build_desktop_config(PROJECT_ROOT)
    controller = build_controller(config)
    controller.masking_service = MaskingService(
        runtime_root=config.runtime_root,
        controller_factory=lambda: FakeController(),
        sam_backend="sam3",
        sam3_checkpoint_path=str(config.sam3_checkpoint_path),
    )

    smoke_root = config.runtime_root / f"smoke-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    smoke_root.mkdir(parents=True, exist_ok=True)
    video_path = args.video or _create_sample_video(smoke_root / "synthetic.mp4")

    controller.open_video(video_path)
    controller.apply_processing_range(
        start_frame_index=args.start_frame,
        end_frame_index=args.end_frame,
    )
    controller.apply_anchor(frame_index=args.anchor_frame)
    controller.apply_click(x=120, y=96, positive=True)
    mask_name = controller.save_active_target()
    controller.set_selected_masks([mask_name])
    payload = controller.submit_job(smoke_root / "job")

    required_paths = [
        Path(payload["foreground_video_path"]),
        Path(payload["alpha_video_path"]),
        Path(payload["png_zip_path"]),
    ]
    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(path)

    print(f"smoke_root={smoke_root}")
    print(f"job_id={payload['job_id']}")
    print(f"foreground={payload['foreground_video_path']}")
    print(f"alpha={payload['alpha_video_path']}")
    print(f"png_zip={payload['png_zip_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

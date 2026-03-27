import numpy as np
from pathlib import Path

from PIL import Image, ImageDraw

from matanyone2.webapp.models import AnnotationTarget, DraftRecord, DraftSession, MaskingResult
from matanyone2.webapp.runtime_paths import ensure_dir


SAM2_CHECKPOINTS = {
    "sam2.1_hiera_tiny": {
        "config": "configs/sam2.1/sam2.1_hiera_t.yaml",
        "filename": "sam2.1_hiera_tiny.pt",
        "url": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt",
    },
    "sam2.1_hiera_small": {
        "config": "configs/sam2.1/sam2.1_hiera_s.yaml",
        "filename": "sam2.1_hiera_small.pt",
        "url": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt",
    },
    "sam2.1_hiera_base_plus": {
        "config": "configs/sam2.1/sam2.1_hiera_b+.yaml",
        "filename": "sam2.1_hiera_base_plus.pt",
        "url": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt",
    },
    "sam2.1_hiera_large": {
        "config": "configs/sam2.1/sam2.1_hiera_l.yaml",
        "filename": "sam2.1_hiera_large.pt",
        "url": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt",
    },
}


def merge_masks(masks: list[np.ndarray]) -> np.ndarray:
    if not masks:
        raise ValueError("at least one mask is required")

    merged = np.zeros_like(masks[0], dtype=np.uint8)
    for mask in masks:
        merged = np.where(mask > 0, 255, merged).astype(np.uint8)
    return merged


class SamMaskController:
    def __init__(self, checkpoint_path: str, model_type: str, device: str):
        from hugging_face.tools.interact_tools import SamControler

        self._controller = SamControler(checkpoint_path, model_type, device)

    def first_frame_click(self, image, points, labels, multimask=True):
        self._controller.sam_controler.reset_image()
        self._controller.sam_controler.set_image(image)
        return self._controller.first_frame_click(
            image=image,
            points=points,
            labels=labels,
            multimask=multimask,
        )


def _render_mask_preview(image: np.ndarray, mask: np.ndarray, points, labels) -> Image.Image:
    base = Image.fromarray(image.astype(np.uint8), mode="RGB").convert("RGBA")
    overlay = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
    overlay[mask > 0] = np.array([110, 132, 255, 118], dtype=np.uint8)
    composite = Image.alpha_composite(base, Image.fromarray(overlay, mode="RGBA"))
    draw = ImageDraw.Draw(composite)

    for (x, y), label in zip(points.tolist(), labels.tolist()):
        color = (118, 230, 136, 255) if label == 1 else (232, 105, 196, 255)
        outline = (255, 143, 96, 255)
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=outline)
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)

    return composite.convert("RGB")


class Sam2MaskController:
    def __init__(self, predictor):
        self._predictor = predictor

    def first_frame_click(self, image, points, labels, multimask=True):
        self._predictor.set_image(image)
        masks, scores, _ = self._predictor.predict(
            point_coords=points,
            point_labels=labels,
            multimask_output=multimask,
        )

        masks = np.asarray(masks)
        scores = np.asarray(scores)
        if masks.ndim == 3:
            best_index = int(np.argmax(scores)) if scores.size else 0
            mask = masks[best_index]
        else:
            mask = masks
        mask = mask.astype(np.uint8)
        painted_image = _render_mask_preview(image, mask, points, labels)
        return mask, scores, painted_image


class MaskingService:
    VALID_STAGES = {"coarse", "refine", "preview"}

    def __init__(
        self,
        *,
        runtime_root: Path,
        controller_factory=None,
        sam_backend: str = "sam2",
        sam_model_type: str = "vit_h",
        sam2_variant: str = "sam2.1_hiera_large",
        sam2_checkpoint_path: str | None = None,
    ):
        self.runtime_root = Path(runtime_root)
        self.controller_factory = controller_factory
        self.sam_backend = sam_backend
        self.sam_model_type = sam_model_type
        self.sam2_variant = sam2_variant
        self.sam2_checkpoint_path = sam2_checkpoint_path
        self._controller = None

    def create_session(self, draft: DraftRecord) -> DraftSession:
        session_dir = ensure_dir(self.runtime_root / "drafts" / draft.draft_id / "annotation")
        return DraftSession(draft=draft, session_dir=session_dir)

    def create_target(self, session: DraftSession, name: str | None = None) -> AnnotationTarget:
        session.current_mask_path = None
        session.current_preview_path = None
        return session.create_target(name=name)

    def select_target(self, session: DraftSession, target_id: str) -> AnnotationTarget:
        session.current_mask_path = None
        session.current_preview_path = None
        return session.select_target(target_id)

    def update_target(
        self,
        session: DraftSession,
        target_id: str,
        *,
        name: str | None = None,
        visible: bool | None = None,
        locked: bool | None = None,
    ) -> AnnotationTarget:
        target = session.targets.get(target_id)
        if target is None:
            raise KeyError(target_id)
        if name is not None:
            stripped = name.strip()
            if not stripped:
                raise ValueError("target name cannot be empty")
            target.name = stripped
        if visible is not None:
            target.visible = visible
        if locked is not None:
            target.locked = locked
        return target

    def set_stage(self, session: DraftSession, stage: str) -> str:
        if stage not in self.VALID_STAGES:
            raise ValueError(f"unknown stage: {stage}")
        session.stage = stage
        return session.stage

    def apply_click(
        self,
        session: DraftSession,
        *,
        x: int,
        y: int,
        positive: bool,
    ) -> MaskingResult:
        session.click_points = session.click_points + [(x, y)]
        session.click_labels = session.click_labels + [1 if positive else 0]
        return self._render_active_target(session)

    def undo_last_click(self, session: DraftSession) -> MaskingResult | None:
        if not session.click_points:
            self._clear_current_render(session)
            return None

        session.click_points = session.click_points[:-1]
        session.click_labels = session.click_labels[:-1]
        if not session.click_points:
            self._clear_current_render(session)
            return None
        return self._render_active_target(session)

    def reset_active_target(self, session: DraftSession) -> None:
        session.click_points = []
        session.click_labels = []
        self._clear_current_render(session)

    def _render_active_target(self, session: DraftSession) -> MaskingResult:
        image = np.array(Image.open(session.draft.template_frame_path).convert("RGB"))
        points = np.array(session.click_points, dtype=np.int32)
        labels = np.array(session.click_labels, dtype=np.int32)

        mask, _, painted_image = self._get_controller().first_frame_click(
            image=image,
            points=points,
            labels=labels,
            multimask=True,
        )

        current_mask_path = session.session_dir / "current_mask.png"
        current_preview_path = session.session_dir / "current_preview.png"
        Image.fromarray(np.where(mask > 0, 255, 0).astype(np.uint8), mode="L").save(
            current_mask_path
        )
        painted_image.save(current_preview_path)

        session.click_points = [(int(px), int(py)) for px, py in points.tolist()]
        session.click_labels = [int(label) for label in labels.tolist()]
        session.current_mask_path = current_mask_path
        session.current_preview_path = current_preview_path
        return MaskingResult(
            current_mask_path=current_mask_path,
            current_preview_path=current_preview_path,
        )

    def _clear_current_render(self, session: DraftSession) -> None:
        session.current_mask_path = None
        session.current_preview_path = None

    def save_current_mask(self, session: DraftSession) -> str:
        if session.current_mask_path is None:
            raise ValueError("no current mask to save")
        mask_name = f"mask_{len(session.saved_masks) + 1:03d}"
        saved_mask_path = session.session_dir / f"{mask_name}.png"
        Image.open(session.current_mask_path).save(saved_mask_path)
        session.saved_masks[mask_name] = saved_mask_path
        session.selected_mask_names.add(mask_name)
        session.active_target.saved_mask_name = mask_name
        session.click_points = []
        session.click_labels = []
        session.current_mask_path = None
        session.current_preview_path = None
        return mask_name

    def write_merged_mask(self, session: DraftSession, selected_masks: list[str]) -> Path:
        if not selected_masks:
            raise ValueError("at least one selected mask is required")
        masks = []
        for mask_name in selected_masks:
            mask_path = session.saved_masks.get(mask_name)
            if mask_path is None:
                raise KeyError(mask_name)
            masks.append(np.array(Image.open(mask_path).convert("L")))
        merged_mask = merge_masks(masks)
        merged_mask_path = session.session_dir / "merged_mask.png"
        Image.fromarray(merged_mask, mode="L").save(merged_mask_path)
        return merged_mask_path

    def _get_controller(self):
        if self._controller is None:
            factory = self.controller_factory or self._build_default_controller
            self._controller = factory()
        return self._controller

    def _build_default_controller(self):
        if self.sam_backend == "sam2":
            return self._build_sam2_controller()
        if self.sam_backend == "sam1":
            return self._build_sam1_controller()
        raise ValueError(f"unknown sam backend: {self.sam_backend}")

    def _build_sam1_controller(self):
        from hugging_face.tools.download_util import load_file_from_url
        from hugging_face.tools.misc import get_device

        checkpoint_urls = {
            "vit_h": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
            "vit_l": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth",
            "vit_b": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
        }
        checkpoint_path = load_file_from_url(
            checkpoint_urls[self.sam_model_type],
            model_dir=str(Path("pretrained_models")),
        )
        return SamMaskController(
            checkpoint_path=checkpoint_path,
            model_type=self.sam_model_type,
            device=str(get_device()),
        )

    def _build_sam2_controller(self):
        from hugging_face.tools.download_util import load_file_from_url
        from hugging_face.tools.misc import get_device

        try:
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor
        except ImportError as exc:
            raise RuntimeError(
                "SAM2 backend is selected but the 'SAM-2' package is not installed"
            ) from exc

        variant = SAM2_CHECKPOINTS.get(self.sam2_variant)
        if variant is None:
            raise ValueError(f"unknown SAM2 variant: {self.sam2_variant}")

        checkpoint_path = self.sam2_checkpoint_path
        if checkpoint_path is None:
            checkpoint_path = load_file_from_url(
                variant["url"],
                model_dir=str(Path("pretrained_models")),
            )

        predictor = SAM2ImagePredictor(
            build_sam2(
                variant["config"],
                checkpoint_path,
                device=str(get_device()),
            )
        )
        return Sam2MaskController(predictor)

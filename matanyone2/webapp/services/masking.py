import numpy as np
from pathlib import Path

from PIL import Image

from matanyone2.webapp.models import AnnotationTarget, DraftRecord, DraftSession, MaskingResult
from matanyone2.webapp.runtime_paths import ensure_dir


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


class MaskingService:
    VALID_STAGES = {"coarse", "refine", "preview"}

    def __init__(
        self,
        *,
        runtime_root: Path,
        controller_factory=None,
        sam_model_type: str = "vit_h",
    ):
        self.runtime_root = Path(runtime_root)
        self.controller_factory = controller_factory
        self.sam_model_type = sam_model_type
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
        image = np.array(Image.open(session.draft.template_frame_path).convert("RGB"))
        points = np.array(session.click_points + [(x, y)], dtype=np.int32)
        labels = np.array(session.click_labels + [1 if positive else 0], dtype=np.int32)

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

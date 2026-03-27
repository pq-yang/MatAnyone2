import numpy as np
from pathlib import Path
import sys
import types
from importlib.machinery import ModuleSpec

from PIL import Image, ImageDraw, ImageFilter

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

PRESET_LABELS = {
    "balanced": "Balanced",
    "hair": "Hair Priority",
    "edge": "Edge Priority",
    "motion": "Motion Blur",
}


def _rewrite_sam3_editable_mapping_if_needed() -> None:
    local_repo_root = Path(r"D:\my_app\lens_hunter2\models\sam3\sam3_repo\sam3")
    if not local_repo_root.exists():
        return
    try:
        import __editable___sam3_0_1_0_finder as sam3_editable_finder
    except ImportError:
        return

    current_root = sam3_editable_finder.MAPPING.get("sam3")
    if current_root == str(local_repo_root):
        return

    sam3_editable_finder.MAPPING["sam3"] = str(local_repo_root)
    for namespace, paths in list(sam3_editable_finder.NAMESPACES.items()):
        rewritten = []
        for path in paths:
            if current_root and path.startswith(current_root):
                rewritten.append(path.replace(current_root, str(local_repo_root), 1))
            else:
                rewritten.append(path)
        sam3_editable_finder.NAMESPACES[namespace] = rewritten


def _install_triton_stub_if_needed() -> None:
    try:
        import triton  # noqa: F401
        import triton.language  # noqa: F401
        return
    except ImportError:
        pass

    triton_module = types.ModuleType("triton")
    triton_language_module = types.ModuleType("triton.language")

    def _jit(function=None, **_kwargs):
        if function is None:
            def _decorator(inner):
                return inner
            return _decorator
        return function

    class _MissingTritonSymbol:
        def __call__(self, *args, **kwargs):
            raise RuntimeError("SAM3 requested a Triton-only code path that is unavailable on this runtime")

    def _missing_attr(_name):
        return _MissingTritonSymbol()

    triton_module.jit = _jit
    triton_module.__spec__ = ModuleSpec("triton", loader=None)
    triton_language_module.constexpr = object()
    triton_language_module.__getattr__ = _missing_attr
    triton_language_module.__spec__ = ModuleSpec("triton.language", loader=None)

    sys.modules.setdefault("triton", triton_module)
    sys.modules.setdefault("triton.language", triton_language_module)


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


class Sam3MaskController:
    def __init__(self, predictor_or_model, processor=None):
        self._predictor = predictor_or_model if processor is None else None
        self._model = predictor_or_model if processor is not None else None
        self._processor = processor

    def first_frame_click(self, image, points, labels, multimask=True):
        if self._processor is None:
            self._predictor.set_image(image)
            masks, scores, _ = self._predictor.predict(
                point_coords=points,
                point_labels=labels,
                multimask_output=multimask,
            )
        else:
            inference_state = self._processor.set_image(Image.fromarray(image.astype(np.uint8)))
            masks, scores, _ = self._model.predict_inst(
                inference_state,
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
    VALID_REFINE_PRESETS = {"balanced", "hair", "edge", "motion"}
    VALID_BRUSH_MODES = {"add", "remove", "feather"}

    def __init__(
        self,
        *,
        runtime_root: Path,
        controller_factory=None,
        sam_backend: str = "sam3",
        sam_model_type: str = "vit_h",
        sam2_variant: str = "sam2.1_hiera_large",
        sam2_checkpoint_path: str | None = None,
        sam3_checkpoint_path: str | None = None,
    ):
        self.runtime_root = Path(runtime_root)
        self.controller_factory = controller_factory
        self.sam_backend = sam_backend
        self.sam_model_type = sam_model_type
        self.sam2_variant = sam2_variant
        self.sam2_checkpoint_path = sam2_checkpoint_path
        self.sam3_checkpoint_path = sam3_checkpoint_path
        self._controller = None

    def create_session(self, draft: DraftRecord) -> DraftSession:
        session_dir = ensure_dir(self.runtime_root / "drafts" / draft.draft_id / "annotation")
        return DraftSession(draft=draft, session_dir=session_dir)

    def create_target(self, session: DraftSession, name: str | None = None) -> AnnotationTarget:
        self._clear_current_render(session)
        return session.create_target(name=name)

    def select_target(self, session: DraftSession, target_id: str) -> AnnotationTarget:
        target = session.select_target(target_id)
        self._hydrate_target_render(session)
        return target

    def update_target(
        self,
        session: DraftSession,
        target_id: str,
        *,
        name: str | None = None,
        visible: bool | None = None,
        locked: bool | None = None,
        refine_preset: str | None = None,
        preset_strength: float | None = None,
        motion_strength: float | None = None,
        temporal_stability: float | None = None,
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
        if refine_preset is not None:
            if refine_preset not in self.VALID_REFINE_PRESETS:
                raise ValueError(f"unknown refine preset: {refine_preset}")
            target.refine_preset = refine_preset
        if preset_strength is not None:
            target.preset_strength = self._validate_unit_interval(
                preset_strength,
                field_name="preset_strength",
            )
        if motion_strength is not None:
            target.motion_strength = self._validate_unit_interval(
                motion_strength,
                field_name="motion_strength",
            )
        if temporal_stability is not None:
            target.temporal_stability = self._validate_unit_interval(
                temporal_stability,
                field_name="temporal_stability",
            )
        if (
            refine_preset is not None
            or preset_strength is not None
            or motion_strength is not None
            or temporal_stability is not None
        ):
            self._rerender_current_from_base(session)
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

    def apply_brush(
        self,
        session: DraftSession,
        *,
        points: list[tuple[int, int]],
        mode: str,
        radius: int,
    ) -> MaskingResult:
        if session.stage == "preview":
            raise ValueError("preview mode is read-only")
        if session.active_target.locked:
            raise ValueError("active target is locked")
        if mode not in self.VALID_BRUSH_MODES:
            raise ValueError(f"unknown brush mode: {mode}")
        if radius < 1:
            raise ValueError("brush radius must be at least 1")
        if not points:
            raise ValueError("at least one brush point is required")

        mask = self._load_editable_mask(session)
        mask_image = Image.fromarray(mask, mode="L")
        stroke_mask = Image.new("L", mask_image.size, 0)
        stroke_draw = ImageDraw.Draw(stroke_mask)

        for x, y in points:
            bounds = (x - radius, y - radius, x + radius, y + radius)
            stroke_draw.ellipse(bounds, fill=255)

        if mode == "add":
            ImageDraw.Draw(mask_image).bitmap((0, 0), stroke_mask, fill=255)
        elif mode == "remove":
            ImageDraw.Draw(mask_image).bitmap((0, 0), stroke_mask, fill=0)
        else:
            blurred = mask_image.filter(ImageFilter.GaussianBlur(radius=max(1, radius // 4)))
            mask_image = Image.composite(blurred, mask_image, stroke_mask)

        result_mask = np.where(np.array(mask_image, dtype=np.uint8) > 127, 255, 0).astype(np.uint8)
        return self._write_current_render(session, result_mask)

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

    def apply_refine_preset(
        self,
        mask: np.ndarray,
        preset: str,
        *,
        preset_strength: float = 0.5,
        motion_strength: float = 0.35,
    ) -> np.ndarray:
        if preset not in self.VALID_REFINE_PRESETS:
            raise ValueError(f"unknown refine preset: {preset}")

        preset_strength = self._validate_unit_interval(
            preset_strength,
            field_name="preset_strength",
        )
        motion_strength = self._validate_unit_interval(
            motion_strength,
            field_name="motion_strength",
        )
        binary_mask = np.where(mask > 127, 255, 0).astype(np.uint8)
        if preset == "balanced":
            if motion_strength <= 0:
                return binary_mask
            softened = Image.fromarray(binary_mask, mode="L").filter(
                ImageFilter.GaussianBlur(radius=0.4 + (motion_strength * 1.4))
            )
            return np.where(np.array(softened, dtype=np.uint8) >= 112, 255, 0).astype(np.uint8)

        mask_image = Image.fromarray(binary_mask, mode="L")
        if preset == "hair":
            filter_size = self._odd_kernel_size(3 + int(round(preset_strength * 4)))
            processed = mask_image.filter(ImageFilter.MaxFilter(filter_size))
        elif preset == "edge":
            filter_size = self._odd_kernel_size(3 + int(round(preset_strength * 4)))
            processed = mask_image.filter(ImageFilter.MinFilter(filter_size))
        else:
            blur_radius = 0.8 + (motion_strength * 2.4)
            processed = mask_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            threshold = max(36, int(round(112 - (preset_strength * 36))))
            return np.where(np.array(processed, dtype=np.uint8) >= threshold, 255, 0).astype(np.uint8)

        return np.where(np.array(processed, dtype=np.uint8) > 127, 255, 0).astype(np.uint8)

    def apply_temporal_stability_preview(
        self,
        mask: np.ndarray,
        *,
        temporal_stability: float = 0.0,
    ) -> np.ndarray:
        temporal_stability = self._validate_unit_interval(
            temporal_stability,
            field_name="temporal_stability",
        )
        binary_mask = np.where(mask > 127, 255, 0).astype(np.uint8)
        if temporal_stability <= 0:
            return binary_mask

        blur_radius = 0.6 + (temporal_stability * 2.8)
        blurred = Image.fromarray(binary_mask, mode="L").filter(
            ImageFilter.GaussianBlur(radius=blur_radius)
        )
        threshold = max(72, int(round(152 - (temporal_stability * 64))))
        stabilized = np.where(np.array(blurred, dtype=np.uint8) >= threshold, 255, 0).astype(np.uint8)

        filter_size = self._odd_kernel_size(3 + int(round(temporal_stability * 4)))
        stabilized_image = Image.fromarray(stabilized, mode="L")
        stabilized_image = stabilized_image.filter(ImageFilter.MaxFilter(filter_size))
        stabilized_image = stabilized_image.filter(ImageFilter.MinFilter(filter_size))
        return np.where(np.array(stabilized_image, dtype=np.uint8) > 127, 255, 0).astype(np.uint8)

    def apply_target_controls(
        self,
        mask: np.ndarray,
        target: AnnotationTarget,
    ) -> np.ndarray:
        refined_mask = self.apply_refine_preset(
            mask,
            target.refine_preset,
            preset_strength=target.preset_strength,
            motion_strength=target.motion_strength,
        )
        temporal_input = refined_mask if np.any(refined_mask > 0) else np.where(mask > 127, 255, 0).astype(np.uint8)
        return self.apply_temporal_stability_preview(
            temporal_input,
            temporal_stability=target.temporal_stability,
        )

    def reset_session_for_template_frame(self, session: DraftSession, *, frame_index: int) -> None:
        session.targets = {}
        session.active_target_id = None
        session.saved_masks = {}
        session.saved_mask_presets = {}
        session.selected_mask_names = set()
        session.stage = "coarse"
        session._target_sequence = 0
        session.draft.template_frame_index = frame_index
        self._clear_current_render(session)
        session.create_target()

    def _render_active_target(self, session: DraftSession) -> MaskingResult:
        image = np.array(Image.open(session.draft.template_frame_path).convert("RGB"))
        points = np.array(session.click_points, dtype=np.int32)
        labels = np.array(session.click_labels, dtype=np.int32)

        mask, _, _ = self._get_controller().first_frame_click(
            image=image,
            points=points,
            labels=labels,
            multimask=True,
        )

        session.click_points = [(int(px), int(py)) for px, py in points.tolist()]
        session.click_labels = [int(label) for label in labels.tolist()]
        return self._write_current_render(session, np.where(mask > 0, 255, 0).astype(np.uint8))

    def _clear_current_render(self, session: DraftSession) -> None:
        session.current_mask_base_path = None
        session.current_mask_path = None
        session.current_preview_path = None

    def save_current_mask(self, session: DraftSession) -> str:
        if session.current_mask_path is None:
            raise ValueError("no current mask to save")
        mask_name = f"mask_{len(session.saved_masks) + 1:03d}"
        saved_mask_path = session.session_dir / f"{mask_name}.png"
        current_mask = self._load_current_base_mask(session)
        processed_mask = self.apply_target_controls(current_mask, session.active_target)
        Image.fromarray(processed_mask, mode="L").save(saved_mask_path)
        session.saved_masks[mask_name] = saved_mask_path
        session.saved_mask_presets[mask_name] = session.active_target.refine_preset
        session.selected_mask_names.add(mask_name)
        session.active_target.saved_mask_name = mask_name
        session.click_points = []
        session.click_labels = []
        self._hydrate_target_render(session)
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

    def _load_editable_mask(self, session: DraftSession) -> np.ndarray:
        if session.current_mask_base_path is not None and session.current_mask_base_path.exists():
            return np.array(Image.open(session.current_mask_base_path).convert("L"), dtype=np.uint8)

        saved_mask_name = session.active_target.saved_mask_name
        if saved_mask_name:
            saved_mask_path = session.saved_masks.get(saved_mask_name)
            if saved_mask_path is not None and saved_mask_path.exists():
                return np.array(Image.open(saved_mask_path).convert("L"), dtype=np.uint8)

        if session.current_mask_path is not None and session.current_mask_path.exists():
            return np.array(Image.open(session.current_mask_path).convert("L"), dtype=np.uint8)

        height = session.draft.height
        width = session.draft.width
        return np.zeros((height, width), dtype=np.uint8)

    def _load_current_base_mask(self, session: DraftSession) -> np.ndarray:
        if session.current_mask_base_path is not None and session.current_mask_base_path.exists():
            return np.array(Image.open(session.current_mask_base_path).convert("L"), dtype=np.uint8)
        return self._load_editable_mask(session)

    def _write_current_render(
        self,
        session: DraftSession,
        mask: np.ndarray,
    ) -> MaskingResult:
        current_mask_base_path = session.session_dir / "current_mask_base.png"
        current_mask_path = session.session_dir / "current_mask.png"
        current_preview_path = session.session_dir / "current_preview.png"
        base_mask = np.where(mask > 0, 255, 0).astype(np.uint8)
        Image.fromarray(base_mask, mode="L").save(current_mask_base_path)
        display_mask = self.apply_target_controls(base_mask, session.active_target)
        Image.fromarray(display_mask, mode="L").save(current_mask_path)

        image = np.array(Image.open(session.draft.template_frame_path).convert("RGB"))
        points = np.array(session.click_points, dtype=np.int32)
        labels = np.array(session.click_labels, dtype=np.int32)
        painted_image = _render_mask_preview(image, display_mask, points, labels)

        painted_image.save(current_preview_path)
        session.current_mask_base_path = current_mask_base_path
        session.current_mask_path = current_mask_path
        session.current_preview_path = current_preview_path
        return MaskingResult(
            current_mask_path=current_mask_path,
            current_preview_path=current_preview_path,
        )

    def _rerender_current_from_base(self, session: DraftSession) -> None:
        if session.current_mask_base_path is not None and session.current_mask_base_path.exists():
            base_mask = np.array(Image.open(session.current_mask_base_path).convert("L"), dtype=np.uint8)
            self._write_current_render(session, base_mask)
            return
        if session.current_mask_path is not None and session.current_mask_path.exists():
            base_mask = np.array(Image.open(session.current_mask_path).convert("L"), dtype=np.uint8)
            self._write_current_render(session, base_mask)
            return
        saved_mask_name = session.active_target.saved_mask_name
        if saved_mask_name:
            saved_mask_path = session.saved_masks.get(saved_mask_name)
            if saved_mask_path is not None and saved_mask_path.exists():
                saved_mask = np.array(Image.open(saved_mask_path).convert("L"), dtype=np.uint8)
                self._write_current_render(session, saved_mask)
                return

    def _hydrate_target_render(self, session: DraftSession) -> None:
        if session.click_points:
            self._render_active_target(session)
            return

        saved_mask_name = session.active_target.saved_mask_name
        if saved_mask_name:
            saved_mask_path = session.saved_masks.get(saved_mask_name)
            if saved_mask_path is not None and saved_mask_path.exists():
                saved_mask = np.array(Image.open(saved_mask_path).convert("L"), dtype=np.uint8)
                self._write_current_render(session, saved_mask)
                return
        self._clear_current_render(session)

    def _build_default_controller(self):
        if self.sam_backend == "sam3":
            return self._build_sam3_controller()
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

    def _build_sam3_controller(self):
        from hugging_face.tools.misc import get_device

        _rewrite_sam3_editable_mapping_if_needed()
        _install_triton_stub_if_needed()
        try:
            from sam3 import build_sam3_image_model
            from sam3.model.sam3_image_processor import Sam3Processor
        except ImportError as exc:
            raise RuntimeError(
                "SAM3 backend is selected but the local 'sam3' runtime could not be imported"
            ) from exc

        checkpoint_path = self.sam3_checkpoint_path
        if not checkpoint_path:
            raise RuntimeError("SAM3 backend requires a checkpoint path")

        model = build_sam3_image_model(
            checkpoint_path=str(checkpoint_path),
            device=str(get_device()),
            load_from_HF=False,
            enable_inst_interactivity=True,
        )
        predictor = getattr(model, "inst_interactive_predictor", None)
        if predictor is None:
            raise RuntimeError("SAM3 image model did not expose an interactive predictor")
        processor = Sam3Processor(model, device=str(get_device()))
        return Sam3MaskController(model, processor)

    @staticmethod
    def _validate_unit_interval(value: float, *, field_name: str) -> float:
        numeric = float(value)
        if numeric < 0.0 or numeric > 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0")
        return numeric

    @staticmethod
    def _odd_kernel_size(size: int) -> int:
        return size if size % 2 == 1 else size + 1

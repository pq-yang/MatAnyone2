import numpy as np
from PIL import Image

from matanyone2.webapp.models import DraftRecord
from matanyone2.webapp.services.masking import MaskingService, merge_masks


def test_merge_masks_collapses_multiple_targets_into_single_uint8_mask():
    mask_a = np.array([[1, 0], [0, 0]], dtype=np.uint8)
    mask_b = np.array([[0, 0], [1, 0]], dtype=np.uint8)

    merged = merge_masks([mask_a, mask_b])

    assert merged.dtype == np.uint8
    assert merged.tolist() == [[255, 0], [255, 0]]


def test_apply_click_and_save_mask_persists_named_mask(tmp_path):
    template_frame = tmp_path / "template.png"
    Image.new("RGB", (4, 4), color=(0, 0, 0)).save(template_frame)
    draft = DraftRecord(
        draft_id="draft-1",
        video_path=tmp_path / "input.mp4",
        template_frame_path=template_frame,
        width=4,
        height=4,
        fps=24.0,
        frame_count=1,
        duration_seconds=0.04,
    )

    class FakeController:
        def __init__(self):
            self.calls = []

        def first_frame_click(self, image, points, labels, multimask=True):
            self.calls.append((points.copy(), labels.copy(), multimask))
            mask = np.zeros((4, 4), dtype=np.uint8)
            mask[1, 1] = 1
            return mask, np.zeros((4, 4), dtype=np.float32), Image.fromarray(image)

    controller = FakeController()
    service = MaskingService(runtime_root=tmp_path, controller_factory=lambda: controller)
    session = service.create_session(draft)

    result = service.apply_click(session, x=1, y=1, positive=True)
    mask_name = service.save_current_mask(session)

    assert result.current_mask_path.exists()
    assert mask_name == "mask_001"
    assert session.saved_masks[mask_name].exists()
    assert controller.calls[0][0].tolist() == [[1, 1]]

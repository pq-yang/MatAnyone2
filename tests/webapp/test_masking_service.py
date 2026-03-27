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


def test_save_current_mask_resets_click_history_for_next_target(tmp_path):
    template_frame = tmp_path / "template.png"
    Image.new("RGB", (10, 10), color=(0, 0, 0)).save(template_frame)
    draft = DraftRecord(
        draft_id="draft-1",
        video_path=tmp_path / "input.mp4",
        template_frame_path=template_frame,
        width=10,
        height=10,
        fps=24.0,
        frame_count=1,
        duration_seconds=0.04,
    )

    class FakeController:
        def __init__(self):
            self.calls = []

        def first_frame_click(self, image, points, labels, multimask=True):
            self.calls.append((points.copy(), labels.copy(), multimask))
            mask = np.zeros((10, 10), dtype=np.uint8)
            for x, y in points.tolist():
                mask[y, x] = 1
            return mask, np.zeros((10, 10), dtype=np.float32), Image.fromarray(image)

    controller = FakeController()
    service = MaskingService(runtime_root=tmp_path, controller_factory=lambda: controller)
    session = service.create_session(draft)

    service.apply_click(session, x=1, y=1, positive=True)
    service.save_current_mask(session)
    service.apply_click(session, x=8, y=8, positive=True)

    assert session.click_points == [(8, 8)]
    assert session.click_labels == [1]
    assert controller.calls[1][0].tolist() == [[8, 8]]


def test_update_target_mutates_name_visibility_and_lock_state(tmp_path):
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

    service = MaskingService(runtime_root=tmp_path, controller_factory=lambda: None)
    session = service.create_session(draft)
    target = service.create_target(session, name="Hero")

    updated = service.update_target(
        session,
        target.target_id,
        name="Lead Actor",
        visible=False,
        locked=True,
    )

    assert updated.name == "Lead Actor"
    assert updated.visible is False
    assert updated.locked is True

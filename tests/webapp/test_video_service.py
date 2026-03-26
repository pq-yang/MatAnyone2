from pathlib import Path

from matanyone2.webapp.services.video import VideoDraftService


def test_create_draft_extracts_template_frame_and_metadata(tmp_path, sample_video_path):
    service = VideoDraftService(
        runtime_root=tmp_path,
        max_video_seconds=10,
        max_upload_bytes=10_000_000,
    )
    draft = service.create_draft(Path(sample_video_path))

    assert draft.frame_count > 0
    assert draft.template_frame_path.exists()
    assert draft.duration_seconds <= 10

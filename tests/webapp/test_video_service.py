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
    assert draft.template_frame_index == 0


def test_create_draft_records_browser_preview_path(tmp_path, sample_video_path, monkeypatch):
    service = VideoDraftService(
        runtime_root=tmp_path,
        max_video_seconds=10,
        max_upload_bytes=10_000_000,
    )

    def fake_ensure_browser_preview(video_path, *, preview_path=None):
        assert preview_path is not None
        preview_path.write_bytes(b"preview")
        return preview_path

    monkeypatch.setattr(service, "ensure_browser_preview", fake_ensure_browser_preview)

    draft = service.create_draft(Path(sample_video_path))

    assert draft.browser_preview_path is not None
    assert draft.browser_preview_path.name == "preview_source.mp4"
    assert draft.browser_preview_path.exists()


def test_select_template_frame_updates_draft_metadata_and_file(tmp_path, sample_video_path):
    service = VideoDraftService(
        runtime_root=tmp_path,
        max_video_seconds=10,
        max_upload_bytes=10_000_000,
    )
    draft = service.create_draft(Path(sample_video_path))

    updated = service.select_template_frame(draft, 2)

    assert updated.template_frame_index == 2
    assert updated.template_frame_path.exists()

from pathlib import Path

from matanyone2.webapp.services.inference import InferenceService


def test_run_job_writes_foreground_and_alpha_outputs(tmp_path, monkeypatch):
    service = InferenceService(model_name="MatAnyone 2")
    job_dir = tmp_path / "job-1"
    job_dir.mkdir()

    monkeypatch.setattr(
        service,
        "_run_model",
        lambda **_: (Path(job_dir / "foreground.mp4"), Path(job_dir / "alpha.mp4")),
    )
    result = service.run_job(
        source_video_path=Path("input.mp4"),
        mask_path=Path("mask.png"),
        job_dir=job_dir,
        template_frame_index=0,
    )

    assert result.foreground_video_path.name == "foreground.mp4"
    assert result.alpha_video_path.name == "alpha.mp4"

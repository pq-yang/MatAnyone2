from pathlib import Path

import torch

from matanyone2.utils.get_default_model import get_matanyone2_model
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
        process_start_frame_index=0,
        process_end_frame_index=None,
    )

    assert result.foreground_video_path.name == "foreground.mp4"
    assert result.alpha_video_path.name == "alpha.mp4"


def test_run_job_dispatches_bidirectional_flow_for_nonzero_template_frame_index(
    tmp_path,
    monkeypatch,
):
    service = InferenceService(model_name="MatAnyone 2")
    job_dir = tmp_path / "job-1"
    job_dir.mkdir()
    observed = {}

    def fake_bidirectional(**kwargs):
        observed.update(kwargs)
        return Path(job_dir / "foreground.mp4"), Path(job_dir / "alpha.mp4")

    monkeypatch.setattr(service, "_run_bidirectional_job", fake_bidirectional, raising=False)

    result = service.run_job(
        source_video_path=Path("input.mp4"),
        mask_path=Path("mask.png"),
        job_dir=job_dir,
        template_frame_index=12,
        process_start_frame_index=0,
        process_end_frame_index=None,
    )

    assert observed["template_frame_index"] == 12
    assert result.foreground_video_path.name == "foreground.mp4"


def test_run_job_uses_processing_range_clip_and_relative_anchor(tmp_path, monkeypatch):
    service = InferenceService(model_name="MatAnyone 2")
    job_dir = tmp_path / "job-1"
    job_dir.mkdir()
    observed = {}

    def fake_prepare_processing_clip(**kwargs):
        observed["clip_request"] = kwargs
        clip_path = job_dir / "processing_range.mp4"
        clip_path.write_bytes(b"clip")
        return clip_path, 1, 3.0

    def fake_bidirectional(**kwargs):
        observed["bidirectional"] = kwargs
        return Path(job_dir / "foreground.mp4"), Path(job_dir / "alpha.mp4")

    monkeypatch.setattr(service, "_prepare_processing_clip", fake_prepare_processing_clip, raising=False)
    monkeypatch.setattr(service, "_run_bidirectional_job", fake_bidirectional, raising=False)

    result = service.run_job(
        source_video_path=Path("input.mp4"),
        mask_path=Path("mask.png"),
        job_dir=job_dir,
        template_frame_index=3,
        process_start_frame_index=2,
        process_end_frame_index=4,
    )

    assert observed["clip_request"]["process_start_frame_index"] == 2
    assert observed["clip_request"]["process_end_frame_index"] == 4
    assert observed["bidirectional"]["source_video_path"] == job_dir / "processing_range.mp4"
    assert observed["bidirectional"]["template_frame_index"] == 1
    assert result.foreground_video_path.name == "foreground.mp4"


def test_run_job_passes_resolved_inference_hyperparameters_to_model(tmp_path, monkeypatch):
    service = InferenceService(model_name="MatAnyone 2")
    job_dir = tmp_path / "job-1"
    job_dir.mkdir()
    observed = {}

    clip_path = job_dir / "processing_range.mp4"
    clip_path.write_bytes(b"clip")

    monkeypatch.setattr(
        service,
        "_prepare_processing_clip",
        lambda **kwargs: (clip_path, 0, 24.0),
        raising=False,
    )
    monkeypatch.setattr(
        service,
        "_resolve_inference_hyperparameters",
        lambda **kwargs: {"n_warmup": 12, "r_erode": 14, "r_dilate": 16},
        raising=False,
    )

    def fake_run_model(**kwargs):
        observed.update(kwargs)
        return Path(job_dir / "foreground.mp4"), Path(job_dir / "alpha.mp4")

    monkeypatch.setattr(service, "_run_model", fake_run_model, raising=False)

    service.run_job(
        source_video_path=Path("input.mp4"),
        mask_path=Path("mask.png"),
        job_dir=job_dir,
        template_frame_index=0,
        process_start_frame_index=0,
        process_end_frame_index=None,
        selected_mask_controls={"mask_001": {"edge_feather_radius": 6.0, "temporal_stability": 0.8}},
        selected_mask_presets={"mask_001": "hair"},
    )

    assert observed["n_warmup"] == 12
    assert observed["r_erode"] == 14
    assert observed["r_dilate"] == 16


def test_get_matanyone2_model_can_be_called_twice_in_same_process(monkeypatch, tmp_path):
    checkpoint_path = tmp_path / "matanyone2.pth"
    checkpoint_path.write_bytes(b"weights")

    class FakeModel:
        def __init__(self, cfg, single_object):
            self.cfg = cfg
            self.single_object = single_object
            self.loaded_weights = None

        def to(self, device):
            self.device = device
            return self

        def eval(self):
            return self

        def load_weights(self, weights):
            self.loaded_weights = weights

    monkeypatch.setattr(
        "matanyone2.utils.get_default_model.MatAnyone2",
        FakeModel,
    )
    monkeypatch.setattr(
        "matanyone2.utils.get_default_model.torch.load",
        lambda path, map_location=None: {"path": str(path), "map_location": str(map_location)},
    )

    first_model = get_matanyone2_model(str(checkpoint_path), device=torch.device("cpu"))
    second_model = get_matanyone2_model(str(checkpoint_path), device=torch.device("cpu"))

    assert first_model.cfg.weights == str(checkpoint_path)
    assert second_model.cfg.weights == str(checkpoint_path)

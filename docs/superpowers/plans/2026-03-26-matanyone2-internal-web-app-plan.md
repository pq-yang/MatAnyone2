# MatAnyone2 Internal Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-machine internal web app that supports upload, template-frame target selection, queued MatAnyone2 processing, and transparent result download for short clips.

**Architecture:** Add a new `matanyone2.webapp` package inside the existing repository. Keep the current Hugging Face demo as reference-only code, extract reusable masking and inference behaviors into service modules, and run GPU inference/export in a separate worker process backed by SQLite job persistence and per-job runtime directories.

**Tech Stack:** Python 3.10+, FastAPI, Jinja2 templates, vanilla JavaScript, sqlite3, ffmpeg, pytest, existing MatAnyone2 inference code, existing SAM interaction code from `hugging_face/tools`

---

## File Structure

### Modify

- `D:\my_app\matanyone2\pyproject.toml`
  Add runtime/test dependencies for the internal web app and expose optional scripts if desired.
- `D:\my_app\matanyone2\README.md`
  Add a short internal-web-app section with run commands after implementation is complete.

### Create

- `D:\my_app\matanyone2\matanyone2\webapp\__init__.py`
  Package marker.
- `D:\my_app\matanyone2\matanyone2\webapp\config.py`
  Environment-driven settings object for runtime paths, size limits, queue policy, and export toggles.
- `D:\my_app\matanyone2\matanyone2\webapp\runtime_paths.py`
  Helpers for creating and resolving runtime directories for jobs, drafts, uploads, and exports.
- `D:\my_app\matanyone2\matanyone2\webapp\db.py`
  SQLite schema initialization and connection helpers.
- `D:\my_app\matanyone2\matanyone2\webapp\models.py`
  Dataclasses and typed enums for job status, draft payloads, and export outcomes.
- `D:\my_app\matanyone2\matanyone2\webapp\repository.py`
  CRUD operations for jobs and queue ordering.
- `D:\my_app\matanyone2\matanyone2\webapp\queue.py`
  Single-worker queue coordinator and restart recovery logic.
- `D:\my_app\matanyone2\matanyone2\webapp\worker.py`
  Worker loop that consumes queued jobs and drives inference/export.
- `D:\my_app\matanyone2\matanyone2\webapp\services\__init__.py`
  Services package marker.
- `D:\my_app\matanyone2\matanyone2\webapp\services\video.py`
  Upload staging, metadata extraction, frame extraction, and draft creation helpers.
- `D:\my_app\matanyone2\matanyone2\webapp\services\masking.py`
  SAM-backed click refinement, multi-mask merge, and mask persistence logic.
- `D:\my_app\matanyone2\matanyone2\webapp\services\inference.py`
  MatAnyone2 wrapper that accepts a job payload and writes foreground/alpha intermediates.
- `D:\my_app\matanyone2\matanyone2\webapp\services\export.py`
  RGBA PNG sequence generation, zip packaging, and best-effort ProRes export.
- `D:\my_app\matanyone2\matanyone2\webapp\api\__init__.py`
  API package marker.
- `D:\my_app\matanyone2\matanyone2\webapp\api\app.py`
  FastAPI app factory and startup wiring.
- `D:\my_app\matanyone2\matanyone2\webapp\api\dependencies.py`
  Shared dependency providers for settings, repository, queue, and services.
- `D:\my_app\matanyone2\matanyone2\webapp\api\routes\__init__.py`
  Routes package marker.
- `D:\my_app\matanyone2\matanyone2\webapp\api\routes\pages.py`
  HTML pages for upload, annotation, and job status.
- `D:\my_app\matanyone2\matanyone2\webapp\api\routes\uploads.py`
  Video upload, draft creation, and template-frame metadata endpoints.
- `D:\my_app\matanyone2\matanyone2\webapp\api\routes\annotation.py`
  Click-refinement, mask merge, and submission endpoints.
- `D:\my_app\matanyone2\matanyone2\webapp\api\routes\jobs.py`
  Job status JSON endpoints and artifact download endpoints.
- `D:\my_app\matanyone2\matanyone2\webapp\templates\base.html`
  Shared layout.
- `D:\my_app\matanyone2\matanyone2\webapp\templates\upload.html`
  Upload step UI.
- `D:\my_app\matanyone2\matanyone2\webapp\templates\annotate.html`
  Annotation step UI with template frame, controls, and queue submit button.
- `D:\my_app\matanyone2\matanyone2\webapp\templates\job.html`
  Job status and download UI.
- `D:\my_app\matanyone2\matanyone2\webapp\static\styles.css`
  Minimal UI styling.
- `D:\my_app\matanyone2\matanyone2\webapp\static\annotator.js`
  Client-side click capture, mask preview refresh, and polling.
- `D:\my_app\matanyone2\scripts\run_internal_webapp.py`
  App startup entry point.
- `D:\my_app\matanyone2\scripts\run_internal_worker.py`
  Worker startup entry point.
- `D:\my_app\matanyone2\tests\webapp\conftest.py`
  Shared fixtures for temp runtime directories, fake settings, and app factory helpers.
- `D:\my_app\matanyone2\tests\webapp\test_app_factory.py`
  App-factory and startup smoke tests.
- `D:\my_app\matanyone2\tests\webapp\test_repository.py`
  SQLite repository and queue ordering tests.
- `D:\my_app\matanyone2\tests\webapp\test_video_service.py`
  Draft creation and metadata extraction tests.
- `D:\my_app\matanyone2\tests\webapp\test_masking_service.py`
  Click refinement and mask merge tests with SAM monkeypatching.
- `D:\my_app\matanyone2\tests\webapp\test_inference_service.py`
  Inference wrapper tests with processor monkeypatching.
- `D:\my_app\matanyone2\tests\webapp\test_export_service.py`
  RGBA PNG, zip, and warning-path export tests.
- `D:\my_app\matanyone2\tests\webapp\test_worker.py`
  Worker state transition and restart recovery tests.
- `D:\my_app\matanyone2\tests\webapp\test_api_flow.py`
  End-to-end request flow tests with fake inference/export services.

## Task 1: Bootstrap The Web App Package

**Files:**
- Create: `D:\my_app\matanyone2\matanyone2\webapp\__init__.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\config.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\api\__init__.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\api\app.py`
- Create: `D:\my_app\matanyone2\scripts\run_internal_webapp.py`
- Create: `D:\my_app\matanyone2\tests\webapp\conftest.py`
- Create: `D:\my_app\matanyone2\tests\webapp\test_app_factory.py`
- Modify: `D:\my_app\matanyone2\pyproject.toml`

- [ ] **Step 1: Write the failing smoke test for settings and app factory**

```python
from fastapi.testclient import TestClient

from matanyone2.webapp.api.app import create_app
from matanyone2.webapp.config import WebAppSettings


def test_create_app_builds_health_route(tmp_path, monkeypatch):
    monkeypatch.setenv("MATANYONE2_WEBAPP_RUNTIME_ROOT", str(tmp_path))
    settings = WebAppSettings()
    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `python -m pytest tests\webapp\test_app_factory.py -q`
Expected: FAIL with `ModuleNotFoundError` or missing `create_app`.

- [ ] **Step 3: Implement settings, app factory, and startup script**

```python
# matanyone2/webapp/config.py
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class WebAppSettings:
    runtime_root: Path = Path(os.getenv("MATANYONE2_WEBAPP_RUNTIME_ROOT", "runtime/webapp"))
    database_path: Path = Path(os.getenv("MATANYONE2_WEBAPP_DATABASE_PATH", "runtime/webapp/jobs.db"))
    max_video_seconds: int = int(os.getenv("MATANYONE2_WEBAPP_MAX_VIDEO_SECONDS", "10"))
    max_upload_bytes: int = int(os.getenv("MATANYONE2_WEBAPP_MAX_UPLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))
    enable_prores_export: bool = os.getenv("MATANYONE2_WEBAPP_ENABLE_PRORES", "1") == "1"


# matanyone2/webapp/api/app.py
from fastapi import FastAPI


def create_app(settings=None) -> FastAPI:
    app = FastAPI(title="MatAnyone2 Internal Web App")
    app.state.settings = settings

    @app.get("/healthz")
    def healthcheck():
        return {"status": "ok"}

    return app
```

- [ ] **Step 4: Update dependencies and rerun the smoke test**

Add to `pyproject.toml` dependencies:

```toml
"fastapi>=0.111,<1.0",
"uvicorn>=0.30,<1.0",
"jinja2>=3.1,<4.0",
"python-multipart>=0.0.9,<1.0",
"httpx>=0.27,<1.0",
"pytest>=8.0,<9.0",
```

Run: `python -m pytest tests\webapp\test_app_factory.py -q`
Expected: PASS

- [ ] **Step 5: Commit the bootstrap**

```bash
git add pyproject.toml matanyone2/webapp scripts/run_internal_webapp.py tests/webapp
git commit -m "feat: bootstrap internal web app package"
```

## Task 2: Add Persistent Runtime Paths And SQLite Job Storage

**Files:**
- Create: `D:\my_app\matanyone2\matanyone2\webapp\runtime_paths.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\db.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\models.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\repository.py`
- Create: `D:\my_app\matanyone2\tests\webapp\test_repository.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\api\app.py`

- [ ] **Step 1: Write failing repository tests for create, update, and queue order**

```python
from matanyone2.webapp.models import JobStatus
from matanyone2.webapp.repository import JobRepository


def test_repository_creates_job_and_reports_queue_position(tmp_path):
    repo = JobRepository.from_path(tmp_path / "jobs.db")
    first = repo.create_job(source_video_path="a.mp4", template_frame_index=0, mask_path="a.png", params_json="{}")
    second = repo.create_job(source_video_path="b.mp4", template_frame_index=0, mask_path="b.png", params_json="{}")

    assert repo.get_job(first.job_id).status is JobStatus.QUEUED
    assert repo.get_queue_position(second.job_id) == 2
```

- [ ] **Step 2: Run the repository tests to verify they fail**

Run: `python -m pytest tests\webapp\test_repository.py -q`
Expected: FAIL because the repository and models do not exist yet.

- [ ] **Step 3: Implement SQLite schema, typed statuses, and runtime-path helpers**

```python
from dataclasses import dataclass
from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNING = "completed_with_warning"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(slots=True)
class JobRecord:
    job_id: str
    status: JobStatus
    source_video_path: str
    mask_path: str
    template_frame_index: int
    params_json: str
    warning_text: str | None = None
    error_text: str | None = None
```

- [ ] **Step 4: Wire database initialization into app startup and rerun tests**

Run: `python -m pytest tests\webapp\test_repository.py tests\webapp\test_app_factory.py -q`
Expected: PASS

- [ ] **Step 5: Commit the persistence layer**

```bash
git add matanyone2/webapp/runtime_paths.py matanyone2/webapp/db.py matanyone2/webapp/models.py matanyone2/webapp/repository.py matanyone2/webapp/api/app.py tests/webapp/test_repository.py
git commit -m "feat: add persistent job repository"
```

## Task 3: Add Queue Coordination And Worker Recovery

**Files:**
- Create: `D:\my_app\matanyone2\matanyone2\webapp\queue.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\worker.py`
- Create: `D:\my_app\matanyone2\scripts\run_internal_worker.py`
- Create: `D:\my_app\matanyone2\tests\webapp\test_worker.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\api\app.py`

- [ ] **Step 1: Write failing queue and restart-recovery tests**

```python
from matanyone2.webapp.models import JobStatus
from matanyone2.webapp.queue import QueueCoordinator
from matanyone2.webapp.repository import JobRepository


def test_recover_running_jobs_marks_them_interrupted(tmp_path):
    repo = JobRepository.from_path(tmp_path / "jobs.db")
    job = repo.create_job(source_video_path="a.mp4", template_frame_index=0, mask_path="a.png", params_json="{}")
    repo.update_status(job.job_id, JobStatus.RUNNING)

    coordinator = QueueCoordinator(repo)
    coordinator.recover_interrupted_jobs()

    assert repo.get_job(job.job_id).status is JobStatus.INTERRUPTED
```

- [ ] **Step 2: Run the worker tests to verify they fail**

Run: `python -m pytest tests\webapp\test_worker.py -q`
Expected: FAIL because queue coordination does not exist yet.

- [ ] **Step 3: Implement queue coordinator, worker loop, and script entry point**

```python
class QueueCoordinator:
    def __init__(self, repository):
        self.repository = repository

    def recover_interrupted_jobs(self) -> None:
        self.repository.mark_running_jobs_interrupted()

    def next_job_id(self) -> str | None:
        next_job = self.repository.next_queued_job()
        return None if next_job is None else next_job.job_id
```

- [ ] **Step 4: Rerun worker tests and verify app startup triggers recovery**

Run: `python -m pytest tests\webapp\test_worker.py tests\webapp\test_app_factory.py -q`
Expected: PASS

- [ ] **Step 5: Commit the queue layer**

```bash
git add matanyone2/webapp/queue.py matanyone2/webapp/worker.py scripts/run_internal_worker.py matanyone2/webapp/api/app.py tests/webapp/test_worker.py
git commit -m "feat: add queue coordination and worker recovery"
```

## Task 4: Add Video Draft Creation And Upload Validation

**Files:**
- Create: `D:\my_app\matanyone2\matanyone2\webapp\services\video.py`
- Create: `D:\my_app\matanyone2\tests\webapp\test_video_service.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\models.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\runtime_paths.py`

- [ ] **Step 1: Write failing tests for draft creation and duration limits**

```python
from pathlib import Path

from matanyone2.webapp.services.video import VideoDraftService


def test_create_draft_extracts_template_frame_and_metadata(tmp_path, sample_video_path):
    service = VideoDraftService(runtime_root=tmp_path, max_video_seconds=10, max_upload_bytes=10_000_000)
    draft = service.create_draft(Path(sample_video_path))

    assert draft.frame_count > 0
    assert draft.template_frame_path.exists()
    assert draft.duration_seconds <= 10
```

- [ ] **Step 2: Run the draft tests to verify they fail**

Run: `python -m pytest tests\webapp\test_video_service.py -q`
Expected: FAIL because `VideoDraftService` does not exist yet.

- [ ] **Step 3: Implement upload staging, metadata extraction, and template-frame image output**

```python
@dataclass(slots=True)
class DraftRecord:
    draft_id: str
    video_path: Path
    template_frame_path: Path
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float
```

- [ ] **Step 4: Rerun draft tests with a generated short sample video fixture**

Run: `python -m pytest tests\webapp\test_video_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit the draft service**

```bash
git add matanyone2/webapp/services/video.py matanyone2/webapp/models.py matanyone2/webapp/runtime_paths.py tests/webapp/test_video_service.py tests/webapp/conftest.py
git commit -m "feat: add upload draft and video validation service"
```

## Task 5: Extract SAM Masking And Multi-Mask Merge Into A Service

**Files:**
- Create: `D:\my_app\matanyone2\matanyone2\webapp\services\masking.py`
- Create: `D:\my_app\matanyone2\tests\webapp\test_masking_service.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\models.py`

- [ ] **Step 1: Write failing tests for click refinement and merged mask output**

```python
import numpy as np

from matanyone2.webapp.services.masking import merge_masks


def test_merge_masks_collapses_multiple_targets_into_single_uint8_mask():
    mask_a = np.array([[1, 0], [0, 0]], dtype=np.uint8)
    mask_b = np.array([[0, 0], [1, 0]], dtype=np.uint8)

    merged = merge_masks([mask_a, mask_b])

    assert merged.dtype == np.uint8
    assert merged.tolist() == [[255, 0], [255, 0]]
```

- [ ] **Step 2: Run the masking tests to verify they fail**

Run: `python -m pytest tests\webapp\test_masking_service.py -q`
Expected: FAIL because the masking service does not exist yet.

- [ ] **Step 3: Implement a service that wraps current SAM interaction utilities**

```python
from hugging_face.tools.interact_tools import SamControler


def merge_masks(masks: list[np.ndarray]) -> np.ndarray:
    if not masks:
        raise ValueError("at least one mask is required")
    merged = np.zeros_like(masks[0], dtype=np.uint8)
    for mask in masks:
        merged = np.where(mask > 0, 255, merged).astype(np.uint8)
    return merged
```

- [ ] **Step 4: Add monkeypatched refinement tests and rerun**

Run: `python -m pytest tests\webapp\test_masking_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit the masking service**

```bash
git add matanyone2/webapp/services/masking.py matanyone2/webapp/models.py tests/webapp/test_masking_service.py
git commit -m "feat: extract masking refinement service"
```

## Task 6: Wrap MatAnyone2 Inference For Job Execution

**Files:**
- Create: `D:\my_app\matanyone2\matanyone2\webapp\services\inference.py`
- Create: `D:\my_app\matanyone2\tests\webapp\test_inference_service.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\models.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\worker.py`

- [ ] **Step 1: Write failing tests for inference output paths and state transitions**

```python
from pathlib import Path

from matanyone2.webapp.services.inference import InferenceService


def test_run_job_writes_foreground_and_alpha_outputs(tmp_path, monkeypatch):
    service = InferenceService(model_name="MatAnyone 2")
    job_dir = tmp_path / "job-1"
    job_dir.mkdir()

    monkeypatch.setattr(service, "_run_model", lambda **_: (Path(job_dir / "foreground.mp4"), Path(job_dir / "alpha.mp4")))
    result = service.run_job(source_video_path=Path("input.mp4"), mask_path=Path("mask.png"), job_dir=job_dir, template_frame_index=0)

    assert result.foreground_video_path.name == "foreground.mp4"
    assert result.alpha_video_path.name == "alpha.mp4"
```

- [ ] **Step 2: Run the inference tests to verify they fail**

Run: `python -m pytest tests\webapp\test_inference_service.py -q`
Expected: FAIL because the inference service does not exist yet.

- [ ] **Step 3: Implement a thin wrapper around the current repository inference path**

```python
@dataclass(slots=True)
class InferenceResult:
    foreground_video_path: Path
    alpha_video_path: Path


class InferenceService:
    def run_job(self, source_video_path: Path, mask_path: Path, job_dir: Path, template_frame_index: int) -> InferenceResult:
        foreground_path = job_dir / "foreground.mp4"
        alpha_path = job_dir / "alpha.mp4"
        self._run_model(
            source_video_path=source_video_path,
            mask_path=mask_path,
            foreground_path=foreground_path,
            alpha_path=alpha_path,
            template_frame_index=template_frame_index,
        )
        return InferenceResult(foreground_video_path=foreground_path, alpha_video_path=alpha_path)
```

- [ ] **Step 4: Integrate the inference wrapper into the worker and rerun tests**

Run: `python -m pytest tests\webapp\test_inference_service.py tests\webapp\test_worker.py -q`
Expected: PASS

- [ ] **Step 5: Commit the inference service**

```bash
git add matanyone2/webapp/services/inference.py matanyone2/webapp/models.py matanyone2/webapp/worker.py tests/webapp/test_inference_service.py
git commit -m "feat: wrap matanyone2 inference for queued jobs"
```

## Task 7: Add Transparent Export Packaging

**Files:**
- Create: `D:\my_app\matanyone2\matanyone2\webapp\services\export.py`
- Create: `D:\my_app\matanyone2\tests\webapp\test_export_service.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\models.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\worker.py`

- [ ] **Step 1: Write failing tests for RGBA PNG zip success and ProRes warning fallback**

```python
from pathlib import Path

from matanyone2.webapp.services.export import ExportService


def test_export_assets_creates_png_zip_even_when_prores_fails(tmp_path, monkeypatch):
    service = ExportService(enable_prores=True)
    foreground = tmp_path / "foreground.mp4"
    alpha = tmp_path / "alpha.mp4"
    foreground.write_bytes(b"fg")
    alpha.write_bytes(b"a")

    monkeypatch.setattr(service, "_extract_frames", lambda *args, **kwargs: ([tmp_path / "fg-0001.png"], [tmp_path / "a-0001.png"]))
    monkeypatch.setattr(service, "_write_rgba_pngs", lambda *args, **kwargs: tmp_path / "rgba_png")
    monkeypatch.setattr(service, "_zip_directory", lambda *args, **kwargs: tmp_path / "rgba_png.zip")
    monkeypatch.setattr(service, "_export_prores", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ffmpeg failed")))

    result = service.export_assets(foreground, alpha, tmp_path)

    assert result.png_zip_path.name == "rgba_png.zip"
    assert result.warning_text == "ffmpeg failed"
```

- [ ] **Step 2: Run the export tests to verify they fail**

Run: `python -m pytest tests\webapp\test_export_service.py -q`
Expected: FAIL because the export service does not exist yet.

- [ ] **Step 3: Implement RGBA composition, zip packaging, and warning-path ProRes export**

```python
@dataclass(slots=True)
class ExportResult:
    rgba_png_dir: Path
    png_zip_path: Path
    prores_path: Path | None
    warning_text: str | None


def compose_rgba_frame(foreground_rgb: np.ndarray, alpha_gray: np.ndarray) -> Image.Image:
    rgba = np.dstack([foreground_rgb, alpha_gray]).astype(np.uint8)
    return Image.fromarray(rgba, mode="RGBA")
```

- [ ] **Step 4: Update worker final-status logic and rerun export tests**

Run: `python -m pytest tests\webapp\test_export_service.py tests\webapp\test_worker.py -q`
Expected: PASS

- [ ] **Step 5: Commit the export layer**

```bash
git add matanyone2/webapp/services/export.py matanyone2/webapp/models.py matanyone2/webapp/worker.py tests/webapp/test_export_service.py
git commit -m "feat: add transparent export packaging"
```

## Task 8: Build The Upload, Annotation, Job, And Download Web Flow

**Files:**
- Create: `D:\my_app\matanyone2\matanyone2\webapp\api\dependencies.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\api\routes\pages.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\api\routes\uploads.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\api\routes\annotation.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\api\routes\jobs.py`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\templates\base.html`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\templates\upload.html`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\templates\annotate.html`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\templates\job.html`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\static\styles.css`
- Create: `D:\my_app\matanyone2\matanyone2\webapp\static\annotator.js`
- Create: `D:\my_app\matanyone2\tests\webapp\test_api_flow.py`
- Modify: `D:\my_app\matanyone2\matanyone2\webapp\api\app.py`

- [ ] **Step 1: Write failing API flow tests for upload, annotate, submit, and status**

```python
from fastapi.testclient import TestClient


def test_submit_flow_returns_job_page(app_client: TestClient, sample_video_upload):
    upload_response = app_client.post("/api/uploads", files={"video": sample_video_upload})
    assert upload_response.status_code == 200
    draft_id = upload_response.json()["draft_id"]

    annotate_response = app_client.post(
        f"/api/drafts/{draft_id}/submit",
        json={"template_frame_index": 0, "selected_masks": ["mask_001"]},
    )

    assert annotate_response.status_code == 200
    assert annotate_response.json()["status"] == "queued"
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run: `python -m pytest tests\webapp\test_api_flow.py -q`
Expected: FAIL because routes and templates do not exist yet.

- [ ] **Step 3: Implement the three-page web flow and JSON endpoints**

```python
router = APIRouter()


@router.post("/api/uploads")
async def upload_video(video: UploadFile, video_service=Depends(get_video_service)):
    draft = await video_service.create_draft_from_upload(video)
    return {"draft_id": draft.draft_id, "template_frame_url": f"/api/drafts/{draft.draft_id}/template-frame"}


@router.get("/jobs/{job_id}")
def job_page(job_id: str, request: Request, repository=Depends(get_repository)):
    job = repository.get_job(job_id)
    return templates.TemplateResponse("job.html", {"request": request, "job": job})
```

- [ ] **Step 4: Rerun API tests with fake services monkeypatched into dependencies**

Run: `python -m pytest tests\webapp\test_api_flow.py tests\webapp\test_app_factory.py -q`
Expected: PASS

- [ ] **Step 5: Commit the web flow**

```bash
git add matanyone2/webapp/api matanyone2/webapp/templates matanyone2/webapp/static tests/webapp/test_api_flow.py
git commit -m "feat: add internal web upload and job flow"
```

## Task 9: Finish End-To-End Verification And Operator Documentation

**Files:**
- Modify: `D:\my_app\matanyone2\tests\webapp\conftest.py`
- Modify: `D:\my_app\matanyone2\tests\webapp\test_worker.py`
- Modify: `D:\my_app\matanyone2\tests\webapp\test_api_flow.py`
- Modify: `D:\my_app\matanyone2\README.md`

- [ ] **Step 1: Add failing tests for restart behavior and queue handoff**

```python
def test_second_job_waits_until_first_job_finishes(app_client, seeded_jobs):
    first_job_id, second_job_id = seeded_jobs

    first_status = app_client.get(f"/api/jobs/{first_job_id}").json()
    second_status = app_client.get(f"/api/jobs/{second_job_id}").json()

    assert first_status["status"] == "running"
    assert second_status["status"] == "queued"
    assert second_status["queue_position"] == 1
```

- [ ] **Step 2: Run the full webapp test suite to verify the new checks fail**

Run: `python -m pytest tests\webapp -q`
Expected: FAIL on the newly added restart or queue handoff assertions.

- [ ] **Step 3: Implement the missing restart/status details and update operator docs**

````markdown
## Internal Web App

Run the web server:

```shell
python scripts/run_internal_webapp.py
```

Run the worker in a separate process:

```shell
python scripts/run_internal_worker.py
```
````

- [ ] **Step 4: Run the full webapp suite and a syntax smoke check**

Run: `python -m pytest tests\webapp -q`
Expected: PASS

Run: `python -m compileall matanyone2\webapp scripts\run_internal_webapp.py scripts\run_internal_worker.py`
Expected: PASS with no syntax errors

- [ ] **Step 5: Commit the final plan deliverable**

```bash
git add tests/webapp README.md
git commit -m "test: cover internal web app flow and docs"
```

## Manual Verification Checklist

- Upload a real short clip from `D:\my_app\matanyone2\test_sample`.
- Select a non-zero template frame and verify the displayed frame changes.
- Add positive and negative clicks, save two masks, and submit a merged multi-target job.
- Submit a second job while the first is running and confirm the second shows queued status.
- Confirm the completed job exposes `foreground.mp4`, `alpha.mp4`, `rgba_png.zip`, and optionally `output_prores4444.mov`.
- Force a ProRes export failure and confirm the job lands in `completed_with_warning`.
- Restart the web process while a queued job exists and confirm it remains queued.
- Restart during a running job and confirm the old job becomes `interrupted`.

## Review Notes For The Implementer

- Keep `hugging_face/app.py` unchanged unless a small shared extraction is clearly lower-risk than duplication.
- Prefer monkeypatched lightweight tests over GPU-backed tests inside `pytest`.
- Treat RGBA PNG zip as the primary artifact; do not make ProRes success a hard requirement.
- Keep queue semantics simple: one worker, one running job, FIFO ordering.
- Avoid premature streaming refactors in version 1. Wrap the current memory-heavy inference path first, then optimize later.

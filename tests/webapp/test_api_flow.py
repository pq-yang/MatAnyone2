from fastapi.testclient import TestClient
from matanyone2.webapp.models import JobStatus


def test_upload_page_exposes_browser_entrypoint(app_client: TestClient):
    response = app_client.get("/")

    assert response.status_code == 200
    assert 'id="upload-form"' in response.text
    assert 'data-upload-endpoint="/api/uploads"' in response.text
    assert "/static/upload.js" in response.text


def test_submit_flow_returns_job_page(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    assert upload_response.status_code == 200
    draft_id = upload_response.json()["draft_id"]
    template_frame_url = upload_response.json()["template_frame_url"]

    template_response = app_client.get(template_frame_url)
    annotate_page = app_client.get(f"/drafts/{draft_id}/annotate")

    assert template_response.status_code == 200
    assert template_response.headers["content-type"] == "image/png"
    assert annotate_page.status_code == 200
    assert draft_id in annotate_page.text

    click_response = app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    assert click_response.status_code == 200
    current_preview_url = click_response.json()["current_preview_url"]
    preview_response = app_client.get(current_preview_url)

    assert preview_response.status_code == 200
    assert preview_response.headers["content-type"] == "image/png"
    assert 'id="annotator-app"' in annotate_page.text
    assert f'data-click-endpoint="/api/drafts/{draft_id}/click"' in annotate_page.text
    assert "/static/workbench.js" in annotate_page.text

    save_response = app_client.post(f"/api/drafts/{draft_id}/masks")
    assert save_response.status_code == 200
    assert save_response.json()["mask_name"] == "mask_001"

    annotate_response = app_client.post(
        f"/api/drafts/{draft_id}/submit",
        json={"template_frame_index": 0, "selected_masks": ["mask_001"]},
    )

    assert annotate_response.status_code == 200
    assert annotate_response.json()["status"] == "queued"


def test_annotation_page_exposes_workbench_contract(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    response = app_client.get(f"/drafts/{draft_id}/annotate")

    assert response.status_code == 200
    assert f'data-workbench-endpoint="/api/drafts/{draft_id}"' in response.text
    assert f'data-targets-endpoint="/api/drafts/{draft_id}/targets"' in response.text


def test_target_creation_and_selection_round_trip(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    state_response = app_client.get(f"/api/drafts/{draft_id}")
    create_response = app_client.post(
        f"/api/drafts/{draft_id}/targets",
        json={"name": "Hero"},
    )
    created = create_response.json()
    select_response = app_client.post(
        f"/api/drafts/{draft_id}/targets/{created['target_id']}/select"
    )
    selected = select_response.json()

    assert state_response.status_code == 200
    assert state_response.json()["stage"] == "coarse"
    assert state_response.json()["active_target_id"] is not None
    assert create_response.status_code == 200
    assert created["name"] == "Hero"
    assert any(target["name"] == "Hero" for target in created["targets"])
    assert select_response.status_code == 200
    assert selected["active_target_id"] == created["target_id"]
    assert any(
        target["target_id"] == created["target_id"] and target["selected"]
        for target in selected["targets"]
    )


def test_stage_change_round_trip(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    response = app_client.post(
        f"/api/drafts/{draft_id}/stage",
        json={"stage": "refine"},
    )

    assert response.status_code == 200
    assert response.json()["stage"] == "refine"


def test_upload_validation_errors_return_400(app_client: TestClient):
    with TestClient(app_client.app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/uploads",
            files={"video": ("broken.mp4", b"not-a-video", "video/mp4")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "unable to read video frames"


def test_second_job_waits_until_first_job_finishes(app_client, seeded_jobs):
    first_job_id, second_job_id = seeded_jobs

    first_status = app_client.get(f"/api/jobs/{first_job_id}").json()
    second_status = app_client.get(f"/api/jobs/{second_job_id}").json()

    assert first_status["status"] == "running"
    assert second_status["status"] == "queued"
    assert second_status["queue_position"] == 1


def test_job_page_exposes_polling_entrypoint(app_client):
    repository = app_client.app.state.repository
    job = repository.create_job(
        source_video_path="queued.mp4",
        template_frame_index=0,
        mask_path="queued.png",
        params_json="{}",
    )

    response = app_client.get(f"/jobs/{job.job_id}")

    assert response.status_code == 200
    assert 'id="job-app"' in response.text
    assert f'data-status-endpoint="/api/jobs/{job.job_id}"' in response.text
    assert 'id="artifact-list"' in response.text
    assert "/static/annotator.js" in response.text


def test_missing_job_page_returns_404(app_client: TestClient):
    with TestClient(app_client.app, raise_server_exceptions=False) as client:
        response = client.get("/jobs/missing-job")

    assert response.status_code == 404
    assert response.json()["detail"] == "job not found"


def test_completed_job_exposes_artifacts_and_downloads_zip(app_client):
    repository = app_client.app.state.repository
    runtime_root = app_client.app.state.settings.runtime_root
    job = repository.create_job(
        source_video_path="finished.mp4",
        template_frame_index=0,
        mask_path="finished.png",
        params_json="{}",
    )
    repository.update_status(job.job_id, JobStatus.COMPLETED)

    job_dir = runtime_root / "jobs" / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = job_dir / "rgba_png.zip"
    artifact_path.write_bytes(b"zip")

    status_response = app_client.get(f"/api/jobs/{job.job_id}")
    download_response = app_client.get(
        f"/api/jobs/{job.job_id}/artifacts/rgba_png.zip"
    )

    assert status_response.status_code == 200
    assert status_response.json()["artifacts"]["rgba_png.zip"].endswith("rgba_png.zip")
    assert download_response.status_code == 200
    assert download_response.content == b"zip"


def test_job_status_exposes_warning_and_error_text(app_client):
    repository = app_client.app.state.repository
    warning_job = repository.create_job(
        source_video_path="warning.mp4",
        template_frame_index=0,
        mask_path="warning.png",
        params_json="{}",
    )
    failed_job = repository.create_job(
        source_video_path="failed.mp4",
        template_frame_index=0,
        mask_path="failed.png",
        params_json="{}",
    )

    repository.update_status(
        warning_job.job_id,
        JobStatus.COMPLETED_WITH_WARNING,
        warning_text="prores export skipped",
    )
    repository.update_status(
        failed_job.job_id,
        JobStatus.FAILED,
        error_text="gpu worker crashed",
    )

    warning_response = app_client.get(f"/api/jobs/{warning_job.job_id}")
    failed_response = app_client.get(f"/api/jobs/{failed_job.job_id}")

    assert warning_response.status_code == 200
    assert warning_response.json()["warning_text"] == "prores export skipped"
    assert warning_response.json()["error_text"] is None
    assert failed_response.status_code == 200
    assert failed_response.json()["warning_text"] is None
    assert failed_response.json()["error_text"] == "gpu worker crashed"

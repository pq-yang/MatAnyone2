from fastapi.testclient import TestClient
from matanyone2.webapp.models import JobStatus


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

    click_response = app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    assert click_response.status_code == 200

    save_response = app_client.post(f"/api/drafts/{draft_id}/masks")
    assert save_response.status_code == 200
    assert save_response.json()["mask_name"] == "mask_001"

    annotate_response = app_client.post(
        f"/api/drafts/{draft_id}/submit",
        json={"template_frame_index": 0, "selected_masks": ["mask_001"]},
    )

    assert annotate_response.status_code == 200
    assert annotate_response.json()["status"] == "queued"


def test_second_job_waits_until_first_job_finishes(app_client, seeded_jobs):
    first_job_id, second_job_id = seeded_jobs

    first_status = app_client.get(f"/api/jobs/{first_job_id}").json()
    second_status = app_client.get(f"/api/jobs/{second_job_id}").json()

    assert first_status["status"] == "running"
    assert second_status["status"] == "queued"
    assert second_status["queue_position"] == 1


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

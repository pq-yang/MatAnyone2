from fastapi.testclient import TestClient


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

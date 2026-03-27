from fastapi.testclient import TestClient


def test_upload_page_renders_new_session_shell(app_client: TestClient):
    response = app_client.get("/")

    assert response.status_code == 200
    assert 'class="app-shell"' in response.text
    assert 'data-page="upload"' in response.text
    assert 'id="dropzone-panel"' in response.text
    assert 'id="media-info-card"' in response.text


def test_annotation_page_renders_workbench_layout(
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
    assert 'class="workbench-shell"' in response.text
    assert 'id="workflow-panel"' in response.text
    assert 'id="target-controls"' in response.text
    assert 'id="selection-controls"' in response.text
    assert 'id="preset-controls"' in response.text
    assert 'id="brush-controls"' in response.text
    assert 'id="detail-controls"' in response.text
    assert 'id="export-selection-panel"' in response.text
    assert 'id="canvas-stage"' in response.text
    assert 'id="layer-panel"' in response.text
    assert 'id="inspector-panel"' in response.text
    assert 'id="canvas-view-tabs"' in response.text
    assert 'data-canvas-mode="source"' in response.text
    assert 'data-canvas-mode="overlay"' in response.text
    assert 'data-canvas-mode="mask"' in response.text
    assert 'id="undo-click"' in response.text
    assert 'id="reset-target"' in response.text
    assert 'id="brush-radius"' in response.text
    assert 'id="overlay-opacity"' in response.text
    assert 'id="canvas-stage-note"' in response.text
    assert 'id="stage-guidance-title"' in response.text
    assert 'id="stage-guidance-copy"' in response.text


def test_job_page_renders_review_viewport(app_client: TestClient):
    repository = app_client.app.state.repository
    job = repository.create_job(
        source_video_path="queued.mp4",
        template_frame_index=0,
        mask_path="queued.png",
        params_json="{}",
    )

    response = app_client.get(f"/jobs/{job.job_id}")

    assert response.status_code == 200
    assert 'id="preview-viewport"' in response.text
    assert 'id="preview-mode-tabs"' in response.text
    assert 'id="artifact-panel"' in response.text
    assert 'id="preview-overlay-canvas"' in response.text
    assert 'id="overlay-foreground-video"' in response.text
    assert 'id="overlay-alpha-video"' in response.text
    assert 'id="review-summary-panel"' in response.text
    assert 'id="job-timeline"' in response.text
    assert 'id="artifact-summary-list"' in response.text
    assert 'id="warning-panel"' in response.text

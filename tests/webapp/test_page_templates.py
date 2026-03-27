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

    response = app_client.get(f"/drafts/{draft_id}/workspace")

    assert response.status_code == 200
    assert 'id="workspace-app"' in response.text
    assert 'class="workspace-shell"' in response.text
    assert 'data-default-canvas-mode="source"' in response.text
    assert 'id="workflow-stepper"' in response.text
    assert 'data-workflow-step="clip"' in response.text
    assert 'data-workflow-step="mask"' in response.text
    assert 'data-workflow-step="refine"' in response.text
    assert 'data-workflow-step="review"' in response.text
    assert 'id="workspace-monitor"' in response.text
    assert 'id="workspace-sidebar"' in response.text
    assert 'id="workspace-sidebar-tabs"' in response.text
    assert 'id="sidebar-tab-targets"' in response.text
    assert 'id="sidebar-tab-refine"' in response.text
    assert 'id="sidebar-tab-export"' in response.text
    assert 'id="sidebar-panel-targets"' in response.text
    assert 'id="sidebar-panel-refine"' in response.text
    assert 'id="sidebar-panel-export"' in response.text
    assert 'id="monitor-view-tabs"' in response.text
    assert 'data-canvas-mode="source"' in response.text
    assert 'data-canvas-mode="overlay"' in response.text
    assert 'data-canvas-mode="mask"' in response.text
    assert 'data-canvas-mode="alpha"' in response.text
    assert 'data-canvas-mode="foreground"' in response.text
    assert 'id="workspace-monitor-frame"' in response.text
    assert 'id="workspace-monitor-video"' in response.text
    assert 'id="workspace-monitor-image"' in response.text
    assert 'id="workspace-overlay-canvas"' in response.text
    assert 'id="workspace-timeline-dock"' in response.text
    assert 'id="clip-primary-rail"' in response.text
    assert 'id="mark-range-in"' in response.text
    assert 'id="mark-range-out"' in response.text
    assert 'id="clear-range-selection"' in response.text
    assert 'class="timeline-inline-actions timeline-inline-actions--compact"' in response.text
    assert 'id="timeline-current-label"' in response.text
    assert 'id="timeline-in-chip"' in response.text
    assert 'id="timeline-out-chip"' in response.text
    assert 'id="timeline-duration-chip"' in response.text
    assert 'id="anchor-rail"' in response.text
    assert 'id="anchor-frame-slider"' in response.text
    assert 'id="compare-toggle"' in response.text
    assert 'id="compare-drawer"' in response.text
    assert 'id="undo-click"' in response.text
    assert 'id="reset-target"' in response.text
    assert 'id="brush-radius"' in response.text
    assert 'id="overlay-opacity"' in response.text
    assert 'id="preset-strength"' in response.text
    assert 'id="motion-strength"' in response.text
    assert 'id="temporal-stability"' in response.text
    assert 'id="edge-feather-radius"' in response.text
    assert 'id="workspace-review-sidebar"' in response.text
    assert 'id="review-summary-list"' in response.text
    assert 'id="target-review-list"' in response.text
    assert 'id="artifact-summary-list"' in response.text
    assert 'id="workspace-nav-back"' in response.text
    assert 'id="workspace-nav-next"' in response.text
    assert 'id="workspace-return-to-clip"' in response.text
    assert 'id="workspace-return-to-refine"' in response.text
    assert 'id="preview-compare-strip"' not in response.text
    assert 'id="keyframe-video"' not in response.text
    assert 'id="canvas-keyframe-panel"' not in response.text
    assert 'id="anchor-frame-panel"' not in response.text


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
    assert 'id="target-review-panel"' in response.text
    assert 'id="target-review-list"' in response.text
    assert 'id="job-timeline"' in response.text
    assert 'id="artifact-summary-list"' in response.text
    assert 'id="warning-panel"' in response.text


def test_job_page_keeps_preview_streams_separate_from_download_artifacts(app_client: TestClient):
    repository = app_client.app.state.repository
    job = repository.create_job(
        source_video_path="queued.mp4",
        template_frame_index=0,
        mask_path="queued.png",
        params_json="{}",
    )

    response = app_client.get(f"/jobs/{job.job_id}")

    assert response.status_code == 200
    assert 'data-preview-foreground-endpoint' in response.text
    assert 'data-preview-alpha-endpoint' in response.text


def test_annotate_route_keeps_workspace_compatibility(
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
    assert 'id="workspace-app"' in response.text

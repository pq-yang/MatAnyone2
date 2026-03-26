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
    assert 'id="tool-rail"' in response.text
    assert 'id="canvas-stage"' in response.text
    assert 'id="layer-panel"' in response.text
    assert 'id="inspector-panel"' in response.text

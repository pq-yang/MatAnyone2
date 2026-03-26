from fastapi.testclient import TestClient


def test_upload_page_renders_new_session_shell(app_client: TestClient):
    response = app_client.get("/")

    assert response.status_code == 200
    assert 'class="app-shell"' in response.text
    assert 'data-page="upload"' in response.text
    assert 'id="dropzone-panel"' in response.text
    assert 'id="media-info-card"' in response.text

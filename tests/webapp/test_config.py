from matanyone2.webapp.config import WebAppSettings


def test_webapp_settings_default_to_sam2_backend(monkeypatch):
    monkeypatch.delenv("MATANYONE2_WEBAPP_SAM_BACKEND", raising=False)
    monkeypatch.delenv("MATANYONE2_WEBAPP_SAM2_VARIANT", raising=False)

    settings = WebAppSettings()

    assert settings.sam_backend == "sam2"
    assert settings.sam2_variant == "sam2.1_hiera_large"

from pathlib import Path

import nkr_gcs.settings as settings_module
from nkr_gcs.settings import Settings, load_settings, save_setting, settings_path


def test_missing_settings_are_created(tmp_path):
    path = tmp_path / "nested" / "settings.yaml"
    settings = load_settings(path)
    assert settings == Settings()
    assert path.exists()
    assert "video_port: 8554" in path.read_text(encoding="utf-8")
    assert "video_width: 640" in path.read_text(encoding="utf-8")
    assert "video_height: 480" in path.read_text(encoding="utf-8")


def test_linux_settings_path_uses_xdg(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_module.sys, "platform", "linux")
    monkeypatch.delenv("NKR_GCS_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert settings_path() == Path(tmp_path) / "nkr-gcs" / "settings.yaml"


def test_windows_settings_path_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_module.sys, "platform", "win32")
    monkeypatch.delenv("NKR_GCS_CONFIG", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert settings_path() == Path(tmp_path) / "NKR-GCS" / "settings.yaml"


def test_settings_path_can_be_overridden(monkeypatch, tmp_path):
    expected = tmp_path / "custom.yaml"
    monkeypatch.setenv("NKR_GCS_CONFIG", str(expected))
    assert settings_path() == expected


def test_input_device_is_saved_without_losing_other_settings(tmp_path):
    path = tmp_path / "settings.yaml"
    settings = load_settings(path)
    assert settings.input_device == "steamdeck"
    save_setting("input_device", "dualsense", path)
    settings = load_settings(path)
    assert settings.input_device == "dualsense"
    assert settings.robot_host == "100.72.220.66"

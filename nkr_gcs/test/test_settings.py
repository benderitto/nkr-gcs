from nkr_gcs.settings import load_settings, save_setting


def test_input_device_is_saved_without_losing_other_settings(tmp_path):
    path = tmp_path / "settings.yaml"
    settings = load_settings(path)
    assert settings.input_device == "steamdeck"
    save_setting("input_device", "dualsense", path)
    settings = load_settings(path)
    assert settings.input_device == "dualsense"
    assert settings.robot_host == "100.72.220.66"

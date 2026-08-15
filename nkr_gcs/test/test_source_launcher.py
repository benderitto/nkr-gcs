import run


def test_flatpak_detection_is_disabled_on_windows(monkeypatch):
    monkeypatch.setattr(run.sys, "platform", "win32")
    assert run._flatpak_is_installed() is False


def test_host_dependency_detection_uses_pyside(monkeypatch):
    monkeypatch.setattr(run.importlib.util, "find_spec", lambda name: object())
    assert run._host_dependencies_available() is True

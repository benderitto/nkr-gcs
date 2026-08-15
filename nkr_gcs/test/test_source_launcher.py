import run


def test_flatpak_detection_is_disabled_on_windows(monkeypatch):
    monkeypatch.setattr(run.sys, "platform", "win32")
    assert run._flatpak_is_installed() is False


def test_host_dependency_detection_uses_pyside(monkeypatch):
    monkeypatch.setattr(run.importlib.util, "find_spec", lambda name: object())
    assert run._host_dependencies_available() is True


def test_graphical_environment_is_inherited_for_ssh(monkeypatch):
    for key in run.GRAPHICAL_ENVIRONMENT:
        monkeypatch.delenv(key, raising=False)

    class Result:
        returncode = 0
        stdout = "DISPLAY=:0\nWAYLAND_DISPLAY=wayland-0\nUNRELATED=ignored\n"

    monkeypatch.setattr(run.subprocess, "run", lambda *args, **kwargs: Result())
    run._inherit_graphical_session_environment()
    assert run.os.environ["DISPLAY"] == ":0"
    assert run.os.environ["WAYLAND_DISPLAY"] == "wayland-0"
    assert "UNRELATED" not in run.os.environ

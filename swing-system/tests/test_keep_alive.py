import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("keep_alive", Path(__file__).parent.parent / "scripts" / "keep_alive.py")
ka = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ka)


class R:
    def __init__(self, code=200, body=None):
        self.status_code, self._b = code, body or {}

    def json(self):
        return self._b


def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GH_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    monkeypatch.setattr(ka, "LOG", tmp_path / "ka.json")
    monkeypatch.setattr("time.sleep", lambda s: None)


def test_starts_next_run_once_and_guards_crash_loops(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    posts = []
    monkeypatch.setattr(ka.requests, "get", lambda *a, **k: R(body={"workflow_runs": [{"id": 1}]}))
    monkeypatch.setattr(ka.requests, "post", lambda *a, **k: posts.append(k["json"]) or R(204))
    for _ in range(4):
        assert ka.main() == "next run started"
    assert posts[0] == {"ref": "main", "inputs": {"task": "bot"}}
    monkeypatch.setattr("swing.telegram.send", lambda *a, **k: "ok")
    assert ka.main().startswith("paused")                     # 5th restart within an hour: stop


def test_does_nothing_when_a_run_is_already_waiting(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setattr(ka.requests, "get", lambda *a, **k: R(body={"workflow_runs": [{"id": 2}]}))
    monkeypatch.setattr(ka.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no dispatch")))
    assert ka.main().startswith("another run")


def test_off_github_does_nothing(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert ka.main() == "not on GitHub"

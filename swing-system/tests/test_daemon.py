from datetime import datetime

from swing import daemon


def _t(s):
    return datetime.fromisoformat(s).replace(tzinfo=daemon.IST)


def test_due_jobs_follow_the_ist_clock(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon, "STATE", tmp_path / "jobs.json")
    assert daemon.due(_t("2026-11-04T10:47")) == ["scan"]            # Wednesday morning
    assert daemon.due(_t("2026-11-04T16:30")) == []
    assert daemon.due(_t("2026-11-04T18:45")) == ["nightly"]
    assert "research" in daemon.due(_t("2026-11-04T21:40"))
    assert daemon.due(_t("2026-11-07T10:30")) == ["weekly"]          # Saturday
    assert daemon.due(_t("2026-11-08T12:00")) == []                  # Sunday


def test_claim_prevents_double_runs_but_not_manual_daytime_runs(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon, "STATE", tmp_path / "jobs.json")
    monkeypatch.setattr(daemon, "now", lambda: _t("2026-11-04T18:50"))
    assert daemon.claim("nightly") and not daemon.claim("nightly")
    monkeypatch.setattr(daemon, "now", lambda: _t("2026-11-04T10:30"))
    assert daemon.claim("scan") and not daemon.claim("scan")
    assert daemon.claim("nightly") and daemon.claim("nightly")        # morning manual run: not recorded


def test_company_of_the_day_is_its_own_job_and_retried(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon, "STATE", tmp_path / "jobs.json")
    monkeypatch.setattr(daemon, "now", lambda: _t("2026-11-04T18:50"))
    assert daemon.due(_t("2026-11-04T18:50")) == ["nightly"]          # trades message first
    assert daemon.claim("nightly")
    assert daemon.due(_t("2026-11-04T18:50")) == ["company"]
    assert daemon.claim("company") and "company" not in daemon.due(_t("2026-11-04T18:51"))
    daemon.failed("company")                                           # Telegram did not take it: try again
    assert "company" in daemon.due(_t("2026-11-04T18:52"))
    assert daemon.claim("company")
    daemon.failed("company")
    assert daemon.claim("company")
    daemon.failed("company")                                           # third failure: stop (no spam)
    assert "company" not in daemon.due(_t("2026-11-04T18:55"))
    # nightly never ran (e.g. crashed before claiming)? company still goes out by 19:30
    monkeypatch.setattr(daemon, "STATE", tmp_path / "jobs2.json")
    st = {"nightly 2026-11-04": "x"}
    (tmp_path / "jobs2.json").write_text(__import__("json").dumps(st))
    assert "company" in daemon.due(_t("2026-11-04T19:31"))


def test_jobs_today_line(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon, "STATE", tmp_path / "jobs.json")
    monkeypatch.setattr(daemon, "now", lambda: _t("2026-11-04T10:30"))
    daemon.claim("scan")
    line = daemon.jobs_today_line(_t("2026-11-04T18:45"))
    assert "1 of 6" in line and "11:20" in line and "10:20" not in line.split("missed")[1]


def test_new_program_code_ends_the_run(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("SWING_BRANCH", "b")
    monkeypatch.setattr(daemon.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(daemon, "code_version", lambda ref="HEAD": "new|x")
    assert daemon.update_waiting("old|x") is True
    assert daemon.update_waiting("new|x") is False
    monkeypatch.delenv("GITHUB_ACTIONS")
    assert daemon.update_waiting("old|x") is False                   # never on the owner's own computer

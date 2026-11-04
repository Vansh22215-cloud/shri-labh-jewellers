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

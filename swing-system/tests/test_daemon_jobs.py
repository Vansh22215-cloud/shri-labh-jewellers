import time

from swing import daemon


def test_jobs_run_in_background_one_at_a_time(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon, "STATE", tmp_path / "state.json")
    calls = []
    monkeypatch.setattr(daemon.subprocess, "run", lambda *a, **k: (calls.append(a), time.sleep(0.5)))
    monkeypatch.setattr(daemon, "key", lambda job, t=None: f"{job} today")
    t0 = time.time()
    assert daemon.run_job("nightly", 100) is True
    assert time.time() - t0 < 0.3 and daemon.job_running()        # returns at once, job keeps running
    assert daemon.run_job("research", 100) is False                 # one at a time
    daemon._JOB["thread"].join()
    assert len(calls) == 1 and not daemon.job_running()

"""Private R2 storage: off without the four secrets; with them, files go up, come down, and leave the GitHub cache."""
import json

import pytest

from swing import r2


class FakeS3:
    def __init__(self):
        self.objs = {}

    def upload_file(self, path, bucket, key):
        self.objs[key] = open(path, "rb").read()

    def download_file(self, bucket, key, path):
        open(path, "wb").write(self.objs[key])

    def get_paginator(self, name):
        objs = self.objs

        class P:
            def paginate(self, Bucket, Prefix):
                return [{"Contents": [{"Key": k, "Size": len(v)} for k, v in objs.items() if k.startswith(Prefix)]}]
        return P()


@pytest.fixture
def env(tmp_path, monkeypatch):
    for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(r2, "ROOT", tmp_path / "repo" / "swing-system")
    monkeypatch.setattr(r2, "DATA", tmp_path / "repo" / "swing-system" / "data")
    s3 = FakeS3()
    monkeypatch.setattr(r2, "_client", lambda: s3)
    return s3, tmp_path


def test_off_without_secrets(monkeypatch):
    monkeypatch.delenv("R2_BUCKET", raising=False)
    assert not r2.configured() and r2.push() == 0 and r2.pull() == 0


def test_migrate_moves_kite_data_out_of_the_github_cache(env):
    s3, tmp = env
    old = r2.DATA / "candles" / "5minute" / "AAA.parquet"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"candles")
    (r2.DATA / "private").mkdir()
    (r2.DATA / "private" / "kite_token.bin").write_bytes(b"t")
    assert r2.migrate() == 1
    assert s3.objs["kite/candles/5minute/AAA.parquet"] == b"candles"
    assert not (r2.DATA / "candles").exists() and (r2.DATA / "private" / "kite_token.bin").exists()
    assert r2.push() == 0                                     # nothing changed: nothing uploaded again
    import shutil
    shutil.rmtree(r2.root())                                  # a fresh GitHub computer ...
    assert r2.pull() == 1 and (r2.root() / "candles" / "5minute" / "AAA.parquet").read_bytes() == b"candles"

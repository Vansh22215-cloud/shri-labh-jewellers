"""Kite data in a PRIVATE Cloudflare R2 bucket instead of GitHub (owner 21 Nov: "we can't take the risk of this data
on GitHub"). Active only when the four GitHub Secrets exist:
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
Then all Kite-derived files (candles, live candles, test trade lists, replay candles) live OUTSIDE the GitHub cache
folder: they are downloaded from R2 when a run starts and every changed file is uploaded back during and at the
end of the run. The first time, everything still in the GitHub cache is uploaded to R2 and then deleted from the
cache, so GitHub keeps no Kite data at all. Keys come from GitHub Secrets only - never printed, never written."""
import json
import os
import shutil
from pathlib import Path

from .config import DATA, ROOT, get_logger

log = get_logger()
PREFIX = "kite/"
OLD = ["candles", "live", "tests", "replay"]          # the Kite-data folders that used to sit in the GitHub cache


def configured():
    return all(os.environ.get(k) for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"))


def root():
    """Where Kite data lives on this computer: outside the cached folder when R2 is set up."""
    return (ROOT.parent / ".kite_data") if configured() else DATA


def _client():
    import boto3
    return boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")


def _manifest_path():
    return root() / ".r2_manifest.json"


def _load_manifest():
    try:
        return json.loads(_manifest_path().read_text())
    except Exception:
        return {}


def pull():
    """Download every object not already here (same size). -> files downloaded."""
    if not configured():
        return 0
    c, b, n = _client(), os.environ["R2_BUCKET"], 0
    base = root()
    man = _load_manifest()
    for page in c.get_paginator("list_objects_v2").paginate(Bucket=b, Prefix=PREFIX):
        for o in page.get("Contents", []):
            rel = o["Key"][len(PREFIX):]
            f = base / rel
            if f.exists() and f.stat().st_size == o["Size"]:
                man[rel] = [f.stat().st_size, f.stat().st_mtime]
                continue
            f.parent.mkdir(parents=True, exist_ok=True)
            c.download_file(b, o["Key"], str(f))
            man[rel] = [f.stat().st_size, f.stat().st_mtime]
            n += 1
    base.mkdir(parents=True, exist_ok=True)
    _manifest_path().write_text(json.dumps(man))
    log.info("R2: %d files downloaded", n)
    return n


def push():
    """Upload every file changed since the last upload. -> files uploaded."""
    if not configured():
        return 0
    c, b, n = _client(), os.environ["R2_BUCKET"], 0
    base = root()
    man = _load_manifest()
    for f in base.rglob("*"):
        if not f.is_file() or f.name.startswith(".r2_") or f.suffix == ".tmp":
            continue
        rel = f.relative_to(base).as_posix()
        st = [f.stat().st_size, f.stat().st_mtime]
        if man.get(rel) == st:
            continue
        c.upload_file(str(f), b, PREFIX + rel)
        man[rel] = st
        n += 1
    _manifest_path().write_text(json.dumps(man))
    if n:
        log.info("R2: %d files uploaded", n)
    return n


def migrate():
    """Once: move the Kite data still in the GitHub cache folder to R2, then delete it from the cache folder."""
    if not configured():
        return None
    base = root()
    moved = 0
    for name in OLD:
        src = DATA / name
        if src.exists():
            dst = base / name
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.rglob("*"):
                if f.is_file():
                    t = dst / f.relative_to(src)
                    t.parent.mkdir(parents=True, exist_ok=True)
                    if not t.exists():
                        shutil.move(str(f), str(t))
                        moved += 1
    up = push()                                          # in R2 first ...
    for name in OLD:
        shutil.rmtree(DATA / name, ignore_errors=True)   # ... then gone from the GitHub cache folder
    if moved:
        log.info("R2: %d Kite files moved out of the GitHub cache (%d uploaded)", moved, up)
    return moved

"""Private backup of your records (tips, outbox) to your own Telegram chat - GitHub's cache can be cleared, Telegram
keeps the file. Sent at 9:30 pm only when something changed. Forward the file back to the bot to restore it
(nothing already stored is overwritten; tips are merged by their id). The Kite login pass is never included."""
import hashlib
import io
import zipfile

import pandas as pd

from .config import DATA, PRIVATE, get_logger

log = get_logger()
HASH_F = DATA / "backup_hash.txt"
SKIP = {"kite_token.bin"}


def build():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PRIVATE.rglob("*")):
            if p.is_file() and not (set(p.relative_to(PRIVATE).parts) & SKIP):
                z.write(p, p.relative_to(PRIVATE).as_posix())
    return buf.getvalue()


def send_if_changed(settings):
    from . import telegram
    blob = build()
    h = hashlib.sha256(blob).hexdigest()
    if HASH_F.exists() and HASH_F.read_text().strip() == h:
        return "unchanged"
    f = DATA / f"atlas-backup-{pd.Timestamp.now():%Y%m%d}.zip"
    f.write_bytes(blob)
    r = telegram.send_document(settings, f, caption="🔒 ATLAS backup of your records. Keep it; forward it back to me "
                                                    "to restore.", mime="application/zip", label="backup")
    f.unlink(missing_ok=True)
    if r == "report sent":
        HASH_F.write_text(h)
    return r


def restore(blob):
    """Merge a backup back. -> number of files restored or merged."""
    n = 0
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            if ".." in name or name.startswith("/") or set(name.split("/")) & SKIP:
                continue
            dst = PRIVATE / name
            data = z.read(name)
            if name == "tips.csv" and dst.exists():
                old = pd.read_csv(dst)
                new = pd.read_csv(io.BytesIO(data))
                m = pd.concat([old, new[~new["id"].isin(old["id"])]], ignore_index=True)
                m.to_csv(dst, index=False)
                n += 1
            elif not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                n += 1
    return n

"""After this run saved its data: delete every OLDER saved copy from GitHub's cache, so the 10 GB GitHub allows
holds one copy of the data instead of several (each run saves a full copy). Uses only the run's own short-lived
GitHub key (actions: write). Never deletes the copy this run just saved."""
import os

import requests

API = "https://api.github.com"

if __name__ == "__main__":
    token, repo, run_id = os.environ.get("GH_TOKEN"), os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID")
    if not (token and repo and run_id):
        raise SystemExit("not on GitHub")
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    mine = f"swing-data-{run_id}"
    caches = requests.get(f"{API}/repos/{repo}/actions/caches", headers=h, timeout=30,
                          params={"key": "swing-data-", "per_page": 100}).json().get("actions_caches", [])
    if not any(c["key"] == mine for c in caches):
        raise SystemExit("this run's copy is not saved - nothing deleted")
    n = 0
    for c in caches:
        if c["key"] != mine:
            r = requests.delete(f"{API}/repos/{repo}/actions/caches/{c['id']}", headers=h, timeout=30)
            n += r.status_code in (200, 204)
    print(f"old saved copies deleted: {n}")

"""Daily pipeline: fetch every source, build the history, write the status file
and the issue body. GitHub Actions runs this once a day (.github/workflows/daily.yml).

    python run.py           # full run for today's UTC date
    python run.py --check   # call every source and print counts; writes nothing
"""
import argparse
import gzip
import json
import os
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

from watcher.build import main as build_main, raw_days
from watcher.fetch import fetch_source
from watcher.issue import make_issue_body
from watcher.normalize import normalize
from watcher.status import make_status, write_status

DATA = Path("data")


def load_sources(path="sources.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_raw(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0 keeps the compressed bytes the same for the same content
    with open(path, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def fetch_all(sources, run_day, run_time, write=True):
    """Call every source. One source failing never stops the run."""
    day_dir = DATA / "raw" / run_day
    if write and day_dir.exists():
        shutil.rmtree(day_dir)  # a second run on the same day replaces that day
    results = []
    for src in sources:
        try:
            responses, meta = fetch_source(src)
            count = len(normalize(src, responses, meta))
            if write:
                write_raw(day_dir / f"{src['name']}.json.gz", {
                    "source": src["name"], "fetched_at": run_time,
                    "config": src, "meta": meta, "responses": responses,
                })
            results.append({"name": src["name"], "ok": True, "count": count, "error": ""})
            print(f"ok    {src['name']:<16} {count:>6} postings {meta or ''}")
        except Exception as exc:
            results.append({"name": src["name"], "ok": False, "count": 0,
                            "error": f"{type(exc).__name__}: {exc}"})
            print(f"FAIL  {src['name']:<16} {type(exc).__name__}: {exc}")
            traceback.print_exc(limit=1)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="call every source and print counts without writing files")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    run_day = os.environ.get("RUN_DATE") or now.strftime("%Y-%m-%d")
    run_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    sources = load_sources()

    if args.check:
        results = fetch_all(sources, run_day, run_time, write=False)
        ok = sum(r["ok"] for r in results)
        print(f"\n{ok} of {len(results)} sources returned JSON")
        return

    results = fetch_all(sources, run_day, run_time)
    runs_dir = DATA / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{run_day}.json").write_text(
        json.dumps({"run_time": run_time, "results": results}, indent=2) + "\n")

    rows = build_main(DATA)
    status = make_status(rows, run_time, run_day, raw_days(DATA / "raw"), results)
    write_status(status, DATA / "status.json")

    body = make_issue_body(rows, run_day, status, os.environ.get("SITE_URL", ""))
    Path("issue.md").write_text(body, encoding="utf-8")
    print(f"status: {status['open']} open, {status['new_today']} new, "
          f"{status['removed_today']} removed")


if __name__ == "__main__":
    main()

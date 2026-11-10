"""Build data/history.csv from the raw files alone.

Run it with:  python -m watcher.build

The build walks data/raw/<date>/ in date order. It reads nothing but the raw
files, so running it again gives the same file, and a change to a rule (the
title rule or a converter) applies to every day of the history.
"""
import csv
import gzip
import json
import sys
from pathlib import Path

from watcher.normalize import COLUMNS, normalize
from watcher.titles import in_role

HISTORY_COLUMNS = COLUMNS + ["in_role", "first_run", "first_seen", "last_seen",
                             "status", "removed_date"]

DATA = Path("data")


def raw_days(raw_dir):
    """Sorted list of (date, [raw file paths]) for every date folder with raw files."""
    days = []
    if not Path(raw_dir).exists():
        return days
    for day_dir in sorted(p for p in Path(raw_dir).iterdir() if p.is_dir()):
        files = sorted(day_dir.glob("*.json.gz"))
        if files:
            days.append((day_dir.name, files))
    return days


def read_raw(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def apply_day(history, day, listings, source_first_day):
    """Update history (dict posting_id -> row) with one day's listings.

    listings maps source name -> list of postings (common columns) for every
    source that has a raw file that day. Sources without a raw file are untouched.
    """
    for source, postings in listings.items():
        source_first_day.setdefault(source, day)
        listed = set()
        for p in postings:
            listed.add(p["posting_id"])
            row = history.get(p["posting_id"])
            if row is None:
                row = {
                    "first_seen": day,
                    "first_run": source_first_day[source] == day,
                }
                history[p["posting_id"]] = row
            # A removed posting listed again is reopened; first_seen never changes.
            row.update(p)
            row["in_role"] = in_role(p["title"])
            row["last_seen"] = day
            row["status"] = "open"
            row["removed_date"] = ""
        for pid, row in history.items():
            if row["source"] == source and row["status"] == "open" and pid not in listed:
                row["status"] = "removed"
                row["removed_date"] = day
    return history


def build_history(raw_dir):
    history, source_first_day = {}, {}
    for day, files in raw_days(raw_dir):
        listings = {}
        for path in files:
            raw = read_raw(path)
            src = raw["config"]
            listings[src["name"]] = normalize(src, raw["responses"], raw.get("meta"))
        apply_day(history, day, listings, source_first_day)
    return [history[pid] for pid in sorted(history)]


def _fmt(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_history(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HISTORY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: _fmt(row.get(c, "")) for c in HISTORY_COLUMNS})


def main(data_dir=DATA):
    data_dir = Path(data_dir)
    rows = build_history(data_dir / "raw")
    write_history(rows, data_dir / "history.csv")
    print(f"history.csv: {len(rows)} postings")
    return rows


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DATA)

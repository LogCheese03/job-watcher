"""First-seen, last-seen, removed and reopened logic, and the build from raw files."""
import gzip
import json

from watcher.build import apply_day, build_history, raw_days, write_history
from watcher.status import make_status


def posting(source, sid, title="Financial Analyst"):
    return {"posting_id": f"{source}:{sid}", "source": source, "source_id": str(sid),
            "employer": source.title(), "title": title, "location": "", "department": "",
            "posted_date": "", "url": f"https://example.com/{sid}"}


def run_days(days):
    """days: list of (date, {source: [ids]}) -> history dict"""
    history, first = {}, {}
    for day, listing in days:
        apply_day(history, day, {s: [posting(s, i) for i in ids] for s, ids in listing.items()},
                  first)
    return history


def test_first_seen_and_last_seen():
    h = run_days([("2026-11-16", {"a": [1]}), ("2026-11-17", {"a": [1, 2]})])
    assert h["a:1"]["first_seen"] == "2026-11-16"
    assert h["a:1"]["last_seen"] == "2026-11-17"
    assert h["a:2"]["first_seen"] == "2026-11-17"


def test_first_run_flag_is_per_source():
    h = run_days([("2026-11-16", {"a": [1]}),
                  ("2026-11-17", {"a": [1, 2], "b": [9]})])
    assert h["a:1"]["first_run"] is True
    assert h["a:2"]["first_run"] is False
    assert h["b:9"]["first_run"] is True  # b's first raw file is on 11-17


def test_removed_when_source_stops_listing():
    h = run_days([("2026-11-16", {"a": [1, 2]}), ("2026-11-17", {"a": [2]})])
    assert h["a:1"]["status"] == "removed"
    assert h["a:1"]["removed_date"] == "2026-11-17"
    assert h["a:1"]["last_seen"] == "2026-11-16"
    assert h["a:2"]["status"] == "open"


def test_not_removed_when_source_has_no_raw_file():
    h = run_days([("2026-11-16", {"a": [1], "b": [5]}),
                  ("2026-11-17", {"a": [1]})])  # b failed on 11-17
    assert h["b:5"]["status"] == "open"
    assert h["b:5"]["removed_date"] == ""


def test_empty_listing_removes_everything_for_that_source():
    h = run_days([("2026-11-16", {"a": [1, 2]}), ("2026-11-17", {"a": []})])
    assert all(r["status"] == "removed" for r in h.values())


def test_reopened_posting_keeps_first_seen():
    h = run_days([("2026-11-16", {"a": [1]}),
                  ("2026-11-17", {"a": []}),
                  ("2026-11-19", {"a": [1]})])
    r = h["a:1"]
    assert r["status"] == "open"
    assert r["removed_date"] == ""
    assert r["first_seen"] == "2026-11-16"
    assert r["last_seen"] == "2026-11-19"


def test_in_role_uses_title_rule():
    history, first = {}, {}
    apply_day(history, "2026-11-16",
              {"a": [posting("a", 1), posting("a", 2, "Software Engineer")]}, first)
    assert history["a:1"]["in_role"] is True
    assert history["a:2"]["in_role"] is False


def write_raw(root, day, name, ids):
    path = root / day / f"{name}.json.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    src = {"name": name, "employer": name.title(), "ats": "greenhouse", "board": name}
    jobs = [{"id": i, "title": "Financial Analyst", "absolute_url": f"u{i}"} for i in ids]
    with gzip.open(path, "wt") as fh:
        json.dump({"config": src, "meta": {}, "responses": [{"jobs": jobs}]}, fh)


def test_build_from_raw_files_is_reproducible(tmp_path):
    raw = tmp_path / "raw"
    write_raw(raw, "2026-11-16", "a", [3, 1])
    write_raw(raw, "2026-11-17", "a", [1, 2])
    rows = build_history(raw)
    assert [r["posting_id"] for r in rows] == ["a:1", "a:2", "a:3"]  # sorted
    write_history(rows, tmp_path / "h1.csv")
    write_history(build_history(raw), tmp_path / "h2.csv")
    assert (tmp_path / "h1.csv").read_bytes() == (tmp_path / "h2.csv").read_bytes()
    header = (tmp_path / "h1.csv").read_text().splitlines()[0]
    assert header == ("posting_id,source,source_id,employer,title,location,department,"
                      "posted_date,url,in_role,first_run,first_seen,last_seen,status,removed_date")


def test_status_counts(tmp_path):
    raw = tmp_path / "raw"
    write_raw(raw, "2026-11-16", "a", [1, 2])
    write_raw(raw, "2026-11-17", "a", [2, 3])
    rows = build_history(raw)
    results = [{"name": "a", "ok": True, "count": 2}, {"name": "b", "ok": False, "count": 0}]
    s = make_status(rows, "2026-11-17T12:00:00Z", "2026-11-17", raw_days(raw), results)
    assert s["first_run_date"] == "2026-11-16"
    assert s["days_with_success"] == 2
    assert s["open"] == 2
    assert s["new_today"] == 1       # a:3
    assert s["removed_today"] == 1   # a:1
    assert s["sources"][1] == {"name": "b", "ok": False, "count": 0}


def test_first_day_postings_are_not_new_today(tmp_path):
    raw = tmp_path / "raw"
    write_raw(raw, "2026-11-16", "a", [1, 2])
    rows = build_history(raw)
    s = make_status(rows, "t", "2026-11-16", raw_days(raw), [])
    assert s["new_today"] == 0

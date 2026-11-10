"""Write data/status.json describing the latest run."""
import json
from pathlib import Path


def make_status(rows, run_time, run_day, raw_days_list, results):
    days = [d for d, _ in raw_days_list]
    return {
        "run_time": run_time,
        "first_run_date": days[0] if days else None,
        "days_with_success": len(days),
        "open": sum(1 for r in rows if r["status"] == "open"),
        "new_today": sum(1 for r in rows if r["first_seen"] == run_day and not r["first_run"]),
        "removed_today": sum(1 for r in rows if r["removed_date"] == run_day),
        "sources": [{"name": r["name"], "ok": r["ok"], "count": r["count"]} for r in results],
    }


def write_status(status, path):
    Path(path).write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

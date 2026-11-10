"""Convert each source's raw responses into one common set of columns."""
from datetime import datetime, timezone

COLUMNS = ["posting_id", "source", "source_id", "employer", "title",
           "location", "department", "posted_date", "url"]


def _clean(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def _utc_date(value):
    """ISO timestamp or epoch milliseconds -> YYYY-MM-DD in UTC ('' if missing)."""
    if value in (None, ""):
        return ""
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OverflowError, OSError):
        return ""


def _row(src, source_id, title, location, department, posted_date, url):
    source_id = _clean(source_id)
    return {
        "posting_id": f"{src['name']}:{source_id}",
        "source": src["name"],
        "source_id": source_id,
        "employer": src["employer"],
        "title": _clean(title),
        "location": _clean(location),
        "department": _clean(department),
        "posted_date": posted_date,
        "url": _clean(url),
    }


def from_greenhouse(src, responses, meta):
    rows = []
    for resp in responses:
        for job in resp.get("jobs", []):
            depts = ", ".join(d.get("name", "") for d in job.get("departments") or [])
            rows.append(_row(src, job.get("id"), job.get("title"),
                             (job.get("location") or {}).get("name"), depts,
                             _utc_date(job.get("first_published")),
                             job.get("absolute_url")))
    return rows


def from_lever(src, responses, meta):
    rows = []
    for resp in responses:
        for job in resp:
            cats = job.get("categories") or {}
            rows.append(_row(src, job.get("id"), job.get("text"),
                             cats.get("location"),
                             cats.get("department") or cats.get("team"),
                             _utc_date(job.get("createdAt")), job.get("hostedUrl")))
    return rows


def from_ashby(src, responses, meta):
    rows = []
    for resp in responses:
        for job in resp.get("jobs", []):
            rows.append(_row(src, job.get("id"), job.get("title"), job.get("location"),
                             job.get("department"), _utc_date(job.get("publishedAt")),
                             job.get("jobUrl")))
    return rows


def from_smartrecruiters(src, responses, meta):
    rows = []
    for resp in responses:
        for job in resp.get("content", []):
            loc = job.get("location") or {}
            location = loc.get("fullLocation") or ", ".join(
                p for p in (loc.get("city"), loc.get("region"), loc.get("country")) if p)
            rows.append(_row(src, job.get("id"), job.get("name"), location,
                             (job.get("department") or {}).get("label"),
                             _utc_date(job.get("releasedDate")),
                             f"https://jobs.smartrecruiters.com/{src['board']}/{job.get('id')}"))
    return rows


def from_workday(src, responses, meta):
    site = meta.get("site") or src["site"]
    rows = []
    for resp in responses:
        for job in resp.get("jobPostings", []):
            path = job.get("externalPath", "")
            # Workday only gives relative dates ("Posted 3 Days Ago"), so posted_date
            # and department are left empty for Workday sources.
            rows.append(_row(src, path, job.get("title"), job.get("locationsText"),
                             "", "", f"https://{src['host']}/en-US/{site}{path}"))
    return rows


CONVERTERS = {
    "greenhouse": from_greenhouse,
    "lever": from_lever,
    "ashby": from_ashby,
    "smartrecruiters": from_smartrecruiters,
    "workday": from_workday,
}


def normalize(src, responses, meta=None):
    """Return the source's postings in common columns, one row per posting ID."""
    seen, out = set(), []
    for row in CONVERTERS[src["ats"]](src, responses, meta or {}):
        if row["source_id"] and row["posting_id"] not in seen:
            seen.add(row["posting_id"])
            out.append(row)
    return out

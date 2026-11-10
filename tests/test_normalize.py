"""Each source's raw response converts to the common columns."""
from watcher.normalize import COLUMNS, normalize


def check_columns(rows):
    for row in rows:
        assert list(row) == COLUMNS


def test_greenhouse():
    src = {"name": "affirm", "employer": "Affirm", "ats": "greenhouse", "board": "affirm"}
    raw = [{"jobs": [{
        "id": 123, "title": "  Senior  Financial Analyst ",
        "location": {"name": "Remote, US"},
        "departments": [{"name": "Finance"}, {"name": "FP&A"}],
        "first_published": "2026-11-15T22:30:00-05:00",
        "absolute_url": "https://job-boards.greenhouse.io/affirm/jobs/123",
    }]}]
    rows = normalize(src, raw)
    check_columns(rows)
    assert rows[0] == {
        "posting_id": "affirm:123", "source": "affirm", "source_id": "123",
        "employer": "Affirm", "title": "Senior Financial Analyst",
        "location": "Remote, US", "department": "Finance, FP&A",
        "posted_date": "2026-11-16",  # converted to UTC
        "url": "https://job-boards.greenhouse.io/affirm/jobs/123",
    }


def test_greenhouse_drops_duplicate_ids():
    src = {"name": "x", "employer": "X", "ats": "greenhouse", "board": "x"}
    job = {"id": 1, "title": "A", "absolute_url": "u"}
    assert len(normalize(src, [{"jobs": [job, job]}])) == 1


def test_lever():
    src = {"name": "plaid", "employer": "Plaid", "ats": "lever", "board": "plaid"}
    raw = [[{
        "id": "abc-1", "text": "FP&A Analyst",
        "categories": {"location": "San Francisco", "team": "Finance"},
        "createdAt": 1763251200000,  # 2025-11-16 00:00 UTC
        "hostedUrl": "https://jobs.lever.co/plaid/abc-1",
    }]]
    rows = normalize(src, raw)
    check_columns(rows)
    r = rows[0]
    assert r["posting_id"] == "plaid:abc-1"
    assert r["department"] == "Finance"
    assert r["posted_date"] == "2025-11-16"
    assert r["url"] == "https://jobs.lever.co/plaid/abc-1"


def test_ashby():
    src = {"name": "ramp", "employer": "Ramp", "ats": "ashby", "board": "ramp"}
    raw = [{"jobs": [{
        "id": "u-1", "title": "Strategic Finance Associate", "location": "New York",
        "department": "Finance", "publishedAt": "2026-11-10T15:00:00.000+00:00",
        "jobUrl": "https://jobs.ashbyhq.com/ramp/u-1",
    }]}]
    rows = normalize(src, raw)
    check_columns(rows)
    assert rows[0]["title"] == "Strategic Finance Associate"
    assert rows[0]["posted_date"] == "2026-11-10"
    assert rows[0]["location"] == "New York"


def test_smartrecruiters():
    src = {"name": "visa", "employer": "Visa", "ats": "smartrecruiters", "board": "Visa"}
    raw = [{"totalFound": 1, "content": [{
        "id": "744000", "name": "Credit Analyst",
        "location": {"city": "Austin", "region": "TX", "country": "us"},
        "department": {"label": "Finance"},
        "releasedDate": "2026-11-12T08:00:00.000Z",
    }]}]
    rows = normalize(src, raw)
    check_columns(rows)
    r = rows[0]
    assert r["location"] == "Austin, TX, us"
    assert r["department"] == "Finance"
    assert r["url"] == "https://jobs.smartrecruiters.com/Visa/744000"


def test_workday_uses_site_that_worked():
    src = {"name": "ameriprise", "employer": "Ameriprise Financial", "ats": "workday",
           "host": "ameriprise.wd5.myworkdayjobs.com", "tenant": "ameriprise",
           "site": ["Ameriprise", "External"]}
    raw = [{"total": 1, "jobPostings": [{
        "title": "Financial Analyst", "externalPath": "/job/Minneapolis-MN/Financial-Analyst_R123",
        "locationsText": "Minneapolis, MN", "postedOn": "Posted 3 Days Ago",
    }]}]
    rows = normalize(src, raw, {"site": "External"})
    check_columns(rows)
    r = rows[0]
    assert r["source_id"] == "/job/Minneapolis-MN/Financial-Analyst_R123"
    assert r["posted_date"] == ""   # Workday gives no absolute date
    assert r["department"] == ""
    assert r["url"] == ("https://ameriprise.wd5.myworkdayjobs.com/en-US/External"
                        "/job/Minneapolis-MN/Financial-Analyst_R123")


def test_missing_fields_are_empty():
    src = {"name": "x", "employer": "X", "ats": "greenhouse", "board": "x"}
    rows = normalize(src, [{"jobs": [{"id": 5, "title": "Analyst"}]}])
    assert rows[0]["location"] == "" and rows[0]["posted_date"] == "" and rows[0]["url"] == ""

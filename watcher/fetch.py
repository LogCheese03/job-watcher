"""Call each source's job board API and return the raw JSON responses.

Every function returns a list of the JSON responses the board sent back
(one per page for boards that paginate). Nothing here reads HTML.
"""
import json
import time
import urllib.request

USER_AGENT = "job-watcher (class project; GitHub Actions)"
TIMEOUT = 60


def _request(url, body=None):
    data = None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # retry network hiccups, then give up
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise last_error


def fetch_greenhouse(src):
    url = f"https://boards-api.greenhouse.io/v1/boards/{src['board']}/jobs?content=true"
    return [_request(url)]


def fetch_lever(src):
    url = f"https://api.lever.co/v0/postings/{src['board']}?mode=json"
    return [_request(url)]


def fetch_ashby(src):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{src['board']}"
    return [_request(url)]


def fetch_smartrecruiters(src):
    pages, offset = [], 0
    while True:
        url = (f"https://api.smartrecruiters.com/v1/companies/{src['board']}/postings"
               f"?limit=100&offset={offset}")
        page = _request(url)
        pages.append(page)
        offset += len(page.get("content", []))
        if not page.get("content") or offset >= page.get("totalFound", 0):
            return pages


def workday_sites(src):
    """A Workday source may list several candidate board (site) names to try."""
    site = src["site"]
    return site if isinstance(site, list) else [site]


def fetch_workday(src):
    last_error = None
    for site in workday_sites(src):
        try:
            return _fetch_workday_site(src, site), {"site": site}
        except Exception as exc:
            last_error = exc
    raise last_error


def _fetch_workday_site(src, site):
    url = f"https://{src['host']}/wday/cxs/{src['tenant']}/{site}/jobs"
    pages, offset, total = [], 0, None
    while True:
        body = {"appliedFacets": {}, "limit": 20, "offset": offset,
                "searchText": src.get("search", "")}
        page = _request(url, body)
        pages.append(page)
        if total is None:  # Workday only reports the total on the first page
            total = page.get("total", 0)
        got = len(page.get("jobPostings", []))
        offset += got
        if got == 0 or offset >= total:
            return pages
        time.sleep(0.3)


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "workday": fetch_workday,
}


def fetch_source(src):
    """Return (responses, meta). meta records details needed to read the responses."""
    result = FETCHERS[src["ats"]](src)
    if isinstance(result, tuple):
        return result
    return result, {}

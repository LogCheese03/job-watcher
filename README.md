# Job Watcher

[![Tests](https://github.com/LogCheese03/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/LogCheese03/job-watcher/actions/workflows/tests.yml)

A tool that watches the job market for **finance analyst** roles. Every day GitHub Actions pulls the
open positions at 22 employers from their applicant tracking systems, compares them with the day
before, records what is new and what is gone, opens a GitHub Issue with the changes, and publishes
the result to a website on GitHub Pages.

- **Site:** https://logcheese03.github.io/job-watcher/
- **Role watched:** finance analyst (financial analyst, FP&A, credit, treasury, investment analyst)

## Sources

Every source is read through its job board's public JSON API, with no login. No HTML is read.

| Source | Employer | Applicant tracking system | Board |
|---|---|---|---|
| affirm | Affirm | Greenhouse | `affirm` |
| robinhood | Robinhood | Greenhouse | `robinhood` |
| chime | Chime | Greenhouse | `chime` |
| sofi | SoFi | Greenhouse | `sofi` |
| brex | Brex | Greenhouse | `brex` |
| toast | Toast | Greenhouse | `toast` |
| betterment | Betterment | Greenhouse | `betterment` |
| coinbase | Coinbase | Greenhouse | `coinbase` |
| stripe | Stripe | Greenhouse | `stripe` |
| adyen | Adyen | Greenhouse | `adyen` |
| plaid | Plaid | Ashby | `plaid` |
| wealthfront | Wealthfront | Lever | `wealthfront` |
| ramp | Ramp | Ashby | `ramp` |
| visa | Visa | Workday | `visa.wd5.myworkdayjobs.com/Visa` |
| mastercard | Mastercard | Workday | `mastercard.wd1.myworkdayjobs.com/CorporateCareers` |
| capitalone | Capital One | Workday | `capitalone.wd12.myworkdayjobs.com/Capital_One` |
| fidelity | Fidelity | Workday | `fmr.wd1.myworkdayjobs.com/targeted` |
| statestreet | State Street | Workday | `statestreet.wd1.myworkdayjobs.com/Global` |
| morganstanley | Morgan Stanley | Workday | `ms.wd5.myworkdayjobs.com/External` |
| ameriprise | Ameriprise Financial | Workday | `ameriprise.wd5.myworkdayjobs.com/Ameriprise` |
| bankofamerica | Bank of America | Workday | `ghr.wd1.myworkdayjobs.com/Lateral-US` |
| blackrock | BlackRock | Workday | `blackrock.wd1.myworkdayjobs.com/BlackRock_Professional` |

No board returns more than 5,000 postings (the largest, Morgan Stanley, State Street, Capital One and Bank of America, each return about 1,100–2,100), so **no search term is used**: every board is read in full. The pipeline supports a `"search"` setting per Workday source if a board ever grows past 5,000. The list of sources and their settings is in `sources.json`.

## Title rule

A posting is **in the role** (`in_role = true`) when its title contains at least one of these phrases
(case-insensitive, whole words):

> financial analyst · finance analyst · FP&A · financial planning · corporate finance ·
> credit analyst · credit risk analyst · treasury analyst · investment analyst ·
> finance associate · financial associate · finance partner / finance business partner ·
> finance or financial rotation(al) program

and contains none of: **intern / internship, engineer, developer, recruiter, sales**.
Seniority does not matter: "Senior Financial Analyst" and "FP&A Manager" are in the role.
The rule is in `watcher/titles.py`.

## Build the history file from the raw files

```bash
python -m watcher.build
```

This reads only `data/raw/<date>/<source>.json.gz` and rewrites `data/history.csv`. Running it again
produces the same file, and a change to a rule applies to every day of the history.

Other commands:

```bash
python run.py            # the full daily run (what GitHub Actions runs)
python run.py --check    # call every source and print counts, writing nothing
python -m pytest         # run the tests
```

## How a run works

1. Calls every source and saves its responses, compressed, to `data/raw/<date>/<source>.json.gz`.
   A source that fails writes no raw file that day; the run carries on. The result of every source
   is recorded in `data/runs/<date>.json`.
2. Builds `data/history.csv` from all the raw files, day by day: converts each posting to the common
   columns, applies the title rule, then sets first-seen, last-seen, removed and reopened status.
   A posting is only marked removed on a day its source has a raw file.
3. Writes `data/status.json`.
4. Opens a GitHub Issue titled with the date listing new and removed postings with links, and
   closes the previous day's issue (an issue is opened every day, even with no changes).
5. Commits the raw files, the history, the status file and the run log.

Dates are UTC. A second run on the same day replaces that day's raw files, rebuilds the history and
updates that day's issue, so each day counts once.

## Files

| File | What it does |
|---|---|
| `run.py` | The daily pipeline: fetch, build, status, issue body. `--check` tests the sources. |
| `sources.json` | The watch list: each employer, its ATS and the settings needed to call it. |
| `watcher/fetch.py` | Calls each ATS's JSON API (Greenhouse, Lever, Ashby, SmartRecruiters, Workday), with paging and retries. |
| `watcher/normalize.py` | Converts each source's responses to the common columns. |
| `watcher/titles.py` | The title rule (`in_role`). |
| `watcher/build.py` | Builds `data/history.csv` from the raw files (first-seen, last-seen, removed logic). |
| `watcher/status.py` | Writes `data/status.json`. |
| `watcher/issue.py` | Writes the body of the daily GitHub Issue. |
| `tests/test_normalize.py` | Tests the conversion of each source to the common columns. |
| `tests/test_titles.py` | Tests the title rule. |
| `tests/test_history.py` | Tests first-seen, last-seen, removed and reopened logic, the build and the status counts. |
| `.github/workflows/daily.yml` | Runs the pipeline every day at 12:23 UTC, opens the issue and commits the data. Can also be run by hand, with a `check` mode. |
| `.github/workflows/tests.yml` | Runs the tests on every push. |
| `data/raw/<date>/<source>.json.gz` | What each source returned that day, compressed. |
| `data/runs/<date>.json` | Result of every source on that day (ok, count, error). |
| `data/history.csv` | One row per posting, built from the raw files. |
| `data/status.json` | Summary of the latest run. |
| `index.html` | Today page: last run, source status, the four counts, new and removed postings. |
| `browse.html` | Browse page: open postings with role switch, filters, title search, sort, apply links and a starred shortlist saved in the browser. |
| `market.html` | Market page: six findings computed in the browser from `history.csv`. |
| `assets/style.css` | Fonts and colors shared by all pages. |
| `assets/common.js` | Shared navigation bar, data loading, CSV parsing and service worker registration. |
| `assets/charts.js` | Small SVG chart drawing used by the Market page (no outside library, so it works offline). |
| `manifest.webmanifest` | Web app manifest so the site installs as an app. |
| `sw.js` | Service worker: loads from the network when online, serves the last loaded data when offline. |
| `icons/` | App icons. |
| `pytest.ini`, `.gitignore` | Test settings and ignored files. |

## History columns

`posting_id` (source:source_id), `source`, `source_id`, `employer`, `title`, `location`, `department`,
`posted_date`, `url`, `in_role`, `first_run`, `first_seen`, `last_seen`, `status` (open/removed),
`removed_date`. Workday boards give no absolute posting date or department, so those columns are
empty for Workday sources.

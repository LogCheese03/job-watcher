"""Write the body of the daily GitHub Issue (new and removed postings, with links)."""

MAX_BODY = 60000  # GitHub's limit on an issue body is 65,536 characters


def _line(r):
    role = " ⭐ in role" if r["in_role"] else ""
    loc = f" — {r['location']}" if r["location"] else ""
    return f"- [{r['title']}]({r['url']}) · {r['employer']}{loc}{role}"


def _section(heading, rows, note):
    out = [f"## {heading} ({len(rows)})", ""]
    if not rows:
        out.append(note)
    else:
        rows = sorted(rows, key=lambda r: (not r["in_role"], r["employer"], r["title"]))
        out.extend(_line(r) for r in rows)
    out.append("")
    return out


def make_issue_body(rows, run_day, status, site_url=""):
    new = [r for r in rows if r["first_seen"] == run_day and not r["first_run"]]
    removed = [r for r in rows if r["removed_date"] == run_day]
    failed = [s["name"] for s in status["sources"] if not s["ok"]]

    lines = [f"Daily run for **{run_day}** (UTC). Open postings: **{status['open']}**.", ""]
    if site_url:
        lines += [f"Site: {site_url}", ""]
    if failed:
        lines += [f"Sources that failed today: {', '.join(failed)}", ""]
    lines += _section("New postings", new, "No new postings today.")
    lines += _section("Removed postings", removed, "No removed postings today.")
    body = "\n".join(lines)

    if len(body) > MAX_BODY:  # keep the issue valid on very busy days
        cut = body[:MAX_BODY].rsplit("\n", 1)[0]
        body = cut + "\n\n…list cut short to fit GitHub's size limit; see the site for the rest."
    return body

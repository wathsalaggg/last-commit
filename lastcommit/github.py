"""Gather verified facts about a repo from the GitHub REST API.

Everything returned here is fact: it comes straight from the API and is shown
on the ofrenda separately from the ghost's (fictional) monologue.
"""

import re
from datetime import datetime, timezone

from . import config
from .http import HTTPError, get_json

API = "https://api.github.com"


def parse_repo(url_or_slug: str) -> tuple[str, str]:
    """Accept 'owner/repo', 'github.com/owner/repo' or a full URL."""
    s = url_or_slug.strip().rstrip("/")
    s = re.sub(r"\.git$", "", s)
    m = re.search(r"(?:github\.com[/:])?([\w.-]+)/([\w.-]+)$", s)
    if not m:
        raise ValueError(f"Not a GitHub repo: {url_or_slug!r}")
    return m.group(1), m.group(2)


def _headers():
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "last-commit",
    }
    token = config.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(path, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{API}{path}" + (f"?{query}" if query else "")
    return get_json(url, headers=_headers())


def _last_page(headers) -> int | None:
    """Read the page count from a Link header (per_page=1 -> item count)."""
    link = headers.get("Link", "")
    m = re.search(r'[?&]page=(\d+)>; rel="last"', link)
    return int(m.group(1)) if m else None


def _commit_summary(c):
    commit = c["commit"]
    return {
        "sha": c["sha"][:7],
        "url": c["html_url"],
        "message": commit["message"].split("\n", 1)[0][:200],
        "date": commit["committer"]["date"] or commit["author"]["date"],
        "author": (c.get("author") or {}).get("login") or commit["author"]["name"],
    }


def _years_between(a: str, b: str) -> float:
    fa = datetime.fromisoformat(a.replace("Z", "+00:00"))
    fb = datetime.fromisoformat(b.replace("Z", "+00:00"))
    return round((fb - fa).days / 365.25, 1)


def gather(url_or_slug: str) -> dict:
    owner, name = parse_repo(url_or_slug)
    repo, _ = _get(f"/repos/{owner}/{name}")
    full = repo["full_name"]  # canonical casing, follows renames

    commits, h = _get(f"/repos/{full}/commits", per_page=1)
    last = _commit_summary(commits[0]) if commits else None
    total = _last_page(h) or len(commits)

    first = last
    if total and total > 1:
        oldest, _ = _get(f"/repos/{full}/commits", per_page=1, page=total)
        if oldest:
            first = _commit_summary(oldest[0])

    try:
        contribs, h = _get(f"/repos/{full}/contributors", per_page=5)
        contributors = [
            {"login": c["login"], "contributions": c["contributions"]}
            for c in contribs if c.get("type") != "Bot"
        ]
    except HTTPError:
        contributors = []  # very large repos can refuse this endpoint

    try:
        rel, _ = _get(f"/repos/{full}/releases/latest")
        latest_release = {"tag": rel["tag_name"], "date": rel["published_at"]}
    except HTTPError:
        latest_release = None

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    born = first["date"] if first else repo["created_at"]
    died = last["date"] if last else repo["pushed_at"]

    return {
        "full_name": full,
        "url": repo["html_url"],
        "description": repo.get("description") or "",
        "language": repo.get("language"),
        "license": (repo.get("license") or {}).get("spdx_id"),
        "homepage": repo.get("homepage") or None,
        "archived": repo["archived"],
        "created_at": repo["created_at"],
        "pushed_at": repo["pushed_at"],
        "born": born,
        "died": died,
        "lifespan_years": _years_between(born, died),
        "years_since_last_commit": _years_between(died, now),
        "stars": repo["stargazers_count"],
        "forks": repo["forks_count"],
        "open_issues": repo["open_issues_count"],
        "total_commits": total,
        "first_commit": first,
        "last_commit": last,
        "top_contributors": contributors,
        "latest_release": latest_release,
        "fetched_at": now,
    }

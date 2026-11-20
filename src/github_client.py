import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.github.com"
# Six weeks gives a weekly trend while keeping one analysis to a few seconds.
WINDOW_DAYS = 42
MAX_PAGES = 3
# Each PR's reviews are a separate request, so cap how many we look up.
MAX_REVIEWED_PRS = 40


class GitHubError(Exception):
    """A problem worth showing the visitor as-is (wrong name, private repo, rate limit)."""


def _headers():
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN")
    # Sending "token None" makes GitHub reject even public repos, so only send a real token.
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(path, params=None, missing_ok=False):
    try:
        response = requests.get(f"{API}{path}", headers=_headers(), params=params, timeout=15)
    except requests.RequestException:
        raise GitHubError("We couldn't reach GitHub. Please try again in a minute.")

    if response.status_code == 404 and missing_ok:
        return []
    if response.status_code == 404:
        raise GitHubError("We couldn't find that repository. Check the owner and name, and make sure it's public.")
    if response.status_code in (403, 429) and response.headers.get("X-RateLimit-Remaining") == "0":
        raise GitHubError("GitHub's hourly limit was reached. Please try again in a few minutes.")
    if response.status_code == 409:
        raise GitHubError("This repository is empty, so there's nothing to analyze yet.")
    if response.status_code == 401:
        raise RuntimeError("GITHUB_TOKEN was rejected by GitHub")
    response.raise_for_status()
    return response.json()


def _is_bot(user):
    return bool(user) and (user.get("type") == "Bot" or user.get("login", "").endswith("[bot]"))


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def _recent_pull_requests(owner, repo, since):
    # Sorted by last update, so we can stop paging once PRs are older than the window.
    prs = []
    for page in range(1, MAX_PAGES + 1):
        # Some projects (the Linux kernel, for one) switch pull requests off, and GitHub
        # answers 404 even though the repo exists; treat that as "no PRs".
        batch = _get(f"/repos/{owner}/{repo}/pulls",
                     {"state": "all", "sort": "updated", "direction": "desc", "per_page": 100, "page": page},
                     missing_ok=True)
        for pr in batch:
            if _parse(pr["updated_at"]) < since:
                return prs
            if not _is_bot(pr.get("user")):
                prs.append(pr)
        if len(batch) < 100:
            break
    return prs


def _recent_commits(owner, repo, since):
    commits = []
    for page in range(1, MAX_PAGES + 1):
        batch = _get(f"/repos/{owner}/{repo}/commits",
                     {"since": since.isoformat(), "per_page": 100, "page": page})
        commits.extend(c for c in batch if not _is_bot(c.get("author")))
        if len(batch) < 100:
            break
    return commits


def _reviews_for(owner, repo, prs):
    reviewed = [pr for pr in prs if pr.get("merged_at")][:MAX_REVIEWED_PRS]

    def fetch(pr):
        try:
            reviews = _get(f"/repos/{owner}/{repo}/pulls/{pr['number']}/reviews", {"per_page": 100})
        except GitHubError:
            reviews = []
        return pr["number"], [r for r in reviews if r.get("user") and not _is_bot(r["user"])]

    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(fetch, reviewed))


def fetch_repo_activity(owner, repo):
    """Everything the metrics need for the last WINDOW_DAYS, in one call."""
    info = _get(f"/repos/{owner}/{repo}")
    if info.get("private"):
        raise GitHubError("That repository is private. Only public repositories can be analyzed for now.")

    until = datetime.now(timezone.utc)
    since = until - timedelta(days=WINDOW_DAYS)
    prs = _recent_pull_requests(owner, repo, since)
    commits = _recent_commits(owner, repo, since)
    if not prs and not commits:
        raise GitHubError("There were no pull requests or commits in the last six weeks, so there's nothing to analyze yet.")

    return {
        "owner": info["owner"]["login"],
        "repo": info["name"],
        "since": since,
        "until": until,
        "pull_requests": prs,
        "commits": commits,
        "reviews": _reviews_for(owner, repo, prs),
    }


if __name__ == "__main__":
    activity = fetch_repo_activity("ttabirami12062", "IPMS")
    print(f"{len(activity['pull_requests'])} PRs, {len(activity['commits'])} commits, "
          f"{sum(len(r) for r in activity['reviews'].values())} reviews since {activity['since']:%b %d}")

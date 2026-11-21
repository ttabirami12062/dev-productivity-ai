import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv

load_dotenv()

GRAPHQL = "https://api.github.com/graphql"
# Six weeks gives a weekly trend while keeping one analysis to a few seconds.
WINDOW_DAYS = 42
MAX_PAGES = 3

# One query returns the repo details, a page of PRs with their reviews, and a page of
# commits. The REST API needed a separate request per PR's reviews (45 requests for a
# busy repo); this needs 1 to 3 in total.
QUERY = """
query($owner: String!, $name: String!, $since: GitTimestamp!,
      $prCursor: String, $commitCursor: String, $withPrs: Boolean!, $withCommits: Boolean!) {
  repository(owner: $owner, name: $name) {
    name
    owner { login }
    isPrivate
    pullRequests(first: 100, after: $prCursor, orderBy: {field: UPDATED_AT, direction: DESC}) @include(if: $withPrs) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title state createdAt updatedAt mergedAt additions deletions
        labels(first: 10) { nodes { name } }
        author { __typename login }
        reviews(first: 50) { nodes { submittedAt author { __typename login } } }
      }
    }
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100, after: $commitCursor, since: $since) @include(if: $withCommits) {
            pageInfo { hasNextPage endCursor }
            nodes { committedDate author { name date user { login } } }
          }
        }
      }
    }
  }
}
"""


class GitHubError(Exception):
    """A problem worth showing the visitor as-is (wrong name, private repo, rate limit)."""


def _headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    # GitHub's GraphQL API always needs a token; sending "token None" would be rejected anyway.
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _query(variables):
    try:
        response = requests.post(GRAPHQL, json={"query": QUERY, "variables": variables}, headers=_headers(), timeout=30)
    except requests.RequestException:
        raise GitHubError("We couldn't reach GitHub. Please try again in a minute.")

    if response.status_code == 401:
        raise RuntimeError("GITHUB_TOKEN was rejected by GitHub")
    if response.status_code in (403, 429):
        raise GitHubError("GitHub's hourly limit was reached. Please try again in a few minutes.")
    response.raise_for_status()

    body = response.json()
    for error in body.get("errors") or []:
        if error.get("type") == "NOT_FOUND":
            raise GitHubError("We couldn't find that repository. Check the owner and name, and make sure it's public.")
        if error.get("type") == "RATE_LIMITED":
            raise GitHubError("GitHub's hourly limit was reached. Please try again in a few minutes.")
    if body.get("errors") and not (body.get("data") or {}).get("repository"):
        raise RuntimeError(f"GitHub GraphQL error: {body['errors'][0].get('message')}")
    return body["data"]["repository"]


def _is_bot(author):
    login = (author or {}).get("login") or ""
    return (author or {}).get("__typename") == "Bot" or login.endswith("[bot]")


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def _as_pr(node):
    # Same shape the REST API used, so metrics.py doesn't need to know where data came from.
    author = node.get("author") or {}
    return {
        "number": node["number"],
        "state": "open" if node["state"] == "OPEN" else "closed",
        "created_at": node["createdAt"],
        "updated_at": node["updatedAt"],
        "merged_at": node["mergedAt"],
        "user": {"login": author.get("login"), "type": author.get("__typename")} if author else None,
        # For time to first review: when someone other than the author first reviewed it.
        "first_review_at": min((r["submittedAt"] for r in (node.get("reviews") or {}).get("nodes", [])
                                if r.get("submittedAt") and r.get("author") and not _is_bot(r["author"])
                                and r["author"].get("login") != author.get("login")), default=None),
        # For cycle time; filled in by _add_first_commits for merged PRs only.
        "first_commit_at": None,
        "lines_changed": (node.get("additions") or 0) + (node.get("deletions") or 0),
        "is_fix": _looks_like_fix(node),
        "files": None,  # filled in for merged fixes by _add_first_commits
    }


FIX_WORDS = re.compile(r"\b(fix|fixes|fixed|bug|bugfix|hotfix|regression|patch)\b", re.IGNORECASE)


def _looks_like_fix(node):
    labels = [l["name"].lower() for l in ((node.get("labels") or {}).get("nodes") or [])]
    return bool(FIX_WORDS.search(node.get("title") or "")) or any("bug" in l or "regression" in l for l in labels)


def _as_commit(node):
    author = node.get("author") or {}
    login = (author.get("user") or {}).get("login")
    return {
        "author": {"login": login} if login else None,
        # author.date keeps the author's own UTC offset (e.g. 20:54+05:30), unlike committedDate.
        "commit": {"author": {"name": author.get("name") or "Unknown", "date": author.get("date")},
                   "committer": {"date": node["committedDate"]}},
    }


def _add_first_commits(owner, repo, prs, since):
    """Adds when each merged PR's first commit was written, for cycle time.

    Asking for commits inside the main query made it about twice as slow, so this is a
    second, small query for just the PRs merged in the window (100 per request).
    """
    merged = [pr for pr in prs if pr["merged_at"] and _parse(pr["merged_at"]) >= since]

    def fetch(batch):
        # Fix PRs also bring their file list, to spot files that keep needing fixes.
        fields = " ".join(f"p{pr['number']}: pullRequest(number: {pr['number']}) {{ commits(first: 1) {{ nodes {{ commit {{ authoredDate }} }} }}"
                          + (" files(first: 30) { nodes { path } }" if pr["is_fix"] else "") + " }"
                          for pr in batch)
        try:
            response = requests.post(GRAPHQL, headers=_headers(), timeout=30, json={
                "query": f"query($owner: String!, $name: String!) {{ repository(owner: $owner, name: $name) {{ {fields} }} }}",
                "variables": {"owner": owner, "name": repo}})
            found = ((response.json().get("data") or {}).get("repository") or {})
        except (requests.RequestException, ValueError):
            return  # cycle time and fix files are a bonus; the rest of the analysis doesn't need them
        for pr in batch:
            data = found.get(f"p{pr['number']}") or {}
            nodes = (data.get("commits") or {}).get("nodes") or []
            pr["first_commit_at"] = nodes[0]["commit"]["authoredDate"] if nodes else None
            if pr["is_fix"]:
                pr["files"] = [f["path"] for f in ((data.get("files") or {}).get("nodes") or [])]

    # Small batches in parallel: one big request with every fix PR's file list took ~8s on django.
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(fetch, [merged[i:i + 25] for i in range(0, len(merged), 25)]))


def _is_bot_commit(node):
    author = node.get("author") or {}
    return (author.get("name") or "").endswith("[bot]") or _is_bot(author.get("user"))


def window_for(tz):
    """The last WINDOW_DAYS ending at midnight tonight in the viewer's time zone.

    Lining the window up with the viewer's midnights means a PR merged at 7:37pm on
    Oct 11 their time lands in the same week they'd expect from GitHub, not the
    next one because it was already Oct 12 in UTC.
    """
    now = datetime.now(timezone.utc)
    local_now = now.astimezone(tz)
    tonight = datetime.combine(local_now.date() + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    return tonight - timedelta(days=WINDOW_DAYS), now, tonight


def fetch_repo_activity(owner, repo, tz=ZoneInfo("UTC")):
    """Everything the metrics need for the last WINDOW_DAYS."""
    since, until, window_end = window_for(tz)
    variables = {"owner": owner, "name": repo, "since": since.astimezone(timezone.utc).isoformat(),
                 "prCursor": None, "commitCursor": None, "withPrs": True, "withCommits": True}

    prs, reviews, commits, info = [], {}, [], None
    prs_done = commits_done = False
    for _ in range(MAX_PAGES):
        data = _query(variables)
        if info is None:
            info = data
            if data.get("isPrivate"):
                raise GitHubError("That repository is private. Only public repositories can be analyzed for now.")

        if not prs_done:
            page = data.get("pullRequests") or {"nodes": [], "pageInfo": {"hasNextPage": False}}
            for node in page["nodes"]:
                # Sorted by last update, so everything after this is older than the window.
                if _parse(node["updatedAt"]) < since:
                    prs_done = True
                    break
                if _is_bot(node.get("author")):
                    continue
                prs.append(_as_pr(node))
                # Review load counts only PRs merged inside the window, like the merge times do.
                if node["mergedAt"] and _parse(node["mergedAt"]) >= since:
                    reviews[node["number"]] = [{"user": {"login": r["author"]["login"]}}
                                               for r in node["reviews"]["nodes"] if r.get("author") and not _is_bot(r["author"])]
            prs_done = prs_done or not page["pageInfo"]["hasNextPage"]
            variables["prCursor"] = page["pageInfo"].get("endCursor")

        if not commits_done:
            target = (data.get("defaultBranchRef") or {}).get("target") or {}
            history = target.get("history") or {"nodes": [], "pageInfo": {"hasNextPage": False}}
            commits += [_as_commit(n) for n in history["nodes"] if not _is_bot_commit(n)]
            commits_done = not history["pageInfo"]["hasNextPage"]
            variables["commitCursor"] = history["pageInfo"].get("endCursor")

        if prs_done and commits_done:
            break
        variables["withPrs"], variables["withCommits"] = not prs_done, not commits_done

    _add_first_commits(owner, repo, prs, since)

    # Stopped after MAX_PAGES with more still in the window, so the counts are minimums.
    prs_capped, commits_capped = not prs_done, not commits_done

    if not prs and not commits:
        raise GitHubError("There were no pull requests or commits in the last six weeks, so there's nothing to analyze yet.")

    return {
        "owner": info["owner"]["login"],
        "repo": info["name"],
        "since": since,
        "until": until,
        "window_end": window_end,
        "tz": tz,
        "pull_requests": prs,
        "commits": commits,
        "reviews": reviews,
        "prs_capped": prs_capped,
        "commits_capped": commits_capped,
    }


if __name__ == "__main__":
    activity = fetch_repo_activity("tailwindlabs", "tailwindcss")
    print(f"{len(activity['pull_requests'])} PRs, {len(activity['commits'])} commits, "
          f"{sum(len(r) for r in activity['reviews'].values())} reviews since {activity['since']:%b %d}")

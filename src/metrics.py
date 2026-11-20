from datetime import datetime, timedelta, timezone
from statistics import median

# Thresholds a reviewer can reason about. They match the sample incident report
# (merge within 24h, nobody over 50% of reviews), so the report can cite them.
MERGE_TARGET_HOURS = 24
REVIEW_SHARE_LIMIT = 50
STALE_OPEN_HOURS = 72
# Below this much activity a score says more about silence than about the team.
QUIET_ACTIVITY = 5


def duration(hours):
    """Plain wording for a wait: '9 hours', '2.5 days', '30 days'."""
    if hours < 48:
        return f"{hours:g} hours"
    days = hours / 24
    return f"{days:.1f} days".replace(".0 days", " days") if days < 10 else f"{round(days)} days"


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def _person(commit):
    # Prefer the GitHub login so one person with two git names counts once.
    if commit.get("author") and commit["author"].get("login"):
        return commit["author"]["login"]
    return commit.get("commit", {}).get("author", {}).get("name", "Unknown")


def _share(counts):
    total = sum(counts.values())
    if not total:
        return None, 0
    top = max(counts, key=counts.get)
    return top, round(counts[top] / total * 100)


def _weekly_merge_hours(merged, until, weeks=6):
    buckets = []
    for i in range(weeks, 0, -1):
        start, end = until - timedelta(days=7 * i), until - timedelta(days=7 * (i - 1))
        hours = [h for at, h in merged if start <= at < end]
        last = end - timedelta(days=1)
        # A range, not just the start date: "Oct 9" alone reads as a single day.
        label = f"{start:%b} {start.day}-{last.day}" if start.month == last.month else f"{start:%b} {start.day}-{last:%b} {last.day}"
        buckets.append({
            "week_start": start.date().isoformat(),
            "label": label,
            "merged": len(hours),
            "median_hours": round(median(hours), 1) if hours else None,
        })
    return buckets


def calculate_metrics(activity):
    since, until = activity["since"], activity["until"]
    prs = activity["pull_requests"]

    # Time from opening a PR to merging it, for PRs merged inside the window.
    merged = []
    for pr in prs:
        merged_at = _parse(pr.get("merged_at"))
        if merged_at and merged_at >= since:
            merged.append((merged_at, (merged_at - _parse(pr["created_at"])).total_seconds() / 3600))
    merge_hours = [h for _, h in merged]

    open_prs = [pr for pr in prs if pr["state"] == "open"]
    stale = [pr for pr in open_prs if (until - _parse(pr["created_at"])).total_seconds() / 3600 > STALE_OPEN_HOURS]
    closed_unmerged = [pr for pr in prs if pr["state"] == "closed" and not pr.get("merged_at")]

    review_counts = {}
    for reviews in activity["reviews"].values():
        # One person approving and commenting on the same PR counts as one review of it.
        for login in {r["user"]["login"] for r in reviews}:
            review_counts[login] = review_counts.get(login, 0) + 1
    top_reviewer, top_review_share = _share(review_counts)

    commit_counts = {}
    for commit in activity["commits"]:
        person = _person(commit)
        commit_counts[person] = commit_counts.get(person, 0) + 1
    top_author, top_commit_share = _share(commit_counts)

    people = set(commit_counts) | set(review_counts) | {pr["user"]["login"] for pr in prs if pr.get("user")}

    return {
        "window": {"since": since.date().isoformat(), "until": until.date().isoformat(), "days": (until - since).days},
        "people": len(people),
        "solo": len(people) <= 1,
        "quiet": len(merged) + len(activity["commits"]) < QUIET_ACTIVITY,
        "uses_prs": bool(prs),
        "prs": {
            "total": len(prs),
            "merged": len(merged),
            "open": len(open_prs),
            "stale_open": len(stale),
            "closed_unmerged": len(closed_unmerged),
            "median_merge_hours": round(median(merge_hours), 1) if merge_hours else None,
            "weekly": _weekly_merge_hours(merged, until),
        },
        "reviews": {
            "total": sum(review_counts.values()),
            "reviewed_prs": len(activity["reviews"]),
            "per_reviewer": dict(sorted(review_counts.items(), key=lambda kv: -kv[1])),
            "top_reviewer": top_reviewer,
            "top_share": top_review_share,
        },
        "commits": {
            "total": len(activity["commits"]),
            "per_author": dict(sorted(commit_counts.items(), key=lambda kv: -kv[1])),
            "top_author": top_author,
            "top_share": top_commit_share,
        },
    }


def calculate_health_score(metrics):
    """Returns (score, signals). Each signal explains one deduction, so the score is never a mystery."""
    score, signals = 100, []
    prs, reviews, commits = metrics["prs"], metrics["reviews"], metrics["commits"]

    merge = prs["median_merge_hours"]
    if merge is not None and merge > 7 * 24:
        score -= 35
        signals.append(f"PRs take {duration(merge)} to merge, far over the {MERGE_TARGET_HOURS}-hour target.")
    elif merge is not None and merge > 2 * MERGE_TARGET_HOURS:
        score -= 25
        signals.append(f"PRs take {duration(merge)} to merge, more than twice the {MERGE_TARGET_HOURS}-hour target.")
    elif merge is not None and merge > MERGE_TARGET_HOURS:
        score -= 12
        signals.append(f"PRs take {duration(merge)} to merge, over the {MERGE_TARGET_HOURS}-hour target.")

    weeks = [w["median_hours"] for w in prs["weekly"] if w["median_hours"] is not None]
    if len(weeks) >= 3 and weeks[-1] > MERGE_TARGET_HOURS and weeks[-1] >= 2 * weeks[0]:
        score -= 10
        signals.append(f"Merge time has climbed from {duration(weeks[0])} to {duration(weeks[-1])} over the last few weeks.")

    if prs["stale_open"] >= 5:
        score -= 15
        signals.append(f"{prs['stale_open']} PRs have been open for more than 3 days.")
    elif prs["stale_open"] >= 2:
        score -= 8
        signals.append(f"{prs['stale_open']} PRs have been open for more than 3 days.")

    # Workload balance only means something when there is a team to balance it across.
    if not metrics["solo"]:
        if reviews["total"] >= 5 and reviews["top_share"] > 70:
            score -= 25
            signals.append(f"{reviews['top_reviewer']} did {reviews['top_share']}% of all reviews.")
        elif reviews["total"] >= 5 and reviews["top_share"] > REVIEW_SHARE_LIMIT:
            score -= 12
            signals.append(f"{reviews['top_reviewer']} did {reviews['top_share']}% of all reviews, over the {REVIEW_SHARE_LIMIT}% limit.")
        if commits["total"] >= 10 and commits["top_share"] > 80:
            score -= 10
            signals.append(f"{commits['top_author']} made {commits['top_share']}% of all commits.")

    return max(score, 0), signals


def health_status(score):
    if score >= 80:
        return "healthy"
    if score >= 60:
        return "watch"
    return "at_risk"

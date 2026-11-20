"""Fast checks of the scoring math. No API keys or network needed."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.metrics import calculate_health_score, calculate_metrics

NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def pr(number, author, opened_days_ago, merge_after_hours=None, state="closed"):
    created = NOW - timedelta(days=opened_days_ago)
    merged = created + timedelta(hours=merge_after_hours) if merge_after_hours is not None else None
    return {"number": number, "user": {"login": author}, "state": "open" if merged is None and state == "open" else state,
            "created_at": iso(created), "updated_at": iso(merged or created), "merged_at": iso(merged) if merged else None}


def commit(login):
    return {"author": {"login": login}, "commit": {"author": {"name": login.title()}}}


def activity(prs, commits, reviews):
    return {"since": NOW - timedelta(days=42), "until": NOW, "pull_requests": prs, "commits": commits, "reviews": reviews}


def review(login):
    return {"user": {"login": login}}


def test_solo_repo_is_not_punished_for_workload():
    prs = [pr(i, "abi", 30 - i * 4, merge_after_hours=2) for i in range(5)]
    metrics = calculate_metrics(activity(prs, [commit("abi")] * 20, {}))
    score, signals = calculate_health_score(metrics)
    assert metrics["solo"] and score == 100, (score, signals)


def test_overloaded_reviewer_and_slow_merges_lower_the_score():
    prs = [pr(i, "dev", 35 - i * 5, merge_after_hours=60) for i in range(6)]
    reviews = {p["number"]: [review("priya")] for p in prs}
    reviews[0].append(review("sam"))
    metrics = calculate_metrics(activity(prs, [commit("dev")] * 5 + [commit("priya")] * 5, reviews))
    score, signals = calculate_health_score(metrics)
    assert metrics["reviews"]["top_reviewer"] == "priya" and metrics["reviews"]["top_share"] == 86
    assert score <= 50 and any("priya" in s for s in signals), (score, signals)


def test_same_person_reviewing_twice_counts_once_per_pr():
    prs = [pr(1, "dev", 10, merge_after_hours=5)]
    metrics = calculate_metrics(activity(prs, [commit("dev")], {1: [review("lena"), review("lena")]}))
    assert metrics["reviews"]["per_reviewer"] == {"lena": 1}


def test_weekly_trend_has_six_weeks():
    metrics = calculate_metrics(activity([pr(1, "dev", 3, merge_after_hours=10)], [commit("dev")], {}))
    weeks = metrics["prs"]["weekly"]
    assert len(weeks) == 6 and weeks[-1]["median_hours"] == 10.0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")

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


def test_almost_no_activity_is_marked_quiet():
    metrics = calculate_metrics(activity([pr(1, "dev", 10)], [commit("dev")], {}))
    assert metrics["quiet"] and metrics["uses_prs"]


def test_repo_without_pull_requests():
    metrics = calculate_metrics(activity([], [commit("linus")] * 30, {}))
    assert not metrics["uses_prs"] and not metrics["quiet"]


def test_first_review_cycle_time_and_unreviewed_merges():
    created = NOW - timedelta(days=5)
    def reviewed_pr(number, review_after, commit_before, merge_after, reviewed=True):
        return {"number": number, "user": {"login": "dev"}, "state": "closed", "created_at": iso(created),
                "updated_at": iso(created + timedelta(hours=merge_after)), "merged_at": iso(created + timedelta(hours=merge_after)),
                "first_review_at": iso(created + timedelta(hours=review_after)) if reviewed else None,
                "first_commit_at": iso(created - timedelta(hours=commit_before))}
    prs = [reviewed_pr(1, 2, 10, 20), reviewed_pr(2, 4, 20, 30), reviewed_pr(3, 0, 0, 1, reviewed=False)]
    m = calculate_metrics(activity(prs, [commit("dev"), commit("ana")], {1: [review("ana")], 2: [review("ana")]}))
    assert m["prs"]["median_first_review_hours"] == 3.0    # reviews after 2h and 4h
    assert m["prs"]["median_cycle_hours"] == 30.0          # 30h, 50h and 1h from first commit to merge
    assert m["prs"]["merged_unreviewed"] == 1


def test_slow_first_review_lowers_a_teams_score():
    created = NOW - timedelta(days=6)
    prs = [{"number": i, "user": {"login": "dev"}, "state": "closed", "created_at": iso(created), "updated_at": iso(created),
            "merged_at": iso(created + timedelta(hours=60)), "first_review_at": iso(created + timedelta(hours=50)),
            "first_commit_at": iso(created)} for i in range(3)]
    m = calculate_metrics(activity(prs, [commit("dev"), commit("ana")], {i: [review("ana")] for i in range(3)}))
    score, signals = calculate_health_score(m)
    assert any("before anyone reviews them" in s for s in signals), signals


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")

"""Month-over-month comparisons. No database or network needed."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.history import month_over_month


def snap(day, score, hours, share, stale):
    return {"day": day, "health_score": score, "median_merge_hours": hours, "top_review_share": share, "stale_open_prs": stale}


def test_needs_two_snapshots():
    assert month_over_month([]) == [] and month_over_month([snap("2026-11-20", 80, 10, 40, 1)]) == []


def test_compares_with_about_a_month_ago_and_marks_what_got_worse():
    rows = [snap("2026-10-15", 85, 12.0, 45, 1), snap("2026-10-21", 80, 14.0, 50, 2), snap("2026-11-20", 60, 30.5, 72, 6)]
    changes = {c["label"]: c for c in month_over_month(rows)}
    assert changes["Health score"]["before"] == 80 and changes["Health score"]["worse"]
    assert changes["Typical wait to merge"]["text"] == "Typical wait to merge is 30.5 hours, up from 14 hours last month."
    assert changes["Busiest reviewer's share"]["worse"] and changes["PRs open over 3 days"]["worse"]


def test_improvements_are_not_marked_worse_and_short_spans_say_days():
    rows = [snap("2026-11-10", 60, 30.0, 70, 5), snap("2026-11-20", 75, 18.0, 55, 2)]
    changes = {c["label"]: c for c in month_over_month(rows)}
    assert not any(c["worse"] for c in changes.values())
    assert changes["Health score"]["text"].endswith("10 days ago.")


def test_unchanged_values_are_left_out():
    rows = [snap("2026-10-20", 90, 5.0, 30, 0), snap("2026-11-20", 90, 5.0, 30, 0)]
    assert month_over_month(rows) == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")

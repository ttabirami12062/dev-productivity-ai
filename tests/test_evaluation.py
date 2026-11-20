import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.metrics import calculate_health_score
from src.report_generator import generate_health_report, report_as_text

THRESHOLD = 0.8
SAMPLE_HISTORY = [{"title": "Incident Report - March 2024", "match": 88,
                   "text": "One senior developer reviewed all PRs alone. Fix: redistribute reviews, 24 hour review limit."}]


def metrics_for(case):
    weeks = [{"label": f"W{i + 1}", "median_hours": h, "merged": 3} for i, h in enumerate(case["weekly_hours"])]
    reviews, commits = case["reviews"], case["commits"]
    return {
        "window": {"since": "2026-10-09", "until": "2026-11-20", "days": 42},
        "people": case["people"], "solo": case["people"] <= 1,
        "prs": {"total": 20, "merged": 14, "open": case["open"], "stale_open": case["stale_open"], "closed_unmerged": 1,
                "median_merge_hours": case["median_merge_hours"], "weekly": weeks},
        "reviews": {"total": sum(reviews.values()), "reviewed_prs": 14, "per_reviewer": reviews,
                    "top_reviewer": max(reviews, key=reviews.get),
                    "top_share": round(max(reviews.values()) / sum(reviews.values()) * 100)},
        "commits": {"total": sum(commits.values()), "per_author": commits, "top_author": max(commits, key=commits.get),
                    "top_share": round(max(commits.values()) / sum(commits.values()) * 100)},
    }


def check(case):
    """Returns a list of problems with the report; an empty list means it passed."""
    metrics = metrics_for(case)
    score, signals = calculate_health_score(metrics)
    report, _ = generate_health_report("example", "team", metrics, score, signals, SAMPLE_HISTORY)
    problems = []

    if not report["headline"]:
        problems.append("no headline")
    kinds = {f["kind"] for f in report["findings"]}
    for kind in case["expect_kinds"]:
        if kind not in kinds:
            problems.append(f"missing a {kind} finding")
    if case["expect_kinds"] == ["positive"] and "risk" in kinds:
        problems.append("flagged risks for a healthy team")
    for f in report["findings"]:
        if any(s not in (0, 1) for s in f["sources"]):
            problems.append(f"cited a source that doesn't exist: {f['sources']}")
    text = report_as_text(report).lower()
    for kw in case["expected_keywords"]:
        if kw not in text:
            problems.append(f"never mentions '{kw}'")
    return score, problems


def run_evaluation():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_dataset.json")) as f:
        cases = json.load(f)["test_cases"]

    passed = 0
    for case in cases:
        score, problems = check(case)
        passed += not problems
        print(f"Test {case['id']}: {case['scenario']} (score {score}): {'PASS' if not problems else 'FAIL: ' + '; '.join(problems)}")

    rate = passed / len(cases)
    print(f"\n{passed}/{len(cases)} passed ({rate:.0%}), gate is {THRESHOLD:.0%}")
    sys.exit(0 if rate >= THRESHOLD else 1)


if __name__ == "__main__":
    run_evaluation()

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.citation_check import judge_citations, numbers_grounded
from src.metrics import calculate_health_score
from src.report_generator import generate_health_report, report_as_text, team_data_text

THRESHOLD = 0.8
# Share of cited findings the judge must agree are supported by their sources.
FAITHFULNESS_THRESHOLD = 0.9
SAMPLE_HISTORY = [{"title": "Incident Report - March 2024", "match": 88,
                   "text": "One senior developer reviewed all PRs alone. Fix: redistribute reviews, 24 hour review limit."}]


def metrics_for(case):
    weeks = [{"label": f"W{i + 1}", "median_hours": h, "merged": 0 if h is None else 3} for i, h in enumerate(case["weekly_hours"])]
    reviews, commits = case["reviews"], case["commits"]
    review_total = sum(reviews.values())
    merged = sum(w["merged"] for w in weeks)
    return {
        "window": {"since": "2026-10-09", "until": "2026-11-20", "days": 42, "timezone": "UTC"},
        "people": case["people"], "solo": case["people"] <= 1, "quiet": case.get("quiet", False), "uses_prs": case.get("uses_prs", True),
        "prs": {"total": case.get("total_prs", 20 if merged else case["open"]), "merged": merged, "open": case["open"],
                "stale_open": case["stale_open"], "closed_unmerged": 0,
                "median_merge_hours": case["median_merge_hours"], "weekly": weeks},
        "reviews": {"total": review_total, "reviewed_prs": merged, "per_reviewer": reviews,
                    "top_reviewer": max(reviews, key=reviews.get) if reviews else None,
                    "top_share": round(max(reviews.values()) / review_total * 100) if review_total else 0},
        "commits": {"total": sum(commits.values()), "per_author": commits, "top_author": max(commits, key=commits.get),
                    "top_share": round(max(commits.values()) / sum(commits.values()) * 100)},
    }


def check(case):
    """Returns (score, problems, judgements); no problems means the report passed."""
    metrics = metrics_for(case)
    score, signals = calculate_health_score(metrics)
    report, _ = generate_health_report("example", "team", metrics, score, signals, SAMPLE_HISTORY)
    problems = []

    data = team_data_text("example", "team", metrics, score, signals)
    grounded, unsupported = numbers_grounded(report, data, *(f"{h['title']}\n{h['text']}" for h in SAMPLE_HISTORY), *signals)
    if not grounded:
        problems.append(f"used numbers that aren't in its data: {unsupported}")
    judgements = judge_citations(report, data, SAMPLE_HISTORY)

    if not report["headline"]:
        problems.append("no headline")
    kinds = {f["kind"] for f in report["findings"]}
    for kind in case["expect_kinds"]:
        if kind not in kinds:
            problems.append(f"missing a {kind} finding")
    for kind in case.get("forbid_kinds", ["risk"] if case["expect_kinds"] == ["positive"] else []):
        if kind in kinds:
            problems.append(f"gave a {kind} finding it shouldn't")
    for f in report["findings"]:
        if any(s not in (0, 1) for s in f["sources"]):
            problems.append(f"cited a source that doesn't exist: {f['sources']}")
    text = report_as_text(report).lower()
    for kw in case["expected_keywords"]:
        if kw not in text:
            problems.append(f"never mentions '{kw}'")
    if case.get("expected_any") and not any(kw in text for kw in case["expected_any"]):
        problems.append(f"never says any of {case['expected_any']}")
    for kw in case.get("forbidden_keywords", []):
        if kw in f" {text} ":
            problems.append(f"mentions '{kw.strip()}', which doesn't apply here")
    return score, problems, judgements


def run_evaluation():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_dataset.json")) as f:
        cases = json.load(f)["test_cases"]

    passed, judged, supported = 0, 0, 0
    for case in cases:
        score, problems, judgements = check(case)
        passed += not problems
        print(f"Test {case['id']}: {case['scenario']} (score {score}): {'PASS' if not problems else 'FAIL: ' + '; '.join(problems)}")
        for j in judgements:
            judged += 1
            supported += j["supported"]
            print(f"    citation {'supported' if j['supported'] else 'NOT SUPPORTED'}: {j['title']} ({j['reason']})")

    rate = passed / len(cases)
    faithfulness = supported / judged if judged else 1.0
    print(f"\n{passed}/{len(cases)} reports passed ({rate:.0%}), gate is {THRESHOLD:.0%}")
    print(f"{supported}/{judged} cited findings supported by their sources ({faithfulness:.0%}), gate is {FAITHFULNESS_THRESHOLD:.0%}")
    sys.exit(0 if rate >= THRESHOLD and faithfulness >= FAITHFULNESS_THRESHOLD else 1)


if __name__ == "__main__":
    run_evaluation()

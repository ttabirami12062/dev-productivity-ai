import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.report_generator import generate_health_report
from src.metrics import calculate_health_score

def load_golden_dataset():
    dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'golden_dataset.json')
    with open(dataset_path, 'r') as f:
        return json.load(f)

def evaluate_report_quality(report, expected_keywords):
    report_lower = report.lower()
    matched = [kw for kw in expected_keywords if kw.lower() in report_lower]
    score = len(matched) / len(expected_keywords)
    return score, matched

def run_evaluation():
    print("Running evaluation on golden dataset...")
    print("=" * 50)

    dataset = load_golden_dataset()
    test_cases = dataset["test_cases"]

    total_score = 0
    passed = 0
    failed = 0
    threshold = 0.5

    for test in test_cases:
        print(f"\nTest {test['id']}: {test['scenario']}")

        report = generate_health_report(
            test["pr_metrics"],
            test["commit_metrics"],
            test["health_score"],
            rag_context=""
        )

        score, matched = evaluate_report_quality(report, test["expected_keywords"])
        total_score += score

        status = "PASS" if score >= threshold else "FAIL"
        if score >= threshold:
            passed += 1
        else:
            failed += 1

        print(f"  Score: {score:.0%}")
        print(f"  Matched keywords: {matched}")
        print(f"  Status: {status}")

    avg_score = total_score / len(test_cases)
    print("\n" + "=" * 50)
    print(f"EVALUATION RESULTS")
    print(f"  Total tests: {len(test_cases)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Average quality score: {avg_score:.0%}")
    print("=" * 50)

    if avg_score < threshold:
        print("QUALITY GATE FAILED - average score below 50%")
        sys.exit(1)
    else:
        print("QUALITY GATE PASSED")
        sys.exit(0)

if __name__ == "__main__":
    run_evaluation()



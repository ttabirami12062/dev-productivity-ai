"""The number check must catch made-up numbers. No API keys or network needed."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.citation_check import numbers_grounded

DATA = "Median time from open to merge: 127.4 hours (about 5.3 days). Reviews: 31; top reviewer RobinMalfait did 81%. 36 open over 3 days."


def report(detail):
    return {"headline": "Reviews are concentrated", "summary": "", "findings": [{"title": "Risk", "detail": detail, "sources": [0]}]}


def test_numbers_from_the_data_pass():
    ok, missing = numbers_grounded(report("RobinMalfait did 81% of 31 reviews and PRs wait 5.3 days; 36 are stuck."), DATA)
    assert ok, missing


def test_invented_number_is_caught():
    ok, missing = numbers_grounded(report("RobinMalfait did 57% of reviews."), DATA)
    assert not ok and missing == ["57"]


def test_miscalculated_number_is_caught():
    ok, missing = numbers_grounded(report("PRs now wait 6.1 days on average."), DATA)
    assert not ok and missing == ["6.1"]


def test_rule_numbers_are_allowed():
    ok, missing = numbers_grounded(report("Keep reviews under 24 hours and no reviewer above 50%."), DATA)
    assert ok, missing


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")

"""Email building and address checks. Nothing is sent; no keys or network needed."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mailer import confirmation_email, report_email
from src.subscriptions import EMAIL

BUILT = {"score": 48, "status": "at_risk", "signals": ["PRs take 2.2 days to merge."],
         "report": {"headline": "Reviews <script>alert(1)</script> are slow", "summary": "Merges take 2.2 days.",
                    "findings": [{"kind": "risk", "title": "Slow reviews", "detail": "One reviewer & everyone waits.", "sources": [0]}]}}


def test_email_addresses():
    for good in ["abi@example.com", "a.b+weekly@gmail.com"]:
        assert EMAIL.match(good), good
    for bad in ["", "abi", "a@b", "a b@example.com", "@example.com"]:
        assert not EMAIL.match(bad), bad


def test_report_email_escapes_text_and_has_unsubscribe():
    subject, html, text = report_email("acme/api", "T" * 22, BUILT, "tok_123")
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "One reviewer &amp; everyone waits." in html
    assert "?unsubscribe=tok_123" in html and "?unsubscribe=tok_123" in text
    assert "repo=acme/api" in html and subject.startswith("acme/api:")


def test_confirmation_email_has_the_link():
    subject, html, text = confirmation_email("acme/api", "tok_abc")
    assert "?confirm=tok_abc" in html and "?confirm=tok_abc" in text and "acme/api" in subject


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")

"""Daily snapshots of tracked repositories, stored in Supabase Postgres.

Only the backend talks to Supabase, using the secret key over the REST API. When
the keys are missing (CI, a fresh checkout) history is simply switched off.
"""
import os
import re
from datetime import date, datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from src.metrics import calculate_health_score, calculate_metrics, health_status

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# The Data API page shows the URL with "/rest/v1/" on the end; accept it either way.
URL = re.sub(r"/(rest/v1)?/?$", "", (os.getenv("SUPABASE_URL") or "").strip())
KEY = (os.getenv("SUPABASE_SERVICE_KEY") or "").strip()
ENABLED = bool(URL and KEY)
MAX_TRACKED = int(os.getenv("MAX_TRACKED_REPOS", "50"))


class HistoryError(Exception):
    """A problem worth showing the visitor as-is."""


def _headers(extra=None):
    headers = {"apikey": KEY, "Content-Type": "application/json"}
    # Legacy service_role keys are JWTs and also go in Authorization; new sb_secret_ keys don't.
    if KEY.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {KEY}"
    return {**headers, **(extra or {})}


def _request(method, table, **kwargs):
    response = requests.request(method, f"{URL}/rest/v1/{table}", headers=_headers(kwargs.pop("headers", None)), timeout=20, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else None


def repo_key(owner, repo):
    return f"{owner}/{repo}".lower()


def is_tracked(owner, repo):
    if not ENABLED:
        return False
    return bool(_request("GET", "tracked_repos", params={"repo": f"eq.{repo_key(owner, repo)}", "select": "repo"}))


def tracked_repos():
    return _request("GET", "tracked_repos", params={"select": "repo,display_name,last_snapshot_at", "order": "added_at"})


def track(owner, repo):
    if not ENABLED:
        raise HistoryError("History isn't switched on for this site yet.")
    if is_tracked(owner, repo):
        return False
    count = len(_request("GET", "tracked_repos", params={"select": "repo"}))
    if count >= MAX_TRACKED:
        raise HistoryError(f"This demo can track up to {MAX_TRACKED} projects, and that's full right now.")
    _request("POST", "tracked_repos", json={"repo": repo_key(owner, repo), "display_name": f"{owner}/{repo}"},
             headers={"Prefer": "resolution=ignore-duplicates"})
    return True


def save_snapshot(owner, repo, metrics, score, status, signals, day=None):
    """Writes today's numbers for a tracked repo (one row per repo per UTC day; reruns overwrite)."""
    weeks = [w["median_hours"] for w in metrics["prs"]["weekly"] if w["median_hours"] is not None]
    row = {
        "repo": repo_key(owner, repo),
        "day": (day or datetime.now(timezone.utc).date()).isoformat(),
        "health_score": score,
        "status": status,
        "median_merge_hours": metrics["prs"]["median_merge_hours"],
        "latest_week_hours": weeks[-1] if weeks else None,
        "top_review_share": metrics["reviews"]["top_share"] if metrics["reviews"]["total"] else None,
        "top_reviewer": metrics["reviews"]["top_reviewer"],
        "open_prs": metrics["prs"]["open"],
        "stale_open_prs": metrics["prs"]["stale_open"],
        "merged_prs": metrics["prs"]["merged"],
        "commits": metrics["commits"]["total"],
        "people": metrics["people"],
        "signals": signals,
    }
    _request("POST", "daily_snapshots", json=row, headers={"Prefer": "resolution=merge-duplicates"})
    _request("PATCH", "tracked_repos", params={"repo": f"eq.{row['repo']}"},
             json={"last_snapshot_at": datetime.now(timezone.utc).isoformat(), "last_error": None})
    return row


def snapshot_from_activity(activity):
    metrics = calculate_metrics(activity)
    score, signals = calculate_health_score(metrics)
    status = "quiet" if metrics["quiet"] else health_status(score)
    return save_snapshot(activity["owner"], activity["repo"], metrics, score, status, signals)


def get_history(owner, repo, days=180):
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = _request("GET", "daily_snapshots", params={
        "repo": f"eq.{repo_key(owner, repo)}", "day": f"gte.{since}", "order": "day",
        "select": "day,health_score,status,median_merge_hours,latest_week_hours,top_review_share,top_reviewer,open_prs,stale_open_prs,merged_prs,commits,people"})
    return rows or []


def _closest(rows, target_day):
    earlier = [r for r in rows if r["day"] <= target_day.isoformat()]
    return earlier[-1] if earlier else None


def month_over_month(rows):
    """Plain comparisons between the latest snapshot and the one closest to 30 days before it."""
    if len(rows) < 2:
        return []
    latest = rows[-1]
    before = _closest(rows[:-1], date.fromisoformat(latest["day"]) - timedelta(days=30)) or rows[0]
    span = (date.fromisoformat(latest["day"]) - date.fromisoformat(before["day"])).days
    if span < 1:
        return []
    when = "last month" if span >= 25 else f"{span} days ago"
    out = []

    def compare(label, key, unit="", better="lower", fmt=lambda v: f"{v:g}"):
        a, b = before.get(key), latest.get(key)
        if a is None or b is None or a == b:
            return
        worse = (b > a) if better == "lower" else (b < a)
        out.append({"label": label, "before": a, "now": b, "when": when, "worse": worse,
                    "text": f"{label} is {fmt(b)}{unit}, {'up' if b > a else 'down'} from {fmt(a)}{unit} {when}."})

    compare("Health score", "health_score", better="higher")
    compare("Typical wait to merge", "median_merge_hours", " hours", fmt=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
    compare("Busiest reviewer's share", "top_review_share", "%")
    compare("PRs open over 3 days", "stale_open_prs")
    return out

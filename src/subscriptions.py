"""Weekly email subscriptions, made from a team space and confirmed by email (double opt-in)."""
import re
import secrets
from datetime import datetime, timezone

from src import history, mailer

EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")
MAX_PER_TEAM = 10


class SubscriptionError(Exception):
    """A problem worth showing the person as-is."""


def _find(**filters):
    params = {k: f"eq.{v}" for k, v in filters.items()}
    return history._request("GET", "subscriptions", params={**params, "select": "*"}) or []


def subscribe(email, owner, repo, team, timezone_name):
    """Creates (or re-sends) a pending subscription and emails the confirmation link."""
    if not (history.ENABLED and mailer.ENABLED):
        raise SubscriptionError("Weekly emails aren't switched on for this site yet.")
    email = email.strip().lower()
    if not EMAIL.match(email):
        raise SubscriptionError("That email address doesn't look right.")
    key = history.repo_key(owner, repo)

    existing = _find(email=email, repo=key, team=team)
    if existing and existing[0]["confirmed"]:
        return "already"
    if existing:
        token = existing[0]["token"]
    else:
        if len(_find(team=team)) >= MAX_PER_TEAM:
            raise SubscriptionError(f"A team space can have up to {MAX_PER_TEAM} weekly emails.")
        token = secrets.token_urlsafe(24)
        history._request("POST", "subscriptions", json={"email": email, "repo": key, "display_name": f"{owner}/{repo}",
                                                        "team": team, "timezone": timezone_name, "token": token})
    mailer.send(email, *mailer.confirmation_email(f"{owner}/{repo}", token))
    return "sent"


def _by_token(token):
    if not token or not re.fullmatch(r"[A-Za-z0-9_-]{20,64}", token):
        return None
    rows = _find(token=token)
    return rows[0] if rows else None


def confirm(token):
    row = _by_token(token)
    if not row:
        raise SubscriptionError("That confirmation link isn't valid any more. Subscribe again from your team space.")
    if not row["confirmed"]:
        history._request("PATCH", "subscriptions", params={"token": f"eq.{token}"},
                         json={"confirmed": True, "confirmed_at": datetime.now(timezone.utc).isoformat()})
    return row["display_name"]


def unsubscribe(token):
    row = _by_token(token)
    if row:
        # Deleting the row deletes the email address too.
        history._request("DELETE", "subscriptions", params={"token": f"eq.{token}"})
    return row["display_name"] if row else None


def confirmed_subscriptions():
    return history._request("GET", "subscriptions", params={"confirmed": "eq.true", "select": "*", "order": "repo"}) or []

"""Monday job: write one report per subscribed project and team, and email it to that team.

Run by .github/workflows/weekly-reports.yml. Each (project, team) pair costs one AI
report however many people subscribed, about $0.0025.
"""
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src import history, mailer
from src.github_client import GitHubError
from src.pipeline import build_report
from src.subscriptions import confirmed_subscriptions


def run():
    if not (history.ENABLED and mailer.ENABLED):
        print("Supabase or Gmail settings are missing; nothing to do.")
        return 1
    subs = confirmed_subscriptions()
    groups = {}
    for sub in subs:
        groups.setdefault((sub["display_name"], sub["team"]), []).append(sub)
    print(f"{len(subs)} confirmed subscriptions across {len(groups)} reports, {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")

    sent = failed = 0
    for (display_name, team), group in groups.items():
        owner, repo = display_name.split("/", 1)
        try:
            built = build_report(owner, repo, ZoneInfo(group[0]["timezone"] or "UTC"), team)
            if history.is_tracked(owner, repo):
                history.save_snapshot(owner, repo, built["metrics"], built["score"], built["status"], built["signals"])
        except Exception as e:  # one broken project shouldn't stop the others
            failed += len(group)
            print(f"  {display_name}: FAILED to build ({e if isinstance(e, GitHubError) else type(e).__name__})")
            continue
        for sub in group:
            try:
                mailer.send(sub["email"], *mailer.report_email(display_name, team, built, sub["token"]))
                history._request("PATCH", "subscriptions", params={"id": f"eq.{sub['id']}"},
                                 json={"last_sent_at": datetime.now(timezone.utc).isoformat()})
                sent += 1
            except Exception as e:
                failed += 1
                print(f"  {display_name}: FAILED to send one email ({type(e).__name__})")
        print(f"  {display_name}: score {built['score']}, sent to {len(group)}")
    print(f"Done: {sent} sent, {failed} failed")
    return 1 if subs and sent == 0 else 0


if __name__ == "__main__":
    sys.exit(run())

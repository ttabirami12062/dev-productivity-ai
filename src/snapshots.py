"""Nightly job: save today's numbers for every tracked repository.

Run by .github/workflows/nightly-snapshots.yml. Uses GitHub data and the scoring
math only, no OpenAI, so it costs nothing. It also keeps the free Supabase
project from pausing.
"""
import sys
import time
from datetime import datetime, timezone

from src import history
from src.github_client import GitHubError, fetch_repo_activity


def run():
    if not history.ENABLED:
        print("SUPABASE_URL / SUPABASE_SERVICE_KEY are not set; nothing to do.")
        return 1
    repos = history.tracked_repos()
    print(f"{len(repos)} tracked repositories, {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    failed = 0
    for row in repos:
        owner, repo = row["display_name"].split("/", 1)
        started = time.time()
        try:
            snap = history.snapshot_from_activity(fetch_repo_activity(owner, repo))
            print(f"  {row['display_name']:40} score {snap['health_score']:3} {snap['status']:8} ({time.time() - started:.1f}s)")
        except Exception as e:  # one broken repo shouldn't stop the others
            failed += 1
            message = str(e) if isinstance(e, GitHubError) else type(e).__name__
            history._request("PATCH", "tracked_repos", params={"repo": f"eq.{row['repo']}"}, json={"last_error": message[:300]})
            print(f"  {row['display_name']:40} FAILED: {message}")
    print(f"Done: {len(repos) - failed} saved, {failed} failed")
    # Fail the job only if everything failed, which points at a setup problem.
    return 1 if repos and failed == len(repos) else 0


if __name__ == "__main__":
    sys.exit(run())

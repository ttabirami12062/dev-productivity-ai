"""Builds one report from start to finish. Shared by the website and the weekly emails,
so both always write reports the same way."""
import logging

from src.citation_check import numbers_grounded
from src.github_client import fetch_repo_activity
from src.metrics import calculate_health_score, calculate_metrics, health_status
from src.rag_pipeline import retrieve_history
from src.report_generator import generate_health_report, team_data_text

log = logging.getLogger("pipeline")


def build_report(owner, repo, tz, team=""):
    """Raises GitHubError for problems the visitor should see; anything else is a server problem."""
    activity = fetch_repo_activity(owner, repo, tz)
    metrics = calculate_metrics(activity)
    score, signals = calculate_health_score(metrics)

    try:
        # A team's own documents come first; teams that haven't added any yet get the samples.
        history = retrieve_history(signals, namespace=team) if team else []
        if not history:
            history = retrieve_history(signals)
    except Exception:
        # A report without history is still useful, so don't fail the whole analysis.
        log.exception("History search failed")
        history = []

    report, usage = generate_health_report(activity["owner"], activity["repo"], metrics, score, signals, history)
    status = "quiet" if metrics["quiet"] else health_status(score)

    # Free check on every report: each number the model wrote must come from its inputs.
    grounded, unsupported = numbers_grounded(
        report, team_data_text(activity["owner"], activity["repo"], metrics, score, signals),
        *(f"{h['title']}\n{h['text']}" for h in history), *signals)
    if not grounded:
        log.warning("Report for %s/%s used numbers not in its data: %s", owner, repo, unsupported)

    return {"activity": activity, "metrics": metrics, "score": score, "signals": signals, "status": status,
            "history": history, "report": report, "usage": usage, "grounded": grounded, "unsupported": unsupported}

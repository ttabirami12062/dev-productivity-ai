import os
import sys
import time

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.github_client import fetch_repo_activity
from src.metrics import calculate_metrics, calculate_health_score
from src.rag_pipeline import retrieve_history
from src.report_generator import generate_health_report, report_as_text
from src.observability import flush


def run_analysis(owner, repo):
    """Same steps as the /analyze endpoint, printed to the terminal for quick checks."""
    print(f"\nAnalyzing {owner}/{repo}")
    activity = fetch_repo_activity(owner, repo)
    metrics = calculate_metrics(activity)
    score, signals = calculate_health_score(metrics)
    print(f"{metrics['prs']['total']} PRs, {metrics['commits']['total']} commits, {metrics['reviews']['total']} reviews")
    print(f"Health score: {score}/100")
    for s in signals:
        print(f"  - {s}")

    history = retrieve_history(signals)
    for i, h in enumerate(history, start=1):
        print(f"  [{i}] {h['title']} ({h['match']}% match)")

    started = time.time()
    report, usage = generate_health_report(activity["owner"], activity["repo"], metrics, score, signals, history)
    print("\n" + report_as_text(report))
    print(f"\n{round(time.time() - started, 1)}s, {usage['input_tokens']} in / {usage['output_tokens']} out tokens, model {usage['model']}")


if __name__ == "__main__":
    owner, repo = (sys.argv[1].split("/", 1) if len(sys.argv) > 1 else ("ttabirami12062", "IPMS"))
    run_analysis(owner, repo)
    flush()  # send any pending Langfuse traces before the script exits

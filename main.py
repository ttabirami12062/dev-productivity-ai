import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.github_client import get_pull_requests, get_commits, get_contributors
from src.metrics import calculate_pr_metrics, calculate_commit_metrics, calculate_health_score
from src.report_generator import generate_health_report
from src.rag_pipeline import build_rag_context
from src.observability import track_report_generation

def run_analysis(owner, repo):
    print(f"\nAnalyzing repository: {owner}/{repo}")
    print("=" * 50)

    print("\nFetching GitHub data...")
    pull_requests = get_pull_requests(owner, repo)
    commits = get_commits(owner, repo)
    contributors = get_contributors(owner, repo)

    print("\nCalculating metrics...")
    pr_metrics = calculate_pr_metrics(pull_requests)
    commit_metrics = calculate_commit_metrics(commits)
    health_score = calculate_health_score(pr_metrics, commit_metrics)

    print("\nPR METRICS:")
    print(f"  Total PRs: {pr_metrics.get('total_prs')}")
    print(f"  Merged PRs: {pr_metrics.get('merged_prs')}")
    print(f"  Open PRs: {pr_metrics.get('open_prs')}")
    print(f"  Avg Review Time: {pr_metrics.get('avg_review_time_hours')} hours")

    print("\nCOMMIT METRICS:")
    print(f"  Total Commits: {commit_metrics.get('total_commits')}")
    print(f"  Most Active Author: {commit_metrics.get('most_active_author')}")
    print(f"  Commits Per Author: {commit_metrics.get('commits_per_author')}")

    print(f"\nTEAM HEALTH SCORE: {health_score}/100")

    print("\nFetching historical context from RAG...")
    rag_context = build_rag_context(pr_metrics, commit_metrics, health_score)
    print("Historical context retrieved!")

    print("\nGenerating AI health report...")
    start_time = time.time()
    report = generate_health_report(pr_metrics, commit_metrics, health_score, rag_context)
    latency_ms = round((time.time() - start_time) * 1000)

    cost_estimate = round((len(report.split()) * 2) * 0.000002, 6)

    print("\nTracking to Langfuse...")
    track_report_generation(pr_metrics, commit_metrics, health_score, report, latency_ms, cost_estimate)

    print("\n" + "=" * 50)
    print("WEEKLY TEAM HEALTH REPORT")
    print("=" * 50)
    print(report)
    print("=" * 50)
    print(f"\nLatency: {latency_ms}ms | Cost: ${cost_estimate}")

if __name__ == "__main__":
    owner = "ttabirami12062"
    repo = "IPMS"
    run_analysis(owner, repo)

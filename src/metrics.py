from datetime import datetime, timezone

def calculate_pr_metrics(pull_requests):
    if not pull_requests or not isinstance(pull_requests, list):
        return {}

    total_prs = len(pull_requests)
    merged_prs = [pr for pr in pull_requests if pr.get("merged_at")]
    open_prs = [pr for pr in pull_requests if pr.get("state") == "open"]

    review_times = []
    for pr in merged_prs:
        created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        merged = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
        hours = (merged - created).total_seconds() / 3600
        review_times.append(hours)

    avg_review_time = round(sum(review_times) / len(review_times), 2) if review_times else 0

    return {
        "total_prs": total_prs,
        "merged_prs": len(merged_prs),
        "open_prs": len(open_prs),
        "avg_review_time_hours": avg_review_time
    }

def calculate_commit_metrics(commits):
    if not commits or not isinstance(commits, list):
        return {}

    author_counts = {}
    for commit in commits:
        author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
        author_counts[author] = author_counts.get(author, 0) + 1

    most_active = max(author_counts, key=author_counts.get) if author_counts else "Unknown"

    return {
        "total_commits": len(commits),
        "commits_per_author": author_counts,
        "most_active_author": most_active
    }

def calculate_health_score(pr_metrics, commit_metrics):
    score = 100

    if pr_metrics.get("avg_review_time_hours", 0) > 48:
        score -= 30
    elif pr_metrics.get("avg_review_time_hours", 0) > 24:
        score -= 15

    if pr_metrics.get("open_prs", 0) > 5:
        score -= 20
    elif pr_metrics.get("open_prs", 0) > 3:
        score -= 10

    commits_per_author = commit_metrics.get("commits_per_author", {})
    if commits_per_author:
        total = sum(commits_per_author.values())
        max_commits = max(commits_per_author.values())
        if total > 0 and (max_commits / total) > 0.8:
            score -= 25

    return max(score, 0)

if __name__ == "__main__":
    sample_prs = [
        {"state": "closed", "merged_at": "2026-03-10T10:00:00Z", "created_at": "2026-03-08T10:00:00Z"},
        {"state": "open", "merged_at": None, "created_at": "2026-03-12T10:00:00Z"},
    ]
    sample_commits = [
        {"commit": {"author": {"name": "Abi"}}},
        {"commit": {"author": {"name": "Abi"}}},
        {"commit": {"author": {"name": "John"}}},
    ]

    pr_metrics = calculate_pr_metrics(sample_prs)
    commit_metrics = calculate_commit_metrics(sample_commits)
    health_score = calculate_health_score(pr_metrics, commit_metrics)

    print("PR Metrics:", pr_metrics)
    print("Commit Metrics:", commit_metrics)
    print("Team Health Score:", health_score)
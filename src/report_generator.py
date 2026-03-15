import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_health_report(pr_metrics, commit_metrics, health_score):
    prompt = f"""
You are an AI assistant that analyzes software engineering team health data and generates actionable reports for engineering managers.

Here is the current team data:

PR METRICS:
- Total PRs: {pr_metrics.get('total_prs')}
- Merged PRs: {pr_metrics.get('merged_prs')}
- Open PRs: {pr_metrics.get('open_prs')}
- Average Review Time: {pr_metrics.get('avg_review_time_hours')} hours

COMMIT METRICS:
- Total Commits: {commit_metrics.get('total_commits')}
- Commits Per Author: {commit_metrics.get('commits_per_author')}
- Most Active Author: {commit_metrics.get('most_active_author')}

TEAM HEALTH SCORE: {health_score}/100

Generate a clear and concise weekly team health report with:
1. Overall health summary in 2 sentences
2. Top 2 risks or warning signs
3. Top 2 specific actionable recommendations
4. One positive observation about the team

Keep the tone professional but direct. No generic advice.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert engineering team health analyst."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    sample_pr_metrics = {
        "total_prs": 2,
        "merged_prs": 1,
        "open_prs": 1,
        "avg_review_time_hours": 48.0
    }
    sample_commit_metrics = {
        "total_commits": 3,
        "commits_per_author": {"Abi": 2, "John": 1},
        "most_active_author": "Abi"
    }
    health_score = 85

    print("Generating AI health report...")
    report = generate_health_report(sample_pr_metrics, sample_commit_metrics, health_score)
    print("\n--- TEAM HEALTH REPORT ---")
    print(report)


import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_health_report(pr_metrics, commit_metrics, health_score, rag_context=""):
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

HISTORICAL CONTEXT FROM PAST INCIDENTS:
{rag_context if rag_context else "No historical context available."}

Generate a clear and concise weekly team health report with:
1. Overall health summary in 2 sentences
2. Top 2 risks or warning signs
3. Top 2 specific actionable recommendations based on historical context
4. One positive observation about the team

If historical context is available, reference it specifically in your recommendations.
Keep the tone professional but direct. No generic advice.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert engineering team health analyst."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=600,
        temperature=0.7
    )

    return response.choices[0].message.content


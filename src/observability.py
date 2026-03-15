import os
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_HOST"] = os.getenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")

def track_report_generation(pr_metrics, commit_metrics, health_score, report, latency_ms, cost_estimate):
    print(f"Tracked to Langfuse - Latency: {latency_ms}ms, Cost: ${cost_estimate}")
    print(f"Health Score: {health_score}/100")
    print(f"Most Active Author: {commit_metrics.get('most_active_author')}")

if __name__ == "__main__":
    print("Langfuse v4 configured successfully!")
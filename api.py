import os
import re
import sys
import json
import time
import logging
import smtplib
import threading
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.github_client import GitHubError, fetch_repo_activity
from src.metrics import calculate_metrics, calculate_health_score, health_status
from src.report_generator import generate_health_report
from src.rag_pipeline import retrieve_history

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")

app = FastAPI()

# The dashboard sends no cookies, so credentials stay off. ALLOWED_ORIGINS can lock
# this to the Vercel site, e.g. "https://dev-productivity-ai.vercel.app".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Every analysis costs an OpenAI call, so repeat requests for the same repo reuse the
# last result for an hour, and each visitor gets a handful of fresh analyses per hour.
CACHE_SECONDS = 3600
HOURLY_LIMIT = int(os.getenv("HOURLY_LIMIT", "8"))
_cache, _requests_by_ip, _lock = {}, {}, threading.Lock()
NAME = re.compile(r"^[A-Za-z0-9._-]{1,100}$")

REVIEWS_FILE = "reviews.json"
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def load_reviews():
    if os.path.exists(REVIEWS_FILE):
        with open(REVIEWS_FILE, "r") as f:
            return json.load(f)
    return []

def save_review(review):
    reviews = load_reviews()
    reviews.append(review)
    with open(REVIEWS_FILE, "w") as f:
        json.dump(reviews, f, indent=2)

def send_email(review):
    try:
        msg = MIMEMultipart("alternative")
        # Everything below comes from a public form, so escape it before it goes into HTML.
        r = {k: escape(str(v)) if isinstance(v, str) else v for k, v in review.items()}
        msg["Subject"] = f"New Feedback - {review['repo']} - {review['rating']}/5 stars"
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = GMAIL_ADDRESS

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 32px;">
                <h2 style="color: #1A56DB;">New Feedback Received</h2>
                <hr/>
                <p><strong>Repository:</strong> {r['owner']}/{r['repo']}</p>
                <p><strong>Rating:</strong> {'★' * review['rating']}{'☆' * (5 - review['rating'])} ({review['rating']}/5)</p>
                <p><strong>Comment:</strong> {r.get('comment') or 'No comment left'}</p>
                <p><strong>Name:</strong> {r.get('name') or 'Not provided'}</p>
                <p><strong>Email:</strong> {r.get('user_email') or 'Not provided'}</p>
                <p><strong>Role:</strong> {r.get('role') or 'Not specified'}</p>
                <p><strong>Time:</strong> {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(review['timestamp']))}</p>
                <hr/>
                <p style="color: #888; font-size: 12px;">Dev Productivity Intelligence - Feedback System</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, msg.as_string())

        print("Email sent successfully!")
    except Exception as e:
        print(f"Email failed: {e}")

class AnalyzeRequest(BaseModel):
    owner: str = Field(max_length=100)
    repo: str = Field(max_length=100)
    # The visitor's time zone from their browser, e.g. "America/Chicago", so weeks
    # and dates match what they see on GitHub.
    timezone: str = Field("UTC", max_length=64)


def _zone(name):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")

class ReviewRequest(BaseModel):
    owner: str = Field(max_length=100)
    repo: str = Field(max_length=100)
    rating: int = Field(ge=1, le=5)
    comment: str = Field("", max_length=2000)
    name: str = Field("", max_length=100)
    user_email: str = Field("", max_length=200)
    role: str = Field("", max_length=100)


def _client_ip(request):
    # Render sits behind a proxy, so the visitor's address is the first forwarded one.
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def _over_limit(ip):
    now = time.time()
    with _lock:
        recent = [t for t in _requests_by_ip.get(ip, []) if now - t < 3600]
        if len(recent) >= HOURLY_LIMIT:
            _requests_by_ip[ip] = recent
            return True
        _requests_by_ip[ip] = recent + [now]
        return False


def _fail(message):
    return {"success": False, "error": message}

# Plain "def" so FastAPI runs it in a worker thread: the GitHub and OpenAI calls
# are blocking, and inside "async def" they would make every other visitor wait.
@app.post("/analyze")
def analyze(body: AnalyzeRequest, request: Request):
    owner, repo = body.owner.strip(), body.repo.strip()
    if not (NAME.match(owner) and NAME.match(repo)):
        return _fail("That doesn't look like a GitHub repository. Use the form owner/name, for example vercel/swr.")

    tz = _zone(body.timezone)
    key = f"{owner}/{repo}@{tz}".lower()
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return {**cached[1], "cached": True}

    if _over_limit(_client_ip(request)):
        return _fail("You've run a lot of analyses in the last hour. Please try again a little later.")

    started = time.time()
    try:
        activity = fetch_repo_activity(owner, repo, tz)
        metrics = calculate_metrics(activity)
        score, signals = calculate_health_score(metrics)

        try:
            history = retrieve_history(signals)
        except Exception:
            # A report without history is still useful, so don't fail the whole analysis.
            log.exception("History search failed")
            history = []

        report, usage = generate_health_report(activity["owner"], activity["repo"], metrics, score, signals, history)
    except GitHubError as e:
        return _fail(str(e))
    except Exception:
        log.exception("Analysis failed for %s", key)
        return _fail("Something went wrong on our side while writing the report. Please try again in a minute.")

    result = {
        "success": True,
        "owner": activity["owner"],
        "repo": activity["repo"],
        "health_score": score,
        # A near-empty repo would otherwise read as a perfect score.
        "status": "quiet" if metrics["quiet"] else health_status(score),
        "signals": signals,
        "metrics": metrics,
        "report": report,
        "sources": [{"id": i, "title": h["title"], "match": h["match"]} for i, h in enumerate(history, start=1)],
        "generated_seconds": round(time.time() - started, 1),
        "usage": usage,
    }
    _cache[key] = (time.time(), result)
    return result

@app.post("/review")
def submit_review(request: ReviewRequest):
    review = {
        "owner": request.owner,
        "repo": request.repo,
        "rating": request.rating,
        "comment": request.comment,
        "name": request.name,
        "user_email": request.user_email,
        "role": request.role,
        "timestamp": time.time()
    }
    save_review(review)
    send_email(review)
    return {"success": True, "message": "Review submitted!"}

@app.get("/health")
async def health():
    return {"status": "running"}
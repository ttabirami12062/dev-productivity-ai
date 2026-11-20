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
from src.observability import report_trace
from src.citation_check import numbers_grounded
from src.report_generator import team_data_text

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
# A spending cap that doesn't depend on OpenAI's dashboard: at most this many new
# reports per day across all visitors (measured in Langfuse at about $0.0025 each,
# so 300 is about $0.75 and 80 is about $0.20).
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "300"))
_cache, _requests_by_ip, _lock = {}, {}, threading.Lock()
_daily = {"day": "", "count": 0}
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


def _daily_cap_reached():
    today = time.strftime("%Y-%m-%d", time.gmtime())
    with _lock:
        if _daily["day"] != today:
            _daily.update(day=today, count=0)
        if _daily["count"] >= DAILY_LIMIT:
            return True
        _daily["count"] += 1
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
    if _daily_cap_reached():
        log.warning("Daily limit of %s reports reached", DAILY_LIMIT)
        return _fail("The site has written its maximum number of reports for today. Please come back tomorrow.")

    started = time.time()
    with report_trace(owner, repo, str(tz)) as record:
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
            record(error=str(e))
            return _fail(str(e))
        except Exception as e:
            log.exception("Analysis failed for %s", key)
            record(error=type(e).__name__)
            if "insufficient_quota" in str(e):
                return _fail("This demo has used up its AI budget for now. Please check back later.")
            return _fail("Something went wrong on our side while writing the report. Please try again in a minute.")

        status = "quiet" if metrics["quiet"] else health_status(score)
        # Free check on every report: each number the model wrote must come from its inputs.
        grounded, unsupported = numbers_grounded(
            report, team_data_text(activity["owner"], activity["repo"], metrics, score, signals),
            *(f"{h['title']}\n{h['text']}" for h in history), *signals)
        if not grounded:
            log.warning("Report for %s used numbers not in its data: %s", key, unsupported)
        record(score=score, status=status, headline=report["headline"], signals=signals,
               sources=[h["title"] for h in history], seconds=round(time.time() - started, 1),
               numbers_grounded=grounded, unsupported_numbers=unsupported)

    result = {
        "success": True,
        "owner": activity["owner"],
        "repo": activity["repo"],
        "health_score": score,
        # A near-empty repo would otherwise read as a perfect score.
        "status": status,
        "signals": signals,
        "metrics": metrics,
        "report": report,
        "sources": [{"id": i, "title": h["title"], "match": h["match"]} for i, h in enumerate(history, start=1)],
        "generated_seconds": round(time.time() - started, 1),
        "usage": usage,
        "checks": {"numbers_grounded": grounded, "unsupported_numbers": unsupported},
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
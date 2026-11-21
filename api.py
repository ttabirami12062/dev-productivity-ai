import os
import re
import sys
import time
import logging
import smtplib
import threading
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.github_client import GitHubError, fetch_repo_activity
from src.observability import record_feedback, report_trace
from src.pipeline import build_report
from src import history as history_store
from src import subscriptions
from src.team_docs import TeamDocError, add_document, delete_document, is_team_id, list_documents, new_team_id, text_from_file

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")

app = FastAPI()

# The dashboard sends no cookies, so credentials stay off. ALLOWED_ORIGINS can lock
# this to the Vercel site, e.g. "https://dev-productivity-ai.vercel.app".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Every analysis costs an OpenAI call, so repeat requests for the same repo reuse the
# last result for an hour, and each visitor gets a handful of fresh analyses per hour.
CACHE_SECONDS = 3600
HOURLY_LIMIT = int(os.getenv("HOURLY_LIMIT", "8"))
# Adding a document costs an embedding call, so uploads get their own hourly limit.
UPLOAD_HOURLY_LIMIT = int(os.getenv("UPLOAD_HOURLY_LIMIT", "20"))
_uploads_by_ip = {}
# A spending cap that doesn't depend on OpenAI's dashboard: at most this many new
# reports per day across all visitors (measured in Langfuse at about $0.0025 each,
# so 300 is about $0.75 and 80 is about $0.20).
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "300"))
_cache, _requests_by_ip, _lock = {}, {}, threading.Lock()
_daily = {"day": "", "count": 0}
NAME = re.compile(r"^[A-Za-z0-9._-]{1,100}$")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

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
    # A team space id from the team's private link; its documents replace the samples.
    team: str = Field("", max_length=40)


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
    # Links the rating to the report's Langfuse trace.
    trace_id: str = Field("", max_length=64)


def _client_ip(request):
    # Render sits behind a proxy, so the visitor's address is the first forwarded one.
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def _over_limit(ip, log_by_ip=None, limit=None):
    log_by_ip = _requests_by_ip if log_by_ip is None else log_by_ip
    limit = HOURLY_LIMIT if limit is None else limit
    now = time.time()
    with _lock:
        recent = [t for t in log_by_ip.get(ip, []) if now - t < 3600]
        if len(recent) >= limit:
            log_by_ip[ip] = recent
            return True
        log_by_ip[ip] = recent + [now]
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
    team = body.team if is_team_id(body.team) else ""
    key = f"{owner}/{repo}@{tz}#{team}".lower()
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
            built = build_report(owner, repo, tz, team)
        except GitHubError as e:
            record(error=str(e))
            return _fail(str(e))
        except Exception as e:
            log.exception("Analysis failed for %s", key)
            record(error=type(e).__name__)
            if "insufficient_quota" in str(e):
                return _fail("This demo has used up its AI budget for now. Please check back later.")
            return _fail("Something went wrong on our side while writing the report. Please try again in a minute.")

        activity, metrics, score, signals = built["activity"], built["metrics"], built["score"], built["signals"]
        status, history, report, usage = built["status"], built["history"], built["report"], built["usage"]
        grounded, unsupported = built["grounded"], built["unsupported"]
        # Tracked repos get today's numbers saved whenever someone analyzes them, too.
        tracked = False
        try:
            tracked = history_store.is_tracked(activity["owner"], activity["repo"])
            if tracked:
                history_store.save_snapshot(activity["owner"], activity["repo"], metrics, score, status, signals)
        except Exception:
            log.exception("Saving history failed")
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
        "sources": [{"id": i, "title": h["title"], "match": h["match"], "kind": h.get("kind", "sample")}
                    for i, h in enumerate(history, start=1)],
        "generated_seconds": round(time.time() - started, 1),
        "usage": usage,
        "checks": {"numbers_grounded": grounded, "unsupported_numbers": unsupported},
        "trace_id": record.trace_id,
        "tracked": tracked,
        "history_enabled": history_store.ENABLED,
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
    # Render's disk is wiped on every deploy, so nothing is written there. The rating and
    # comment go to Langfuse on the report's trace; the full details go to the owner by email.
    try:
        record_feedback(request.trace_id, request.rating, request.comment, request.role)
    except Exception:
        log.exception("Could not record feedback in Langfuse")
    send_email(review)
    return {"success": True, "message": "Review submitted!"}

class TrackRequest(BaseModel):
    owner: str = Field(max_length=100)
    repo: str = Field(max_length=100)


@app.post("/track")
def track_repo(body: TrackRequest, request: Request):
    """Starts saving a repo's numbers every night. Takes the first snapshot straight away."""
    owner, repo = body.owner.strip(), body.repo.strip()
    if not (NAME.match(owner) and NAME.match(repo)):
        return _fail("That doesn't look like a GitHub repository.")
    if _over_limit(_client_ip(request), _uploads_by_ip, UPLOAD_HOURLY_LIMIT):
        return _fail("Too many changes in the last hour. Please try again a little later.")
    try:
        activity = fetch_repo_activity(owner, repo)  # also confirms the repo exists and is public
        history_store.track(activity["owner"], activity["repo"])
        history_store.snapshot_from_activity(activity)
    except (GitHubError, history_store.HistoryError) as e:
        return _fail(str(e))
    except Exception:
        log.exception("Tracking %s/%s failed", owner, repo)
        return _fail("Something went wrong while starting to track this project. Please try again in a minute.")
    return {"success": True}


@app.get("/history/{owner}/{repo}")
def repo_history(owner: str, repo: str):
    if not (NAME.match(owner) and NAME.match(repo)):
        return _fail("That doesn't look like a GitHub repository.")
    if not history_store.ENABLED:
        return {"success": True, "enabled": False, "tracked": False, "snapshots": [], "changes": []}
    try:
        tracked = history_store.is_tracked(owner, repo)
        rows = history_store.get_history(owner, repo) if tracked else []
    except Exception:
        log.exception("Reading history failed")
        return _fail("We couldn't load this project's history right now.")
    return {"success": True, "enabled": True, "tracked": tracked, "snapshots": rows, "changes": history_store.month_over_month(rows)}


class SubscribeRequest(BaseModel):
    email: str = Field(max_length=254)
    owner: str = Field(max_length=100)
    repo: str = Field(max_length=100)
    team: str = Field(max_length=40)
    timezone: str = Field("UTC", max_length=64)


class TokenRequest(BaseModel):
    token: str = Field(max_length=64)


@app.post("/subscriptions")
def subscribe(body: SubscribeRequest, request: Request):
    """Weekly emails are only offered from a team space, for the team's own project."""
    owner, repo = body.owner.strip(), body.repo.strip()
    if not is_team_id(body.team):
        return _fail("Weekly emails are set up from your team space. Open 'Your team's history' first.")
    if not (NAME.match(owner) and NAME.match(repo)):
        return _fail("That doesn't look like a GitHub repository.")
    if _over_limit(_client_ip(request), _uploads_by_ip, UPLOAD_HOURLY_LIMIT):
        return _fail("Too many changes in the last hour. Please try again a little later.")
    try:
        activity = fetch_repo_activity(owner, repo)  # confirms it's public, and gets GitHub's spelling
        history_store.track(activity["owner"], activity["repo"])  # weekly emails come with trends
        outcome = subscriptions.subscribe(body.email, activity["owner"], activity["repo"], body.team, str(_zone(body.timezone)))
    except (GitHubError, history_store.HistoryError, subscriptions.SubscriptionError) as e:
        return _fail(str(e))
    except Exception:
        log.exception("Subscribing failed")
        return _fail("Something went wrong setting up the weekly email. Please try again in a minute.")
    if outcome == "already":
        return {"success": True, "message": "This email already gets the weekly report for this project."}
    return {"success": True, "message": "Check your inbox and click the link to confirm. If it's not there, look in your spam folder."}


@app.post("/subscriptions/confirm")
def confirm_subscription(body: TokenRequest):
    try:
        name = subscriptions.confirm(body.token)
    except subscriptions.SubscriptionError as e:
        return _fail(str(e))
    except Exception:
        log.exception("Confirming a subscription failed")
        return _fail("Something went wrong. Please try the link again in a minute.")
    return {"success": True, "message": f"Confirmed. You'll get the report on {name} every Monday."}


@app.post("/subscriptions/unsubscribe")
def unsubscribe(body: TokenRequest):
    try:
        name = subscriptions.unsubscribe(body.token)
    except Exception:
        log.exception("Unsubscribing failed")
        return _fail("Something went wrong. Please try the link again in a minute.")
    return {"success": True, "message": f"Unsubscribed from {name}. Your email address has been deleted." if name
            else "You're already unsubscribed."}


@app.api_route("/subscriptions/unsubscribe/{token}", methods=["GET", "POST"], response_class=HTMLResponse)
def unsubscribe_link(token: str):
    """Target of Gmail's own Unsubscribe button: works on its own, without the website."""
    try:
        name = subscriptions.unsubscribe(token)
        message = f"Unsubscribed from {escape(name)}. Your email address has been deleted." if name else "You're already unsubscribed."
    except Exception:
        log.exception("Unsubscribe link failed")
        message = "Something went wrong. Please try again in a minute."
    return f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dev Productivity AI</title><body style="font-family:Helvetica,Arial,sans-serif;background:#F5F6F2;color:#15201C;padding:40px 16px">
<div style="max-width:480px;margin:0 auto;background:#fff;border:1px solid #DCE1DC;border-radius:12px;padding:24px">
<div style="font-weight:700;color:#0E6B57;margin-bottom:12px">Dev Productivity AI</div><p style="font-size:16px">{message}</p></div></body>"""


@app.post("/teams")
def create_team(request: Request):
    if _over_limit(_client_ip(request), _uploads_by_ip, UPLOAD_HOURLY_LIMIT):
        return _fail("Too many changes in the last hour. Please try again a little later.")
    return {"success": True, "team": new_team_id()}


@app.get("/teams/{team}/documents")
def team_documents(team: str):
    if not is_team_id(team):
        return _fail("That team link isn't valid. Check you copied all of it.")
    return {"success": True, "documents": list_documents(team)}


@app.post("/teams/{team}/documents")
async def add_team_document(team: str, request: Request, title: str = Form(""), text: str = Form(""),
                            file: UploadFile | None = File(None)):
    if not is_team_id(team):
        return _fail("That team link isn't valid. Check you copied all of it.")
    if _over_limit(_client_ip(request), _uploads_by_ip, UPLOAD_HOURLY_LIMIT):
        return _fail("Too many uploads in the last hour. Please try again a little later.")
    try:
        if file is not None and file.filename:
            text = text_from_file(file.filename, await file.read(2_000_001))
            # A short first line ("POSTMORTEM: Search outage, May 2025") beats the file name.
            first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
            title = title or (first_line if len(first_line) <= 100 else "") or os.path.splitext(file.filename)[0].replace("_", " ").replace("-", " ")
        doc = add_document(team, title, text)
    except TeamDocError as e:
        return _fail(str(e))
    except Exception:
        log.exception("Adding a team document failed")
        return _fail("Something went wrong saving that document. Please try again in a minute.")
    # Cached reports for this team were written without the new document.
    for key in [k for k in _cache if k.endswith(f"#{team.lower()}")]:
        _cache.pop(key, None)
    return {"success": True, "document": doc}


@app.delete("/teams/{team}/documents/{doc_id}")
def remove_team_document(team: str, doc_id: str):
    if not is_team_id(team):
        return _fail("That team link isn't valid. Check you copied all of it.")
    try:
        delete_document(team, doc_id)
    except TeamDocError as e:
        return _fail(str(e))
    for key in [k for k in _cache if k.endswith(f"#{team.lower()}")]:
        _cache.pop(key, None)
    return {"success": True}


@app.get("/health")
async def health():
    return {"status": "running"}
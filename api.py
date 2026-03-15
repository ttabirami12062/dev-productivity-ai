import os
import sys
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.github_client import get_pull_requests, get_commits, get_contributors
from src.metrics import calculate_pr_metrics, calculate_commit_metrics, calculate_health_score
from src.report_generator import generate_health_report
from src.rag_pipeline import build_rag_context

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        msg["Subject"] = f"New Feedback - {review['repo']} - {review['rating']}/5 stars"
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = GMAIL_ADDRESS

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 32px;">
                <h2 style="color: #1A56DB;">New Feedback Received</h2>
                <hr/>
                <p><strong>Repository:</strong> {review['owner']}/{review['repo']}</p>
                <p><strong>Rating:</strong> {'★' * review['rating']}{'☆' * (5 - review['rating'])} ({review['rating']}/5)</p>
                <p><strong>Comment:</strong> {review.get('comment', 'No comment left') or 'No comment left'}</p>
                <p><strong>Name:</strong> {review.get('name', 'Not provided') or 'Not provided'}</p>
                <p><strong>Email:</strong> {review.get('user_email', 'Not provided') or 'Not provided'}</p>
                <p><strong>Role:</strong> {review.get('role', 'Not specified') or 'Not specified'}</p>
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
    owner: str
    repo: str

class ReviewRequest(BaseModel):
    owner: str
    repo: str
    rating: int
    comment: str = ""
    name: str = ""
    user_email: str = ""
    role: str = ""

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        pull_requests = get_pull_requests(request.owner, request.repo)
        commits = get_commits(request.owner, request.repo)
        contributors = get_contributors(request.owner, request.repo)

        pr_metrics = calculate_pr_metrics(pull_requests)
        commit_metrics = calculate_commit_metrics(commits)
        health_score = calculate_health_score(pr_metrics, commit_metrics)

        rag_context = build_rag_context(pr_metrics, commit_metrics, health_score)
        report = generate_health_report(pr_metrics, commit_metrics, health_score, rag_context)

        return {
            "success": True,
            "owner": request.owner,
            "repo": request.repo,
            "health_score": health_score,
            "pr_metrics": pr_metrics,
            "commit_metrics": commit_metrics,
            "report": report
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/review")
async def submit_review(request: ReviewRequest):
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

@app.get("/reviews")
async def get_reviews():
    return {"reviews": load_reviews()}

@app.get("/health")
async def health():
    return {"status": "running"}
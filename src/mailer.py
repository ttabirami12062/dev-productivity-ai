"""Sends email through Gmail with an app password, plus the weekly report and confirmation designs.

Emails are plain HTML with inline styles (email apps ignore stylesheets) and a text version
for apps that don't show HTML. Every value that came from GitHub or the AI is escaped.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SITE_URL = (os.getenv("SITE_URL") or "https://dev-productivity-ai.vercel.app").rstrip("/")
ENABLED = bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)

STATUS = {"healthy": ("Healthy", "#1E8A4C"), "watch": ("Worth watching", "#C27A00"),
          "at_risk": ("At risk", "#C8372D"), "quiet": ("Too little activity", "#7F8D87")}
KIND = {"risk": ("Risk", "#C8372D"), "action": ("Do this week", "#0E6B57"), "positive": ("Going well", "#1E8A4C")}


def send(to, subject, html, text):
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"Dev Productivity AI <{GMAIL_ADDRESS}>"
    message["To"] = to
    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [to], message.as_string())


def _page(body):
    return f"""<div style="background:#F5F6F2;padding:24px 12px;font-family:Helvetica,Arial,sans-serif;color:#15201C">
<div style="max-width:560px;margin:0 auto;background:#FFFFFF;border:1px solid #DCE1DC;border-radius:12px;padding:24px">
<div style="font-weight:700;font-size:15px;color:#0E6B57;margin-bottom:18px">Dev Productivity AI</div>
{body}
</div></div>"""


def confirmation_email(display_name, token):
    link = f"{SITE_URL}/?confirm={token}"
    html = _page(f"""<h1 style="font-size:22px;margin:0 0 12px">Confirm your weekly report</h1>
<p style="font-size:15px;line-height:1.5;color:#4B5A54">Someone (hopefully you) asked for a team health report on
<b>{escape(display_name)}</b> every Monday. Click the button to confirm. If this wasn't you, ignore this email and nothing will be sent.</p>
<p style="margin:22px 0"><a href="{link}" style="background:#0E6B57;color:#FFFFFF;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:600">Confirm weekly report</a></p>
<p style="font-size:12px;color:#7F8D87">Your email is only used to send this report, and is deleted when you unsubscribe.</p>""")
    text = (f"Confirm your weekly Dev Productivity AI report on {display_name}:\n{link}\n\n"
            "If this wasn't you, ignore this email and nothing will be sent.")
    return f"Confirm your weekly report on {display_name}", html, text


def report_email(display_name, team, built, token):
    report, score = built["report"], built["score"]
    label, color = STATUS.get(built["status"], ("", "#15201C"))
    dashboard = f"{SITE_URL}/?team={team}&repo={display_name}"
    unsubscribe = f"{SITE_URL}/?unsubscribe={token}"
    findings = "".join(
        f"""<tr><td style="border-left:4px solid {KIND[f['kind']][1]};padding:8px 12px">
<div style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#7F8D87">{KIND[f['kind']][0]}</div>
<div style="font-size:15px;font-weight:600;margin:2px 0">{escape(f['title'])}</div>
<div style="font-size:14px;line-height:1.45;color:#4B5A54">{escape(f['detail'])}</div></td></tr>
<tr><td style="height:8px"></td></tr>""" for f in report["findings"])
    signals = "".join(f"<li>{escape(s)}</li>" for s in built["signals"]) or "<li>No warning signs this week.</li>"
    html = _page(f"""<div style="font-size:12px;color:#7F8D87;text-transform:uppercase;letter-spacing:.06em">{escape(display_name)} &middot; weekly report</div>
<h1 style="font-size:22px;line-height:1.2;margin:8px 0 10px">{escape(report['headline'])}</h1>
<p style="font-size:15px;line-height:1.5;color:#4B5A54;margin:0 0 16px">{escape(report['summary'])}</p>
<div style="font-size:40px;font-weight:800;color:{color}">{score}<span style="font-size:16px;color:#7F8D87">/100</span>
<span style="font-size:13px;font-weight:600;color:{color};margin-left:8px">{label}</span></div>
<div style="background:#FFF1D6;border-radius:8px;padding:10px 14px;margin:16px 0;font-size:14px;color:#5E4300">
<b>What lowered the score</b><ul style="margin:6px 0 0;padding-left:18px">{signals}</ul></div>
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%">{findings}</table>
<p style="margin:20px 0"><a href="{dashboard}" style="background:#0E6B57;color:#FFFFFF;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:600">Open the full dashboard</a></p>
<p style="font-size:12px;color:#7F8D87;line-height:1.5">You get this because your team subscribed from its team space.
<a href="{unsubscribe}" style="color:#7F8D87">Unsubscribe</a> in one click.</p>""")
    text = "\n".join([f"{display_name}: weekly report", report["headline"], report["summary"], f"Health score: {score}/100 ({label})", ""]
                     + [f"- {KIND[f['kind']][0]}: {f['title']}. {f['detail']}" for f in report["findings"]]
                     + ["", f"Full dashboard: {dashboard}", f"Unsubscribe: {unsubscribe}"])
    return f"{display_name}: {report['headline']}", html, text

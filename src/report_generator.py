import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.metrics import duration

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Read from the environment so a retired model can be swapped on Render without a code change.
MODEL = os.getenv("OPENAI_MODEL") or "gpt-5.4-mini"
KINDS = ("risk", "action", "positive")

SYSTEM = """You write weekly team health reports for engineering managers.
Rules:
- Use only the numbers in TEAM DATA. Never invent numbers, names or dates.
- HISTORY entries are numbered. When a sentence relies on one, cite it as its number in "sources".
  Cite the GitHub data as source 0. Never cite a number that isn't listed.
- If HISTORY doesn't fit this team's situation, don't force it in.
- Plain, direct sentences. No filler, no generic advice, no emojis.
- Write waits of 48 hours or more in days (say "30 days", not "726 hours").
Reply with JSON only."""

SHAPE = """{
  "headline": "one sentence, at most 14 words, the single most important thing this week",
  "highlight": "the key phrase from the headline, copied exactly (a few words)",
  "summary": "two sentences explaining the headline with the most important numbers",
  "findings": [
    {"kind": "risk", "title": "short title", "detail": "1-2 sentences", "sources": [0]},
    {"kind": "action", "title": "a concrete step for this week", "detail": "1-2 sentences", "sources": [1]},
    {"kind": "positive", "title": "something going well", "detail": "1 sentence", "sources": [0]}
  ]
}
Give up to 2 risks, up to 2 actions and exactly 1 positive. A healthy team may have 0 risks."""


def _team_data(owner, repo, metrics, score, signals):
    prs, reviews, commits = metrics["prs"], metrics["reviews"], metrics["commits"]
    # Pre-written as "7.4 hours" / "5.3 days" so the model copies readable values.
    weekly = ", ".join(f"{w['label']}: {duration(w['median_hours']) if w['median_hours'] is not None else 'no merges'}"
                       for w in prs["weekly"])
    return f"""Repository: {owner}/{repo}, last {metrics['window']['days']} days ({metrics['window']['since']} to {metrics['window']['until']}, dates in {metrics['window'].get('timezone', 'UTC')})
People active: {metrics['people']}{' (solo project, so workload balance does not apply)' if metrics['solo'] else ''}
{'VERY LITTLE ACTIVITY: say plainly that there is too little recent work to judge team health. Give no risks and no actions, only the positive finding.' if metrics.get('quiet') else ''}
{'This project does not use GitHub pull requests (they are switched off), so judge it on commits only and do not mention PR or review metrics.' if not metrics.get('uses_prs', True) else ''}
Health score: {score}/100
What lowered the score: {' '.join(signals) if signals else 'nothing'}
PRs: {prs['total']} active, {prs['merged']} merged, {prs['open']} open ({prs['stale_open']} open over 3 days), {prs['closed_unmerged']} closed without merging
Median time from open to merge: {prs['median_merge_hours']} hours{f" (about {duration(prs['median_merge_hours'])})" if prs['median_merge_hours'] and prs['median_merge_hours'] >= 48 else ''}
Median wait to merge, by week: {weekly}
Reviews: {reviews['total']} on {reviews['reviewed_prs']} merged PRs; by person: {reviews['per_reviewer'] or 'none'}
Commits: {commits['total']}; by person: {commits['per_author']}"""


def _history_block(history):
    if not history:
        return "No history available."
    return "\n\n".join(f"[{i}] {h['title']}\n{h['text']}" for i, h in enumerate(history, start=1))


def _clean(report, max_source):
    """Keeps the model's reply to the shape the dashboard expects, whatever it sent."""
    findings = []
    for f in report.get("findings", []):
        kind = f.get("kind")
        if kind not in KINDS or not f.get("title"):
            continue
        sources = sorted({s for s in f.get("sources", []) if isinstance(s, int) and 0 <= s <= max_source})
        findings.append({"kind": kind, "title": str(f["title"]), "detail": str(f.get("detail", "")), "sources": sources})
    findings.sort(key=lambda f: KINDS.index(f["kind"]))
    headline = str(report.get("headline", "")).strip()
    highlight = str(report.get("highlight", "")).strip()
    return {
        "headline": headline,
        "highlight": highlight if highlight and highlight in headline else "",
        "summary": str(report.get("summary", "")).strip(),
        "findings": findings,
    }


def generate_health_report(owner, repo, metrics, score, signals, history):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = f"TEAM DATA\n{_team_data(owner, repo, metrics, score, signals)}\n\nHISTORY\n{_history_block(history)}\n\nReply in this JSON shape:\n{SHAPE}"
    options = {}
    # Reasoning models (gpt-5 family, o-series) reject temperature; low effort keeps them fast.
    if MODEL.startswith(("gpt-5", "o")):
        options["reasoning_effort"] = "low"
    else:
        options["temperature"] = 0.3
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_completion_tokens=1500,
        **options,
    )
    report = _clean(json.loads(response.choices[0].message.content), max_source=len(history))
    usage = response.usage
    return report, {"model": MODEL, "input_tokens": usage.prompt_tokens, "output_tokens": usage.completion_tokens}


def report_as_text(report):
    """Flat text version, used by the evaluation tests."""
    parts = [report["headline"], report["summary"]] + [f"{f['title']}. {f['detail']}" for f in report["findings"]]
    return "\n".join(p for p in parts if p)

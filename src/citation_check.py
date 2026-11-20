"""Checks that a report's claims are backed by what the model was actually given.

Two checks:
- numbers_grounded: free and instant, runs on every live report. Every number the
  model wrote must appear in the team data or the history it was shown.
- judge_citations: a second model reads each finding next to the sources it cites
  and says whether they support it. Used by the evaluation tests in CI.
"""
import json
import re

from src.observability import OpenAI, generation_options

# Numbers that come from the rules or plain wording rather than from the data.
ALWAYS_OK = {"0", "1", "2", "3", "24", "48", "50", "70", "80", "100"}
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")


def _numbers(text):
    return {n.replace(",", "") for n in NUMBER.findall(text)}


def _normalized(n):
    # "5.30" and "5.3" are the same number; "81" and "81.0" too.
    try:
        return f"{float(n):g}"
    except ValueError:
        return n


def report_text(report):
    parts = [report.get("headline", ""), report.get("summary", "")]
    parts += [f"{f['title']}. {f['detail']}" for f in report.get("findings", [])]
    return "\n".join(parts)


def numbers_grounded(report, *source_texts):
    """Returns (ok, unsupported numbers). ok is True when every number has a source."""
    allowed = {_normalized(n) for text in source_texts for n in _numbers(text)} | ALWAYS_OK
    used = {_normalized(n) for n in _numbers(report_text(report))}
    unsupported = sorted(used - allowed, key=lambda n: float(n) if n.replace(".", "", 1).isdigit() else 0)
    return not unsupported, unsupported


JUDGE = """You check an engineering report for faithfulness.
For each FINDING you get the SOURCES it cites. Source 0 is the TEAM DATA. Decide whether the
cited sources support the finding's factual claims (numbers, names, what happened before).
Recommendations count as supported if a cited source suggests that step or the data clearly
justifies it. Reply with JSON: {"results": [{"finding": <index>, "supported": true|false, "reason": "<short>"}]}"""


def judge_citations(report, team_data, history, model="gpt-5.4-mini"):
    """Returns a list of {finding, title, supported, reason} for findings that cite sources."""
    sources = {0: team_data} | {i: f"{h['title']}\n{h['text']}" for i, h in enumerate(history, start=1)}
    items = []
    for i, f in enumerate(report.get("findings", [])):
        if not f["sources"]:
            continue
        cited = "\n\n".join(f"[{s}] {sources.get(s, '(missing source)')}" for s in f["sources"])
        items.append(f"FINDING {i}: {f['title']}. {f['detail']}\nSOURCES:\n{cited}")
    if not items:
        return []

    response = OpenAI().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": JUDGE}, {"role": "user", "content": "\n\n---\n\n".join(items)}],
        response_format={"type": "json_object"},
        reasoning_effort="low",
        max_completion_tokens=1500,
        **generation_options("citation-judge"),
    )
    results = json.loads(response.choices[0].message.content).get("results", [])
    findings = report.get("findings", [])
    return [{"finding": r.get("finding"), "title": findings[r["finding"]]["title"] if isinstance(r.get("finding"), int) and r["finding"] < len(findings) else "?",
             "supported": bool(r.get("supported")), "reason": r.get("reason", "")} for r in results]

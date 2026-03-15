# AI Developer Productivity Intelligence System

Most engineering teams don't see burnout coming. They see it after — when a deadline is missed, a developer quits, or a system goes down at 2am.

This project is my attempt to fix that.

---

## What It Does

It connects to your GitHub, watches how your team works, and generates a report that sounds like this:

> "PR review time jumped to 52 hours this week. One developer handled 78% of all reviews. This exact pattern appeared in your March 2024 incident. Based on your own retrospective, the fix was to redistribute reviews across the team immediately."

Not generic advice. Not just a dashboard. Specific, grounded, actionable intelligence built from your team's own history.

---

## Live Demo

Enter any public GitHub repository on the dashboard and get an instant AI-powered team health report in seconds.

---

## Why I Built This

Tools like LinearB and Jellyfish already do developer analytics. They charge $30k–$100k per year and show dashboards full of numbers.

But they cannot answer the question that actually matters: "Why is this happening, and what should I do about it right now?"

That gap is what this project fills. It uses RAG to retrieve your team's own past incidents and retrospectives, then grounds every recommendation in that history. No hallucinations. No generic advice. Just context-aware intelligence.

---

## How It Works
```
GitHub Repo
    ↓
GitHub API pulls PR data, commits, code churn, review patterns
    ↓
Python processes and calculates team health metrics
    ↓
RAG layer searches Pinecone for similar past incidents
    ↓
LLM generates a grounded, cited health report
    ↓
React dashboard displays health score, metrics and report
    ↓
Langfuse tracks every LLM call — latency, cost, quality
    ↓
CI/CD pipeline runs evaluation tests on every push
```

---

## What Makes This Production Grade

Most AI portfolio projects stop at calling an API. This one goes further:

**RAG with semantic search** — retrieves the most relevant historical context from your team's own past incidents and retrospectives

**Citation enforcement** — the system grounds every recommendation in retrieved evidence, not generic advice

**Langfuse observability** — every LLM call is tracked with latency, cost per report, and quality scores

**CI/CD evaluation gate** — a golden dataset of test scenarios runs on every push. If report quality drops below threshold, the build fails. This is how real AI teams operate.

**Feedback system** — users can rate reports and leave contact details. Feedback is saved and emailed instantly.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Source | GitHub API |
| Vector DB | Pinecone |
| RAG Framework | LangChain |
| LLM | OpenAI GPT-3.5 |
| Observability | Langfuse |
| Frontend | React + TypeScript |
| Backend | FastAPI (Python) |
| CI/CD | GitHub Actions |

---

## Run It Yourself
```bash
git clone https://github.com/ttabirami12062/dev-productivity-ai
cd dev-productivity-ai
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
uvicorn api:app --reload
# In a new terminal
cd frontend && npm install && npm start
```

---

## Project Structure
```
dev-productivity-ai/
├── src/
│   ├── github_client.py      # GitHub API integration
│   ├── metrics.py            # Health score algorithm
│   ├── report_generator.py   # LLM report generation
│   ├── rag_pipeline.py       # RAG with Pinecone
│   └── observability.py      # Langfuse tracking
├── documents/                # Historical incident docs for RAG
├── frontend/                 # React + TypeScript dashboard
├── tests/
│   ├── golden_dataset.json   # Evaluation test cases
│   └── test_evaluation.py    # Automated quality gate
├── api.py                    # FastAPI backend
└── .github/workflows/        # CI/CD pipeline
```

---

## About

Built by Abirami Thiyagarajan, MS Computer Science at the University of Oklahoma.

I am interested in building AI systems that solve real operational problems — not demos, but things that actually work in production.

If you are an engineering manager or team lead and found this useful, I would love to connect and hear how this could help your team.

[GitHub](https://github.com/ttabirami12062) · [LinkedIn](https://linkedin.com/in/abirami-thiyagarajan)

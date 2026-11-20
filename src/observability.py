"""Langfuse tracing for every report.

Each analysis becomes one trace in Langfuse: the history search shows up as a
retriever step and the OpenAI call as a generation with its tokens, cost and
latency. Without Langfuse keys (CI, a fresh checkout) everything here quietly
does nothing, so the app never depends on Langfuse being reachable.
"""
import os
from contextlib import contextmanager

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Older .env files name the region URL LANGFUSE_BASE_URL; the SDK also reads LANGFUSE_HOST.
if os.getenv("LANGFUSE_BASE_URL") and not os.getenv("LANGFUSE_HOST"):
    os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]

ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))

if ENABLED:
    from langfuse import get_client, observe, propagate_attributes
    from langfuse.openai import OpenAI  # drop-in client that records each call as a generation
else:
    from openai import OpenAI  # noqa: F401  (re-exported for report_generator)


def retriever(func):
    """Marks a function as the retrieval step in the trace."""
    return observe(name="history-search", as_type="retriever")(func) if ENABLED else func


@contextmanager
def report_trace(owner, repo, timezone):
    """Wraps one analysis. Yields a callback that records the outcome on the trace."""
    if not ENABLED:
        def finish(**_):
            pass
        finish.trace_id = None
        yield finish
        return

    langfuse = get_client()
    with propagate_attributes(trace_name="weekly-report", tags=["report"], metadata={"repo": f"{owner}/{repo}", "timezone": timezone}):
        with langfuse.start_as_current_observation(as_type="span", name="weekly-report",
                                                   input={"repo": f"{owner}/{repo}", "timezone": timezone}) as span:
            def finish(score=None, status=None, headline=None, error=None, **extra):
                """Records the outcome on the trace."""
                span.update(output={"score": score, "status": status, "headline": headline, "error": error, **extra})
                if score is not None:
                    langfuse.score_current_trace(name="health_score", value=score, comment=status)
                if "numbers_grounded" in extra:
                    langfuse.score_current_trace(name="numbers_grounded", value=1 if extra["numbers_grounded"] else 0,
                                                 comment=", ".join(extra.get("unsupported_numbers") or []) or None)
            # The dashboard sends this back with feedback, so ratings land on the right report.
            finish.trace_id = langfuse.get_current_trace_id()
            yield finish


def record_feedback(trace_id, rating, comment, role):
    """Attaches a visitor's rating to the report's trace. Names and emails never go here."""
    if not (ENABLED and trace_id):
        return False
    langfuse = get_client()
    langfuse.create_score(trace_id=trace_id, name="user_rating", value=rating, data_type="NUMERIC",
                          comment=comment or None, metadata={"role": role} if role else None)
    langfuse.flush()
    return True


def generation_options(name):
    """Extra arguments the Langfuse OpenAI client understands; the plain client would reject them."""
    return {"name": name} if ENABLED else {}


def flush():
    if ENABLED:
        get_client().flush()

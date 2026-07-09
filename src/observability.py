"""Day 5, Session 3 -- Observability: logging, cost tracking, session stats,
threshold alerts, and input validation for the BVRIT chatbot.

Two log granularities, both JSON Lines for persistence:

- **Raw call log** (`logs/llm_calls.jsonl`, Exercise 1): one line per actual
  `chat.completions.create` call -- RAG generation, each tool-loop round,
  summarization, and the eval judge all go through `logged_llm_call()`, so
  every model invocation is accounted for individually (a multi-tool-round
  answer produces several raw-call lines, not one).
- **Query log** (`logs/query_log.jsonl`, Exercises 2-4): one line per
  `pipeline.answer_question()` call -- the unit a user (or the Session Stats
  panel) actually cares about. Cost/tokens here are the sum across every raw
  call that query triggered; latency is the full wall-clock the user waited,
  not just LLM time. This is also where the A/B prompt variant is recorded.

Both logs write to disk immediately (append, one line at a time) rather than
batching, so a crash mid-session doesn't lose already-completed calls -- and
also live in an in-session list (Streamlit session_state when available,
falling back to a module-level list for plain scripts like judge.py) so the
dashboard/alerts can read them back without re-parsing the file.
"""

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import config

LOG_DIR = config.PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
CALL_LOG_PATH = LOG_DIR / "llm_calls.jsonl"
QUERY_LOG_PATH = LOG_DIR / "query_log.jsonl"

# USD per 1M tokens -- OpenRouter's rates for the exact OpenAI-family models this
# project uses (see config.py). Embeddings have no output tokens.
PRICING_PER_MILLION_TOKENS = {
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/text-embedding-3-small": {"input": 0.02, "output": 0.0},
}

# Exercise 3 thresholds. LATENCY reuses the SLA already defined for eval
# dimension 06 (config.PERFORMANCE_SLA_SECONDS) rather than a second constant
# for the same number.
LATENCY_ALERT_SECONDS = config.PERFORMANCE_SLA_SECONDS
COST_PER_QUERY_ALERT_USD = 0.10
ERROR_RATE_ALERT_FRACTION = 0.05
ERROR_RATE_ROLLING_WINDOW = 20
MAX_INPUT_CHARS = 2000

_FALLBACK_CALL_LOGS: list[dict] = []
_FALLBACK_QUERY_LOGS: list[dict] = []


def _session_list(key: str, fallback: list[dict]) -> list[dict]:
    """Streamlit session_state when running in the app (so each browser session
    gets its own stats), a plain module-level list otherwise (judge.py,
    run_tests.py, the A/B script -- no Streamlit session to hang state off).
    """
    try:
        import streamlit as st
        if not st.runtime.exists():
            raise RuntimeError("no Streamlit runtime")
        if key not in st.session_state:
            st.session_state[key] = []
        return st.session_state[key]
    except Exception:
        return fallback


def get_call_logs() -> list[dict]:
    return _session_list("observability_call_logs", _FALLBACK_CALL_LOGS)


def get_query_logs() -> list[dict]:
    return _session_list("observability_query_logs", _FALLBACK_QUERY_LOGS)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING_PER_MILLION_TOKENS.get(model)
    if not rates:
        return 0.0
    return (input_tokens / 1_000_000) * rates["input"] + (output_tokens / 1_000_000) * rates["output"]


def _append_jsonl(path: Path, entry: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def logged_llm_call(client, *, call_type: str, **kwargs):
    """Wraps `client.chat.completions.create(**kwargs)`, logging timestamp,
    model, input/output tokens, latency, estimated cost, and status
    (success/failure) to both the raw call log file and the in-session list.
    `call_type` tags the call site (e.g. "generation", "tool_round",
    "summarization", "judge") so a slow/expensive query can be attributed to
    the right stage. Re-raises on failure after logging it -- this wrapper
    observes, it doesn't swallow errors.
    """
    model = kwargs.get("model", "unknown")
    start = time.perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:
        entry = {
            "timestamp": timestamp,
            "call_type": call_type,
            "model": model,
            "input_tokens": 0,
            "output_tokens": 0,
            "latency": round(time.perf_counter() - start, 4),
            "cost": 0.0,
            "status": "failure",
            "error": f"{type(exc).__name__}: {exc}",
        }
        get_call_logs().append(entry)
        _append_jsonl(CALL_LOG_PATH, entry)
        raise

    latency = time.perf_counter() - start
    usage = response.usage
    input_tokens = usage.prompt_tokens if usage else 0
    output_tokens = usage.completion_tokens if usage else 0
    cost = estimate_cost(model, input_tokens, output_tokens)

    entry = {
        "timestamp": timestamp,
        "call_type": call_type,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency": round(latency, 4),
        "cost": round(cost, 6),
        "status": "success",
    }
    get_call_logs().append(entry)
    _append_jsonl(CALL_LOG_PATH, entry)
    return response


def log_query(
    *,
    query: str,
    latency: float,
    input_tokens: int,
    output_tokens: int,
    status: str,
    variant: str | None = None,
    error: str | None = None,
) -> dict:
    """One entry per `pipeline.answer_question()` call -- the query-level
    record used by the Session Stats dashboard, threshold alerts, and the A/B
    test. Cost is derived from the same PRICING table using CHAT_MODEL, since
    every raw call within a query uses that one model.
    """
    cost = estimate_cost(config.CHAT_MODEL, input_tokens, output_tokens)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "latency": round(latency, 4),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": round(cost, 6),
        "status": status,
        "variant": variant,
    }
    if error:
        entry["error"] = error
    get_query_logs().append(entry)
    _append_jsonl(QUERY_LOG_PATH, entry)
    return entry


def log_rejected_input(query: str, reason: str) -> dict:
    """Exercise 3's input-length validator logs the attempt even though it
    never reaches retrieval/generation -- a status distinct from "failure"
    (that's an API/model error) and "success".
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query[:200] + ("..." if len(query) > 200 else ""),
        "latency": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost": 0.0,
        "status": "rejected",
        "variant": None,
        "error": reason,
    }
    get_query_logs().append(entry)
    _append_jsonl(QUERY_LOG_PATH, entry)
    return entry


def validate_input_length(text: str) -> str | None:
    """Returns a friendly rejection message if `text` exceeds MAX_INPUT_CHARS
    (the worst cost-blowout scenario: a user pasting an entire document as a
    query), or None if the input is fine.
    """
    if len(text) > MAX_INPUT_CHARS:
        return (
            f"That question is too long ({len(text):,} characters, limit {MAX_INPUT_CHARS:,}). "
            "Please shorten it to a specific question."
        )
    return None


def session_stats(logs: list[dict] | None = None) -> dict:
    """Exercise 2's sidebar metrics, computed over the query log."""
    logs = logs if logs is not None else get_query_logs()
    counted = [l for l in logs if l["status"] != "rejected"]
    if not counted:
        return {
            "total_queries": 0, "avg_latency": 0.0, "p95_latency": 0.0,
            "total_cost": 0.0, "total_tokens": 0, "error_count": 0,
        }
    latencies = [l["latency"] for l in counted]
    return {
        "total_queries": len(counted),
        "avg_latency": statistics.fmean(latencies),
        "p95_latency": (
            statistics.quantiles(latencies, n=100, method="inclusive")[94]
            if len(latencies) > 1 else latencies[0]
        ),
        "total_cost": sum(l["cost"] for l in counted),
        "total_tokens": sum(l["input_tokens"] + l["output_tokens"] for l in counted),
        "error_count": sum(1 for l in counted if l["status"] == "failure"),
    }


def check_alerts(logs: list[dict] | None = None) -> list[str]:
    """Exercise 3 -- run after every query. Checks the most recent query
    against the latency/cost thresholds, and the rolling last-N queries
    against the error-rate threshold. Returns human-readable warning strings
    (empty list if nothing breached).
    """
    logs = logs if logs is not None else get_query_logs()
    counted = [l for l in logs if l["status"] != "rejected"]
    if not counted:
        return []

    alerts = []
    last = counted[-1]
    if last["latency"] > LATENCY_ALERT_SECONDS:
        alerts.append(
            f"⚠️ High latency: this query took {last['latency']:.1f}s "
            f"(threshold {LATENCY_ALERT_SECONDS:.0f}s)."
        )
    if last["cost"] > COST_PER_QUERY_ALERT_USD:
        alerts.append(
            f"⚠️ High cost: this query cost ${last['cost']:.4f} "
            f"(threshold ${COST_PER_QUERY_ALERT_USD:.2f})."
        )

    window = counted[-ERROR_RATE_ROLLING_WINDOW:]
    error_rate = sum(1 for l in window if l["status"] == "failure") / len(window)
    if error_rate > ERROR_RATE_ALERT_FRACTION:
        alerts.append(
            f"⚠️ Elevated error rate: {error_rate:.0%} of the last {len(window)} queries failed "
            f"(threshold {ERROR_RATE_ALERT_FRACTION:.0%})."
        )
    return alerts

"""Orchestrates retrieval + grounded generation into one call, with latency
measurement and a guard for empty/whitespace input. Used by both the Streamlit
app (Phase 4) and the eval suite (Phase 5) so the two never drift apart.
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import observability
from generation import FALLBACK_CONTACT, REFUSAL_PREFIX, generate_answer, is_refusal
from live_eval import evaluate_live_answer
from retriever import retrieve

MAX_HISTORY_MESSAGES = 20  # a defensive cap, not the real space-management strategy -- the Chat page
                           # (Phase 6, Exercise 2) does the real work via summarizer.maybe_summarize(),
                           # which folds anything older than the last 10 turns into history_summary
                           # instead of silently discarding it. This constant just guarantees no caller
                           # can accidentally send an unbounded history to the model.


def trim_history(history: list[dict]) -> list[dict]:
    return history[-MAX_HISTORY_MESSAGES:] if history else []


def _retrieval_query(query: str, profile: dict | None) -> str:
    """Phase 6, Exercise 4 — nudges retrieval toward the user's known branch of
    interest when their question doesn't name a branch itself (e.g. "What's the
    total 4-year cost?"), so the right section actually ends up in top-k before
    generation ever sees it. Personalizing only the system prompt isn't enough --
    if the wrong branch's chunks are never retrieved, the model has nothing to
    resolve "my branch" against.
    """
    branch = (profile or {}).get("branch_interest")
    if branch and branch.lower() not in query.lower():
        return f"{query} ({branch})"
    return query


def _score_live_answer(
    query: str, answer: str, chunks: list, refused: bool, latency: float,
    tokens_in: int | None, tokens_out: int | None, tool_calls: list[dict], variant: str,
) -> None:
    """Runs the reference-free judge (one extra LLM call) and logs the result
    for the dashboard's "Live Chat Evaluation" history. Runs synchronously,
    in-line with the request: an earlier background-thread version was
    unreliable under Streamlit specifically -- submitting a second question
    before the first question's thread finished scoring reliably killed that
    first thread before it ever ran (Streamlit's rerun mechanism can inject
    an async exception into the whole script thread's call stack, including
    mid-way through starting a child thread), silently dropping entries from
    the history. That's worse than the ~1-2s of added latency this costs.
    Never raises -- a scoring failure must not break the chat flow."""
    try:
        scored = evaluate_live_answer(query, answer, chunks, refused)
        observability.log_live_eval({
            "query": query,
            "answer": answer,
            "refused": refused,
            "rag_used": bool(chunks),
            "num_chunks": len(chunks),
            "sections_used": sorted({c.section for c in chunks}),
            "tools_used": [t["name"] for t in tool_calls],
            "latency": round(latency, 4),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "prompt_variant": variant,
            **scored,
        })
    except Exception:
        pass


def answer_question(
    query: str,
    history: list[dict] | None = None,
    top_k: int = config.DEFAULT_TOP_K,
    section: str | None = None,
    profile: dict | None = None,
    history_summary: str | None = None,
    prompt_variant: str | None = "A",
    live_evaluate: bool = True,
) -> dict:
    """`prompt_variant` is "A" by default (the live app's normal, stable
    grounding prompt). Pass None to get Day 5/Session 3 Exercise 4's random
    50/50 A/B assignment instead -- used by eval/ab_test_grounding_prompt.py,
    not by the live Chat page, so real users never see randomly-varying
    chatbot behavior from an in-progress experiment.

    `live_evaluate` scores this answer for the dashboard's "Live Chat
    Evaluation" history (see _score_live_answer). Defaults to True for
    the live Chat page; the eval suite, A/B script, and governance tests all
    pass False -- they run their own dedicated scoring, and letting their
    synthetic/curated questions into the *live* history would misrepresent
    what real users actually asked.
    """
    start = time.perf_counter()
    variant = prompt_variant if prompt_variant is not None else random.choice(["A", "B"])

    if not query or not query.strip():
        latency = time.perf_counter() - start
        observability.log_query(
            query=query, latency=latency, input_tokens=0, output_tokens=0,
            status="success", variant=variant,
        )
        return {
            "query": query,
            "answer": f"{REFUSAL_PREFIX} That looks like an empty question. {FALLBACK_CONTACT}",
            "retrieved_chunks": [],
            "refused": True,
            "latency": latency,
            "tokens_in": None,
            "tokens_out": None,
            "tool_calls": [],
            "prompt_variant": variant,
            "alerts": [],
        }

    try:
        chunks = retrieve(_retrieval_query(query, profile), top_k=top_k, section=section)
        answer, tokens, tool_calls = generate_answer(
            query, chunks, history=trim_history(history or []), profile=profile,
            history_summary=history_summary, prompt_variant=variant,
        )
    except Exception as exc:
        latency = time.perf_counter() - start
        observability.log_query(
            query=query, latency=latency, input_tokens=0, output_tokens=0,
            status="failure", variant=variant, error=f"{type(exc).__name__}: {exc}",
        )
        raise

    latency = time.perf_counter() - start
    input_tokens = tokens.get("prompt_tokens") or 0
    output_tokens = tokens.get("completion_tokens") or 0
    observability.log_query(
        query=query, latency=latency, input_tokens=input_tokens, output_tokens=output_tokens,
        status="success", variant=variant,
    )

    if live_evaluate:
        _score_live_answer(
            query, answer, chunks, is_refusal(answer), latency,
            input_tokens, output_tokens, tool_calls, variant,
        )

    return {
        "query": query,
        "answer": answer,
        "retrieved_chunks": chunks,
        "refused": is_refusal(answer),
        "latency": latency,
        "tokens_in": tokens.get("prompt_tokens"),
        "tokens_out": tokens.get("completion_tokens"),
        "tool_calls": tool_calls,
        "prompt_variant": variant,
        "alerts": observability.check_alerts(),
    }


if __name__ == "__main__":
    result = answer_question("What is the annual tuition fee for CSE?")
    print(f"Answer: {result['answer']}")
    print(f"Refused: {result['refused']}  Latency: {result['latency']:.2f}s")
    print("Retrieved:")
    for c in result["retrieved_chunks"]:
        print(f"  ({c.section}, page {c.page})")

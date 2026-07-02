"""Orchestrates retrieval + grounded generation into one call, with latency
measurement and a guard for empty/whitespace input. Used by both the Streamlit
app (Phase 4) and the eval suite (Phase 5) so the two never drift apart.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from generation import FALLBACK_CONTACT, REFUSAL_PREFIX, generate_answer, is_refusal
from retriever import retrieve

MAX_HISTORY_MESSAGES = 6  # ~3 user/assistant exchanges of prior context


def trim_history(history: list[dict]) -> list[dict]:
    return history[-MAX_HISTORY_MESSAGES:] if history else []


def answer_question(
    query: str,
    history: list[dict] | None = None,
    top_k: int = config.DEFAULT_TOP_K,
    section: str | None = None,
) -> dict:
    start = time.perf_counter()

    if not query or not query.strip():
        return {
            "query": query,
            "answer": f"{REFUSAL_PREFIX} That looks like an empty question. {FALLBACK_CONTACT}",
            "retrieved_chunks": [],
            "refused": True,
            "latency": time.perf_counter() - start,
            "tokens_in": None,
            "tokens_out": None,
        }

    chunks = retrieve(query, top_k=top_k, section=section)
    answer, tokens = generate_answer(query, chunks, history=trim_history(history or []))

    return {
        "query": query,
        "answer": answer,
        "retrieved_chunks": chunks,
        "refused": is_refusal(answer),
        "latency": time.perf_counter() - start,
        "tokens_in": tokens.get("prompt_tokens"),
        "tokens_out": tokens.get("completion_tokens"),
    }


if __name__ == "__main__":
    result = answer_question("What is the annual tuition fee for CSE?")
    print(f"Answer: {result['answer']}")
    print(f"Refused: {result['refused']}  Latency: {result['latency']:.2f}s")
    print("Retrieved:")
    for c in result["retrieved_chunks"]:
        print(f"  ({c.section}, page {c.page})")

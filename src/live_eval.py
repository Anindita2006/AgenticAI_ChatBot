"""Reference-free judge for real chat questions asked through the live app.

The eval/ suite (judge.py, ragas_eval.py) scores curated test cases that ship
with a hand-written expected_answer -- there's no such reference for an
organic question a real user types in, so this scores the same two RAGAS-style
axes (groundedness/faithfulness to the retrieved CONTEXT, and relevance to the
question actually asked) directly from the CONTEXT and ANSWER alone, with
JUDGE_MODEL (never CHAT_MODEL, so the chatbot is never judging itself).
"""

import json

import config
import observability
from generation import VERIFIED_ROSTER_BLOCK
from retriever import RetrievedChunk

PASS_THRESHOLD = 0.7  # matches the RAGAS dashboard's own 0.7 line, for one consistent bar across the app

JUDGE_SYSTEM_PROMPT = (
    "You are an impartial evaluator scoring one real answer from a RAG college-FAQ chatbot, on two "
    "axes:\n"
    "- groundedness (0.0-1.0): is every factual claim in ANSWER actually supported by CONTEXT, OR by the "
    "VERIFIED LEADERSHIP ROSTER below? 1.0 = fully supported by either source, or a correct refusal when "
    "neither has the answer; 0.0 = confidently states facts absent from or contradicted by both.\n"
    "- relevance (0.0-1.0): does ANSWER actually address QUESTION? 1.0 = directly answers (or correctly "
    "and appropriately refuses) what was asked; 0.0 = off-topic or non-responsive.\n"
    "If REFUSED is true, a short, appropriate refusal should score high on both axes -- refusing when "
    "CONTEXT genuinely lacks the answer is correct behavior, not a failure.\n\n"
    "IMPORTANT: this chatbot's own CONTEXT document has a known extraction defect where some person "
    "names sit next to the wrong role heading (e.g. it may say a management-team member's name is the "
    "Principal, or credit a stale/superseded person as a department HOD). For that reason, the chatbot "
    "is deliberately instructed to answer 'who is the Principal / HOD of <department>' questions ONLY "
    "from this separately verified roster, citing it as [Verified College Roster] instead of a page "
    "number -- NOT from whatever name CONTEXT happens to associate with that role:\n"
    f"{VERIFIED_ROSTER_BLOCK}\n"
    "For exactly this question type, score groundedness against the ROSTER, not CONTEXT: an answer that "
    "gives the roster's name (cited as [Verified College Roster]) is fully grounded (1.0) even though "
    "CONTEXT itself names someone else for that role -- that is correct, intended behavior, not a "
    "hallucination. Only mark it ungrounded if the name given does NOT match the roster.\n\n"
    'Return ONLY a JSON object: {"groundedness": <float>, "relevance": <float>, "reason": "<one sentence>"}'
)


def _build_user_prompt(query: str, answer: str, chunks: list[RetrievedChunk], refused: bool) -> str:
    context = "\n\n".join(f"[{c.section}, Page {c.page}]\n{c.text}" for c in chunks) or "(no context retrieved)"
    return (
        f"QUESTION: {query}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"ANSWER: {answer}\n\n"
        f"REFUSED: {refused}"
    )


def evaluate_live_answer(
    query: str, answer: str, chunks: list[RetrievedChunk], refused: bool,
) -> dict:
    """Never raises -- a scoring failure (rate limit, malformed JSON, etc.) must
    not be allowed to take down the chat flow this runs alongside. Returns a
    dict with an "error" key instead when scoring itself fails."""
    try:
        client = config.get_chat_client()
        response = observability.logged_llm_call(
            client,
            call_type="live_judge",
            model=config.JUDGE_MODEL,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(query, answer, chunks, refused)},
            ],
            temperature=0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        groundedness = float(parsed["groundedness"])
        relevance = float(parsed["relevance"])
        avg = (groundedness + relevance) / 2
        return {
            "groundedness": groundedness,
            "relevance": relevance,
            "avg_score": avg,
            "verdict": "pass" if avg >= PASS_THRESHOLD else "fail",
            "reason": parsed.get("reason", ""),
        }
    except Exception as exc:
        return {
            "groundedness": None, "relevance": None, "avg_score": None,
            "verdict": "error", "reason": f"{type(exc).__name__}: {exc}",
        }

"""Phase 6, Exercise 2 — conversation summarization for long sessions.

Discrete batching, not a rolling window: every 10 turns is a checkpoint. At
turn 20, turns 1-10 fold into the summary and 11-20 stay verbatim. At turn
30, turns 11-20 fold in (extending the existing summary) and 21-30 stay
verbatim. Between checkpoints the window is simply left alone -- matching
the exercise's "after every 10 turns" cadence, and keeping this to one LLM
call per 10 turns rather than one per turn.

`summarized_turns` is the caller's cursor (how many of the earliest turns are
already folded into `summary`) -- callers (pages/0_Chat.py) persist both
`summary` and `summarized_turns` in session state across reruns.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tiktoken

import config
import observability

SUMMARIZE_EVERY_TURNS = 10

SUMMARY_SYSTEM_PROMPT = """You are condensing an earlier part of a conversation between a student and \
the BVRIT Hyderabad FAQ chatbot, so it can be dropped from the message history without losing what \
still matters for later turns. Write ONE dense paragraph (not bullets) that preserves, if present:
- the user's name
- which branches/departments/topics they asked about
- key facts already discussed (specific fee amounts, dates, figures) -- keep numbers exact, do not round
- any preferences they stated (e.g. "I prefer CSE", "explain briefly", "answer in English")
- any question that was left unresolved or a follow-up thread that was never closed

If an EXISTING SUMMARY of even-earlier turns is given, merge it with the new turns into one updated \
paragraph -- do not just append, actually combine so the result stays a single coherent paragraph and \
does not grow unbounded. Omit anything not present rather than inventing detail. Output only the \
paragraph, no preamble."""


def _turns_to_text(turns_messages: list[dict]) -> str:
    lines = []
    for m in turns_messages:
        speaker = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {m['content']}")
    return "\n".join(lines)


def count_tokens(messages: list[dict]) -> int:
    try:
        encoding = tiktoken.encoding_for_model(config.CHAT_MODEL.split("/")[-1])
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return sum(len(encoding.encode(m.get("content") or "")) for m in messages)


def summarize_turns(existing_summary: str | None, new_turns_messages: list[dict]) -> str:
    client = config.get_chat_client()
    prior = f"EXISTING SUMMARY OF EVEN EARLIER TURNS:\n{existing_summary}\n\n" if existing_summary else ""
    user_content = f"{prior}NEW CONVERSATION TURNS TO FOLD IN:\n{_turns_to_text(new_turns_messages)}"

    response = observability.logged_llm_call(
        client,
        call_type="summarization",
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
        max_tokens=500,  # one dense paragraph, not a full chat-answer budget
    )
    return response.choices[0].message.content.strip()


def maybe_summarize(
    history: list[dict],
    summary: str | None,
    summarized_turns: int,
) -> tuple[str | None, int, list[dict]]:
    """Checks whether `history` has just crossed a 10-turn checkpoint and, if so,
    folds the newly-expired block into `summary`. Always returns the verbatim
    tail (messages not yet folded in) regardless of whether folding happened
    this call.
    """
    total_turns = len(history) // 2

    if total_turns > 0 and total_turns % SUMMARIZE_EVERY_TURNS == 0:
        fold_upto_turn = total_turns - SUMMARIZE_EVERY_TURNS
        if fold_upto_turn > summarized_turns:
            new_turns_messages = history[summarized_turns * 2 : fold_upto_turn * 2]
            summary = summarize_turns(summary, new_turns_messages)
            summarized_turns = fold_upto_turn

    verbatim = history[summarized_turns * 2 :]
    return summary, summarized_turns, verbatim

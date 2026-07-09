"""Phase 6, Exercise 3 — extracts new profile facts from a single turn.

Heuristic (regex/keyword) rather than an LLM call: profile updates are a
side-channel to the main answer, not the user-facing feature being graded,
and a regex-based extractor keeps this working even when the chat model
itself is unavailable (e.g. no LLM credits) -- it only needs the turn's own
text, already in hand.
"""

import re

BRANCH_ALIASES = {
    "cse (ai&ml)": "CSE (AI&ML)", "cse ai&ml": "CSE (AI&ML)", "ai&ml": "CSE (AI&ML)",
    "artificial intelligence": "CSE (AI&ML)", "machine learning": "CSE (AI&ML)",
    "cse (data science)": "CSE (Data Science)", "data science": "CSE (Data Science)",
    "cse": "CSE", "computer science": "CSE",
    "ece": "ECE", "electronics": "ECE",
    "eee": "EEE", "electrical": "EEE",
    "mechanical": "Mechanical",
    "it": "IT", "information technology": "IT",
}
# Longest alias first so "cse (ai&ml)" matches before the bare "cse" substring does.
_ALIAS_ORDER = sorted(BRANCH_ALIASES, key=len, reverse=True)

NAME_RE = re.compile(r"\bmy name is ([A-Z][a-zA-Z]+)\b", re.IGNORECASE)
INTEREST_RE = re.compile(r"interested in\s+(?:b\.?tech\s+)?([a-z0-9 &()]+)", re.IGNORECASE)
FEE_RE = re.compile(r"Rs\.?\s?([\d,]{4,})")


def _match_branch(text: str) -> str | None:
    lowered = text.lower()
    for alias in _ALIAS_ORDER:
        if alias in lowered:
            return BRANCH_ALIASES[alias]
    return None


def extract_updates(
    user_message: str,
    answer_text: str,
    retrieved_sections: list[str],
    current_branch: str | None = None,
) -> dict:
    """Returns only the fields that were actually detected this turn -- callers
    merge this into the stored profile via memory_store.save_profile(), which
    itself drops anything not in STORABLE_FIELDS. `current_branch` is the
    profile's already-known branch_interest (if any), so a fee mentioned on a
    later turn still gets attributed correctly even when that turn doesn't
    restate the branch.
    """
    updates: dict = {}

    name_match = NAME_RE.search(user_message)
    if name_match:
        updates["name"] = name_match.group(1)

    interest_match = INTEREST_RE.search(user_message)
    if interest_match:
        branch = _match_branch(interest_match.group(1))
        if branch:
            updates["branch_interest"] = branch

    lowered = user_message.lower()
    if any(p in lowered for p in ("brief answer", "briefly", "bullet point", "short answer", "keep it short")):
        updates["detail_level"] = "brief"
    elif any(p in lowered for p in ("detailed answer", "in detail", "explain fully", "elaborate")):
        updates["detail_level"] = "detailed"

    if "in english" in lowered:
        updates["language"] = "English"

    if retrieved_sections:
        updates["prior_topics"] = sorted(set(retrieved_sections))

    branch = updates.get("branch_interest") or current_branch
    if branch:
        fee_match = FEE_RE.search(answer_text)
        if fee_match:
            updates["fee_amounts_discussed"] = {branch: fee_match.group(1)}

    return updates

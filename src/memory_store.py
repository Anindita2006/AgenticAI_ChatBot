"""Phase 6, Exercise 3/5 — Persistent user memory + privacy controls.

A JSON-file-backed profile store keyed by a user-typed name/ID (see
pages/0_Chat.py's sidebar text box -- this app has no real auth, so the
identifier is whatever the user types, matching the assignment's informal
"Priya" / "Rahul" test scenario).

FIELD_CLASSIFICATION documents the Exercise 5 privacy review: each field a
profile could hold is labelled ESSENTIAL / NICE_TO_HAVE / SENSITIVE. Only
ESSENTIAL and NICE_TO_HAVE fields are ever written to disk -- SENSITIVE
fields (a full verbatim transcript, or scholarship/financial-need details
that can reveal an eligibility category like EWS/SC/ST/BC) are excluded by
data minimisation, not just access control. STORABLE_FIELDS is the actual
enforcement point: build_updates() silently drops anything not in it.
"""

import json
import re
import time
from pathlib import Path

PROFILE_STORE_PATH = Path(__file__).resolve().parent.parent / "user_profiles" / "profiles.json"

AUTO_EXPIRE_SECONDS = 30 * 24 * 60 * 60  # 30 days

ESSENTIAL = "ESSENTIAL"
NICE_TO_HAVE = "NICE_TO_HAVE"
SENSITIVE = "SENSITIVE"

FIELD_CLASSIFICATION = {
    "name": NICE_TO_HAVE,  # personalises greetings/answers, but the bot works without it
    "branch_interest": ESSENTIAL,  # the one field that actually drives personalization (Exercise 4)
    "language": NICE_TO_HAVE,  # only English is supported today, but the field is harmless
    "detail_level": NICE_TO_HAVE,  # response style only, no functional dependency
    "prior_topics": NICE_TO_HAVE,  # short topic tags aid continuity, low sensitivity
    "last_session_summary": NICE_TO_HAVE,  # a short recap, not a transcript
    "full_conversation_transcripts": SENSITIVE,  # verbatim chat logs -- far more than needed; never stored
    "fee_amounts_discussed": NICE_TO_HAVE,  # these are public fee-schedule figures, not personal data
    "scholarship_details": SENSITIVE,  # can reveal financial need / reservation category; never stored
}

STORABLE_FIELDS = {f for f, cls in FIELD_CLASSIFICATION.items() if cls != SENSITIVE}

PRIVACY_NOTICE = (
    "This assistant remembers your name, branch of interest, and a few stated preferences "
    "(language, level of detail) across visits, so you don't have to repeat yourself -- stored "
    "locally under the name/ID you enter, never a full transcript. Profiles are auto-deleted after "
    "30 days of inactivity, and you can delete yours anytime by typing \"clear my data\"."
)


def _slugify(user_id: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", user_id.strip().lower().replace(" ", "_"))


def _load_all() -> dict:
    if not PROFILE_STORE_PATH.exists():
        return {}
    with open(PROFILE_STORE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_all(data: dict) -> None:
    PROFILE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _empty_profile() -> dict:
    return {
        "name": None,
        "branch_interest": None,
        "language": None,
        "detail_level": None,
        "prior_topics": [],
        "last_session_summary": None,
        "fee_amounts_discussed": {},
        "created_at": time.time(),
        "last_accessed": time.time(),
    }


def load_profile(user_id: str) -> dict:
    """Loads a profile by user_id, auto-expiring (deleting) it first if it hasn't
    been touched in AUTO_EXPIRE_SECONDS -- the returned profile is fresh/empty
    in that case, i.e. the user is treated as new, per Exercise 5's pass criteria.
    """
    key = _slugify(user_id)
    data = _load_all()
    profile = data.get(key)

    if profile is not None:
        age = time.time() - profile.get("last_accessed", 0)
        if age > AUTO_EXPIRE_SECONDS:
            del data[key]
            _save_all(data)
            profile = None

    if profile is None:
        profile = _empty_profile()
        data[key] = profile
    else:
        profile["last_accessed"] = time.time()
        data[key] = profile
    _save_all(data)
    return profile


def save_profile(user_id: str, updates: dict) -> dict:
    """Merges `updates` into the stored profile, dropping any field not in
    STORABLE_FIELDS (see the module docstring) regardless of what the caller
    passes in -- data minimisation is enforced here, not left to callers to
    remember.
    """
    key = _slugify(user_id)
    data = _load_all()
    profile = data.get(key, _empty_profile())

    for field, value in updates.items():
        if field not in STORABLE_FIELDS:
            continue
        if field == "prior_topics" and value:
            profile["prior_topics"] = sorted(set(profile.get("prior_topics", []) + list(value)))
        elif field == "fee_amounts_discussed" and value:
            profile.setdefault("fee_amounts_discussed", {}).update(value)
        elif value not in (None, ""):
            profile[field] = value

    profile["last_accessed"] = time.time()
    data[key] = profile
    _save_all(data)
    return profile


def delete_profile(user_id: str) -> bool:
    """Exercise 5's "Clear my data" command. Returns True if a profile existed."""
    key = _slugify(user_id)
    data = _load_all()
    if key in data:
        del data[key]
        _save_all(data)
        return True
    return False


def purge_expired() -> int:
    """Sweeps every stored profile and deletes ones idle past AUTO_EXPIRE_SECONDS.
    Called once at app startup as a general hygiene pass, independent of the
    per-user check in load_profile (which only catches the profile being
    loaded this session)."""
    data = _load_all()
    now = time.time()
    expired = [k for k, p in data.items() if now - p.get("last_accessed", 0) > AUTO_EXPIRE_SECONDS]
    for k in expired:
        del data[k]
    if expired:
        _save_all(data)
    return len(expired)

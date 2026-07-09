"""Phase 4 — Chat UI.

Streamlit chat interface for the BVRITH FAQ chatbot: a simple, non-technical
sidebar (logo, topic filter, clear button) and a main area with cited,
photo-illustrated answers. Deliberately keeps RAG internals (chunk counts,
token counts, retrieval knobs) out of the visible UI — those live in the
Evaluation Dashboard instead, where they're the point.

Page config and theme injection live in app.py (the st.navigation entry
point), which runs before this page is dispatched.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

import streamlit as st

import config
import memory_store
import observability
import theme
from facilities import facilities_mentioned
from generation import REFUSAL_PREFIX
from people import people_mentioned
from pipeline import answer_question
from profile_extraction import extract_updates
from retriever import get_index_stats, list_sections
from sources import GOOGLE_MAPS_URL, location_mentioned, resolve_source_url
from summarizer import count_tokens, maybe_summarize

LOGO_PATH = Path(__file__).resolve().parent.parent / "data" / "images" / "bvrith_logo.jpg"

CLEAR_DATA_PHRASES = {"clear my data", "clear my data.", "delete my data", "forget me"}

FEATURE_BADGES = ["⚡ RAG-Powered", "📚 Cited Sources", "🛠️ Tool-Calling", "🧠 Smart Memory", "📈 Observability"]

QUICK_TOPICS = [
    ("🎓", "Admissions", "What is the admission process and eligibility criteria?"),
    ("🏫", "Departments", "What B.Tech programmes does BVRIT offer?"),
    ("💰", "Fees", "What is the fee structure for B.Tech programmes?"),
    ("🏆", "Scholarships", "What scholarships are available?"),
    ("📈", "Placements", "What are the placement statistics?"),
    ("🏠", "Hostel", "Tell me about hostel facilities."),
    ("👩‍🏫", "Faculty", "Who are the department heads?"),
    ("📞", "Contact", "How can I contact the admissions office?"),
]

SUGGESTED_QUESTIONS = [
    "What is the fee structure for CSE?",
    "When is the last date for EAMCET counselling?",
    "What are the placement statistics for CSE?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "profile" not in st.session_state:
    st.session_state.profile = None
if "history_summary" not in st.session_state:
    st.session_state.history_summary = None
if "summarized_turns" not in st.session_state:
    st.session_state.summarized_turns = 0
if "purged_expired" not in st.session_state:
    memory_store.purge_expired()
    st.session_state.purged_expired = True

# Day 5, Session 3, Exercise 2 -- snapshot of session stats as they stood before
# this rerun, so the Session Stats panel (rendered at the bottom, after any
# query this rerun processes) can show a delta vs. "before this query".
stats_before = observability.session_stats()


def _dedupe_citations(chunks):
    seen = set()
    citations = []
    for c in chunks:
        key = (c.section, c.page)
        if key not in seen:
            seen.add(key)
            citations.append({
                "section": c.section,
                "page": c.page,
                "url": resolve_source_url(c.section, c.text),
            })
    return citations


def _render_citations(citations, answer_text: str = ""):
    with st.expander(f"📚 Sources ({len(citations)})", expanded=False):
        chips = [(f"📄 {c['section']}, Page {c['page']}", c["url"]) for c in citations]
        if location_mentioned(answer_text):
            chips.append(("🗺️ View on Google Maps", GOOGLE_MAPS_URL))
        theme.link_chip_row(chips)


def _render_photos(text: str) -> None:
    subjects = people_mentioned(text) + facilities_mentioned(text)
    subjects = [s for s in subjects if s["image"].exists()]
    if not subjects:
        return
    cols = st.columns(len(subjects))
    for col, subject in zip(cols, subjects):
        with col:
            st.image(str(subject["image"]), width=140)
            caption = subject["name"] if "role" not in subject else f"**{subject['name']}**  \n{subject['role']}"
            st.caption(caption)


# ---------------------------------------------------------------- sidebar --
with st.sidebar:
    theme.sidebar_logo(LOGO_PATH)
    st.caption("Ask me anything about admissions, fees, placements, faculty, or campus life.")

    try:
        stats = get_index_stats()
        topics = ["All topics"] + list_sections()
        assistant_ready = True
    except Exception:
        stats = None
        topics = ["All topics"]
        assistant_ready = False

    if assistant_ready:
        topic_choice = st.selectbox("Ask about a specific topic", topics)
        section_filter = None if topic_choice == "All topics" else topic_choice
    else:
        section_filter = None
        st.warning("The assistant isn't ready yet. Please try again shortly.")

    st.divider()

    user_id_input = st.text_input(
        "Your name or ID (optional)",
        value=st.session_state.user_id,
        help="Lets the assistant remember your branch of interest and preferences next time you visit.",
    )
    if user_id_input != st.session_state.user_id:
        st.session_state.user_id = user_id_input
        st.session_state.profile = memory_store.load_profile(user_id_input) if user_id_input.strip() else None

    with st.expander("🧠 Memory & privacy"):
        st.caption(memory_store.PRIVACY_NOTICE)
        turns = len(st.session_state.messages) // 2
        st.caption(
            f"This conversation: {turns} turn(s)"
            + (f" · earlier turns summarized after turn {st.session_state.summarized_turns}"
               if st.session_state.history_summary else "")
        )
        if st.button("Clear my data", use_container_width=True):
            if st.session_state.user_id.strip():
                memory_store.delete_profile(st.session_state.user_id)
            st.session_state.profile = None
            st.success("Your saved profile has been deleted.")

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history_summary = None
        st.session_state.summarized_turns = 0
        st.rerun()

# ------------------------------------------------------------- main chat --
theme.brand_hero(LOGO_PATH, "Your AI assistant for everything BVRITH")
theme.chip_row(FEATURE_BADGES)

if not st.session_state.messages:
    st.info(memory_store.PRIVACY_NOTICE, icon="🔒")

    st.markdown("###### Quick topics")
    topic_cols = st.columns(4)
    for i, (icon, label, question) in enumerate(QUICK_TOPICS):
        with topic_cols[i % 4]:
            if st.button(f"{icon}  {label}", use_container_width=True, key=f"qa_{label}"):
                st.session_state.pending_prompt = question

    st.markdown("###### Try asking")
    sugg_cols = st.columns(len(SUGGESTED_QUESTIONS))
    for col, question in zip(sugg_cols, SUGGESTED_QUESTIONS):
        with col:
            if st.button(question, use_container_width=True, key=f"sugg_{question}"):
                st.session_state.pending_prompt = question

    st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("refused"):
            st.badge("Not covered", icon="ℹ️", color="gray")
        st.markdown(msg["display_content"])
        if msg["role"] == "assistant":
            _render_photos(msg["display_content"])
        if msg.get("citations"):
            _render_citations(msg["citations"], msg["display_content"])

prompt = st.chat_input("Ask a question about BVRITH...")
if not prompt and st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt

if prompt:
    st.session_state.pending_prompt = None
    st.session_state.messages.append({"role": "user", "content": prompt, "display_content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Exercise 5 — "clear my data" is a chat command, not a normal question: it
    # never reaches retrieval/generation, just the profile store.
    if prompt.strip().lower() in CLEAR_DATA_PHRASES:
        if st.session_state.user_id.strip():
            memory_store.delete_profile(st.session_state.user_id)
        st.session_state.profile = None
        display_content = "Your saved profile has been deleted. You're starting fresh."
        with st.chat_message("assistant"):
            st.markdown(display_content)
        st.session_state.messages.append({
            "role": "assistant", "content": display_content, "display_content": display_content,
            "refused": False, "citations": [],
        })
        st.stop()

    # Day 5, Session 3, Exercise 3 — reject the worst cost-blowout scenario (a
    # user pasting an entire document as a query) before it ever reaches
    # retrieval/generation, and log the attempt.
    rejection = observability.validate_input_length(prompt)
    if rejection:
        observability.log_rejected_input(prompt, rejection)
        with st.chat_message("assistant"):
            st.warning(rejection)
        st.session_state.messages.append({
            "role": "assistant", "content": rejection, "display_content": rejection,
            "refused": False, "citations": [],
        })
        st.stop()

    raw_history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]

    # Exercise 2 — fold anything older than the last 10 turns into a running
    # summary instead of sending (or silently dropping) unbounded history.
    tokens_before = count_tokens(raw_history)
    summary, summarized_turns, verbatim_history = maybe_summarize(
        raw_history, st.session_state.history_summary, st.session_state.summarized_turns
    )
    st.session_state.history_summary = summary
    st.session_state.summarized_turns = summarized_turns
    tokens_after = count_tokens(verbatim_history) + (count_tokens([{"content": summary}]) if summary else 0)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                result = answer_question(
                    prompt,
                    history=verbatim_history,
                    top_k=config.DEFAULT_TOP_K,
                    section=section_filter,
                    profile=st.session_state.profile,
                    history_summary=summary,
                )
        except Exception:
            display_content = "⚠️ The assistant is temporarily unavailable. Please try again in a moment."
            st.warning(display_content)
            st.session_state.messages.append({
                "role": "assistant", "content": display_content, "display_content": display_content,
                "refused": False, "citations": [],
            })
            st.stop()

        display_content = result["answer"]
        if result["refused"]:
            st.badge("Not covered", icon="ℹ️", color="gray")
            display_content = display_content[len(REFUSAL_PREFIX):].strip()
        st.markdown(display_content)
        _render_photos(display_content)

        citations = _dedupe_citations(result["retrieved_chunks"])
        if citations:
            _render_citations(citations, display_content)

        # Day 5, Session 3, Exercise 3 — surface any breached thresholds
        # (latency, cost, rolling error rate) right in the chat area.
        for alert in result.get("alerts", []):
            st.warning(alert)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "display_content": display_content,
        "refused": result["refused"],
        "citations": citations,
    })

    # Exercise 3 — pull any new facts out of this turn and persist them.
    if st.session_state.user_id.strip():
        current_branch = (st.session_state.profile or {}).get("branch_interest")
        updates = extract_updates(
            prompt, display_content, [c.section for c in result["retrieved_chunks"]], current_branch=current_branch
        )
        if updates:
            st.session_state.profile = memory_store.save_profile(st.session_state.user_id, updates)

# ---------------------------------------------------- session stats sidebar --
# Day 5, Session 3, Exercise 2 — rendered after query processing (not in the
# earlier `with st.sidebar:` block) so it reflects this rerun's just-completed
# query, not the stale snapshot captured before it. Deltas compare against
# `stats_before`, the snapshot taken at the top of this script run.
_stats_now = observability.session_stats()
with st.sidebar:
    st.divider()
    st.markdown("###### 📊 Session stats")
    row1 = st.columns(2)
    row1[0].metric(
        "Queries", _stats_now["total_queries"],
        delta=_stats_now["total_queries"] - stats_before["total_queries"] or None,
    )
    row1[1].metric(
        "Errors", _stats_now["error_count"],
        delta=(_stats_now["error_count"] - stats_before["error_count"]) or None,
        delta_color="inverse",
    )
    row2 = st.columns(2)
    row2[0].metric(
        "Avg latency", f"{_stats_now['avg_latency']:.2f}s",
        delta=f"{_stats_now['avg_latency'] - stats_before['avg_latency']:.2f}s" if stats_before["total_queries"] else None,
        delta_color="inverse",
    )
    row2[1].metric(
        "P95 latency", f"{_stats_now['p95_latency']:.2f}s",
        delta=f"{_stats_now['p95_latency'] - stats_before['p95_latency']:.2f}s" if stats_before["total_queries"] else None,
        delta_color="inverse",
    )
    row3 = st.columns(2)
    row3[0].metric(
        "Total cost", f"${_stats_now['total_cost']:.4f}",
        delta=f"${_stats_now['total_cost'] - stats_before['total_cost']:.4f}" if stats_before["total_queries"] else None,
        delta_color="inverse",
    )
    row3[1].metric(
        "Total tokens", f"{_stats_now['total_tokens']:,}",
        delta=(_stats_now["total_tokens"] - stats_before["total_tokens"]) or None,
    )

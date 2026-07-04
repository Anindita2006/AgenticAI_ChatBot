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
import theme
from facilities import facilities_mentioned
from generation import REFUSAL_PREFIX
from people import people_mentioned
from pipeline import answer_question
from retriever import get_index_stats, list_sections
from sources import GOOGLE_MAPS_URL, location_mentioned, resolve_source_url

LOGO_PATH = Path(__file__).resolve().parent.parent / "data" / "images" / "bvrith_logo.jpg"

if "messages" not in st.session_state:
    st.session_state.messages = []


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
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ------------------------------------------------------------- main chat --
theme.brand_hero(LOGO_PATH, "Your AI assistant for everything BVRITH")

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

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt, "display_content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = answer_question(prompt, history=history, top_k=config.DEFAULT_TOP_K, section=section_filter)

        display_content = result["answer"]
        if result["refused"]:
            st.badge("Not covered", icon="ℹ️", color="gray")
            display_content = display_content[len(REFUSAL_PREFIX):].strip()
        st.markdown(display_content)
        _render_photos(display_content)

        citations = _dedupe_citations(result["retrieved_chunks"])
        if citations:
            _render_citations(citations, display_content)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "display_content": display_content,
        "refused": result["refused"],
        "citations": citations,
    })

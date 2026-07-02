"""Phase 4 — Chat UI.

Streamlit chat interface for the BVRIT Hyderabad FAQ chatbot: sidebar shows
knowledge-base status and retrieval settings, main area is a cited chat with
a REFUSED badge on out-of-scope answers and per-query latency/token stats.

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
from generation import REFUSAL_PREFIX
from pipeline import answer_question
from retriever import get_index_stats, list_sections

if "messages" not in st.session_state:
    st.session_state.messages = []


def _dedupe_citations(chunks):
    seen = set()
    citations = []
    for c in chunks:
        key = (c.section, c.page)
        if key not in seen:
            seen.add(key)
            citations.append({"section": c.section, "page": c.page})
    return citations


# ---------------------------------------------------------------- sidebar --
with st.sidebar:
    st.title("🎓 BVRIT Hyderabad")
    st.caption("RAG-powered College Information Assistant")

    st.subheader("Knowledge Base")
    try:
        stats = get_index_stats()
        st.badge(f"{config.KB_SOURCE_NAME}", icon="📄", color="green")
        col1, col2 = st.columns(2)
        col1.metric("Chunks indexed", stats["chunk_count"])
        with col2:
            st.markdown("<div style='margin-top:0.9rem'></div>", unsafe_allow_html=True)
            theme.pulse_dot("LIVE")
    except Exception:
        stats = None
        st.badge("Not indexed", icon="⚠️", color="red")
        st.caption("Run `python src/ingest.py` first to build the index.")

    st.subheader("Retrieval Settings")
    if stats and stats["chunk_size"]:
        st.caption(f"Indexed with chunk_size={stats['chunk_size']}, overlap={stats['chunk_overlap']}")
    top_k = st.slider("Top-K results", min_value=1, max_value=10, value=config.DEFAULT_TOP_K)

    section_options = ["All Sections"] + (list_sections() if stats else [])
    section_choice = st.selectbox("Section filter", section_options)
    section_filter = None if section_choice == "All Sections" else section_choice

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.session_state.messages:
        last = st.session_state.messages[-1]
        if last["role"] == "assistant":
            st.subheader("Last Query")
            chips = [f"⏱ {last['stats']['latency']:.2f}s", f"🧩 {last['stats']['chunk_count']} chunks"]
            if last["stats"]["tokens_in"] is not None:
                chips.append(f"🔤 {last['stats']['tokens_in']}/{last['stats']['tokens_out']} tok")
            theme.chip_row(chips)

# ------------------------------------------------------------- main chat --
theme.hero("💬", "Chat with BVRIT Knowledge Base", "RAG-powered · Cited answers · Refuses gracefully when information isn't in the knowledge base")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("refused"):
            st.badge("REFUSED", icon="🚫", color="red")
        st.markdown(msg["display_content"])
        if msg.get("citations"):
            with st.expander(f"📚 Sources ({len(msg['citations'])})", expanded=False):
                theme.chip_row([f"📄 {c['section']}, Page {c['page']}" for c in msg["citations"]])
        if msg.get("stats"):
            s = msg["stats"]
            chips = [f"⏱ {s['latency']:.2f}s", f"🧩 {s['chunk_count']} chunks"]
            if s["tokens_in"] is not None:
                chips.append(f"🔤 {s['tokens_in']}/{s['tokens_out']} tok")
            theme.chip_row(chips)

prompt = st.chat_input("Ask a question about BVRIT Hyderabad...")

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
            result = answer_question(prompt, history=history, top_k=top_k, section=section_filter)

        display_content = result["answer"]
        if result["refused"]:
            st.badge("REFUSED", icon="🚫", color="red")
            display_content = display_content[len(REFUSAL_PREFIX):].strip()
        st.markdown(display_content)

        citations = _dedupe_citations(result["retrieved_chunks"])
        if citations:
            with st.expander(f"📚 Sources ({len(citations)})", expanded=False):
                theme.chip_row([f"📄 {c['section']}, Page {c['page']}" for c in citations])

        stats = {
            "latency": result["latency"],
            "chunk_count": len(result["retrieved_chunks"]),
            "tokens_in": result["tokens_in"],
            "tokens_out": result["tokens_out"],
        }
        chips = [f"⏱ {stats['latency']:.2f}s", f"🧩 {stats['chunk_count']} chunks"]
        if stats["tokens_in"] is not None:
            chips.append(f"🔤 {stats['tokens_in']}/{stats['tokens_out']} tok")
        theme.chip_row(chips)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "display_content": display_content,
        "refused": result["refused"],
        "citations": citations,
        "stats": stats,
    })

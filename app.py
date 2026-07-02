"""Phase 4 — Chat UI.

Streamlit chat interface for the BVRIT Hyderabad FAQ chatbot: sidebar shows
knowledge-base status and retrieval settings, main area is a cited chat with
a REFUSED badge on out-of-scope answers and per-query latency/token stats.

Run with: streamlit run app.py
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

import streamlit as st

import config
from generation import REFUSAL_PREFIX
from pipeline import answer_question
from retriever import get_index_stats, list_sections

st.set_page_config(page_title="BVRIT Hyderabad FAQ Chatbot", page_icon="🎓", layout="wide")

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
        col2.badge("LIVE", icon="🟢", color="green")
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
            st.caption(f"Latency: {last['stats']['latency']:.2f}s")
            st.caption(f"Chunks retrieved: {last['stats']['chunk_count']}")
            if last["stats"]["tokens_in"] is not None:
                st.caption(f"Tokens (in/out): {last['stats']['tokens_in']} / {last['stats']['tokens_out']}")

# ------------------------------------------------------------- main chat --
st.header("💬 Chat with BVRIT Knowledge Base")
st.caption("RAG-powered · Cited answers · Refuses gracefully when information isn't in the knowledge base")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("refused"):
            st.badge("REFUSED", icon="🚫", color="red")
        st.markdown(msg["display_content"])
        if msg.get("citations"):
            with st.expander(f"📚 Sources ({len(msg['citations'])})", expanded=False):
                for c in msg["citations"]:
                    st.caption(f"📄 {c['section']}, Page {c['page']}")
        if msg.get("stats"):
            s = msg["stats"]
            line = f"⏱ {s['latency']:.2f}s · {s['chunk_count']} chunks"
            if s["tokens_in"] is not None:
                line += f" · tokens {s['tokens_in']}/{s['tokens_out']}"
            st.caption(line)

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
                for c in citations:
                    st.caption(f"📄 {c['section']}, Page {c['page']}")

        stats = {
            "latency": result["latency"],
            "chunk_count": len(result["retrieved_chunks"]),
            "tokens_in": result["tokens_in"],
            "tokens_out": result["tokens_out"],
        }
        line = f"⏱ {stats['latency']:.2f}s · {stats['chunk_count']} chunks"
        if stats["tokens_in"] is not None:
            line += f" · tokens {stats['tokens_in']}/{stats['tokens_out']}"
        st.caption(line)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "display_content": display_content,
        "refused": result["refused"],
        "citations": citations,
        "stats": stats,
    })

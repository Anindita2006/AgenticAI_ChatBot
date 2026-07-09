
"""Entry point.

Sets page config and the shared theme once, then hands off to st.navigation
so the sidebar shows clean, explicitly-titled nav labels ("Chat",
"Evaluation Dashboard") instead of ones derived from filenames.

Run with: streamlit run app.py
"""


import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

import streamlit as st

import theme

LOGO_PATH = Path(__file__).resolve().parent / "data" / "images" / "bvrith_logo.jpg"

st.set_page_config(page_title="BVRITH FAQ Chatbot", page_icon=str(LOGO_PATH), layout="wide")
theme.inject_global_css()

pages = [
    st.Page("pages/0_Chat.py", title="Chat", icon="💬", default=True),
    st.Page("pages/1_Evaluation_Dashboard.py", title="Evaluation Dashboard", icon="📊"),
]
st.navigation(pages).run()

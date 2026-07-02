"""Shared visual theme for the Streamlit app: one CSS injection plus a handful
of small HTML-snippet helpers (hero banner, chips, progress bars).

Presentation only — nothing here touches session state, retrieval, or
generation. app.py calls inject_global_css() once, before st.navigation
dispatches to a page.

No custom [theme] is set in .streamlit/config.toml on purpose — that's what
controls Streamlit's native Light/Dark/"Use system setting" switcher in the
Settings menu, and any [theme] override there replaces it with a differently
labeled "Custom Theme" switcher. Leaving it unset keeps the native toggle
exactly as Streamlit ships it.

Custom decoration here instead reads Streamlit's own resolved theme via
st.context.theme.type ("light"/"dark", following whichever the user has
actually picked — system, light, or dark) and renders the matching CSS
variable block server-side, so the accent colors track the native toggle.
"""

import html

import streamlit as st

# Status palette — fixed, reserved meaning, identical hex in both modes
# (see dataviz skill references/palette.md).
GOOD = "#0ca30c"
WARNING = "#fab219"
CRITICAL = "#d03b3b"
MUTED = "#898781"

_LIGHT = {
    "secondary_ink": "#52514e",
    "gridline": "#e1e0d9",
    "surface": "#fcfcfb",
    "ink_primary": "#0b0b0b",
    "violet": "#4a3aa7",
    "blue": "#2a78d6",
    "magenta": "#e87ba4",
    "card_bg": "rgba(11,11,11,0.035)",
    "card_bg_hover": "rgba(11,11,11,0.06)",
    "border": "rgba(11,11,11,0.10)",
    "glow_a": "rgba(74,58,167,0.10)",
    "glow_b": "rgba(42,120,214,0.08)",
}
_DARK = {
    "secondary_ink": "#c3c2b7",
    "gridline": "#2c2c2a",
    "surface": "#1a1a19",
    "ink_primary": "#ffffff",
    "violet": "#9085e9",
    "blue": "#3987e5",
    "magenta": "#d55181",
    "card_bg": "rgba(255,255,255,0.045)",
    "card_bg_hover": "rgba(255,255,255,0.075)",
    "border": "rgba(255,255,255,0.10)",
    "glow_a": "rgba(144,133,233,0.18)",
    "glow_b": "rgba(57,135,229,0.13)",
}


def _active() -> dict:
    theme_type = getattr(st.context.theme, "type", None)
    return _DARK if theme_type == "dark" else _LIGHT


def chart_colors() -> dict:
    """Hex set for Altair charts, matched to the app's active theme."""
    return _active()


def _vars_block() -> str:
    c = _active()
    return f"""<style>
:root {{
  --gh-violet: {c['violet']};
  --gh-blue: {c['blue']};
  --gh-magenta: {c['magenta']};
  --gh-good: {GOOD};
  --gh-warning: {WARNING};
  --gh-critical: {CRITICAL};
  --gh-surface: {c['card_bg']};
  --gh-surface-hover: {c['card_bg_hover']};
  --gh-border: {c['border']};
  --gh-ink-1: {c['ink_primary']};
  --gh-ink-2: {c['secondary_ink']};
  --gh-ink-3: {MUTED};
  --gh-glow-a: {c['glow_a']};
  --gh-glow-b: {c['glow_b']};
}}
</style>"""


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', system-ui, -apple-system, "Segoe UI", sans-serif; }

/* ---------------------------------------------------------------- page bg */
.stApp {
  background:
    radial-gradient(ellipse 900px 500px at 12% -10%, var(--gh-glow-a), transparent 60%),
    radial-gradient(ellipse 800px 500px at 100% 0%, var(--gh-glow-b), transparent 55%);
}
[data-testid="stHeader"] { background: transparent; }

/* ------------------------------------------------------------------ hero */
.gh-hero {
  padding: 1.35rem 1.6rem;
  border-radius: 18px;
  margin-bottom: 1.2rem;
  background: linear-gradient(135deg, var(--gh-glow-a), var(--gh-glow-b));
  border: 1px solid var(--gh-border);
  box-shadow: 0 8px 30px rgba(0,0,0,0.12);
  animation: gh-fade-up 0.5s ease both;
}
.gh-hero-title {
  font-size: 1.7rem;
  font-weight: 800;
  margin: 0 0 0.15rem 0;
  background: linear-gradient(90deg, var(--gh-violet) 0%, var(--gh-magenta) 50%, var(--gh-blue) 100%);
  background-size: 200% auto;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: gh-shimmer 6s linear infinite;
}
.gh-hero-sub { color: var(--gh-ink-2); font-size: 0.94rem; margin: 0; }

@keyframes gh-shimmer { to { background-position: 200% center; } }
@keyframes gh-fade-up { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

/* --------------------------------------------------------------- sidebar */
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
  font-weight: 700;
}

/* ------------------------------------------------------------- gh-* kit */
.gh-card {
  background: var(--gh-surface);
  border: 1px solid var(--gh-border);
  border-radius: 14px;
  padding: 0.9rem 1rem;
  transition: background 0.2s ease, transform 0.2s ease;
  animation: gh-fade-up 0.4s ease both;
}
.gh-card:hover { background: var(--gh-surface-hover); transform: translateY(-1px); }

.gh-kpi-row { display: flex; gap: 0.7rem; flex-wrap: wrap; margin-bottom: 0.4rem; }
.gh-kpi {
  flex: 1 1 140px;
  background: var(--gh-surface);
  border: 1px solid var(--gh-border);
  border-left: 3px solid var(--gh-accent, var(--gh-violet));
  border-radius: 12px;
  padding: 0.75rem 1rem;
  animation: gh-fade-up 0.45s ease both;
}
.gh-kpi-label { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--gh-ink-3); margin-bottom: 0.2rem; }
.gh-kpi-value { font-size: 1.65rem; font-weight: 800; color: var(--gh-ink-1); line-height: 1.1; }

.gh-chip-row { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.gh-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: var(--gh-surface);
  border: 1px solid var(--gh-border);
  border-radius: 999px;
  padding: 0.22rem 0.7rem;
  font-size: 0.82rem;
  color: var(--gh-ink-2);
}

.gh-progress-track {
  width: 100%; height: 7px; border-radius: 999px;
  background: rgba(128,128,128,0.18);
  overflow: hidden;
  margin-top: 0.5rem;
}
.gh-progress-fill { height: 100%; border-radius: 999px; transition: width 0.6s ease; }

.gh-pulse-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  background: var(--gh-good);
  animation: gh-pulse 1.8s infinite;
}
@keyframes gh-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(12,163,12,0.55); }
  70%  { box-shadow: 0 0 0 8px rgba(12,163,12,0); }
  100% { box-shadow: 0 0 0 0 rgba(12,163,12,0); }
}

/* --------------------------------------------------------------- widgets */
[data-testid="stMetric"] {
  background: var(--gh-surface);
  border: 1px solid var(--gh-border);
  border-radius: 14px;
  padding: 0.8rem 1rem;
}
[data-testid="stExpander"] {
  border: 1px solid var(--gh-border) !important;
  border-radius: 14px !important;
  background: var(--gh-surface);
  overflow: hidden;
}
[data-testid="stExpander"] summary { font-weight: 600; }

.stButton > button {
  border-radius: 10px !important;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px var(--gh-glow-a);
}

/* Recolor a couple of native accent touchpoints to match the brand gradient
   without configuring a fixed [theme] in config.toml (that's what hides the
   native Light/Dark/system switcher). */
[data-testid="stSlider"] [role="slider"] {
  background-color: var(--gh-violet) !important;
  border-color: var(--gh-violet) !important;
}
[data-testid="stSlider"] div[data-baseweb="slider"] > div:nth-of-type(2) > div {
  background-color: var(--gh-violet) !important;
}
::selection { background: var(--gh-glow-a); }

hr, [data-testid="stDivider"] {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gh-border), transparent);
}

/* ---------------------------------------------------------- chat bubbles */
[data-testid="stChatMessage"] {
  border-radius: 16px;
  border: 1px solid var(--gh-border);
  padding: 0.35rem 0.15rem;
  margin-bottom: 0.55rem;
  animation: gh-fade-up 0.35s ease both;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: linear-gradient(135deg, var(--gh-glow-b), transparent);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
  background: linear-gradient(135deg, var(--gh-glow-a), transparent);
}
[data-testid="stChatInput"] {
  border-radius: 16px !important;
}

/* --------------------------------------------------------------- badges */
[data-testid="stBadge"] {
  border-radius: 999px !important;
  font-weight: 600 !important;
}

/* ------------------------------------------------------------ scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, var(--gh-violet), var(--gh-blue));
  border-radius: 999px;
}
</style>
"""


def inject_global_css() -> None:
    st.markdown(_vars_block(), unsafe_allow_html=True)
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""<div class="gh-hero">
            <p class="gh-hero-title">{html.escape(icon)} {html.escape(title)}</p>
            <p class="gh-hero-sub">{html.escape(subtitle)}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def pulse_dot(label: str) -> None:
    st.markdown(
        f"""<span class="gh-pulse-dot"></span>&nbsp;<span style="color:var(--gh-ink-2);font-size:0.85rem;">{html.escape(label)}</span>""",
        unsafe_allow_html=True,
    )


def chip_row(items: list[str]) -> None:
    chips = "".join(f'<span class="gh-chip">{html.escape(item)}</span>' for item in items)
    st.markdown(f'<div class="gh-chip-row">{chips}</div>', unsafe_allow_html=True)


def kpi_row(items: list[tuple[str, str, str]]) -> None:
    """items: list of (label, value, accent_hex)."""
    cards = "".join(
        f"""<div class="gh-kpi" style="--gh-accent:{accent}">
                <div class="gh-kpi-label">{html.escape(label)}</div>
                <div class="gh-kpi-value">{html.escape(str(value))}</div>
            </div>"""
        for label, value, accent in items
    )
    st.markdown(f'<div class="gh-kpi-row">{cards}</div>', unsafe_allow_html=True)


def progress_bar(fraction: float, color: str) -> None:
    pct = max(0.0, min(1.0, fraction)) * 100
    st.markdown(
        f"""<div class="gh-progress-track">
                <div class="gh-progress-fill" style="width:{pct:.1f}%; background:{color};"></div>
            </div>""",
        unsafe_allow_html=True,
    )

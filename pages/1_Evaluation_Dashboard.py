"""Phase 5 dashboard — renders eval/report.json (produced by eval/report.py):
summary stats, per-dimension pass/fail cards, failed-test drill-downs, and
RAGAS metric bars with a diagnosis. Read-only view; run the eval/*.py scripts
to regenerate the underlying report.

Page config and theme injection live in app.py (the st.navigation entry
point), which runs before this page is dispatched.
"""

import json
import statistics
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import config
import observability
import theme

REPORT_PATH = PROJECT_ROOT / "eval" / "report.json"

# Status palette (fixed, reserved meaning, same hex in both modes — see
# dataviz skill's palette.md). Everything else that differs between light
# and dark comes from theme.chart_colors(), matched to the active theme.
GOOD = theme.GOOD
WARNING = theme.WARNING
CRITICAL = theme.CRITICAL
MUTED = theme.MUTED
CC = theme.chart_colors()
SECONDARY_INK = CC["secondary_ink"]
GRIDLINE = CC["gridline"]
CHART_SURFACE = CC["surface"]
VIOLET = CC["violet"]
BLUE = CC["blue"]
INK_PRIMARY = CC["ink_primary"]


def badge_color(passed: int, total: int) -> str:
    if total == 0:
        return "gray"
    if passed == total:
        return "green"
    if passed == 0:
        return "red"
    return "orange"


def status_hex(score: float) -> str:
    if score >= 0.7:
        return GOOD
    if score >= 0.5:
        return WARNING
    return CRITICAL


theme.hero(
    "📊", "Evaluation Dashboard",
    "Live scoring of every real question asked in Chat, plus the curated 8-dimension batch suite",
)

# ============================================================= LIVE SECTION =
header_col, refresh_col = st.columns([5, 1])
header_col.subheader("🔴 Live Chat Evaluation")
if refresh_col.button("🔄 Refresh", use_container_width=True):
    st.rerun()
st.caption(
    "Every question asked on the Chat page is scored in the background by a separate judge model "
    "(groundedness + relevance) and logged here — this updates as real usage happens, independent of "
    "the batch suite below."
)

live_history = observability.get_live_eval_history()

if not live_history:
    st.info("No live chat questions scored yet — ask something on the **Chat** page, then come back here.", icon="💬")
else:
    scored = [e for e in live_history if e.get("verdict") in ("pass", "fail")]
    errored = [e for e in live_history if e.get("verdict") == "error"]

    rag_count = sum(1 for e in live_history if e.get("rag_used"))
    tool_count = sum(1 for e in live_history if e.get("tools_used"))
    refused_count = sum(1 for e in live_history if e.get("refused"))
    live_pass_rate = (sum(1 for e in scored if e["verdict"] == "pass") / len(scored)) if scored else 0.0
    avg_grounded = statistics.fmean(e["groundedness"] for e in scored) if scored else 0.0
    avg_relevance = statistics.fmean(e["relevance"] for e in scored) if scored else 0.0

    theme.kpi_row([
        ("Live questions", len(live_history), VIOLET),
        ("Live pass rate", f"{live_pass_rate*100:.0f}%", status_hex(live_pass_rate)),
        ("RAG used", f"{rag_count}/{len(live_history)}", BLUE),
        ("Avg groundedness", f"{avg_grounded:.2f}", status_hex(avg_grounded)),
        ("Avg relevance", f"{avg_relevance:.2f}", status_hex(avg_relevance)),
    ])
    theme.chip_row([
        f"🔎 RAG retrieval used: {rag_count}/{len(live_history)}",
        f"🧮 Tool called: {tool_count}/{len(live_history)}",
        f"🚫 Refused: {refused_count}/{len(live_history)}",
    ] + ([f"⚠️ Scoring errors: {len(errored)}"] if errored else []))

    if len(scored) >= 2:
        trend_df = pd.DataFrame([
            {"n": i + 1, "metric": "Groundedness", "score": e["groundedness"], "question": e["query"][:60]}
            for i, e in enumerate(scored)
        ] + [
            {"n": i + 1, "metric": "Relevance", "score": e["relevance"], "question": e["query"][:60]}
            for i, e in enumerate(scored)
        ])
        trend_hover = alt.selection_point(fields=["n", "metric"], on="pointerover", nearest=True, empty=False)
        trend_line = alt.Chart(trend_df).mark_line(point=True, strokeWidth=2).encode(
            x=alt.X("n:Q", title="Question # (chronological)", axis=alt.Axis(gridColor=GRIDLINE, tickMinStep=1)),
            y=alt.Y("score:Q", title="Score", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".0%", gridColor=GRIDLINE)),
            color=alt.Color("metric:N", scale=alt.Scale(domain=["Groundedness", "Relevance"], range=[VIOLET, BLUE]), title=None),
            opacity=alt.condition(trend_hover, alt.value(1.0), alt.value(0.75)),
            tooltip=[alt.Tooltip("question:N", title="Question"), alt.Tooltip("metric:N"), alt.Tooltip("score:Q", format=".2f")],
        ).add_params(trend_hover)
        trend_threshold = alt.Chart(pd.DataFrame({"y": [0.7]})).mark_rule(
            color=MUTED, strokeDash=[4, 3], strokeWidth=1.5
        ).encode(y="y:Q")
        trend_chart = (
            (trend_line + trend_threshold)
            .properties(height=220, background="transparent")
            .configure_axis(labelColor=SECONDARY_INK, titleColor=SECONDARY_INK, domainColor=GRIDLINE, tickColor=GRIDLINE)
            .configure_view(strokeWidth=0)
            .configure_legend(labelColor=SECONDARY_INK, titleColor=SECONDARY_INK)
        )
        st.altair_chart(trend_chart, use_container_width=True)
        st.caption("Dashed line = 0.7 pass threshold · hover a point for the question")

    st.markdown("**Recent questions** (most recent first)")
    recent = list(reversed(live_history))[:25]
    live_filter = st.segmented_control(
        "Filter", options=["All", "Pass", "Fail", "Refused"], default="All", label_visibility="collapsed", key="live_filter",
    ) or "All"
    for e in recent:
        if live_filter == "Pass" and e.get("verdict") != "pass":
            continue
        if live_filter == "Fail" and e.get("verdict") != "fail":
            continue
        if live_filter == "Refused" and not e.get("refused"):
            continue
        icon = {"pass": "✅", "fail": "❌", "error": "⚠️"}.get(e.get("verdict"), "❔")
        ts = e.get("timestamp", "")[:19].replace("T", " ")
        with st.expander(f"{icon} {ts} — {e['query'] or '(empty input)'}"):
            st.markdown(f"**Answer:** {e['answer']}")
            flag_bits = [
                f"RAG used: {'yes (' + str(e.get('num_chunks', 0)) + ' chunks)' if e.get('rag_used') else 'no'}",
                f"Sections: {', '.join(e.get('sections_used') or []) or '—'}",
                f"Tools called: {', '.join(e.get('tools_used') or []) or 'none'}",
                f"Refused: {'yes' if e.get('refused') else 'no'}",
                f"Latency: {e.get('latency', 0):.2f}s",
                f"Prompt variant: {e.get('prompt_variant', '—')}",
            ]
            st.caption(" · ".join(flag_bits))
            if e.get("verdict") == "error":
                st.warning(f"Scoring failed: {e.get('reason')}", icon="⚠️")
            else:
                st.markdown(
                    f"**Groundedness:** {e.get('groundedness'):.2f} · **Relevance:** {e.get('relevance'):.2f} "
                    f"· **Verdict:** {e.get('verdict')}"
                )
                if e.get("reason"):
                    st.caption(f"Judge reason: {e['reason']}")

st.divider()

# ============================================================ BATCH SECTION =
if not REPORT_PATH.exists():
    st.subheader("📋 Batch Eval Suite (8-Dimension Report)")
    st.warning(
        "No batch evaluation report found yet. Generate one by running, in order:\n\n"
        "```\n"
        "python eval/generate_test_cases.py\n"
        "python eval/run_tests.py\n"
        "python eval/judge.py\n"
        "python eval/ragas_eval.py\n"
        "python eval/report.py\n"
        "```"
    )
    st.stop()

report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

theme.hero(
    "📋", "Eight-Dimension Evaluation Report (Batch Suite)",
    "Test cases generated by an LLM · executed against the live chatbot · judged by a separate model",
)

# ------------------------------------------------------------- summary row --
s = report["summary"]
rate_color = status_hex(s["pass_rate"])

col_kpi, col_donut = st.columns([3, 1])
with col_kpi:
    theme.kpi_row([
        ("Total test cases", s["total"], VIOLET),
        ("Passed", s["passed"], GOOD),
        ("Failed", s["failed"], CRITICAL if s["failed"] else MUTED),
        ("Pass rate", f"{s['pass_rate']*100:.0f}%", rate_color),
    ])
    weakest = report["weakest_dimension"]
    st.warning(
        f"**Weakest dimension: {weakest['name']} ({weakest['code']})** — {report['recommended_fix']}",
        icon="⚠️",
    )
with col_donut:
    donut_df = pd.DataFrame({"category": ["Passed", "Remaining"], "value": [s["pass_rate"], 1 - s["pass_rate"]]})
    arc = alt.Chart(donut_df).mark_arc(
        innerRadius=52, outerRadius=72, cornerRadius=3, stroke=CHART_SURFACE, strokeWidth=2,
    ).encode(
        theta=alt.Theta("value:Q", stack=True),
        order=alt.Order("value:Q", sort="descending"),
        color=alt.Color(
            "category:N",
            scale=alt.Scale(domain=["Passed", "Remaining"], range=[rate_color, GRIDLINE]),
            legend=None,
        ),
        tooltip=[alt.Tooltip("category:N", title="Segment"), alt.Tooltip("value:Q", title="Share", format=".0%")],
    )
    center_label = pd.DataFrame({"label": [f"{s['pass_rate']*100:.0f}%"]})
    center = alt.Chart(center_label).mark_text(fontSize=22, fontWeight="bold", color=INK_PRIMARY).encode(text="label:N")
    donut = (arc + center).properties(width=170, height=170, background="transparent").configure_view(strokeWidth=0)
    st.altair_chart(donut, use_container_width=True)
    st.caption("Overall pass rate")

st.divider()

# --------------------------------------------------------- dimension cards --
head_col, filter_col = st.columns([3, 2])
head_col.subheader("Per-Dimension Breakdown")
case_filter = filter_col.segmented_control(
    "Show cases", options=["All", "Passed", "Failed"], default="All", label_visibility="collapsed",
)
case_filter = case_filter or "All"

dims = report["dimensions"]
for row_start in (0, 4):
    cols = st.columns(4)
    for col, dim in zip(cols, dims[row_start:row_start + 4]):
        with col.container(border=True):
            st.markdown(f"**{dim['code']} {dim['name']}**")
            st.badge(f"{dim['passed']}/{dim['total']} passed", color=badge_color(dim["passed"], dim["total"]))
            frac = dim["passed"] / dim["total"] if dim["total"] else 0.0
            bar_color = GOOD if frac == 1 else (CRITICAL if frac == 0 else WARNING)
            theme.progress_bar(frac, bar_color)
            shown = [
                c for c in dim["cases"]
                if case_filter == "All"
                or (case_filter == "Passed" and c["verdict"] == "pass")
                or (case_filter == "Failed" and c["verdict"] == "fail")
            ]
            if not shown:
                st.caption("_No cases match this filter._")
            for case in shown:
                icon = "✅" if case["verdict"] == "pass" else "❌"
                preview = case["question"] if case["question"].strip() else "(empty input)"
                st.caption(f"{icon} {case['id']}: {preview[:45]}{'…' if len(preview) > 45 else ''}")

st.divider()

# ------------------------------------------------------- performance latency --
perf_dim = next((d for d in dims if d["code"] == "06"), None)
if perf_dim and any(c.get("latency") is not None for c in perf_dim["cases"]):
    st.subheader("Performance — Latency by Case")
    lat_df = pd.DataFrame([
        {"id": c["id"], "question": c["question"][:60], "latency": c["latency"],
         "color": GOOD if c["latency"] <= config.PERFORMANCE_SLA_SECONDS else CRITICAL}
        for c in perf_dim["cases"] if c.get("latency") is not None
    ])
    lat_hover = alt.selection_point(fields=["id"], on="pointerover", nearest=True, empty=False)
    lat_bars = alt.Chart(lat_df).mark_bar(cornerRadiusEnd=6, size=22).encode(
        x=alt.X("latency:Q", title="Seconds", axis=alt.Axis(gridColor=GRIDLINE)),
        y=alt.Y("id:N", sort=None, axis=alt.Axis(title=None)),
        color=alt.Color("color:N", scale=None, legend=None),
        opacity=alt.condition(lat_hover, alt.value(1.0), alt.value(0.82)),
        tooltip=[alt.Tooltip("id:N", title="Case"), alt.Tooltip("question:N", title="Question"),
                  alt.Tooltip("latency:Q", title="Latency (s)", format=".2f")],
    ).add_params(lat_hover)
    lat_labels = lat_bars.mark_text(align="left", dx=6, color=SECONDARY_INK, fontWeight="bold").encode(
        text=alt.Text("latency:Q", format=".2f"), opacity=alt.value(1.0),
    )
    lat_threshold = alt.Chart(pd.DataFrame({"x": [config.PERFORMANCE_SLA_SECONDS]})).mark_rule(
        color=MUTED, strokeDash=[4, 3], strokeWidth=1.5
    ).encode(x="x:Q")
    lat_chart = (
        (lat_bars + lat_labels + lat_threshold)
        .properties(height=120, background="transparent")
        .configure_axis(labelColor=SECONDARY_INK, titleColor=SECONDARY_INK, domainColor=GRIDLINE, tickColor=GRIDLINE)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(lat_chart, use_container_width=True)
    st.caption(f"Dashed line = {config.PERFORMANCE_SLA_SECONDS:.0f}s SLA · hover a bar for the question")

    st.divider()

# ----------------------------------------------------------- failed details --
failed_cases = [
    (dim, case)
    for dim in dims
    for case in dim["cases"]
    if case["verdict"] == "fail"
]

st.subheader(f"Failed Test Details ({len(failed_cases)})")
if not failed_cases:
    st.success("No failing test cases in this run.")
else:
    query = st.text_input(
        "Search failed cases", placeholder="Filter by case id, dimension, or question text…",
        label_visibility="collapsed",
    ).strip().lower()
    visible = [
        (dim, case) for dim, case in failed_cases
        if not query or query in case["id"].lower() or query in dim["name"].lower()
        or query in (case["question"] or "").lower()
    ]
    if not visible:
        st.caption("_No failed cases match your search._")
    for dim, case in visible:
        with st.expander(f"❌ {case['id']} — {dim['name']}: {case['question'] or '(empty input)'}"):
            st.markdown(f"**Question:** {case['question'] or '_(empty input)_'}")
            st.markdown(f"**Expected:** {case['expected_answer']}")
            st.markdown(f"**Actual:** {case['actual_answer']}")
            st.markdown(f"**Reason:** {case['reason']}")
            if case.get("suggested_fix"):
                st.info(f"**Suggested fix:** {case['suggested_fix']}", icon="🛠️")

st.divider()

# --------------------------------------------------------------- RAGAS bars --
st.subheader("RAGAS Metrics — Retrieval Pipeline Health")
ragas_scores = report["ragas_scores"]

if ragas_scores:
    df = pd.DataFrame(
        [{"metric": k.replace("_", " ").title(), "score": v, "color": status_hex(v)} for k, v in ragas_scores.items()]
    )

    hover = alt.selection_point(fields=["metric"], on="pointerover", nearest=True, empty=False)

    bars = alt.Chart(df).mark_bar(cornerRadiusEnd=6, size=26).encode(
        x=alt.X("score:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".0%", title=None, gridColor=GRIDLINE)),
        y=alt.Y("metric:N", sort=None, axis=alt.Axis(title=None)),
        color=alt.Color("color:N", scale=None, legend=None),
        opacity=alt.condition(hover, alt.value(1.0), alt.value(0.82)),
        tooltip=[alt.Tooltip("metric:N", title="Metric"), alt.Tooltip("score:Q", title="Score", format=".2f")],
    ).add_params(hover)
    labels = bars.mark_text(align="left", dx=6, color=SECONDARY_INK, fontWeight="bold").encode(
        text=alt.Text("score:Q", format=".2f"), opacity=alt.value(1.0),
    )
    threshold = alt.Chart(pd.DataFrame({"x": [0.7]})).mark_rule(color=MUTED, strokeDash=[4, 3], strokeWidth=1.5).encode(x="x:Q")

    chart = (
        (bars + labels + threshold)
        .properties(height=190, background="transparent")
        .configure_axis(labelColor=SECONDARY_INK, titleColor=SECONDARY_INK, domainColor=GRIDLINE, tickColor=GRIDLINE)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)

    st.caption("Dashed line = 0.7 pass threshold · hover a bar to highlight it")
    st.caption(f"📌 {report['ragas_diagnosis']}")
    with st.expander("View as table"):
        st.dataframe(
            df[["metric", "score"]].style.format({"score": "{:.3f}"}),
            hide_index=True, use_container_width=True,
        )
else:
    st.info("No RAGAS-scored test cases in this report.")

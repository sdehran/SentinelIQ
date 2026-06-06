"""SentinelIQ — Dashboard (Page 1) — Gradient Enterprise Theme.

AI Fraud Transaction Investigation Assistant
Developed by Group 9 || Cohort 1 2025-26
"""

import sys
import os
import json
from pathlib import Path

# ── sys.path fix for imports from project root ──
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ui.styles import inject_styles, page_header
from ui.components.sidebar import render_sidebar
from ui.components.chatbot import render_chatbot

# ── Page Config ──
st.set_page_config(
    page_title="SentinelIQ | AI Fraud Transaction Investigation Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject Theme ──
inject_styles()

# ── Session State Defaults ──
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "config" not in st.session_state:
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            st.session_state["config"] = json.load(f)
    else:
        st.session_state["config"] = {
            "critical_threshold": 85,
            "high_threshold": 70,
            "med_threshold": 40,
            "rag_top_k": 3,
            "retry_attempts": 3,
            "fallback_mode": True,
            "batch_schedule_hour": 18,
        }
if "pattern_store" not in st.session_state:
    from pattern_store import PatternStore
    st.session_state["pattern_store"] = PatternStore(
        filepath=os.path.join(PROJECT_ROOT, "pattern_store.json")
    )

# ── Restore cached workflow results on refresh ──
_CACHE_DIR = os.path.join(PROJECT_ROOT, "data", ".cache")
_CACHE_CSV = os.path.join(_CACHE_DIR, "last_transactions.csv")
_CACHE_RESULTS = os.path.join(_CACHE_DIR, "last_results.pkl")

if "workflow_results" not in st.session_state:
    # Try to restore from disk cache
    try:
        import pickle
        if os.path.exists(_CACHE_RESULTS) and os.path.exists(_CACHE_CSV):
            with open(_CACHE_RESULTS, "rb") as f:
                st.session_state["workflow_results"] = pickle.load(f)
            st.session_state["transactions_df"] = pd.read_csv(
                _CACHE_CSV, parse_dates=["timestamp"]
            )
            results = st.session_state["workflow_results"]
            st.session_state["network_graph"] = results.get("network_graph")
    except Exception:
        pass  # Cache corrupted or incompatible — start fresh

if "approval_status" not in st.session_state:
    # Try to load approval status from disk
    _CACHE_APPROVAL = os.path.join(_CACHE_DIR, "approval_status.json")
    if os.path.exists(_CACHE_APPROVAL):
        try:
            with open(_CACHE_APPROVAL, "r") as f:
                st.session_state["approval_status"] = json.load(f)
        except Exception:
            st.session_state["approval_status"] = {}
    else:
        st.session_state["approval_status"] = {}

# ── Sidebar ──
render_sidebar()

# ── Extract stats ──
crit = high = med = auto = 0
ar = 0.0
total = 0
hconf = lconf = 0
processing_time = "—"

if "workflow_results" in st.session_state:
    results = st.session_state["workflow_results"]
    stats = results.get("summary_stats")
    if stats:
        crit = stats.critical_count
        high = stats.high_count
        med = stats.med_count
        auto = stats.auto_cleared_count
        ar = round(stats.autonomy_rate * 100, 1)
        total = stats.total
        hconf = stats.high_confidence_count
        lconf = stats.low_confidence_count
        processing_time = f"{stats.processing_time_sec:.0f}s"

pattern_count = st.session_state["pattern_store"].count

# ══════════════════════════════════════════════════════════
# 2-COLUMN LAYOUT: LEFT (75%) + RIGHT (25%)
# ══════════════════════════════════════════════════════════
col_left, col_right = st.columns([3, 1], gap="medium")

# ════════════════════════════════
# RIGHT COLUMN — GRADIENT STAT CARDS + INLINE CHATBOT
# ════════════════════════════════
with col_right:
    st.markdown("""
    <div style='font-size:10px;font-weight:700;color:#8892b0;
    text-transform:uppercase;letter-spacing:1px;margin-bottom:10px'>
    ▸ RISK OVERVIEW
    </div>""", unsafe_allow_html=True)

    vcards = [
        ("g-critical", "🚨", "CRITICAL", crit, "Immediate action",
         crit / max(total, 1) * 100),
        ("g-high", "⚠️", "HIGH RISK", high, "Awaiting approval",
         high / max(total, 1) * 100),
        ("g-med", "📋", "MED RISK", med, "Daily batch",
         med / max(total, 1) * 100),
        ("g-low", "✅", "AUTO-CLEARED", auto, "No action needed",
         auto / max(total, 1) * 100),
        ("g-auto", "🤖", "AUTONOMY", f"{ar}%", "Auto-resolved", ar),
    ]
    for cls, icon, label, value, sub, bar_pct in vcards:
        st.markdown(f"""
<div class='g-card {cls}' style='margin-bottom:12px;padding:20px 20px'>
  <div style='display:flex;align-items:center;
  justify-content:space-between;margin-bottom:8px'>
    <div style='font-size:11px;font-weight:700;opacity:0.85;
    text-transform:uppercase;letter-spacing:0.8px'>{label}</div>
    <span style='font-size:22px'>{icon}</span>
  </div>
  <div style='font-family:monospace;font-size:38px;
  font-weight:800;line-height:1;margin-bottom:5px'>{value}</div>
  <div style='font-size:11px;opacity:0.65;margin-bottom:10px'>{sub}</div>
  <div class='mini-bar'>
    <div class='mini-bar-fill' style='width:{min(bar_pct, 100):.0f}%'></div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── INLINE CHATBOT STATUS PANEL ──
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown(f"""
<div style='background:linear-gradient(135deg,#1e2448,#2a3060);
border:1px solid rgba(71,118,230,0.3);border-radius:12px;
padding:14px;position:relative;overflow:hidden'>
  <div style='position:absolute;top:-20px;right:-20px;width:70px;height:70px;
  border-radius:50%;background:rgba(71,118,230,0.06)'></div>
  <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px'>
    <div style='width:38px;height:38px;
    background:linear-gradient(135deg,#4776e6,#8e54e9);
    border-radius:12px;display:flex;align-items:center;
    justify-content:center;font-size:20px;
    box-shadow:0 4px 12px rgba(71,118,230,0.5)'>🤖</div>
    <div>
      <div style='color:#e8eaf6;font-weight:700;font-size:13px'>
      SentinelIQ Assistant</div>
      <div style='display:flex;align-items:center;gap:4px'>
        <div style='width:6px;height:6px;background:#38ef7d;
        border-radius:50%;box-shadow:0 0 6px #38ef7d'></div>
        <span style='color:#38ef7d;font-size:10px;font-weight:600'>Online</span>
      </div>
    </div>
  </div>
  <div style='background:rgba(30,36,72,0.8);border:1px solid #2e3a6e;
  border-radius:8px;padding:10px 12px;margin-bottom:10px'>
    <div style='font-size:11px;color:#8892b0;margin-bottom:6px'>Today&apos;s status:</div>
    <div style='display:flex;flex-direction:column;gap:4px;font-size:11px'>
      <div style='display:flex;justify-content:space-between'>
        <span style='color:#ff416c;font-weight:700'>🚨 {crit} CRITICAL</span>
        <span style='color:#8892b0;font-size:10px'>review now</span>
      </div>
      <div style='display:flex;justify-content:space-between'>
        <span style='color:#f7971e;font-weight:600'>⚠️ {high} HIGH</span>
        <span style='color:#8892b0;font-size:10px'>awaiting</span>
      </div>
      <div style='display:flex;justify-content:space-between'>
        <span style='color:#8e54e9;font-weight:600'>🤖 {ar}% auto</span>
        <span style='color:#8892b0;font-size:10px'>resolved</span>
      </div>
    </div>
  </div>
  <div style='display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px'>
    <span style='background:#2e3a6e;color:#8892b0;font-size:9px;
    padding:3px 8px;border-radius:10px;cursor:pointer'>🚨 CRITICAL list</span>
    <span style='background:#2e3a6e;color:#8892b0;font-size:9px;
    padding:3px 8px;border-radius:10px;cursor:pointer'>🤖 Autonomy</span>
    <span style='background:#2e3a6e;color:#8892b0;font-size:9px;
    padding:3px 8px;border-radius:10px;cursor:pointer'>🏦 Banks</span>
    <span style='background:#2e3a6e;color:#8892b0;font-size:9px;
    padding:3px 8px;border-radius:10px;cursor:pointer'>❓ Help</span>
  </div>
  <div style='display:flex;gap:6px'>
    <input type='text' placeholder='Ask about your data...'
    style='flex:1;background:#1a2050;border:1px solid #2e3a6e;
    border-radius:6px;padding:7px 10px;color:#e8eaf6;
    font-size:11px;outline:none'/>
    <div style='background:linear-gradient(135deg,#4776e6,#8e54e9);
    border-radius:6px;padding:7px 12px;font-size:14px;
    cursor:pointer;display:flex;align-items:center'>→</div>
  </div>
  <div style='font-size:9px;color:#4a5580;text-align:center;margin-top:8px'>
  Use NL Query page for full AI-powered queries</div>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════
# LEFT COLUMN — MAIN CONTENT
# ════════════════════════════════
with col_left:

    # ── Page Header (inside left column to avoid empty space on right) ──
    page_header("📊 Investigation Dashboard",
                "AI Fraud Transaction Investigation Assistant")


    # ── UPLOAD + SCHEDULER side by side ──
    c_up, c_sch = st.columns([3, 2], gap="small")
    with c_up:
        st.markdown("""
        <div class='chart-card' style='margin-bottom:4px'>
            <div class='chart-title'>📤 Upload Transaction CSV</div>
            <div class='chart-sub'>9 required columns · up to 1000 rows</div>
        </div>""", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "", type="csv", label_visibility="collapsed"
        )
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.session_state["transactions_df"] = df
                banks = df["bank_name"].value_counts() if "bank_name" in df.columns else {}
                bank_str = " · ".join(
                    f"{b}({c})" for b, c in list(banks.items())[:4]
                )
                st.success(
                    f"✓ {len(df)} transactions loaded · {bank_str}"
                )
            except Exception as e:
                st.error(f"Failed to read CSV: {e}")
        elif "transactions_df" in st.session_state:
            df = st.session_state["transactions_df"]
            st.success(f"✓ {len(df)} transactions loaded")

        # ── RUN INVESTIGATION + RESET ──
        run_clicked = st.button("🔍  RUN INVESTIGATION", type="primary",
                                use_container_width=True)
        reset_clicked = st.button("🔄  NEW ANALYSIS (Reset All)",
                                  use_container_width=True,
                                  help="Clear all data and start fresh")

        if reset_clicked:
            # Clear all cached data from session state and disk
            for key in ["workflow_results", "transactions_df",
                        "network_graph", "approval_status"]:
                if key in st.session_state:
                    del st.session_state[key]
            # Remove disk cache files
            import shutil
            if os.path.exists(_CACHE_DIR):
                shutil.rmtree(_CACHE_DIR, ignore_errors=True)
            st.rerun()

        if run_clicked:
            if "transactions_df" not in st.session_state:
                st.warning("Please upload a CSV file first.")
            else:
                with st.spinner("Running SentinelIQ workflow..."):
                    try:
                        from workflow.langgraph_workflow import SentinelIQWorkflow

                        config = st.session_state["config"]
                        workflow = SentinelIQWorkflow(config=config)
                        final_state = workflow.invoke(
                            st.session_state["transactions_df"]
                        )
                        st.session_state["workflow_results"] = final_state
                        st.session_state["network_graph"] = final_state.get(
                            "network_graph"
                        )
                        st.session_state["pattern_store"] = workflow.pattern_store
                        # Persist results to disk cache for refresh survival
                        try:
                            import pickle
                            os.makedirs(_CACHE_DIR, exist_ok=True)
                            with open(_CACHE_RESULTS, "wb") as f:
                                pickle.dump(final_state, f)
                            st.session_state["transactions_df"].to_csv(
                                _CACHE_CSV, index=False
                            )
                        except Exception:
                            pass
                        st.session_state["approval_status"] = {}
                        # Clear approval cache on new run
                        try:
                            _ap_path = os.path.join(_CACHE_DIR, "approval_status.json")
                            if os.path.exists(_ap_path):
                                os.remove(_ap_path)
                        except Exception:
                            pass
                        st.rerun()
                    except Exception as e:
                        st.error(f"Workflow error: {e}")

    with c_sch:
        batch_hour = st.session_state["config"].get("batch_schedule_hour", 18)
        st.markdown(f"""
        <div class='chart-card' style='min-height:320px;display:flex;
        flex-direction:column;justify-content:space-between'>
            <div style='display:flex;align-items:center;
            justify-content:space-between;margin-bottom:14px'>
                <div>
                    <div class='chart-title'>⏱ Scheduler</div>
                    <div class='chart-sub'>4 background jobs</div>
                </div>
                <span style='background:rgba(56,239,125,0.15);
                color:#38ef7d;font-size:10px;font-weight:700;
                padding:3px 10px;border-radius:12px;
                border:1px solid rgba(56,239,125,0.3)'>● ACTIVE</span>
            </div>
            <table style='width:100%;border-collapse:collapse;flex:1'>
                <tr style='border-bottom:1px solid #2e3a6e'>
                    <td style='color:#8892b0;font-size:12px;padding:10px 0'>Every 6h [batch]</td>
                    <td style='text-align:right;color:#38ef7d;font-size:12px;font-weight:700'>ON</td>
                </tr>
                <tr style='border-bottom:1px solid #2e3a6e'>
                    <td style='color:#8892b0;font-size:12px;padding:10px 0'>Daily {batch_hour}:00</td>
                    <td style='text-align:right;color:#38ef7d;font-size:12px;font-weight:700'>ON</td>
                </tr>
                <tr style='border-bottom:1px solid #2e3a6e'>
                    <td style='color:#8892b0;font-size:12px;padding:10px 0'>Weekly Mon 8AM</td>
                    <td style='text-align:right;color:#38ef7d;font-size:12px;font-weight:700'>ON</td>
                </tr>
                <tr>
                    <td style='color:#8892b0;font-size:12px;padding:10px 0'>Spike detection</td>
                    <td style='text-align:right;color:#38ef7d;font-size:12px;font-weight:700'>ON</td>
                </tr>
            </table>
            <div style='margin-top:auto;padding-top:16px;
            border-top:1px solid #2e3a6e;color:#8892b0;font-size:12px'>
                Next run in:
                <span style='color:#4776e6;font-family:monospace;
                font-weight:700;font-size:18px'> 2h 14m 33s</span>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── 4 FLAT METRIC CARDS ROW ──
    fc1, fc2, fc3, fc4 = st.columns(4, gap="small")
    scards = [
        (fc1, "#4776e6", "🎯", "HIGH Confidence", hconf, "LLM certain",
         "↑ Routing reliable"),
        (fc2, "#f7971e", "❓", "LOW Confidence", lconf, "LLM uncertain",
         "↑ Always escalated"),
        (fc3, "#38ef7d", "🔄", "Patterns", pattern_count, "Self-learning",
         "↑ Active memory"),
        (fc4, "#8e54e9", "⚡", "Processing", processing_time, "Last run",
         "↑ Under 3 min"),
    ]
    for col, color, icon, label, value, sub, trend in scards:
        with col:
            st.markdown(f"""
<div class='f-card'>
  <div style='display:flex;justify-content:space-between;margin-bottom:6px'>
    <div style='font-size:10px;font-weight:700;color:#8892b0;
    text-transform:uppercase;letter-spacing:0.7px'>{label}</div>
    <span>{icon}</span>
  </div>
  <div class='fc-number' style='color:{color}'>{value}</div>
  <div style='font-size:10px;color:#8892b0;margin-top:4px'>{sub}</div>
  <div class='fc-trend' style='color:{color}'>{trend}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── TREND CHART — FULL WIDTH (height=340) ──
    if "workflow_results" in st.session_state:
        routed = st.session_state["workflow_results"].get("routed_transactions", [])
        # Build hourly score distribution from real data
        hourly_scores = [0] * 24
        hourly_counts = [0] * 24
        for rt in routed:
            ts = rt.scored.enriched.row.timestamp
            h = ts.hour if hasattr(ts, "hour") else 0
            hourly_scores[h] += rt.scored.final_score
            hourly_counts[h] += 1
        hours = list(range(24))
        scores = [
            (hourly_scores[i] / hourly_counts[i] if hourly_counts[i] > 0 else 0)
            for i in range(24)
        ]
    else:
        # Placeholder chart
        import random
        random.seed(42)
        hours = list(range(24))
        scores = []
        for x in range(24):
            if 1 <= x <= 4:
                scores.append(random.randint(74, 90))
            elif 5 <= x <= 8:
                scores.append(random.randint(18, 38))
            elif 9 <= x <= 17:
                scores.append(random.randint(12, 32))
            elif 18 <= x <= 22:
                scores.append(random.randint(28, 52))
            else:
                scores.append(random.randint(42, 62))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=scores, fill="tozeroy",
        fillcolor="rgba(71,118,230,0.12)",
        line=dict(color="#4776e6", width=3),
        mode="lines+markers",
        marker=dict(size=6, color="#8e54e9",
                    line=dict(color="#4776e6", width=1.5)),
        hovertemplate="<b>%{x}:00</b><br>Score: %{y}<extra></extra>",
    ))
    fig.add_hrect(y0=85, y1=105, fillcolor="rgba(255,65,108,0.05)",
                  line_width=0)
    fig.add_hrect(y0=70, y1=85, fillcolor="rgba(247,151,30,0.04)",
                  line_width=0)
    fig.add_hrect(y0=40, y1=70, fillcolor="rgba(56,239,125,0.03)",
                  line_width=0)
    for yv, c2, lbl in [
        (85, "#ff416c", "CRITICAL 85"),
        (70, "#f7971e", "HIGH 70"),
        (40, "#38ef7d", "MED 40"),
    ]:
        fig.add_hline(
            y=yv, line_dash="dot", line_color=c2, line_width=1.5,
            annotation_text=lbl, annotation_font_color=c2,
            annotation_font_size=10, annotation_position="right",
        )
    if scores:
        peak = scores.index(max(scores))
        fig.add_annotation(
            x=peak, y=max(scores) + 5, text="Peak Risk Window",
            showarrow=True, arrowhead=2, arrowcolor="#ff416c",
            font=dict(color="#ff416c", size=11),
            bgcolor="rgba(255,65,108,0.15)",
            bordercolor="#ff416c", borderwidth=1, borderpad=4,
        )
    fig.update_layout(
        title=dict(
            text="Fraud Risk Score by Hour of Day",
            font=dict(color="#e8eaf6", size=14, family="Inter"), x=0,
        ),
        xaxis=dict(
            title="Hour of Day", color="#4a5580", gridcolor="#2e3a6e",
            tickfont=dict(size=10, color="#8892b0"),
            dtick=2, range=[-0.5, 23.5],
        ),
        yaxis=dict(
            title="Risk Score", color="#4a5580", gridcolor="#2e3a6e",
            range=[0, 108], tickfont=dict(size=10, color="#8892b0"),
        ),
        plot_bgcolor="#1e2448", paper_bgcolor="#232b52",
        font=dict(color="#8892b0", family="Inter"),
        height=340, margin=dict(t=44, b=44, l=54, r=80),
        showlegend=False, hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── DONUT + 4 FLAT CARDS ROW ──
    cd1, cd2, cd3, cd4, cd5 = st.columns([2, 1, 1, 1, 1], gap="small")

    with cd1:
        fig2 = go.Figure(go.Pie(
            values=[max(crit, 1), max(high, 1), max(med, 1), max(auto, 1)],
            labels=["CRITICAL", "HIGH", "MED", "AUTO-CLEARED"],
            marker=dict(
                colors=["#ff416c", "#f7971e", "#38ef7d", "#4776e6"],
                line=dict(color="#1a1f3a", width=2)),
            hole=0.65, textinfo="percent",
            textfont=dict(size=11, color="white"),
            hovertemplate="<b>%{label}</b><br>%{value} txns<extra></extra>",
        ))
        fig2.add_annotation(
            text=f"<b>{total}</b>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#e8eaf6", family="Inter"),
        )
        fig2.update_layout(
            title=dict(
                text="Risk Distribution",
                font=dict(color="#e8eaf6", size=12, family="Inter"), x=0,
            ),
            plot_bgcolor="#1e2448", paper_bgcolor="#232b52",
            font=dict(color="#8892b0", family="Inter"),
            height=220, margin=dict(t=34, b=0, l=0, r=10),
            legend=dict(
                orientation="v", x=1.0, y=0.5,
                font=dict(size=10, color="#8892b0"),
                bgcolor="rgba(0,0,0,0)",
            ),
        )
        st.plotly_chart(fig2, use_container_width=True,
                        config={"displayModeBar": False})

    flat4 = [
        (cd2, "#4776e6", "HIGH Conf", hconf, "LLM certain", "↑ Reliable"),
        (cd3, "#f7971e", "LOW Conf", lconf, "LLM uncertain", "↑ Escalated"),
        (cd4, "#38ef7d", "Patterns", pattern_count, "Self-learning",
         "↑ Active"),
        (cd5, "#8e54e9", "Speed", processing_time, "Last run", "↑ <3 min"),
    ]
    for col2, color, label, value, sub, trend in flat4:
        with col2:
            st.markdown(
                f"<div class='f-card'>"
                f"<div style='font-size:10px;font-weight:700;color:#8892b0;"
                f"text-transform:uppercase;letter-spacing:0.5px;"
                f"margin-bottom:6px'>{label}</div>"
                f"<div style='font-family:monospace;font-size:28px;"
                f"font-weight:800;color:{color}'>{value}</div>"
                f"<div style='font-size:10px;color:#8892b0;margin-top:4px'>"
                f"{sub}</div>"
                f"<div style='font-size:10px;color:{color};margin-top:4px'>"
                f"{trend}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ── RESULTS TABLE (full width, outside columns) ──
st.markdown("""
<div style='font-size:10px;font-weight:700;color:#8892b0;
text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>
▸ TRANSACTION RESULTS
</div>""", unsafe_allow_html=True)

if "workflow_results" in st.session_state:
    routed = st.session_state["workflow_results"].get(
        "routed_transactions", []
    )
    if routed:
        rows = []
        for rt in routed:
            s = rt.scored
            rows.append({
                "TXN ID": s.enriched.row.transaction_id,
                "Account": s.enriched.row.account_id,
                "Bank": s.enriched.row.bank_name,
                "Amount": f"₹{s.enriched.row.amount:,.0f}",
                "Score": s.final_score,
                "Conf": s.llm_score.confidence,
                "Risk": s.final_label,
                "Tier": rt.tier,
                "Reason": s.llm_score.reason[:80],
            })
        results_df = pd.DataFrame(rows)

        # ── Filters row: Search | Risk | Bank | Confidence ──
        f1, f2, f3, f4 = st.columns([3, 1, 1, 1], gap="small")
        with f1:
            search = st.text_input(
                "", "", placeholder="🔍 Search TXN ID, Account, Bank...",
                label_visibility="collapsed",
            )
        with f2:
            risk_f = st.selectbox(
                "", ["All Risk", "CRITICAL", "HIGH", "MED", "LOW"],
                label_visibility="collapsed",
            )
        with f3:
            banks_list = ["All Banks"] + sorted(
                results_df["Bank"].unique().tolist()
            )
            bank_f = st.selectbox(
                "", banks_list, label_visibility="collapsed",
            )
        with f4:
            conf_f = st.selectbox(
                "", ["All Conf", "HIGH", "LOW"],
                label_visibility="collapsed",
            )

        filtered = results_df.copy()
        if risk_f != "All Risk":
            filtered = filtered[filtered.Risk == risk_f]
        if bank_f != "All Banks":
            filtered = filtered[filtered.Bank == bank_f]
        if conf_f != "All Conf":
            filtered = filtered[filtered.Conf == conf_f]
        if search:
            mask = (
                filtered["TXN ID"].str.contains(search, case=False)
                | filtered["Account"].str.contains(search, case=False)
                | filtered["Bank"].str.contains(search, case=False)
            )
            filtered = filtered[mask]

        # Show count
        st.markdown(
            f"<div style='font-size:11px;color:#8892b0;margin-bottom:6px'>"
            f"Showing <b style='color:#4776e6'>{len(filtered)}</b> of "
            f"{len(results_df)} transactions</div>",
            unsafe_allow_html=True,
        )

        st.dataframe(
            filtered, use_container_width=True,
            hide_index=True, height=420,
        )
    else:
        st.info("No transactions processed yet.")
else:
    st.info("Upload a CSV and run investigation to see results.")

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ── APPROVAL PANEL (3 tabs, with action status) ──
st.markdown("""
<div style='font-size:10px;font-weight:700;color:#8892b0;
text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>
▸ HUMAN APPROVAL PANEL
</div>""", unsafe_allow_html=True)

# Initialize action status tracking in session state
if "approval_status" not in st.session_state:
    st.session_state["approval_status"] = {}

def _save_approval_status():
    """Persist approval status to disk cache."""
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        _ap_path = os.path.join(_CACHE_DIR, "approval_status.json")
        with open(_ap_path, "w") as f:
            json.dump(st.session_state["approval_status"], f)
    except Exception:
        pass


def _send_notification_email(to_email: str, subject: str, body: str):
    """Send an email notification via Gmail SMTP. Fails silently."""
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        gmail_address = os.environ.get("GMAIL_ADDRESS", "")
        gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
        if not gmail_address or not gmail_password or not to_email:
            return False

        msg = MIMEMultipart()
        msg["From"] = gmail_address
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(gmail_address, gmail_password)
            server.send_message(msg)
        return True
    except Exception:
        return False

if "workflow_results" in st.session_state:
    routed = st.session_state["workflow_results"].get(
        "routed_transactions", []
    )
    crit_txns = [r for r in routed if r.tier == "CRITICAL"]
    high_txns = [r for r in routed if r.tier == "HIGH_QUEUE"]
    med_txns = [r for r in routed if r.tier == "MED_BATCH"]

    t_c, t_h, t_m = st.tabs([
        f"🚨 CRITICAL  ({len(crit_txns)})",
        f"⚠️ HIGH Queue  ({len(high_txns)})",
        f"📋 MED Batch  ({len(med_txns)})",
    ])

    with t_c:
        st.markdown(f"""
<div style='background:rgba(255,65,108,0.08);border:1px solid rgba(255,65,108,0.2);
border-radius:8px;padding:10px 14px;margin-bottom:12px;
display:flex;align-items:center;justify-content:space-between'>
  <span style='color:#ff416c;font-weight:700;font-size:13px'>
  🚨 Immediate Response Required</span>
  <span style='color:#ff9aa2;font-family:monospace;font-size:11px'>
  Auto-escalates in: 00:47:23</span>
</div>""", unsafe_allow_html=True)
        # Pagination: show 10 at a time
        crit_page_size = 10
        crit_total_pages = max(1, (len(crit_txns) + crit_page_size - 1) // crit_page_size)
        crit_page = st.number_input(
            f"Page (1-{crit_total_pages})", min_value=1,
            max_value=crit_total_pages, value=1, key="crit_page"
        )
        crit_start = (crit_page - 1) * crit_page_size
        crit_end = min(crit_start + crit_page_size, len(crit_txns))
        st.caption(f"Showing {crit_start+1}-{crit_end} of {len(crit_txns)}")

        for rt in crit_txns[crit_start:crit_end]:
            s = rt.scored
            txn_id = s.enriched.row.transaction_id
            status = st.session_state["approval_status"].get(txn_id, "pending")

            c1, c2, c3, c4, c5 = st.columns(
                [4, 0.8, 0.8, 0.8, 1.2], gap="small"
            )
            with c1:
                st.markdown(f"""
<div class='apr-row apr-critical'>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:3px'>
<span style='color:#ff416c;font-family:monospace;font-weight:700'>
{txn_id}</span>
<span style='background:#ff416c;color:white;font-size:9px;
padding:2px 7px;border-radius:10px;font-weight:700'>CRITICAL</span>
<span style='color:#ff9aa2;font-size:10px'>Score: {s.final_score}</span>
  </div>
  <div style='color:#8892b0;font-size:11px'>
  {s.llm_score.reason[:55]}...</div>
</div>""", unsafe_allow_html=True)
            with c2:
                if st.button("✓", key=f"ca_{txn_id}", type="primary",
                             disabled=(status != "pending")):
                    ps = st.session_state["pattern_store"]
                    ps.record(s.pattern_hash, "approved")
                    st.session_state["approval_status"][txn_id] = "approved"
                    _save_approval_status()
                    # Send approval email to customer
                    cust_email = getattr(s.enriched.row, "customer_email", "")
                    if cust_email:
                        _send_notification_email(
                            cust_email,
                            f"SentinelIQ: Transaction {txn_id} Approved",
                            f"Dear Customer,\n\nYour transaction {txn_id} "
                            f"(₹{s.enriched.row.amount:,.0f}) has been reviewed and APPROVED.\n\n"
                            f"No action is required from your end.\n\n"
                            f"— SentinelIQ Fraud Investigation Team"
                        )
                    st.rerun()
            with c3:
                if st.button("✗", key=f"cr_{txn_id}",
                             disabled=(status != "pending")):
                    ps = st.session_state["pattern_store"]
                    ps.record(s.pattern_hash, "rejected")
                    st.session_state["approval_status"][txn_id] = "rejected"
                    _save_approval_status()
                    # Send rejection email to customer
                    cust_email = getattr(s.enriched.row, "customer_email", "")
                    if cust_email:
                        _send_notification_email(
                            cust_email,
                            f"SentinelIQ: Transaction {txn_id} Flagged",
                            f"Dear Customer,\n\nYour transaction {txn_id} "
                            f"(₹{s.enriched.row.amount:,.0f}) has been flagged and REJECTED "
                            f"due to suspicious activity.\n\n"
                            f"Please contact your bank for further assistance.\n\n"
                            f"— SentinelIQ Fraud Investigation Team"
                        )
                    st.rerun()
            with c4:
                if st.button("↑", key=f"ce_{txn_id}",
                             disabled=(status != "pending")):
                    st.session_state["approval_status"][txn_id] = "escalated"
                    _save_approval_status()
                    # Send escalation email to manager
                    cfg = st.session_state.get("config", {})
                    mgr_email = cfg.get("manager_email", "")
                    if mgr_email:
                        _send_notification_email(
                            mgr_email,
                            f"SentinelIQ ESCALATION: {txn_id} requires attention",
                            f"A transaction has been escalated for manager review:\n\n"
                            f"Transaction ID: {txn_id}\n"
                            f"Account: {s.enriched.row.account_id}\n"
                            f"Bank: {s.enriched.row.bank_name}\n"
                            f"Amount: ₹{s.enriched.row.amount:,.0f}\n"
                            f"Score: {s.final_score}\n"
                            f"Reason: {s.llm_score.reason}\n\n"
                            f"Please review immediately.\n\n"
                            f"— SentinelIQ Fraud Investigation Team"
                        )
                    st.rerun()
            with c5:
                # Action Status indicator
                if status == "approved":
                    st.markdown(
                        "<div style='background:rgba(56,239,125,0.15);"
                        "border:1px solid #38ef7d;border-radius:8px;"
                        "padding:6px 10px;text-align:center;"
                        "font-size:11px;font-weight:700;color:#38ef7d'>"
                        "✓ APPROVED</div>",
                        unsafe_allow_html=True,
                    )
                elif status == "rejected":
                    st.markdown(
                        "<div style='background:rgba(255,65,108,0.15);"
                        "border:1px solid #ff416c;border-radius:8px;"
                        "padding:6px 10px;text-align:center;"
                        "font-size:11px;font-weight:700;color:#ff416c'>"
                        "✗ REJECTED</div>",
                        unsafe_allow_html=True,
                    )
                elif status == "escalated":
                    st.markdown(
                        "<div style='background:rgba(247,151,30,0.15);"
                        "border:1px solid #f7971e;border-radius:8px;"
                        "padding:6px 10px;text-align:center;"
                        "font-size:11px;font-weight:700;color:#f7971e'>"
                        "↑ ESCALATED</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='background:rgba(71,118,230,0.1);"
                        "border:1px solid #2e3a6e;border-radius:8px;"
                        "padding:6px 10px;text-align:center;"
                        "font-size:10px;font-weight:600;color:#8892b0'>"
                        "⏳ PENDING</div>",
                        unsafe_allow_html=True,
                    )

    with t_h:
        approved_high = sum(
            1 for rt in high_txns
            if st.session_state["approval_status"].get(
                rt.scored.enriched.row.transaction_id, "pending"
            ) != "pending"
        )
        st.progress(
            approved_high / max(len(high_txns), 1),
            text=f"**{approved_high} of {len(high_txns)}** reviewed",
        )
        # Pagination: show 10 at a time
        high_page_size = 10
        high_total_pages = max(1, (len(high_txns) + high_page_size - 1) // high_page_size)
        high_page = st.number_input(
            f"Page (1-{high_total_pages})", min_value=1,
            max_value=high_total_pages, value=1, key="high_page"
        )
        high_start = (high_page - 1) * high_page_size
        high_end = min(high_start + high_page_size, len(high_txns))
        st.caption(f"Showing {high_start+1}-{high_end} of {len(high_txns)}")

        for rt in high_txns[high_start:high_end]:
            s = rt.scored
            txn_id = s.enriched.row.transaction_id
            status = st.session_state["approval_status"].get(txn_id, "pending")

            c1, c2, c3, c4 = st.columns([5, 0.8, 0.8, 1.2], gap="small")
            with c1:
                st.markdown(f"""
<div class='apr-row apr-high'>
  <div style='display:flex;align-items:center;gap:8px'>
<span style='color:#f7971e;font-family:monospace;font-weight:700'>
{txn_id}</span>
<span style='background:#f7971e;color:#1a1f3a;font-size:9px;
padding:2px 7px;border-radius:10px;font-weight:800'>HIGH</span>
<span style='color:#8892b0;font-size:11px'>
{s.enriched.row.bank_name} · ₹{s.enriched.row.amount:,.0f}</span>
  </div>
  <div style='color:#8892b0;font-size:11px;margin-top:2px'>
  {s.llm_score.reason[:55]}...</div>
</div>""", unsafe_allow_html=True)
            with c2:
                if st.button("✓", key=f"ha_{txn_id}", type="primary",
                             disabled=(status != "pending")):
                    ps = st.session_state["pattern_store"]
                    ps.record(s.pattern_hash, "approved")
                    st.session_state["approval_status"][txn_id] = "approved"
                    _save_approval_status()
                    cust_email = getattr(s.enriched.row, "customer_email", "")
                    if cust_email:
                        _send_notification_email(
                            cust_email,
                            f"SentinelIQ: Transaction {txn_id} Approved",
                            f"Dear Customer,\n\nYour transaction {txn_id} "
                            f"(₹{s.enriched.row.amount:,.0f}) has been reviewed and APPROVED.\n\n"
                            f"No action is required.\n\n"
                            f"— SentinelIQ Fraud Investigation Team"
                        )
                    st.rerun()
            with c3:
                if st.button("✗", key=f"hr_{txn_id}",
                             disabled=(status != "pending")):
                    ps = st.session_state["pattern_store"]
                    ps.record(s.pattern_hash, "rejected")
                    st.session_state["approval_status"][txn_id] = "rejected"
                    _save_approval_status()
                    cust_email = getattr(s.enriched.row, "customer_email", "")
                    if cust_email:
                        _send_notification_email(
                            cust_email,
                            f"SentinelIQ: Transaction {txn_id} Flagged",
                            f"Dear Customer,\n\nYour transaction {txn_id} "
                            f"(₹{s.enriched.row.amount:,.0f}) has been flagged and REJECTED.\n\n"
                            f"Please contact your bank.\n\n"
                            f"— SentinelIQ Fraud Investigation Team"
                        )
                    st.rerun()
            with c4:
                if status == "approved":
                    st.markdown(
                        "<div style='background:rgba(56,239,125,0.15);"
                        "border:1px solid #38ef7d;border-radius:8px;"
                        "padding:6px 10px;text-align:center;"
                        "font-size:11px;font-weight:700;color:#38ef7d'>"
                        "✓ APPROVED</div>",
                        unsafe_allow_html=True,
                    )
                elif status == "rejected":
                    st.markdown(
                        "<div style='background:rgba(255,65,108,0.15);"
                        "border:1px solid #ff416c;border-radius:8px;"
                        "padding:6px 10px;text-align:center;"
                        "font-size:11px;font-weight:700;color:#ff416c'>"
                        "✗ REJECTED</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='background:rgba(71,118,230,0.1);"
                        "border:1px solid #2e3a6e;border-radius:8px;"
                        "padding:6px 10px;text-align:center;"
                        "font-size:10px;font-weight:600;color:#8892b0'>"
                        "⏳ PENDING</div>",
                        unsafe_allow_html=True,
                    )

    with t_m:
        st.info(
            f"📋 **{len(med_txns)} transactions** in today's batch "
            f"review queue"
        )
        st.markdown(f"""
<div style='background:rgba(17,153,142,0.08);border:1px solid rgba(56,239,125,0.15);
border-radius:8px;padding:12px 14px;margin-top:8px'>
  <div style='color:#8892b0;font-size:12px;line-height:2'>
📅 Batch review: <b style='color:#38ef7d'>Today 6:00 PM</b><br>
📧 Report emailed automatically<br>
⚡ No individual review needed for MED + HIGH confidence
  </div>
</div>""", unsafe_allow_html=True)
        st.button("Review Now (Early)", type="secondary")

    # ── PDF REPORT & EMAIL ALERT BUTTONS ──
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size:10px;font-weight:700;color:#8892b0;
    text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>
    ▸ REPORT & ALERTS
    </div>""", unsafe_allow_html=True)

    btn_pdf, btn_email = st.columns(2, gap="small")
    with btn_pdf:
        if st.button("📄  GENERATE PDF REPORT", type="primary",
                     use_container_width=True):
            with st.spinner("Generating PDF report..."):
                try:
                    from agents.reporting_agent import ReportingAgent
                    agent = ReportingAgent(config=st.session_state.get("config", {}))
                    results = st.session_state["workflow_results"]
                    routed = results.get("routed_transactions", [])
                    summary = results.get("summary_stats")
                    pdf_bytes = agent.build_pdf(routed, summary)
                    st.download_button(
                        "⬇️ Download PDF Report",
                        data=pdf_bytes,
                        file_name="SentinelIQ_FraudReport.pdf",
                        mime="application/pdf",
                    )
                    st.success("✓ PDF report generated!")
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

    with btn_email:
        if st.button("📧  SEND EMAIL ALERT", type="primary",
                     use_container_width=True):
            with st.spinner("Sending email alert..."):
                try:
                    from dotenv import load_dotenv
                    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

                    from agents.reporting_agent import ReportingAgent
                    agent = ReportingAgent(config=st.session_state.get("config", {}))
                    results = st.session_state["workflow_results"]
                    routed = results.get("routed_transactions", [])
                    summary = results.get("summary_stats")
                    report_url = results.get("report_url", "")
                    agent.send_gmail_alert(routed, summary, report_url)
                    st.success("✓ Email alert sent to configured recipient!")
                except ValueError as ve:
                    st.error(f"Email config missing: {ve}")
                except Exception as e:
                    st.error(f"Email failed: {e}")

else:
    t_c, t_h, t_m = st.tabs([
        "🚨 CRITICAL  (0)", "⚠️ HIGH Queue  (0)", "📋 MED Batch  (0)"
    ])
    with t_c:
        st.info("Run an investigation to see CRITICAL transactions.")
    with t_h:
        st.info("No HIGH-risk transactions yet.")
    with t_m:
        st.info("No MED-risk transactions yet.")

# ── Floating Chatbot ──
render_chatbot()

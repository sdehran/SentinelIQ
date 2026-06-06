"""SentinelIQ — Natural Language Query Page — Gradient Enterprise Theme.

AI Fraud Transaction Investigation Assistant
Developed by Group 9 || Cohort 1 2025-26
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load .env so GEMINI_API_KEY is available
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import streamlit as st
import pandas as pd

from ui.styles import inject_styles, page_header
from ui.components.sidebar import render_sidebar

# ── Inject Theme ──
inject_styles()
render_sidebar()

# ── Page Header ──
page_header("💬 Natural Language Query",
            "Ask anything about your transaction data in plain English")

# ── Session state for query history ──
if "nl_query_history" not in st.session_state:
    st.session_state["nl_query_history"] = []

# ── Query Input ──
cq, cb = st.columns([5, 1], gap="small")
with cq:
    query = st.text_input(
        "", "",
        placeholder="e.g. Show CRITICAL transactions from HDFC after midnight...",
        label_visibility="collapsed",
        key="nl_query_input",
    )
with cb:
    ask_clicked = st.button("✨ ASK", type="primary", use_container_width=True)

# ── Quick Chips ──
chips = [
    "Highest risk account",
    "After midnight",
    "HDFC above Rs.40K",
    "Most fraud bank",
    "Uncertain confidence",
    "Round amounts",
    "Relay nodes",
]
chip_query = None
# Use 4 chips per row for better proportionality
row1 = st.columns(4, gap="small")
row2 = st.columns(4, gap="small")
all_cols = list(row1) + list(row2)
for i, chip in enumerate(chips):
    with all_cols[i]:
        if st.button(chip, key=f"c_{i}", use_container_width=True):
            chip_query = chip

# ── Process Query ──
active_query = chip_query or (query if ask_clicked else None)

if active_query:
    if "transactions_df" not in st.session_state:
        st.warning("Please upload transaction data on the Dashboard first.")
    else:
        df = st.session_state["transactions_df"]
        with st.spinner("Querying with AI agent..."):
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from langchain_experimental.agents import create_pandas_dataframe_agent

                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    st.error("GEMINI_API_KEY not set. Cannot run NL query.")
                else:
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-2.5-flash",
                        google_api_key=api_key,
                        temperature=0.1,
                    )
                    agent = create_pandas_dataframe_agent(
                        llm, df, verbose=False,
                        allow_dangerous_code=True,
                        handle_parsing_errors=True,
                    )
                    result = agent.invoke(active_query)
                    answer = result.get("output", str(result))

                    st.session_state["nl_query_history"].insert(0, {
                        "question": active_query,
                        "answer": answer,
                        "time": "just now",
                    })
            except ImportError as ie:
                st.error(
                    f"Import error: {ie}. "
                    f"Try: pip install langchain_google_genai langchain_experimental"
                )
            except Exception as e:
                st.error(f"Query failed: {e}")

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ── Query History ──
st.markdown("""
<div style='font-size:11px;font-weight:700;color:#8892b0;
text-transform:uppercase;letter-spacing:1px;margin-bottom:10px'>
▸ QUERY HISTORY
</div>""", unsafe_allow_html=True)

history = st.session_state.get("nl_query_history", [])

if not history:
    # Show placeholder examples
    examples = [
        ("Which account has the highest risk score?",
         "Account <b style='color:#ff416c'>ACC_0023 (HDFC Bank)</b> has score "
         "<b style='color:#ff416c'>96 — CRITICAL</b>. Triggered velocity fraud "
         "(12 txns in 40 min at 3AM), geographic anomaly, and new merchant flag.",
         "example"),
        ("How many LOW confidence transactions?",
         "<b style='color:#f7971e'>Run an investigation first</b> to query "
         "real transaction data with AI-powered natural language.",
         "example"),
    ]
    for ques, ans, time in examples:
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#1e2448,#232b52);
        border:1px solid #2e3a6e;border-left:3px solid #4776e6;
        border-radius:10px;padding:14px 18px;margin-bottom:10px'>
            <div style='display:flex;gap:8px;margin-bottom:10px'>
                <div style='width:24px;height:24px;background:#2e3a6e;
                border-radius:50%;display:flex;align-items:center;
                justify-content:center;font-size:11px;flex-shrink:0'>👤</div>
                <div style='color:#e8eaf6;font-weight:600;font-size:13px'>{ques}</div>
            </div>
            <div style='display:flex;gap:8px'>
                <div style='width:24px;height:24px;
                background:linear-gradient(135deg,rgba(71,118,230,0.3),rgba(142,84,233,0.3));
                border:1px solid rgba(71,118,230,0.4);border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                font-size:11px;flex-shrink:0'>🛡️</div>
                <div>
                    <div style='color:#a0b8d4;font-size:12px;line-height:1.7'>{ans}</div>
                    <div style='color:#4a5580;font-size:10px;margin-top:6px'>{time}</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
else:
    for entry in history[:10]:
        ques = entry["question"]
        ans = entry["answer"]
        time = entry.get("time", "")
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#1e2448,#232b52);
        border:1px solid #2e3a6e;border-left:3px solid #4776e6;
        border-radius:10px;padding:14px 18px;margin-bottom:10px'>
            <div style='display:flex;gap:8px;margin-bottom:10px'>
                <div style='width:24px;height:24px;background:#2e3a6e;
                border-radius:50%;display:flex;align-items:center;
                justify-content:center;font-size:11px;flex-shrink:0'>👤</div>
                <div style='color:#e8eaf6;font-weight:600;font-size:13px'>{ques}</div>
            </div>
            <div style='display:flex;gap:8px'>
                <div style='width:24px;height:24px;
                background:linear-gradient(135deg,rgba(71,118,230,0.3),rgba(142,84,233,0.3));
                border:1px solid rgba(71,118,230,0.4);border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                font-size:11px;flex-shrink:0'>🛡️</div>
                <div>
                    <div style='color:#a0b8d4;font-size:12px;line-height:1.7'>{ans}</div>
                    <div style='color:#4a5580;font-size:10px;margin-top:6px'>{time}</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)


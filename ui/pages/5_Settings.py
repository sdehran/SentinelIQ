"""SentinelIQ — Settings Page — Gradient Enterprise Theme.

AI Fraud Transaction Investigation Assistant
Developed by Group 9 || Cohort 1 2025-26
"""

import sys
import os
import json
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st

from ui.styles import inject_styles, page_header
from ui.components.sidebar import render_sidebar

# ── Inject Theme ──
inject_styles()
render_sidebar()

# ── Load Config ──
config_path = os.path.join(PROJECT_ROOT, "config.json")
if "config" not in st.session_state:
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

config = st.session_state["config"]

# ── Page Header ──
page_header("⚙️ Settings & Configuration",
            "Manage system parameters without touching source code · config.json")

# ── Section 1: System Configuration ──
with st.expander("🔵  System Configuration", expanded=True):
    s1, s2 = st.columns(2, gap="medium")
    with s1:
        model_options = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash-lite"]
        current_model = config.get("llm_model", "gemini-2.5-flash")
        model_idx = model_options.index(current_model) if current_model in model_options else 0
        llm_model = st.selectbox(
            "LLM Model", model_options,
            index=model_idx,
            key="settings_llm_model",
        )
        rag_top_k = st.number_input(
            "RAG Top-K Chunks",
            value=config.get("rag_top_k", 3),
            min_value=1, max_value=10,
            key="settings_rag_top_k",
        )
        max_rows = st.number_input(
            "Max Rows Per Run", value=1000, key="settings_max_rows"
        )
    with s2:
        # Risk threshold visual bar
        crit_t = config.get("critical_threshold", 85)
        high_t = config.get("high_threshold", 70)
        med_t = config.get("med_threshold", 40)
        st.markdown(f"""
        <div style='margin-bottom:8px;font-size:12px;color:#8892b0'>Risk Threshold Zones</div>
        <div style='height:14px;border-radius:7px;overflow:hidden;display:flex'>
            <div style='background:linear-gradient(90deg,#4776e6,#6a54e9);width:{med_t}%'></div>
            <div style='background:linear-gradient(90deg,#11998e,#38ef7d);width:{high_t - med_t}%'></div>
            <div style='background:linear-gradient(90deg,#f7971e,#ffd200);width:{crit_t - high_t}%'></div>
            <div style='background:linear-gradient(90deg,#ff416c,#ff4b2b);width:{100 - crit_t}%'></div>
        </div>
        <div style='display:flex;justify-content:space-between;
        font-size:9px;color:#4a5580;margin-top:3px'>
            <span>0 LOW</span><span style='color:#38ef7d'>{med_t} MED</span>
            <span style='color:#f7971e'>{high_t} HIGH</span>
            <span style='color:#ff416c'>{crit_t} CRIT</span><span>100</span>
        </div>""", unsafe_allow_html=True)
        processing_timeout = st.number_input(
            "Processing Timeout (s)", value=120,
            key="settings_timeout",
        )

# ── Section 2: 3-Tier Autonomy ──
with st.expander("🤖  3-Tier Autonomy Settings"):
    a1, a2 = st.columns(2, gap="medium")
    with a1:
        low_conf_override = st.toggle(
            "LOW Confidence Override", value=True,
            key="settings_low_conf",
        )
        low_risk_autoclear = st.toggle(
            "LOW Risk Auto-Clear", value=True,
            key="settings_low_risk_ac",
        )
        high_escalation_hrs = st.number_input(
            "HIGH Escalation (hrs)", value=4,
            key="settings_high_esc",
        )
    with a2:
        crit_escalation_hrs = st.number_input(
            "CRITICAL Escalation (hrs)", value=1,
            key="settings_crit_esc",
        )
        autonomy_target = st.slider(
            "Autonomy Rate Target (%)", 50, 95, 75,
            key="settings_autonomy_target",
        )
        pattern_memory_adj = st.toggle(
            "Pattern Memory Adjustments", value=True,
            key="settings_pattern_adj",
        )

# ── Section 3: Alert Recipients ──
with st.expander("🔴  Alert Recipients"):
    manager_email = st.text_input(
        "Manager Email (receives escalation alerts)",
        value=config.get("manager_email", ""),
        placeholder="manager@yourcompany.com",
        key="settings_manager_email",
    )
    critical_recipients = st.text_area(
        "CRITICAL Alert Recipients",
        value=config.get("critical_recipients", "oncall@bank.com\nsenior@bank.com"),
        height=70, key="settings_crit_recip",
    )
    report_recipients = st.text_area(
        "Report Completion Recipients",
        value=config.get("report_recipients", "manager@bank.com"),
        height=70, key="settings_report_recip",
    )
    alert_threshold = st.number_input(
        "Alert if HIGH+CRITICAL exceeds",
        value=config.get("alert_threshold", 50),
        key="settings_alert_thresh",
    )

# ── Section 4: Error Handling ──
with st.expander("🟠  Error Handling"):
    e1, e2 = st.columns(2, gap="medium")
    with e1:
        retry_attempts = st.number_input(
            "LLM Retry Attempts",
            value=config.get("retry_attempts", 3),
            min_value=1, max_value=5,
            key="settings_retry",
        )
        st.info("Retry backoff: 1s → 2s → 4s")
    with e2:
        fallback_mode = st.toggle(
            "Fallback Mode",
            value=config.get("fallback_mode", True),
            key="settings_fallback",
        )
        invalid_csv_action = st.selectbox(
            "Invalid CSV Row",
            ["Skip and continue", "Stop processing"],
            key="settings_invalid_csv",
        )

# ── Section 5: AWS Storage ──
with st.expander("🟢  AWS Storage"):
    g1, g2 = st.columns(2, gap="medium")
    with g1:
        s3_bucket = st.text_input(
            "S3 Bucket Name",
            value="fraud-investigation-group9",
            key="settings_s3_bucket",
        )
        aws_region = st.selectbox(
            "AWS Region",
            ["ap-south-1 (Mumbai)", "us-east-1"],
            key="settings_aws_region",
        )
    with g2:
        auto_save_s3 = st.toggle(
            "Auto-save to S3", value=True, key="settings_auto_s3"
        )
        report_retention = st.selectbox(
            "Report Retention",
            ["90 days", "180 days", "1 year"],
            key="settings_retention",
        )
        pattern_backup = st.toggle(
            "Pattern Store Backup", value=True,
            key="settings_pattern_backup",
        )
    st.markdown("""
    <div style='background:#1e2448;border-radius:6px;padding:10px 14px;
    font-family:monospace;font-size:10px;color:#4a5580;margin-top:8px'>
        reports/{date}/{session_id}/SentinelIQ_Report.pdf<br>
        datasets/{date}/{session_id}/transactions.csv<br>
        audit/{date}/{session_id}/approval_log.json
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ── Save Button ──
if st.button("💾  SAVE CONFIGURATION", type="primary",
             use_container_width=True):
    updated_config = {
        "critical_threshold": crit_t,
        "high_threshold": high_t,
        "med_threshold": med_t,
        "rag_top_k": rag_top_k,
        "retry_attempts": retry_attempts,
        "fallback_mode": fallback_mode,
        "batch_schedule_hour": config.get("batch_schedule_hour", 18),
        "llm_model": llm_model,
        "manager_email": manager_email,
        "critical_recipients": critical_recipients,
        "report_recipients": report_recipients,
        "alert_threshold": alert_threshold,
    }
    try:
        with open(config_path, "w") as f:
            json.dump(updated_config, f, indent=2)
        st.session_state["config"] = updated_config
        st.success("✓ Configuration saved successfully!")
    except Exception as e:
        st.error(f"Failed to save: {e}")

st.markdown("""
<div style='text-align:center;color:#4a5580;font-size:11px;margin-top:8px'>
Changes apply on next run · config.json
</div>""", unsafe_allow_html=True)


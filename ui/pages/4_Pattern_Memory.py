"""SentinelIQ — Pattern Memory Page — Gradient Enterprise Theme.

AI Fraud Transaction Investigation Assistant
Developed by Group 9 || Cohort 1 2025-26
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd

from ui.styles import inject_styles, page_header
from ui.components.sidebar import render_sidebar

# ── Inject Theme ──
inject_styles()
render_sidebar()

# ── Ensure pattern store exists ──
if "pattern_store" not in st.session_state:
    from pattern_store import PatternStore
    st.session_state["pattern_store"] = PatternStore(
        filepath=os.path.join(PROJECT_ROOT, "pattern_store.json")
    )

ps = st.session_state["pattern_store"]

# ── Page Header ──
page_header("🧠 Pattern Memory",
            "Self-learning system — improves accuracy without ML training")

# ── 4 Gradient Stat Cards ──
total_patterns = ps.count
approved_count = ps.approved_count
rejected_count = ps.rejected_count

# Count new today
new_today = 0
today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
for entry in ps.entries.values():
    created = entry.get("created_at", "")
    if created.startswith(today_str):
        new_today += 1

mc1, mc2, mc3, mc4 = st.columns(4, gap="small")
for col, cls, icon, label, val in [
    (mc1, "g-auto", "🧠", "Total Patterns", str(total_patterns)),
    (mc2, "g-med", "✅", "Approved (True +)", str(approved_count)),
    (mc3, "g-critical", "❌", "Rejected (False -)", str(rejected_count)),
    (mc4, "g-high", "⚡", "New Today", str(new_today)),
]:
    with col:
        st.markdown(f"""
        <div class='g-card {cls}'>
            <div class='card-icon'>{icon}</div>
            <div class='card-number'>{val}</div>
            <div class='card-label'>{label}</div>
            <div class='mini-bar' style='margin-top:10px'>
                <div class='mini-bar-fill' style='width:70%'></div>
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Flow Diagram ──
flow_cols = st.columns([1, 0.3, 1, 0.3, 1, 0.3, 1, 0.3, 1])
for ci in [1, 3, 5, 7]:
    with flow_cols[ci]:
        st.markdown(
            "<div style='text-align:center;font-size:20px;color:#4776e6;"
            "padding-top:20px'>→</div>",
            unsafe_allow_html=True,
        )
flow_items = [
    (0, "✅", "g-med", "APPROVE", "Pattern stored"),
    (2, "🧠", "g-auto", "Hash Stored", "JSON updated"),
    (4, "📈", "g-high", "+10 Next Run", "Score boosted"),
    (6, "❌", "g-critical", "REJECT", "False positive"),
    (8, "📉", "g-auto", "-15 Next Run", "Score reduced"),
]
for ci, icon, cls, title, sub in flow_items:
    with flow_cols[ci]:
        st.markdown(f"""
        <div class='g-card {cls}' style='padding:12px;text-align:center'>
            <div style='font-size:22px;margin-bottom:4px'>{icon}</div>
            <div style='font-size:10px;font-weight:700'>{title}</div>
            <div style='font-size:9px;opacity:0.7'>{sub}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("""
<div style='color:#4a5580;font-size:10px;text-align:center;margin-top:8px;margin-bottom:16px'>
No ML training required · Pure JSON storage · 90-day memory decay
</div>""", unsafe_allow_html=True)

# ── Pattern Table ──
if ps.entries:
    rows = []
    for h, entry in list(ps.entries.items())[:50]:
        rows.append({
            "Hash": h[:8],
            "Feature Pattern": entry.get("feature_combination", "—"),
            "Seen": entry.get("times_seen", 0),
            "Decision": entry.get("decision", "").upper(),
            "Score": f"+ 10" if entry.get("score_adjustment", 0) > 0 else "- 15",
            "Updated": entry.get("last_updated", "")[:10],
        })
    pdf = pd.DataFrame(rows)
    st.dataframe(pdf, use_container_width=True, hide_index=True)
else:
    # Show placeholder
    pdf = pd.DataFrame([
        {"Hash": "a3f9b2c1", "Feature Pattern": "velocity+unusual_hour+new_merchant+HDFC",
         "Seen": 12, "Decision": "APPROVED", "Score": "+ 10", "Updated": "2d ago"},
        {"Hash": "b7e4d1a8", "Feature Pattern": "round_amount+unusual_hour+SBI",
         "Seen": 8, "Decision": "APPROVED", "Score": "+ 10", "Updated": "5d ago"},
        {"Hash": "c2f6a9b3", "Feature Pattern": "velocity+geo_anomaly+ICICI",
         "Seen": 6, "Decision": "APPROVED", "Score": "+ 10", "Updated": "1d ago"},
        {"Hash": "d5c1e7f2", "Feature Pattern": "round_amount+new_merchant+Axis",
         "Seen": 4, "Decision": "REJECTED", "Score": "- 15", "Updated": "3d ago"},
    ])
    st.dataframe(pdf, use_container_width=True, hide_index=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── Export / Reset Buttons ──
mb1, mb2, mb3 = st.columns(3, gap="small")
with mb1:
    if st.button("🧹 Clear Expired", type="secondary",
                 use_container_width=True):
        # Remove entries older than 180 days
        now = datetime.now(timezone.utc)
        to_remove = []
        for h, entry in ps.entries.items():
            try:
                last = datetime.fromisoformat(entry["last_updated"])
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                if (now - last).days > 180:
                    to_remove.append(h)
            except Exception:
                pass
        for h in to_remove:
            del ps.entries[h]
        ps.save()
        st.success(f"Removed {len(to_remove)} expired patterns.")
        st.rerun()

with mb2:
    if st.button("📥 Export Store", type="secondary",
                 use_container_width=True):
        export_data = json.dumps(ps.entries, indent=2)
        st.download_button(
            "⬇️ Download JSON",
            data=export_data,
            file_name="pattern_store_export.json",
            mime="application/json",
        )

with mb3:
    if st.button("🗑️ Reset All", type="secondary",
                 use_container_width=True):
        ps.clear()
        st.success("Pattern store cleared.")
        st.rerun()


"""SentinelIQ UI Styles — Gradient Enterprise Theme.

Provides inject_styles() and page_header() helpers used across all pages.
"""

import streamlit as st


def inject_styles():
    """Inject the full gradient enterprise CSS theme into the Streamlit app."""
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    --bg:        #1a1f3a;
    --bg2:       #1e2448;
    --sidebar:   #151933;
    --card:      #232b52;
    --border:    #2e3a6e;
    --text:      #e8eaf6;
    --muted:     #8892b0;
    --dimmed:    #4a5580;
    --font-mono: 'JetBrains Mono', monospace;
    --g-critical: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
    --g-high:     linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
    --g-med:      linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    --g-low:      linear-gradient(135deg, #4776e6 0%, #8e54e9 100%);
    --g-auto:     linear-gradient(135deg, #8e54e9 0%, #43b5a0 100%);
}

html, body, .stApp {
    background-color: var(--bg) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text) !important;
}
.main .block-container {
    padding: 0.5rem 1.6rem 2rem !important;
    max-width: 100% !important;
    background: var(--bg) !important;
}
section[data-testid="stMain"] { background: var(--bg) !important; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { display: none !important; height: 0 !important; }
.stDeployButton { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 0.4rem !important; }

/* Hide Streamlit's auto-generated page navigation in sidebar */
[data-testid="stSidebarNav"] { display: none !important; height: 0 !important; padding: 0 !important; margin: 0 !important; }
nav[data-testid="stSidebarNav"] { display: none !important; height: 0 !important; }
section[data-testid="stSidebar"] > div > div > div > div:first-child ul { display: none !important; }
div[data-testid="stSidebarNavItems"] { display: none !important; }
[data-testid="stSidebarNavSeparator"] { display: none !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] + div { padding-top: 0 !important; }
section[data-testid="stSidebar"] > div { padding-top: 0 !important; }
section[data-testid="stSidebar"] > div > div { padding-top: 0 !important; }
section[data-testid="stSidebar"] > div > div > div { padding-top: 0 !important; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

section[data-testid="stSidebar"] {
    background: var(--sidebar) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .block-container { padding: 0 !important; }

.stButton > button {
    background: linear-gradient(135deg,#4776e6,#8e54e9) !important;
    color: white !important; font-weight: 700 !important;
    font-size: 13px !important; border: none !important;
    border-radius: 8px !important; padding: 10px 22px !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 15px rgba(71,118,230,0.4) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(71,118,230,0.5) !important;
}

[data-testid="stFileUploader"] {
    background: var(--card) !important;
    border: 2px dashed var(--border) !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploader"]:hover { border-color: #4776e6 !important; }

[data-testid="stDataFrame"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important; overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
    background: var(--bg2) !important; color: var(--text) !important;
    font-weight: 700 !important; font-size: 11px !important;
    text-transform: uppercase !important; letter-spacing: 0.5px !important;
}
[data-testid="stDataFrame"] td {
    color: var(--text) !important; font-size: 12px !important;
    border-bottom: 1px solid var(--border) !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--card) !important;
    border-radius: 10px 10px 0 0 !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 4px 4px 0 !important; gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: var(--muted) !important;
    font-size: 12px !important; font-weight: 500 !important;
    padding: 10px 18px !important; border-radius: 8px 8px 0 0 !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text) !important; }
.stTabs [aria-selected="true"] {
    background: var(--bg2) !important; color: #4776e6 !important;
    border-bottom: 2px solid #4776e6 !important; font-weight: 700 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important; padding: 16px !important;
}

.stTextInput>div>div>input,
.stSelectbox>div>div,
.stNumberInput>div>div>input,
.stTextArea>div>div>textarea {
    background: var(--bg2) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text) !important;
    font-size: 13px !important;
}
.stTextInput>div>div>input:focus { border-color: #4776e6 !important; }

.streamlit-expanderHeader {
    background: var(--card) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text) !important;
    font-weight: 600 !important; font-size: 13px !important;
}
.streamlit-expanderContent {
    background: var(--card) !important; border: 1px solid var(--border) !important;
    border-top: none !important; border-radius: 0 0 8px 8px !important;
}

.stSuccess { background: rgba(56,239,125,0.1) !important; border-color: #38ef7d !important; color: #38ef7d !important; border-radius: 8px !important; }
.stError   { background: rgba(255,65,108,0.1) !important; border-color: #ff416c !important; color: #ff9aa2 !important; border-radius: 8px !important; }
.stInfo    { background: rgba(71,118,230,0.1) !important; border-color: #4776e6 !important; color: #a0b4f5 !important; border-radius: 8px !important; }
.stWarning { background: rgba(247,151,30,0.1) !important; border-color: #f7971e !important; color: #ffd200 !important; border-radius: 8px !important; }

.stProgress > div > div { background: var(--bg2) !important; border-radius: 4px !important; }
.stProgress > div > div > div { background: linear-gradient(90deg,#4776e6,#8e54e9) !important; border-radius: 4px !important; }

@keyframes slide-in { from { opacity:0;transform:translateY(8px); } to { opacity:1;transform:translateY(0); } }
@keyframes bob      { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-7px); } }
@keyframes blink    { 0%,88%,100% { opacity:1; } 90%,98% { opacity:0; } }
@keyframes pulse-red  { 0%,100% { box-shadow:0 0 0 0 rgba(255,65,108,0.5); } 50% { box-shadow:0 0 0 6px rgba(255,65,108,0); } }
@keyframes pulse-blue { 0%,100% { box-shadow:0 0 0 0 rgba(71,118,230,0.4); } 50% { box-shadow:0 0 0 8px rgba(71,118,230,0); } }
@keyframes slide-up   { from { opacity:0;transform:translateY(12px); } to { opacity:1;transform:translateY(0); } }

.g-card {
    border-radius: 14px; padding: 20px 20px;
    color: white; position: relative; overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
    animation: slide-in 0.3s ease; cursor: default;
}
.g-card:hover { transform: translateY(-3px); }
.g-card::before {
    content: ''; position: absolute; top: -30%; right: -10%;
    width: 130px; height: 130px; border-radius: 50%;
    background: rgba(255,255,255,0.08);
}
.g-card::after {
    content: ''; position: absolute; bottom: -20%; right: 10%;
    width: 90px; height: 90px; border-radius: 50%;
    background: rgba(255,255,255,0.05);
}
.g-card .card-icon   { position: absolute; top: 16px; right: 16px; font-size: 30px; opacity: 0.7; }
.g-card .card-number { font-family: var(--font-mono); font-size: 42px; font-weight: 800; line-height: 1; margin-bottom: 6px; }
.g-card .card-label  { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; opacity: 0.85; }
.g-card .card-sub    { font-size: 11px; opacity: 0.65; margin-top: 10px; }
.g-card .mini-bar    { margin-top: 14px; height: 4px; border-radius: 2px; background: rgba(255,255,255,0.2); overflow: hidden; }
.g-card .mini-bar-fill { height: 100%; border-radius: 2px; background: rgba(255,255,255,0.7); }

.g-critical { background: var(--g-critical); box-shadow: 0 8px 32px rgba(255,65,108,0.35); }
.g-high     { background: var(--g-high);     box-shadow: 0 8px 32px rgba(247,151,30,0.35); }
.g-med      { background: var(--g-med);      box-shadow: 0 8px 32px rgba(17,153,142,0.35); }
.g-low      { background: var(--g-low);      box-shadow: 0 8px 32px rgba(71,118,230,0.35); }
.g-auto     { background: var(--g-auto);     box-shadow: 0 8px 32px rgba(142,84,233,0.35); }

.f-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 18px 18px;
    transition: all 0.2s; animation: slide-in 0.3s ease;
}
.f-card:hover { border-color: rgba(71,118,230,0.5); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
.f-card .fc-number { font-family: var(--font-mono); font-size: 34px; font-weight: 800; }
.f-card .fc-label  { font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.7px; }
.f-card .fc-trend  { font-size: 11px; margin-top: 8px; }

.chart-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 16px 20px;
    animation: slide-in 0.35s ease;
}
.chart-title { font-size: 14px; font-weight: 700; color: var(--text); }
.chart-sub   { font-size: 11px; color: var(--muted); margin-top: 2px; }

.apr-row {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;
    transition: border-color 0.2s;
}
.apr-row:hover { border-color: rgba(71,118,230,0.4); }
.apr-critical { border-left: 3px solid #ff416c; }
.apr-high     { border-left: 3px solid #f7971e; }
</style>
""", unsafe_allow_html=True)


def page_header(title: str, subtitle: str):
    """Render the standard SentinelIQ page header with breadcrumb and branding."""
    last_word = title.split()[-1] if len(title.split()) > 1 else title
    st.markdown(f"""
<div style='margin-bottom:20px;padding-bottom:14px;
border-bottom:1px solid rgba(71,118,230,0.2)'>
<div style='font-size:10px;color:#4a5580;font-weight:600;
text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>
🛡️ SentinelIQ &nbsp;›&nbsp; {last_word}
</div>
<h1 style='font-size:28px;font-weight:900;color:#a0b4f5;
margin:0 0 4px 0;letter-spacing:-0.5px;line-height:1.1'>
{title}
</h1>
<div style='font-size:12px;color:#4776e6;font-weight:600;
margin-bottom:2px'>{subtitle}</div>
<div style='font-size:10px;color:#4a5580'>
Developed by Group 9 || Cohort 1 2025-26
</div>
</div>
""", unsafe_allow_html=True)

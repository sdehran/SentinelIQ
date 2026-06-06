"""SentinelIQ Sidebar Component — Gradient Enterprise Theme."""

import streamlit as st


def render_sidebar():
    """Render the SentinelIQ sidebar with logo on top, then navigation buttons."""
    with st.sidebar:
        # ── LOGO (on top) ──
        logo_html = (
            "<div style='padding:16px 14px 14px;"
            "background:linear-gradient(160deg,#1a2050 0%,#2a3470 50%,#1e2448 100%);"
            "border-bottom:1px solid rgba(71,118,230,0.3);margin-bottom:6px'>"
            "<div style='display:flex;align-items:center;gap:12px;margin-bottom:12px'>"
            "<div style='width:48px;height:48px;flex-shrink:0;"
            "background:linear-gradient(135deg,#4776e6 0%,#6a54e9 50%,#8e54e9 100%);"
            "border-radius:14px;"
            "display:flex;align-items:center;justify-content:center;"
            "font-size:22px;"
            "box-shadow:0 6px 20px rgba(71,118,230,0.6),"
                       "0 0 0 3px rgba(71,118,230,0.2),"
                       "inset 0 1px 0 rgba(255,255,255,0.15)'>🛡️</div>"
            "<div>"
            "<div style='font-size:18px;font-weight:900;letter-spacing:-0.5px;"
            "background:linear-gradient(135deg,#7ab3ff,#b48fff,#7de8d8);"
            "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
            "background-clip:text;line-height:1'>SentinelIQ</div>"
            "<div style='font-size:8px;color:#5a6a9a;"
            "text-transform:uppercase;letter-spacing:1.5px;"
            "margin-top:3px;font-weight:600'>FRAUD INTELLIGENCE</div>"
            "</div>"
            "</div>"
            "<div style='height:1px;"
            "background:linear-gradient(90deg,transparent,rgba(71,118,230,0.5),rgba(142,84,233,0.4),transparent);"
            "margin-bottom:10px'></div>"
            "<div style='background:rgba(71,118,230,0.07);"
            "border:1px solid rgba(71,118,230,0.18);"
            "border-radius:8px;padding:6px 10px'>"
            "<div style='font-size:9px;color:#7b8ed4;font-weight:700;"
            "margin-bottom:2px;text-transform:uppercase;letter-spacing:0.5px'>"
            "AI Fraud Transaction Investigation Assistant</div>"
            "<div style='font-size:8px;color:#5a6a8a;line-height:1.4'>"
            "<b style='color:#8e9fdb'>Developed by Group 9</b>"
            " || Cohort 1 2025-26"
            "</div>"
            "</div>"
            "</div>"
        )
        st.markdown(logo_html, unsafe_allow_html=True)

        # ── NAVIGATION BUTTONS ──
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        # Map page IDs to actual file paths for st.switch_page
        # Paths are relative to the main app's pages directory
        nav_items = [
            ("📊", "Investigation Dashboard", None),  # Main page = rerun
            ("🔍", "Fraud Network Graph", "pages/2_Network_Graph.py"),
            ("💬", "NL Query", "pages/3_NL_Query.py"),
            ("🧠", "Pattern Memory", "pages/4_Pattern_Memory.py"),
            ("⚙️", "Settings", "pages/5_Settings.py"),
        ]

        for icon, label, page_path in nav_items:
            if st.button(
                f"{icon}  {label}", key=f"nav_{label}",
                use_container_width=True
            ):
                if page_path is None:
                    # Main dashboard - just rerun
                    st.switch_page("streamlit_app.py")
                else:
                    st.switch_page(page_path)

"""SentinelIQ — Network Graph Page — Gradient Enterprise Theme.

AI Fraud Transaction Investigation Assistant
Developed by Group 9 || Cohort 1 2025-26
"""

import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import plotly.graph_objects as go
import random

from ui.styles import inject_styles, page_header
from ui.components.sidebar import render_sidebar

# ── Inject Theme ──
inject_styles()
render_sidebar()

# ── Page Header ──
page_header("🔍 Fraud Network Analysis",
            "Cross-bank transaction connections · 4 institutions")

# ── Summary Cards ──
graph = st.session_state.get("network_graph")
if graph is not None and hasattr(graph, "number_of_nodes"):
    total_nodes = graph.number_of_nodes()
    total_edges = graph.number_of_edges()
    # Simple cycle detection for fraud rings
    import networkx as nx
    try:
        cycles = list(nx.simple_cycles(graph))
        fraud_rings = len([c for c in cycles if len(c) >= 3])
        circular_chains = len([c for c in cycles if len(c) == 2])
    except Exception:
        fraud_rings = 0
        circular_chains = 0
else:
    total_nodes = 0
    total_edges = 0
    fraud_rings = 0
    circular_chains = 0

c1, c2, c3, c4 = st.columns(4, gap="small")
for col, lbl, val, cls in [
    (c1, "Total Nodes", str(total_nodes), "g-low"),
    (c2, "Total Edges", str(total_edges), "g-auto"),
    (c3, "Fraud Rings", str(fraud_rings), "g-critical"),
    (c4, "Circular Chains", str(circular_chains), "g-high"),
]:
    with col:
        st.markdown(f"""
        <div class='g-card {cls}' style='padding:14px 16px'>
            <div class='card-number' style='font-size:28px'>{val}</div>
            <div class='card-label'>{lbl}</div>
            <div class='mini-bar' style='margin-top:8px'>
                <div class='mini-bar-fill' style='width:60%'></div>
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Legend + Graph ──
c_leg, c_graph = st.columns([1, 4], gap="medium")

with c_leg:
    st.markdown("""
    <div class='chart-card' style='min-height:500px;display:flex;flex-direction:column;justify-content:space-between'>
        <div>
        <div class='chart-title' style='margin-bottom:16px'>Legend</div>
        <div style='font-size:10px;color:#8892b0;text-transform:uppercase;
        letter-spacing:0.5px;margin-bottom:10px'>Bank Nodes</div>
        <div style='display:flex;flex-direction:column;gap:10px;margin-bottom:20px'>
            <div style='display:flex;align-items:center;gap:8px'>
                <div style='width:12px;height:12px;background:#4776e6;border-radius:50%'></div>
                <span style='color:#8892b0;font-size:12px'>HDFC</span>
            </div>
            <div style='display:flex;align-items:center;gap:8px'>
                <div style='width:12px;height:12px;background:#38ef7d;border-radius:50%'></div>
                <span style='color:#8892b0;font-size:12px'>SBI</span>
            </div>
            <div style='display:flex;align-items:center;gap:8px'>
                <div style='width:12px;height:12px;background:#f7971e;border-radius:50%'></div>
                <span style='color:#8892b0;font-size:12px'>ICICI</span>
            </div>
            <div style='display:flex;align-items:center;gap:8px'>
                <div style='width:12px;height:12px;background:#ff416c;border-radius:50%'></div>
                <span style='color:#8892b0;font-size:12px'>Axis</span>
            </div>
            <div style='display:flex;align-items:center;gap:8px'>
                <div style='width:12px;height:12px;background:#4a5580;border-radius:3px'></div>
                <span style='color:#8892b0;font-size:12px'>Merchant</span>
            </div>
        </div>
        <div style='font-size:10px;color:#8892b0;text-transform:uppercase;
        letter-spacing:0.5px;margin-bottom:10px'>Detections</div>
        <div style='display:flex;flex-direction:column;gap:8px;font-size:11px;margin-bottom:20px'>
            <div style='color:#ff416c;font-weight:600'>💀 Money Mule (degree>5)</div>
            <div style='color:#f7971e;font-weight:600'>🎯 Hub Merchant</div>
            <div style='color:#ffd200;font-weight:600'>🔄 Circular Chain</div>
            <div style='color:#8892b0'>⬡ Normal Node</div>
        </div>
        </div>
        <div style='border-top:1px solid #2e3a6e;padding-top:12px;font-size:10px;color:#4a5580'>
        Nodes: accounts & merchants<br>
        Edges: transaction flows<br>
        Hover for details
        </div>
    </div>""", unsafe_allow_html=True)

with c_graph:
    if graph is not None and hasattr(graph, "number_of_nodes") and graph.number_of_nodes() > 0:
        # Render real graph using PyVis with physics disabled after stabilization
        try:
            from pyvis.network import Network
            import tempfile
            import os
            import networkx as nx_lib

            net = Network(height="500px", width="100%", bgcolor="#1e2448",
                         font_color="#e8eaf6")
            # Physics: stabilize then stop
            net.set_options("""
            {
                "physics": {
                    "enabled": true,
                    "stabilization": {
                        "enabled": true,
                        "iterations": 150,
                        "fit": true
                    },
                    "barnesHut": {
                        "gravitationalConstant": -4000,
                        "springLength": 150,
                        "springConstant": 0.03
                    }
                },
                "interaction": {
                    "hover": true,
                    "zoomView": true,
                    "dragView": true
                }
            }
            """)

            BCOL = {"HDFC": "#4776e6", "SBI": "#38ef7d",
                    "ICICI": "#f7971e", "Axis": "#ff416c"}

            # Only show SUSPICIOUS nodes: high degree (>3) + their neighbors
            suspicious_nodes = set()
            for node, degree in graph.degree():
                if degree > 3:
                    suspicious_nodes.add(node)
                    for neighbor in graph.neighbors(node):
                        suspicious_nodes.add(neighbor)
                    if graph.is_directed():
                        for pred in graph.predecessors(node):
                            suspicious_nodes.add(pred)

            # If no suspicious nodes, show top 40 by degree
            if len(suspicious_nodes) < 5:
                top_nodes = sorted(graph.degree(), key=lambda x: x[1], reverse=True)[:40]
                suspicious_nodes = set(n for n, d in top_nodes)
                for n in list(suspicious_nodes):
                    for neighbor in graph.neighbors(n):
                        suspicious_nodes.add(neighbor)

            # Cap at 80 nodes for readability
            if len(suspicious_nodes) > 80:
                sorted_by_deg = sorted(
                    suspicious_nodes,
                    key=lambda n: graph.degree(n),
                    reverse=True
                )
                suspicious_nodes = set(sorted_by_deg[:80])

            # Add filtered nodes with detailed titles
            for node_id in suspicious_nodes:
                data = graph.nodes.get(node_id, {})
                bank = data.get("bank", "")
                node_type = data.get("type", "account")
                degree = graph.degree(node_id)
                color = BCOL.get(bank, "#4a5580")

                # Build tooltip with connected transactions
                connections = []
                if graph.is_directed():
                    for _, target, edata in graph.out_edges(node_id, data=True):
                        amt = edata.get("amount", "?")
                        connections.append(f"→ {target} (₹{amt})")
                    for source, _, edata in graph.in_edges(node_id, data=True):
                        amt = edata.get("amount", "?")
                        connections.append(f"← {source} (₹{amt})")
                conn_text = "\n".join(connections[:8])
                if len(connections) > 8:
                    conn_text += f"\n... +{len(connections)-8} more"

                title_text = (
                    f"{'━' * 30}\n"
                    f"  {node_id}\n"
                    f"  Bank: {bank}\n"
                    f"  Type: {node_type}\n"
                    f"  Connections: {degree}\n"
                    f"{'━' * 30}\n"
                    f"  TRANSACTION PATHS:\n"
                    f"{conn_text}"
                )

                # Highlight high-degree nodes
                if degree > 5:
                    color = "#ff416c"
                    size = 28
                    label = f"⚠️ {str(node_id)[:10]}"
                elif degree > 3:
                    size = 20
                    label = str(node_id)[:12]
                else:
                    size = 12
                    label = str(node_id)[:10]

                net.add_node(str(node_id), label=label,
                            color=color, size=size, title=title_text)

            # Add edges with transaction details as labels
            for u, v, edata in graph.edges(data=True):
                if u in suspicious_nodes and v in suspicious_nodes:
                    amt = edata.get("amount", "")
                    edge_title = f"{u} → {v}"
                    if amt:
                        edge_title += f"\nAmount: ₹{amt:,.0f}" if isinstance(amt, (int, float)) else f"\nAmount: ₹{amt}"
                    # Color edges by amount size
                    if isinstance(amt, (int, float)) and amt >= 40000:
                        edge_color = "rgba(255,65,108,0.7)"
                        width = 2.5
                    elif isinstance(amt, (int, float)) and amt >= 20000:
                        edge_color = "rgba(247,151,30,0.6)"
                        width = 2
                    else:
                        edge_color = "rgba(71,118,230,0.4)"
                        width = 1.2
                    net.add_edge(str(u), str(v),
                                color=edge_color, width=width, title=edge_title)

            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=".html", mode="w"
            )
            net.save_graph(tmp.name)
            tmp.close()
            with open(tmp.name, "r") as f:
                html_content = f.read()
            os.unlink(tmp.name)

            import streamlit.components.v1 as components
            # Inject script to disable physics after stabilization
            stabilize_script = """
<script>
setTimeout(function() {
    try {
        network.setOptions({physics: {enabled: false}});
    } catch(e) {
        try {
            var container = document.getElementById('mynetwork');
            if (container && container._vis_network) {
                container._vis_network.setOptions({physics: {enabled: false}});
            }
        } catch(e2) {}
    }
}, 4000);
</script>
"""
            html_content = html_content.replace("</body>", stabilize_script + "</body>")
            components.html(html_content, height=520, scrolling=False)
        except ImportError:
            st.warning("PyVis not installed. Showing Plotly placeholder.")
            _show_placeholder = True
        except Exception as e:
            st.warning(f"Graph rendering error: {e}")
            _show_placeholder = True
        else:
            _show_placeholder = False

        if "_show_placeholder" in dir() and _show_placeholder:
            pass  # handled below
    else:
        _show_placeholder = True

    if "_show_placeholder" not in dir() or _show_placeholder:
        # Placeholder with Plotly (like the template)
        random.seed(99)
        BANKS = ["HDFC", "SBI", "ICICI", "Axis"]
        BCOL = {"HDFC": "#4776e6", "SBI": "#38ef7d",
                "ICICI": "#f7971e", "Axis": "#ff416c"}
        nx_, ny_, nc_, ns_, nl_ = [], [], [], [], []
        for i in range(22):
            b = random.choice(BANKS)
            nx_.append(random.uniform(0, 10))
            ny_.append(random.uniform(0, 10))
            nc_.append(BCOL[b])
            ns_.append(random.choice([14, 14, 14, 22]))
            nl_.append(f"ACC_{i:03d}")
        for i in range(5):
            nx_.append(random.uniform(2, 8))
            ny_.append(random.uniform(2, 8))
            nc_.append("#4a5580")
            ns_.append(18)
            nl_.append(f"MER_{i:03d}")
        ex, ey = [], []
        for _ in range(28):
            a, b = random.randint(0, 21), random.randint(0, 26)
            ex += [nx_[a], nx_[b], None]
            ey += [ny_[a], ny_[b], None]

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=ex, y=ey, mode="lines",
            line=dict(width=0.8, color="rgba(71,118,230,0.3)"),
            hoverinfo="none",
        ))
        for _ in range(4):
            a, b = random.randint(0, 10), random.randint(11, 21)
            fig3.add_trace(go.Scatter(
                x=[nx_[a], nx_[b], None], y=[ny_[a], ny_[b], None],
                mode="lines",
                line=dict(width=2.5, color="#ffd200", dash="dot"),
                hoverinfo="none", showlegend=False,
            ))
        fig3.add_trace(go.Scatter(
            x=nx_, y=ny_, mode="markers+text",
            marker=dict(size=ns_, color=nc_,
                       line=dict(color="#1a1f3a", width=2)),
            text=[l if i < 5 else "" for i, l in enumerate(nl_)],
            textposition="top center",
            textfont=dict(size=8, color="#8892b0"),
            hovertemplate="<b>%{text}</b><extra></extra>",
        ))
        fig3.add_trace(go.Scatter(
            x=[nx_[3]], y=[ny_[3]], mode="markers",
            marker=dict(
                size=38, color="rgba(255,65,108,0.15)",
                line=dict(color="#ff416c", width=2),
            ),
            hovertemplate="💀 Relay Node (Money Mule)<extra></extra>",
            showlegend=False,
        ))
        fig3.update_layout(
            showlegend=False,
            plot_bgcolor="#1e2448", paper_bgcolor="#232b52",
            height=400, margin=dict(t=10, b=10, l=10, r=10),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        )
        st.plotly_chart(fig3, use_container_width=True,
                        config={"displayModeBar": False})

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ── OBSERVATIONS — Only suspicious transactions from the network ──
st.markdown("""
<div style='font-size:10px;font-weight:700;color:#8892b0;
text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>
▸ SUSPICIOUS TRANSACTIONS IN NETWORK
</div>""", unsafe_allow_html=True)

# Build list of suspicious transactions based on network analysis
suspect_txns = []
if graph is not None and hasattr(graph, "number_of_nodes") and graph.number_of_nodes() > 0:
    import networkx as nx

    # Get workflow results for transaction details
    workflow_results = st.session_state.get("workflow_results", {})
    routed = workflow_results.get("routed_transactions", [])

    # Build lookup: account_id → list of routed transactions
    acct_txns = {}
    for rt in routed:
        acct = rt.scored.enriched.row.account_id
        if acct not in acct_txns:
            acct_txns[acct] = []
        acct_txns[acct].append(rt)

    # Find suspicious accounts from graph (degree > 3)
    suspicious_accounts = []
    for node, degree in graph.degree():
        node_data = graph.nodes.get(node, {})
        if node_data.get("type") == "account" and degree > 3:
            suspicious_accounts.append((node, degree))

    suspicious_accounts.sort(key=lambda x: x[1], reverse=True)

    for acct_id, degree in suspicious_accounts[:15]:
        txns = acct_txns.get(acct_id, [])
        # Get only CRITICAL/HIGH/MED transactions for this account
        risky_txns = [t for t in txns if t.tier in ("CRITICAL", "HIGH_QUEUE")]
        if not risky_txns:
            risky_txns = [t for t in txns if t.scored.final_score >= 40]

        for rt in risky_txns[:2]:
            s = rt.scored
            bank = s.enriched.row.bank_name
            amount = s.enriched.row.amount
            score = s.final_score
            tier = rt.tier
            reason = s.llm_score.reason[:70]
            flags = s.enriched.flags.active_count

            # Determine severity color
            if tier == "CRITICAL":
                color = "#ff416c"
                severity = "CRITICAL"
                icon = "🚨"
            elif tier == "HIGH_QUEUE":
                color = "#f7971e"
                severity = "HIGH"
                icon = "⚠️"
            else:
                color = "#8e54e9"
                severity = "SUSPECT"
                icon = "🔍"

            # Get connected nodes for path display
            neighbors = []
            if graph.is_directed():
                for _, target, edata in graph.out_edges(acct_id, data=True):
                    neighbors.append(f"→ {target}")
                for source, _, edata in graph.in_edges(acct_id, data=True):
                    neighbors.append(f"← {source}")
            path_str = " · ".join(neighbors[:4])
            if len(neighbors) > 4:
                path_str += f" (+{len(neighbors)-4})"

            suspect_txns.append({
                "icon": icon,
                "severity": severity,
                "color": color,
                "txn_id": s.enriched.row.transaction_id,
                "account": acct_id,
                "bank": bank,
                "amount": amount,
                "score": score,
                "flags": flags,
                "degree": degree,
                "reason": reason,
                "path": path_str,
            })

    if not suspect_txns:
        suspect_txns.append({
            "icon": "✅", "severity": "CLEAR", "color": "#38ef7d",
            "txn_id": "—", "account": "—", "bank": "—",
            "amount": 0, "score": 0, "flags": 0, "degree": 0,
            "reason": "No high-risk nodes detected in transaction network",
            "path": "—",
        })
else:
    suspect_txns.append({
        "icon": "ℹ️", "severity": "INFO", "color": "#4776e6",
        "txn_id": "—", "account": "—", "bank": "—",
        "amount": 0, "score": 0, "flags": 0, "degree": 0,
        "reason": "Run an investigation to analyze the network",
        "path": "—",
    })

# Render in a scrollable container
obs_html = (
    "<div style='background:var(--card);border:1px solid var(--border);"
    "border-radius:12px;padding:16px;max-height:320px;overflow-y:auto'>"
    f"<div style='font-size:12px;font-weight:700;color:#e8eaf6;"
    f"margin-bottom:12px'>🔗 {len(suspect_txns)} suspicious transaction(s) "
    f"identified in network</div>"
)

for t in suspect_txns:
    obs_html += f"""
<div style='background:var(--bg2);border:1px solid var(--border);
border-left:3px solid {t['color']};border-radius:8px;
padding:12px 14px;margin-bottom:8px'>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:6px'>
    <span style='font-size:14px'>{t['icon']}</span>
    <span style='color:{t['color']};font-weight:700;font-size:11px'>{t['severity']}</span>
    <span style='color:#e8eaf6;font-family:monospace;font-weight:700;font-size:12px'>{t['txn_id']}</span>
    <span style='color:#8892b0;font-size:10px'>Score: {t['score']}</span>
  </div>
  <div style='display:flex;gap:12px;margin-bottom:6px;font-size:11px'>
    <span style='color:#8892b0'>Account: <b style="color:#e8eaf6">{t['account']}</b></span>
    <span style='color:#8892b0'>Bank: <b style="color:#e8eaf6">{t['bank']}</b></span>
    <span style='color:#8892b0'>₹{t['amount']:,.0f}</span>
    <span style='color:#8892b0'>Flags: <b style="color:#f7971e">{t['flags']}</b></span>
    <span style='color:#8892b0'>Degree: <b style="color:#ff416c">{t['degree']}</b></span>
  </div>
  <div style='color:#a0b8d4;font-size:11px;margin-bottom:4px'>{t['reason']}</div>
  <div style='color:#4776e6;font-size:10px;font-family:monospace'>
  Path: {t['path']}</div>
</div>"""

obs_html += "</div>"
st.markdown(obs_html, unsafe_allow_html=True)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ── 3 Findings Cards ──
f1, f2, f3 = st.columns(3, gap="small")
findings = [
    (f1, "g-critical", "💀 Money Mule", "Relay Node Detected",
     "Multiple accounts funneling funds through a single relay account "
     "with rapid forwarding pattern.",
     "Score: 96 CRITICAL"),
    (f2, "g-high", "🎯 Fraud Ring", "Multi-Account Pattern",
     "Several accounts sending near-identical amounts to the same "
     "merchant within a short time window.",
     "Multi-bank coordination"),
    (f3, "g-auto", "🔄 Circular Chain", "Revenue Inflation",
     "Funds circulating between accounts across banks with no net "
     "economic purpose. Suspected revenue inflation.",
     "Cycle: 2-3 hops"),
]
for col, cls, title, sub, desc, extra in findings:
    with col:
        st.markdown(f"""
        <div class='g-card {cls}' style='padding:16px 18px'>
            <div style='font-size:14px;font-weight:800;margin-bottom:4px'>{title}</div>
            <div style='font-size:12px;font-weight:600;margin-bottom:6px;opacity:0.9'>{sub}</div>
            <div style='font-size:11px;opacity:0.75;line-height:1.5;margin-bottom:8px'>{desc}</div>
            <div style='font-size:10px;font-weight:700;opacity:0.9'>{extra}</div>
            <div class='mini-bar'><div class='mini-bar-fill' style='width:75%'></div></div>
        </div>""", unsafe_allow_html=True)

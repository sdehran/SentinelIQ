"""SentinelIQ Floating Chatbot Widget — Gradient Enterprise Theme."""

import streamlit as st
import streamlit.components.v1 as components


def render_chatbot():
    """Render the floating chatbot widget at bottom-right using an HTML component."""
    # Read counts from session state when available
    crit = 0
    high = 0
    med = 0
    auto = 0
    ar = 0.0

    if "workflow_results" in st.session_state:
        results = st.session_state["workflow_results"]
        stats = results.get("summary_stats")
        if stats:
            crit = stats.critical_count
            high = stats.high_count
            med = stats.med_count
            auto = stats.auto_cleared_count
            ar = round(stats.autonomy_rate * 100, 1)

    chatbot_html = f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}}
body{{background:transparent;overflow:hidden}}
#w{{position:fixed;bottom:0;right:0;padding:24px;z-index:9999}}
#robot-popup{{position:absolute;bottom:76px;right:24px;
display:none;text-align:center;animation:bob 2s ease-in-out infinite}}
#rf{{width:52px;height:52px;background:linear-gradient(135deg,#1e2448,#2a3060);
border:2px solid #4776e6;border-radius:14px;margin:0 auto 4px;
display:flex;flex-direction:column;align-items:center;justify-content:center;
gap:3px;box-shadow:0 0 20px rgba(71,118,230,0.6);position:relative}}
.ant{{width:2px;height:12px;background:#4776e6;
position:absolute;top:-12px;left:50%;transform:translateX(-50%)}}
.ant::after{{content:'';width:7px;height:7px;
background:linear-gradient(135deg,#4776e6,#8e54e9);border-radius:50%;
position:absolute;top:-5px;left:-2.5px;
animation:blink 1.5s ease-in-out infinite;box-shadow:0 0 8px #4776e6}}
.eyes{{display:flex;gap:7px}}
.eye{{width:9px;height:9px;background:linear-gradient(135deg,#4776e6,#8e54e9);
border-radius:50%;animation:blink 4s ease-in-out infinite;box-shadow:0 0 6px #4776e6}}
.mouth{{width:18px;height:3px;background:linear-gradient(90deg,#4776e6,#8e54e9);border-radius:2px}}
#tt{{background:linear-gradient(135deg,#1e2448,#2a3060);
color:#e8eaf6;font-size:10px;font-weight:700;padding:5px 10px;
border-radius:8px;white-space:nowrap;
box-shadow:0 4px 15px rgba(71,118,230,0.4);border:1px solid rgba(71,118,230,0.3)}}
#btn{{width:62px;height:62px;border-radius:50%;
background:linear-gradient(135deg,#4776e6,#8e54e9);
border:none;cursor:pointer;font-size:24px;position:relative;
box-shadow:0 0 24px rgba(71,118,230,0.6);transition:transform 0.2s,box-shadow 0.2s;
display:flex;align-items:center;justify-content:center;animation:pulse-blue 3s infinite}}
#btn:hover{{transform:scale(1.12);box-shadow:0 0 36px rgba(71,118,230,0.8)}}
#badge{{position:absolute;top:-4px;right:-4px;
background:linear-gradient(135deg,#ff416c,#ff4b2b);color:white;
font-size:10px;font-weight:800;width:22px;height:22px;border-radius:50%;
display:flex;align-items:center;justify-content:center;
animation:pulse-red 1.5s infinite;border:2px solid #1a1f3a}}
#btn:hover~#robot-popup{{display:block}}
#panel{{position:fixed;bottom:96px;right:24px;width:370px;height:490px;
background:linear-gradient(135deg,#1e2448,#232b52);
border:1px solid rgba(71,118,230,0.3);border-radius:14px;
display:none;flex-direction:column;overflow:hidden;
box-shadow:0 24px 60px rgba(0,0,0,0.6);z-index:9998;animation:slide-up 0.25s ease}}
#panel.open{{display:flex}}
#ph{{background:linear-gradient(135deg,#1a1f3a,#2a3060);padding:12px 16px;
display:flex;align-items:center;gap:10px;border-bottom:1px solid #2e3a6e;flex-shrink:0}}
#pa{{width:34px;height:34px;background:linear-gradient(135deg,rgba(71,118,230,0.2),rgba(142,84,233,0.2));
border:1px solid rgba(71,118,230,0.4);border-radius:50%;
display:flex;align-items:center;justify-content:center;font-size:16px}}
#pn{{color:#e8eaf6;font-weight:800;font-size:13px}}
#ps{{color:#38ef7d;font-size:10px;margin-top:1px}}
#pc{{margin-left:auto;background:none;border:none;color:#4a5580;cursor:pointer;font-size:20px}}
#pc:hover{{color:#e8eaf6}}
#msgs{{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}}
#msgs::-webkit-scrollbar{{width:4px}}
#msgs::-webkit-scrollbar-thumb{{background:#2e3a6e;border-radius:2px}}
.ai-m{{display:flex;gap:8px;align-items:flex-start}}
.ai-av{{width:26px;height:26px;min-width:26px;
background:linear-gradient(135deg,rgba(71,118,230,0.2),rgba(142,84,233,0.2));
border:1px solid rgba(71,118,230,0.3);border-radius:50%;
display:flex;align-items:center;justify-content:center;font-size:12px}}
.ai-b{{background:rgba(30,36,72,0.8);border:1px solid #2e3a6e;
border-radius:0 10px 10px 10px;padding:9px 13px;font-size:11px;color:#e8eaf6;max-width:86%;line-height:1.6}}
.u-m{{display:flex;justify-content:flex-end}}
.u-b{{background:linear-gradient(135deg,rgba(71,118,230,0.2),rgba(142,84,233,0.15));
border:1px solid rgba(71,118,230,0.25);border-radius:10px 0 10px 10px;
padding:9px 13px;font-size:11px;color:#a0b4f5;max-width:86%}}
#chips{{padding:8px 14px;border-top:1px solid #2e3a6e;
display:flex;gap:5px;flex-wrap:wrap;background:#1a1f3a;flex-shrink:0}}
.chip{{font-size:10px;background:#232b52;border:1px solid #2e3a6e;
color:#8892b0;padding:4px 9px;border-radius:14px;cursor:pointer;transition:all 0.15s}}
.chip:hover{{color:#4776e6;border-color:rgba(71,118,230,0.4)}}
#ia{{padding:10px 14px;border-top:1px solid #2e3a6e;
display:flex;gap:8px;background:#1e2448;flex-shrink:0}}
#inp{{flex:1;background:#232b52;border:1px solid #2e3a6e;border-radius:8px;
padding:8px 12px;color:#e8eaf6;font-size:11px;outline:none}}
#inp:focus{{border-color:rgba(71,118,230,0.5)}}
#send{{background:linear-gradient(135deg,#4776e6,#8e54e9);color:white;
border:none;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer;font-size:14px}}
#send:hover{{transform:translateY(-1px)}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-7px)}}}}
@keyframes blink{{0%,88%,100%{{opacity:1}}90%,98%{{opacity:0}}}}
@keyframes pulse-red{{0%,100%{{box-shadow:0 0 0 0 rgba(255,65,108,0.5)}}50%{{box-shadow:0 0 0 6px rgba(255,65,108,0)}}}}
@keyframes pulse-blue{{0%,100%{{box-shadow:0 0 0 0 rgba(71,118,230,0.4)}}50%{{box-shadow:0 0 0 8px rgba(71,118,230,0)}}}}
@keyframes slide-up{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
</style></head><body>
<div id="w">
  <div style="position:relative">
    <button id="btn" onclick="toggleChat()">🛡️<div id="badge">{crit}</div></button>
    <div id="robot-popup">
      <div style="display:flex;flex-direction:column;align-items:center">
        <div id="rf"><div class="ant"></div>
          <div class="eyes"><div class="eye"></div><div class="eye"></div></div>
          <div class="mouth"></div></div>
        <div id="tt">Ask me anything!</div>
      </div>
    </div>
  </div>
</div>
<div id="panel">
  <div id="ph">
    <div id="pa">🛡️</div>
    <div><div id="pn">SentinelIQ</div><div id="ps">● Online</div></div>
    <button id="pc" onclick="toggleChat()">×</button>
  </div>
  <div id="msgs">
    <div class="ai-m"><div class="ai-av">🤖</div>
    <div class="ai-b">👋 Hello! I'm SentinelIQ.<br><br>
      🚨 <b style="color:#ff416c">{crit} CRITICAL</b><br>
      ⚠️ <b style="color:#f7971e">{high} HIGH</b><br>
      📋 <b style="color:#38ef7d">{med} MED</b><br>
      ✅ <b style="color:#4776e6">{auto} AUTO-CLEARED</b><br><br>
      🤖 Autonomy: <b style="color:#8e54e9">{ar}%</b></div></div>
  </div>
  <div id="chips">
    <span class="chip" onclick="ask('CRITICAL')">🚨 CRITICAL</span>
    <span class="chip" onclick="ask('Autonomy')">🤖 Autonomy</span>
    <span class="chip" onclick="ask('Pattern')">🎯 Pattern</span>
    <span class="chip" onclick="ask('Help')">❓ Help</span>
  </div>
  <div id="ia">
    <input id="inp" placeholder="Ask about your transactions..."
           onkeypress="if(event.key==='Enter')send()"/>
    <button id="send" onclick="send()">→</button>
  </div>
</div>
<script>
var open=false;
function toggleChat(){{open=!open;var p=document.getElementById('panel');
if(open){{p.classList.add('open');document.getElementById('inp').focus()}}
else p.classList.remove('open')}}
function ask(q){{document.getElementById('inp').value=q;send()}}
function send(){{var inp=document.getElementById('inp');
var msgs=document.getElementById('msgs');var q=inp.value.trim();if(!q)return;
msgs.innerHTML+='<div class="u-m"><div class="u-b">'+q+'</div></div>';
var a='For full analysis use the NL Query page.';
setTimeout(function(){{msgs.innerHTML+='<div class="ai-m"><div class="ai-av">🤖</div><div class="ai-b">'+a+'</div></div>';
msgs.scrollTop=msgs.scrollHeight}},400);inp.value='';msgs.scrollTop=msgs.scrollHeight}}
</script></body></html>"""

    components.html(chatbot_html, height=1, scrolling=False)

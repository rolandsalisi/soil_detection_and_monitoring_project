"""
app.py  –  AgriSense IoT Agriculture Dashboard
================================================
Features:
  - Live ESP32 sensor data (temperature, humidity, soil moisture, light)
  - Plant category recommendations (leafy greens, root crops, fruiting plants)
  - Full green theme with light / dark mode toggle
  - Persistent floating hamburger button (always visible)
"""

import streamlit as st
import requests
import time
import math
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from plant_advisor import get_plant_recommendations, classify_conditions

# ── Page Configuration ────────────────────────────────────────
st.set_page_config(
    page_title="AgriSense – IoT Agriculture Monitor",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State ─────────────────────────────────────────────
if "history"      not in st.session_state: st.session_state.history      = []
if "use_demo"     not in st.session_state: st.session_state.use_demo     = False
if "auto_refresh" not in st.session_state: st.session_state.auto_refresh = True
if "dark_mode"    not in st.session_state: st.session_state.dark_mode    = False

# ── Constants ─────────────────────────────────────────────────
SERVER_URL   = "http://localhost:8000"
REFRESH_SECS = 5

# ── Theme Palettes ────────────────────────────────────────────
LIGHT = {
    "bg":           "#f0fdf4",
    "bg2":          "#dcfce7",
    "sidebar_bg":   "#d1fae5",
    "card_bg":      "#ffffff",
    "card_shadow":  "0 2px 16px rgba(21,128,61,0.10)",
    "text":         "#14532d",
    "text2":        "#166534",
    "text_muted":   "#4b7c5f",
    "border":       "#bbf7d0",
    "accent":       "#16a34a",
    "accent2":      "#22c55e",
    "hero_grad":    "linear-gradient(135deg, #14532d 0%, #166534 45%, #22c55e 100%)",
    "plot_bg":      "rgba(0,0,0,0)",
    "grid_color":   "#d1fae5",
    "toggle_icon":  "🌙",
    "toggle_label": "Dark Mode",
}
DARK = {
    "bg":           "#0a1f10",
    "bg2":          "#0f2d17",
    "sidebar_bg":   "#0d2414",
    "card_bg":      "#122b1a",
    "card_shadow":  "0 2px 16px rgba(0,0,0,0.40)",
    "text":         "#bbf7d0",
    "text2":        "#86efac",
    "text_muted":   "#6ee7a0",
    "border":       "#166534",
    "accent":       "#22c55e",
    "accent2":      "#4ade80",
    "hero_grad":    "linear-gradient(135deg, #052e16 0%, #14532d 45%, #166534 100%)",
    "plot_bg":      "rgba(0,0,0,0)",
    "grid_color":   "#14532d",
    "toggle_icon":  "☀️",
    "toggle_label": "Light Mode",
}

T = DARK if st.session_state.dark_mode else LIGHT

# ── Plant card backgrounds (need Python bool, not f-string logic) ──
if st.session_state.dark_mode:
    CARD_BG_GOOD = "linear-gradient(145deg,#0d2414,#122b1a)"
    CARD_BG_MOD  = "linear-gradient(145deg,#1a1500,#2a2000)"
    CARD_BG_POOR = "linear-gradient(145deg,#1c0a00,#2d1200)"
    CARD_BD_MOD  = "#713f12"
    CARD_BD_POOR = "#7c2d12"
    STATUS_LIVE_BG    = "#052e16"
    STATUS_OFFLINE_BG = "#2d0808"
    STATUS_DEMO_BG    = "#1c1500"
else:
    CARD_BG_GOOD = "linear-gradient(145deg,#f0fdf4,#dcfce7)"
    CARD_BG_MOD  = "linear-gradient(145deg,#fefce8,#fef9c3)"
    CARD_BG_POOR = "linear-gradient(145deg,#fff7ed,#ffedd5)"
    CARD_BD_MOD  = "#fde68a"
    CARD_BD_POOR = "#fed7aa"
    STATUS_LIVE_BG    = "#dcfce7"
    STATUS_OFFLINE_BG = "#fee2e2"
    STATUS_DEMO_BG    = "#fef9c3"

# ── Inject CSS + Floating Hamburger ──────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500;600&display=swap');

  html, body, [class*="css"], .stApp {{
    font-family: 'Inter', sans-serif;
    background-color: {T['bg']} !important;
    color: {T['text']} !important;
  }}
  h1,h2,h3,h4 {{ font-family: 'Playfair Display', serif; color: {T['text']} !important; }}

  /* ── Hide ALL Streamlit chrome including native hamburger ── */
  #MainMenu, footer {{ visibility: hidden !important; height: 0 !important; }}
  header {{ visibility: hidden !important; height: 0 !important; }}
  [data-testid="collapsedControl"] {{ display: none !important; }}

  /* ── Floating hamburger — always on top, always visible ── */
  #agri-burger {{
    position: fixed;
    top: 14px;
    left: 14px;
    z-index: 999999;
    width: 42px;
    height: 42px;
    background: {T['accent']};
    border: none;
    border-radius: 10px;
    cursor: pointer;
    display: flex !important;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 5px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.30);
    transition: background 0.2s, transform 0.15s;
  }}
  #agri-burger:hover {{ background: {T['text2']}; transform: scale(1.07); }}
  #agri-burger .bar {{
    display: block;
    width: 20px;
    height: 2.5px;
    background: white;
    border-radius: 3px;
    transition: all 0.28s ease;
  }}

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {{
    background: {T['sidebar_bg']} !important;
    border-right: 1px solid {T['border']} !important;
  }}
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] div,
  [data-testid="stSidebar"] span {{
    color: {T['text']} !important;
  }}

  /* ── Main content ── */
  .main .block-container {{
    padding-top: 3.8rem !important;
    background: {T['bg']} !important;
  }}

  /* ── Hero ── */
  .hero-header {{
    background: {T['hero_grad']};
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.2rem;
  }}
  .hero-header h1 {{ font-size: 2.2rem; margin: 0; color: white !important; letter-spacing: -0.02em; }}
  .hero-header p  {{ opacity: 0.88; margin: 0.4rem 0 0; font-size: 1rem; color: white !important; }}

  /* ── Metric cards ── */
  .metric-card {{
    background: {T['card_bg']};
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    box-shadow: {T['card_shadow']};
    border-left: 5px solid;
    margin-bottom: 0.8rem;
  }}
  .metric-card.temp  {{ border-color: #e07a5f; }}
  .metric-card.humid {{ border-color: #22c55e; }}
  .metric-card.soil  {{ border-color: #a3e635; }}
  .metric-card.light {{ border-color: #facc15; }}
  .metric-label {{
    font-size: 0.73rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: {T['text_muted']}; margin-bottom: 0.25rem;
  }}
  .metric-value {{ font-size: 2rem; font-weight: 600; color: {T['text']}; line-height: 1; }}
  .metric-unit  {{ font-size: 0.9rem; color: {T['text_muted']}; margin-left: 3px; }}
  .metric-status {{ font-size: 0.8rem; margin-top: 0.35rem; font-weight: 500; }}

  /* ── Plant cards ── */
  .plant-card {{
    background: {CARD_BG_GOOD};
    border: 1px solid {T['border']};
    border-radius: 12px; padding: 1.2rem;
    margin-bottom: 0.8rem; transition: transform 0.2s;
  }}
  .plant-card:hover {{ transform: translateY(-3px); }}
  .plant-card h4 {{ margin: 0 0 0.45rem; font-size: 1.15rem; color: {T['text']} !important; }}
  .plant-card p  {{ color: {T['text_muted']} !important; }}
  .plant-card .body-text {{ color: {T['text_muted']} !important; font-size: 0.81rem; }}
  .plant-card.moderate {{ background: {CARD_BG_MOD}; border-color: {CARD_BD_MOD}; }}
  .plant-card.poor     {{ background: {CARD_BG_POOR}; border-color: {CARD_BD_POOR}; }}

  /* ── Score badge ── */
  .score-badge {{
    display: inline-block; padding: 0.15rem 0.6rem;
    border-radius: 999px; font-size: 0.74rem; font-weight: 600; margin-left: 0.4rem;
  }}
  .score-good {{ background: #dcfce7; color: #15803d; }}
  .score-ok   {{ background: #fef9c3; color: #a16207; }}
  .score-poor {{ background: #fee2e2; color: #b91c1c; }}

  /* ── Status banner ── */
  .status-banner {{ border-radius: 8px; padding: 0.55rem 1rem; font-size: 0.86rem; font-weight: 500; margin-bottom: 1rem; }}
  .status-live    {{ background: {STATUS_LIVE_BG};    color: #15803d; border-left: 4px solid #22c55e; }}
  .status-offline {{ background: {STATUS_OFFLINE_BG}; color: #b91c1c; border-left: 4px solid #ef4444; }}
  .status-demo    {{ background: {STATUS_DEMO_BG};    color: #a16207; border-left: 4px solid #eab308; }}

  /* ── Section titles ── */
  .section-title {{
    font-family: 'Playfair Display', serif;
    font-size: 1.45rem; color: {T['text']};
    margin: 1.4rem 0 0.7rem;
    padding-bottom: 0.35rem;
    border-bottom: 2px solid {T['border']};
  }}

  /* ── Streamlit inputs ── */
  .stTextInput input {{
    background: {T['card_bg']} !important; color: {T['text']} !important;
    border-color: {T['border']} !important; border-radius: 8px !important;
  }}
  label, .stToggle label {{ color: {T['text']} !important; }}

  /* ── Scrollbar ── */
  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: {T['bg2']}; }}
  ::-webkit-scrollbar-thumb {{ background: {T['accent']}; border-radius: 3px; }}
</style>

<!-- ═══ Persistent Floating Hamburger ═══ -->
<button id="agri-burger" title="Toggle sidebar">
  <span class="bar" id="b1"></span>
  <span class="bar" id="b2"></span>
  <span class="bar" id="b3"></span>
</button>

<script>
(function() {{
  var open = true;   // sidebar starts expanded

  function getSidebar() {{
    return window.parent.document.querySelector('[data-testid="stSidebar"]');
  }}

  function getNativeBtn() {{
    var doc = window.parent.document;
    // Try various selectors Streamlit uses across versions
    return (
      doc.querySelector('[data-testid="collapsedControl"]') ||
      doc.querySelector('button[aria-label="Close sidebar"]') ||
      doc.querySelector('button[aria-label="Open sidebar"]') ||
      doc.querySelector('button[aria-label="open sidebar"]') ||
      doc.querySelector('button[aria-label="close sidebar"]')
    );
  }}

  function animateBurger(isOpen) {{
    var b1 = document.getElementById('b1');
    var b2 = document.getElementById('b2');
    var b3 = document.getElementById('b3');
    if (!b1) return;
    if (isOpen) {{
      b1.style.transform = 'rotate(45deg) translate(5.5px, 5.5px)';
      b2.style.opacity   = '0';
      b3.style.transform = 'rotate(-45deg) translate(5.5px, -5.5px)';
    }} else {{
      b1.style.transform = '';
      b2.style.opacity   = '1';
      b3.style.transform = '';
    }}
  }}

  function toggle() {{
    var sidebar = getSidebar();
    if (!sidebar) return;

    // Detect current state by sidebar width
    open = sidebar.getBoundingClientRect().width > 60;

    // Try clicking the native button first
    var btn = getNativeBtn();
    if (btn) {{
      btn.click();
      open = !open;
      animateBurger(open);
      return;
    }}

    // Fallback: manually toggle sidebar visibility
    if (open) {{
      sidebar.style.marginLeft = '-' + sidebar.offsetWidth + 'px';
      sidebar.style.transition = 'margin-left 0.3s ease';
    }} else {{
      sidebar.style.marginLeft = '0';
      sidebar.style.transition = 'margin-left 0.3s ease';
    }}
    open = !open;
    animateBurger(open);
  }}

  // Attach click
  var burger = document.getElementById('agri-burger');
  if (burger) burger.onclick = toggle;

  // Poll to keep burger icon in sync with actual sidebar state
  setInterval(function() {{
    var sidebar = getSidebar();
    if (!sidebar) return;
    var isOpen = sidebar.getBoundingClientRect().width > 60;
    animateBurger(isOpen);
  }}, 400);
}})();
</script>
""", unsafe_allow_html=True)


# ── Helper: Fetch Data ────────────────────────────────────────
def fetch_sensor_data():
    try:
        r = requests.get(f"{SERVER_URL}/latest", timeout=3)
        if r.status_code == 200:
            return r.json(), "live"
    except Exception:
        pass
    return None, "offline"

def get_demo_data():
    t = time.time()
    return {
        "temperature":   round(26 + 3  * math.sin(t / 60),  1),
        "humidity":      round(65 + 5  * math.sin(t / 45),  1),
        "soil_moisture": int  (55 + 10 * math.sin(t / 90)),
        "light_level":   int  (70 + 15 * math.sin(t / 30)),
        "device_id":     "DEMO-MODE",
        "server_time":   t,
    }

def status_label(value, low, high):
    dark = st.session_state.dark_mode
    if value < low:    return "🔵", "Low",     f"color:{'#60a5fa' if dark else '#3b82f6'}"
    elif value > high: return "🔴", "High",    "color:#ef4444"
    else:              return "🟢", "Optimal", f"color:{T['accent2']}"

# ── Gauge Chart ───────────────────────────────────────────────
def make_gauge(value, title, min_val, max_val, unit, color, thresholds):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 13, "family": "Inter", "color": T["text"]}},
        number={"suffix": unit, "font": {"size": 20, "color": T["text"]}},
        gauge={
            "axis": {"range": [min_val, max_val], "tickwidth": 1, "tickcolor": T["text_muted"]},
            "bar":  {"color": color},
            "bgcolor": T["card_bg"],
            "bordercolor": T["border"],
            "steps": [
                {"range": [min_val,       thresholds[0]], "color": "rgba(239,68,68,0.13)"},
                {"range": [thresholds[0], thresholds[1]], "color": "rgba(34,197,94,0.13)"},
                {"range": [thresholds[1], max_val],       "color": "rgba(239,68,68,0.13)"},
            ],
        },
    ))
    fig.update_layout(
        height=195,
        margin=dict(l=15, r=15, t=42, b=5),
        paper_bgcolor=T["plot_bg"],
        plot_bgcolor=T["plot_bg"],
    )
    return fig

# ── Trend Chart ───────────────────────────────────────────────
def make_trend_chart(history):
    if len(history) < 2:
        return None
    df = pd.DataFrame(history).tail(60)
    df["time"] = pd.to_datetime(df["server_time"], unit="s")
    fig = go.Figure()
    traces = [
        ("temperature",   "Temperature (°C)", "#e07a5f"),
        ("humidity",      "Humidity (%)",      "#22c55e"),
        ("soil_moisture", "Soil Moisture (%)", "#a3e635"),
        ("light_level",   "Light Level (%)",   "#facc15"),
    ]
    for col, name, color in traces:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["time"], y=df[col],
                name=name, line=dict(color=color, width=2),
                mode="lines+markers", marker=dict(size=4),
            ))
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor=T["plot_bg"],
        plot_bgcolor=T["plot_bg"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color=T["text"])),
        xaxis=dict(showgrid=False, color=T["text_muted"]),
        yaxis=dict(showgrid=True, gridcolor=T["grid_color"], color=T["text_muted"]),
    )
    return fig

# ══════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    # Space to clear the floating burger button
    st.markdown("<div style='height:3.2rem'></div>", unsafe_allow_html=True)

    # ── Theme Toggle ──────────────────────────────────────────
    st.markdown(f"<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{T['text_muted']};margin:0 0 0.2rem'>Appearance</p>", unsafe_allow_html=True)
    new_dark = st.toggle(f"{T['toggle_icon']}  {T['toggle_label']}", value=st.session_state.dark_mode)
    if new_dark != st.session_state.dark_mode:
        st.session_state.dark_mode = new_dark
        st.rerun()

    st.markdown(f"<hr style='border:none;border-top:1px solid {T['border']};margin:0.8rem 0'>", unsafe_allow_html=True)

    # ── Data Settings ─────────────────────────────────────────
    st.markdown(f"<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{T['text_muted']};margin:0 0 0.2rem'>Data Settings</p>", unsafe_allow_html=True)
    st.session_state.use_demo     = st.toggle("🧪  Use Demo Data",  value=st.session_state.use_demo)
    st.session_state.auto_refresh = st.toggle("🔄  Auto-refresh",   value=st.session_state.auto_refresh)
    server_input = st.text_input("Data Server URL", value=SERVER_URL)

    st.markdown(f"<hr style='border:none;border-top:1px solid {T['border']};margin:0.8rem 0'>", unsafe_allow_html=True)

    # ── Device Info ───────────────────────────────────────────
    st.markdown(f"<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{T['text_muted']};margin:0 0 0.4rem'>📡 Device Info</p>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.81rem;line-height:1.7;color:{T['text_muted']}'><b>Device:</b> ESP32 WROOM<br><b>Firmware:</b> v1.0.0<br><b>Protocol:</b> HTTP POST<br><b>Interval:</b> 5 s</div>", unsafe_allow_html=True)

    st.markdown(f"<hr style='border:none;border-top:1px solid {T['border']};margin:0.8rem 0'>", unsafe_allow_html=True)

    # ── Sensor Pins ───────────────────────────────────────────
    st.markdown(f"<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{T['text_muted']};margin:0 0 0.4rem'>🔌 Sensor Pins</p>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.81rem;line-height:1.7;color:{T['text_muted']}'><b>DHT22 Data:</b> GPIO 4<br><b>Soil Moisture:</b> GPIO 34<br><b>LDR:</b> GPIO 35<br><b>All VCC:</b> 3.3V</div>", unsafe_allow_html=True)

    st.markdown(f"<hr style='border:none;border-top:1px solid {T['border']};margin:0.8rem 0'>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:0.72rem;color:{T['text_muted']};text-align:center'>AgriSense v1.0 · ESP32 IoT</p>", unsafe_allow_html=True)

# Override server URL with sidebar input
SERVER_URL = server_input

# ══════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ══════════════════════════════════════════════════════════════

st.markdown(f"""
<div class="hero-header">
  <h1>🌱 AgriSense Dashboard</h1>
  <p>Real-time IoT Agriculture Monitoring &amp; Plant Recommendation System</p>
</div>
""", unsafe_allow_html=True)

# ── Fetch Data ────────────────────────────────────────────────
if st.session_state.use_demo:
    data, source = get_demo_data(), "demo"
else:
    data, source = fetch_sensor_data()

if data:
    st.session_state.history.append(data)
    if len(st.session_state.history) > 200:
        st.session_state.history = st.session_state.history[-200:]

# ── Status Banner ─────────────────────────────────────────────
if source == "live" and data:
    ts = datetime.fromtimestamp(data.get("server_time", time.time())).strftime("%H:%M:%S")
    st.markdown(f'<div class="status-banner status-live">🟢 Live — Last update: {ts} · Device: {data.get("device_id","–")}</div>', unsafe_allow_html=True)
elif source == "demo":
    st.markdown('<div class="status-banner status-demo">🟡 Demo Mode — Simulated sensor data</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-banner status-offline">🔴 Offline — Cannot reach data server. Enable Demo Mode or check connection.</div>', unsafe_allow_html=True)

if not data:
    st.info("No sensor data. Enable **Demo Mode** in the sidebar or check your ESP32 and data server.")
    st.stop()

temp  = data["temperature"]
humid = data["humidity"]
soil  = data["soil_moisture"]
light = data["light_level"]

# ══════════════════════════════════════════════════════════════
#  SECTION 1 – GAUGES
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">📊 Current Sensor Readings</div>', unsafe_allow_html=True)

g1, g2, g3, g4 = st.columns(4)
with g1: st.plotly_chart(make_gauge(temp,  "Temperature",  -10, 50,  "°C", "#e07a5f", [18, 32]), width='stretch')
with g2: st.plotly_chart(make_gauge(humid, "Humidity",       0, 100, "%",  "#22c55e", [40, 80]), width='stretch')
with g3: st.plotly_chart(make_gauge(soil,  "Soil Moisture",  0, 100, "%",  "#a3e635", [30, 70]), width='stretch')
with g4: st.plotly_chart(make_gauge(light, "Light Level",    0, 100, "%",  "#facc15", [20, 85]), width='stretch')

m1, m2, m3, m4 = st.columns(4)
for col, cls, label, val, unit, lo, hi in [
    (m1, "temp",  "🌡️ Temperature",   temp,  "°C", 18, 32),
    (m2, "humid", "💧 Humidity",      humid, "%",  40, 80),
    (m3, "soil",  "🌍 Soil Moisture", soil,  "%",  30, 70),
    (m4, "light", "☀️ Light Level",   light, "%",  20, 85),
]:
    emoji, status_text, style = status_label(val, lo, hi)
    with col:
        st.markdown(f"""
        <div class="metric-card {cls}">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{val}<span class="metric-unit">{unit}</span></div>
          <div class="metric-status" style="{style}">{emoji} {status_text}</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  SECTION 2 – TREND
# ══════════════════════════════════════════════════════════════
if len(st.session_state.history) >= 2:
    st.markdown('<div class="section-title">📈 Historical Trend</div>', unsafe_allow_html=True)
    trend_fig = make_trend_chart(st.session_state.history)
    if trend_fig:
        st.plotly_chart(trend_fig, width='stretch')

# ══════════════════════════════════════════════════════════════
#  SECTION 3 – PLANT RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">🌿 Plant Category Recommendations</div>', unsafe_allow_html=True)
st.caption("Suitability scores based on current sensor readings.")

conditions      = classify_conditions(temp, humid, soil, light)
recommendations = get_plant_recommendations(temp, humid, soil, light)

def pill(ok, label):
    bg  = T["bg2"]          if ok else (STATUS_OFFLINE_BG)
    clr = T["accent"]       if ok else "#ef4444"
    return f'<span style="background:{bg};color:{clr};padding:3px 11px;border-radius:999px;font-size:0.79rem;font-weight:600;">{label}</span>'

st.markdown(
    pill(conditions["temp_ok"],  f"Temp: {conditions['temp_label']}")     + " &nbsp;" +
    pill(conditions["humid_ok"], f"Humidity: {conditions['humid_label']}") + " &nbsp;" +
    pill(conditions["soil_ok"],  f"Soil: {conditions['soil_label']}")      + " &nbsp;" +
    pill(conditions["light_ok"], f"Light: {conditions['light_label']}"),
    unsafe_allow_html=True
)
st.markdown("<br>", unsafe_allow_html=True)

r1, r2, r3 = st.columns(3)
for col, rec in zip([r1, r2, r3], recommendations):
    score     = rec["score"]
    css_class = "plant-card" if score >= 70 else ("plant-card moderate" if score >= 45 else "plant-card poor")
    badge_cls = "score-good" if score >= 70 else ("score-ok" if score >= 45 else "score-poor")
    with col:
        st.markdown(f"""
        <div class="{css_class}">
          <h4>{rec['icon']} {rec['category']}
            <span class="score-badge {badge_cls}">{score}%</span>
          </h4>
          <p style="font-size:0.85rem;margin:0 0 0.65rem">{rec['description']}</p>
          <div class="body-text">
            <strong>✅ Suitable Plants:</strong><br>
            {'<br>'.join(f"• {p}" for p in rec['suited_plants'])}
          </div>
          <hr style="margin:0.65rem 0;border:none;border-top:1px solid {T['border']}">
          <div class="body-text">
            <strong>💡 Tips:</strong><br>
            {'<br>'.join(f"• {t}" for t in rec['tips'])}
          </div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  SECTION 4 – RADAR
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">🎯 Suitability Comparison</div>', unsafe_allow_html=True)

categories_radar = ["Temperature", "Humidity", "Soil Moisture", "Light Level"]
fig_radar = go.Figure()
r_colors  = ["#22c55e", "#facc15", "#f87171"]
r_fills   = ["rgba(34,197,94,0.18)", "rgba(250,204,21,0.18)", "rgba(248,113,113,0.18)"]

for rec, color, fill in zip(recommendations, r_colors, r_fills):
    s = rec["radar_scores"]
    fig_radar.add_trace(go.Scatterpolar(
        r=s + [s[0]], theta=categories_radar + [categories_radar[0]],
        fill="toself", name=rec["category"],
        line=dict(color=color, width=2), fillcolor=fill,
    ))
fig_radar.update_layout(
    polar=dict(
        bgcolor=T["card_bg"],
        radialaxis=dict(visible=True, range=[0,100], color=T["text_muted"], gridcolor=T["grid_color"]),
        angularaxis=dict(color=T["text"], gridcolor=T["grid_color"]),
    ),
    height=380,
    paper_bgcolor=T["plot_bg"],
    legend=dict(orientation="h", font=dict(color=T["text"])),
    margin=dict(l=20, r=20, t=30, b=20),
)
st.plotly_chart(fig_radar, width='stretch')

# ══════════════════════════════════════════════════════════════
#  AUTO-REFRESH
# ══════════════════════════════════════════════════════════════
if st.session_state.auto_refresh:
    time.sleep(REFRESH_SECS)
    st.rerun()

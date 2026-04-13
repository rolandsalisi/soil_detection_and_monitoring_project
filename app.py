"""
app.py – boTiny Botanical Dashboard
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
    page_title="boTiny – IoT Botanical Monitor",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State ─────────────────────────────────────────────
if "history"           not in st.session_state: st.session_state.history           = []
if "use_demo"          not in st.session_state: st.session_state.use_demo          = False
if "auto_refresh"      not in st.session_state: st.session_state.auto_refresh      = True
if "dark_mode"         not in st.session_state: st.session_state.dark_mode         = False
if "auto_detected_ip"  not in st.session_state: st.session_state.auto_detected_ip  = None
if "latency_history"   not in st.session_state: st.session_state.latency_history   = []

# ── Constants ─────────────────────────────────────────────────
SERVER_URL   = st.secrets.get("DATA_SERVER_URL", "http://localhost:8000")
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

# ── Styles & Custom CSS ──────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500;600&display=swap');
    html, body, [class*="css"], .stApp {{ font-family: 'Inter', sans-serif; background-color: {T['bg']} !important; color: {T['text']} !important; }}
    h1,h2,h3,h4 {{ font-family: 'Playfair Display', serif; color: {T['text']} !important; }}
    #MainMenu, footer {{ visibility: hidden !important; }}
    header[data-testid="stHeader"] {{ background: transparent !important; height: 3.2rem !important; }}
    [data-testid="collapsedControl"] {{
        display: flex !important; visibility: visible !important; background: {T['accent']} !important;
        border-radius: 10px !important; width: 38px !important; height: 38px !important;
        align-items: center !important; justify-content: center !important;
        margin: 6px 0 0 8px !important; box-shadow: 0 3px 10px rgba(0,0,0,0.25) !important;
    }}
    [data-testid="stSidebar"] {{ background: {T['sidebar_bg']} !important; border-right: 1px solid {T['border']} !important; }}
    .hero-header {{ background: {T['hero_grad']}; border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.2rem; }}
    .hero-header h1 {{ font-size: 2.2rem; margin: 0; color: white !important; letter-spacing: -0.02em; }}
    .hero-header p  {{ opacity: 0.88; margin: 0.4rem 0 0; font-size: 1rem; color: white !important; }}
    .metric-card {{ background: {T['card_bg']}; border-radius: 12px; padding: 1.2rem 1.4rem; box-shadow: {T['card_shadow']}; border-left: 5px solid; margin-bottom: 0.8rem; }}
    .metric-card.temp {{ border-color: #e07a5f; }} .metric-card.humid {{ border-color: #22c55e; }} 
    .metric-card.soil {{ border-color: #a3e635; }} .metric-card.light {{ border-color: #facc15; }}
    .metric-value {{ font-size: 2rem; font-weight: 600; color: {T['text']}; }}
    .section-title {{ font-family: 'Playfair Display', serif; font-size: 1.45rem; color: {T['text']}; margin: 1.4rem 0 0.7rem; border-bottom: 2px solid {T['border']}; }}
    .status-banner {{ border-radius: 8px; padding: 0.55rem 1rem; font-size: 0.86rem; font-weight: 500; margin-bottom: 1rem; }}
    .status-live {{ background: {"#052e16" if st.session_state.dark_mode else "#dcfce7"}; color: #15803d; border-left: 4px solid #22c55e; }}
</style>
""", unsafe_allow_html=True)

# ── Functions ─────────────────────────────────────────────────
def fetch_sensor_data():
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{SERVER_URL}/latest", timeout=3)
        rtt_ms = round((time.perf_counter() - t0) * 1000, 1)
        if r.status_code == 200:
            data = r.json()
            return data, "live", rtt_ms, data.pop("proc_ms", None)
    except: pass
    return None, "offline", 0, None

def get_demo_data():
    t = time.time()
    return {"temperature": round(24 + 4*math.sin(t/60), 1), "humidity": round(60 + 10*math.sin(t/45), 1), 
            "soil_moisture": int(50 + 15*math.sin(t/90)), "light_level": int(75 + 10*math.sin(t/30)), 
            "device_id": "DEMO-MODE", "server_time": t}

def make_gauge(value, title, min_val, max_val, unit, color, thresholds):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        title={"text": title, "font": {"size": 14, "color": T["text"]}},
        number={"suffix": unit, "font": {"color": T["text"]}},
        gauge={"axis": {"range": [min_val, max_val]}, "bar": {"color": color}, "bgcolor": T["card_bg"]}
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='height:3.2rem'></div>", unsafe_allow_html=True)
    st.markdown("**Appearance**")
    if st.toggle(f"{T['toggle_icon']} {T['toggle_label']}", value=st.session_state.dark_mode):
        st.session_state.dark_mode = True
        st.rerun() if not st.session_state.dark_mode else None
    else:
        st.session_state.dark_mode = False
    
    st.markdown("---")
    st.session_state.use_demo = st.toggle("Demo Mode", value=st.session_state.use_demo)
    SERVER_URL = st.text_input("Server URL", value=SERVER_URL)
    st.markdown(f"<center>boTiny v1.0</center>", unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-header">
  <h1>boTiny Dashboard</h1>
  <p>Real-Time Botanical monitor and plant recommendation system</p>
</div>
""", unsafe_allow_html=True)

if st.session_state.use_demo:
    data, source = get_demo_data(), "demo"
else:
    data, source, rtt, proc = fetch_sensor_data()

if data:
    st.session_state.history.append(data)
    if source == "live": st.markdown('<div class="status-banner status-live">System Online: Live Stream</div>', unsafe_allow_html=True)

    # Gauges
    st.markdown('<div class="section-title">Current Botanical Conditions</div>', unsafe_allow_html=True)
    g1, g2, g3, g4 = st.columns(4)
    g1.plotly_chart(make_gauge(data["temperature"], "Temperature", 0, 50, "°C", "#e07a5f", [18, 30]), use_container_width=True)
    g2.plotly_chart(make_gauge(data["humidity"], "Humidity", 0, 100, "%", "#22c55e", [40, 80]), use_container_width=True)
    g3.plotly_chart(make_gauge(data["soil_moisture"], "Soil Moisture", 0, 100, "%", "#a3e635", [30, 70]), use_container_width=True)
    g4.plotly_chart(make_gauge(data["light_level"], "Light Level", 0, 100, "%", "#facc15", [20, 90]), use_container_width=True)

    # Recommendations
    st.markdown('<div class="section-title">Plant Recommendations</div>', unsafe_allow_html=True)
    recs = get_plant_recommendations(data["temperature"], data["humidity"], data["soil_moisture"], data["light_level"])
    for r in recs[:3]:
        st.success(f"**{r['name']}**: {r['reason']}")
else:
    st.warning("No connection to boTiny device. Please check URL or enable Demo Mode.")

if st.session_state.auto_refresh:
    time.sleep(REFRESH_SECS)
    st.rerun()

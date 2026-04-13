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
if "history"           not in st.session_state: st.session_state.history           = []
if "use_demo"          not in st.session_state: st.session_state.use_demo          = False
if "auto_refresh"      not in st.session_state: st.session_state.auto_refresh      = True
if "dark_mode"         not in st.session_state: st.session_state.dark_mode         = False
if "auto_detected_ip"  not in st.session_state: st.session_state.auto_detected_ip  = None
if "esp32_scanning"    not in st.session_state: st.session_state.esp32_scanning    = False

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

  /* ── Hide Streamlit chrome except the sidebar toggle ── */
  #MainMenu {{ visibility: hidden !important; }}
  footer {{ visibility: hidden !important; }}

  /* Keep the header visible but transparent so the native burger shows */
  header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 3.2rem !important;
  }}

  /* Restyle the native hamburger/collapse button to match green theme */
  [data-testid="collapsedControl"] {{
    display: flex !important;
    visibility: visible !important;
    background: {T['accent']} !important;
    border-radius: 10px !important;
    width: 38px !important;
    height: 38px !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 6px 0 0 8px !important;
    box-shadow: 0 3px 10px rgba(0,0,0,0.25) !important;
    transition: background 0.2s !important;
  }}
  [data-testid="collapsedControl"]:hover {{
    background: {T['text2']} !important;
  }}
  [data-testid="collapsedControl"] svg {{
    fill: white !important;
    color: white !important;
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
    padding-top: 1rem !important;
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

  /* ── Datetime weather card ── */
  .dt-card {{
    background: {T['hero_grad']};
    border-radius: 16px;
    padding: 1.4rem 1.8rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    box-shadow: {T['card_shadow']};
    overflow: hidden;
    position: relative;
  }}
  .dt-card::before {{
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 180px; height: 180px;
    border-radius: 50%;
    background: rgba(255,255,255,0.04);
    pointer-events: none;
  }}
  .dt-card::after {{
    content: '';
    position: absolute;
    bottom: -50px; left: 20%;
    width: 220px; height: 220px;
    border-radius: 50%;
    background: rgba(255,255,255,0.03);
    pointer-events: none;
  }}
  .dt-left {{ z-index: 1; }}
  .dt-time {{
    font-family: 'Playfair Display', serif;
    font-size: 3.2rem;
    font-weight: 700;
    color: #ffffff;
    line-height: 1;
    letter-spacing: -0.02em;
  }}
  .dt-date {{
    font-size: 0.95rem;
    color: rgba(255,255,255,0.80);
    margin-top: 0.35rem;
    letter-spacing: 0.02em;
  }}
  .dt-right {{
    z-index: 1;
    text-align: right;
  }}
  .dt-conn-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.20);
    border-radius: 999px;
    padding: 5px 14px;
    font-size: 0.80rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 0.5rem;
  }}
  .dt-conn-dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
  }}
  .dt-conn-dot.live    {{ background: #4ade80; box-shadow: 0 0 6px #4ade80; }}
  .dt-conn-dot.demo    {{ background: #facc15; box-shadow: 0 0 6px #facc15; }}
  .dt-conn-dot.offline {{ background: #f87171; }}
  .dt-ip {{
    font-size: 0.75rem;
    color: rgba(255,255,255,0.55);
    margin-top: 0.2rem;
  }}
</style>
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

# ── ESP32 Auto-scan ───────────────────────────────────────────
def scan_for_esp32(subnet_prefix: str = "192.168.1", timeout: float = 1.0):
    """
    Probe common host addresses on the LAN to find an ESP32
    serving the /latest endpoint.  Returns (ip, data) on first hit.
    Probes .100 → .120 first (common DHCP range), then .1 → .254.
    Skips anything already tried.
    """
    priority = list(range(100, 121)) + [x for x in range(1, 255) if x not in range(100, 121)]
    for host in priority:
        ip = f"{subnet_prefix}.{host}"
        try:
            r = requests.get(f"http://{ip}/latest", timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                # Sanity-check: must have at least one sensor field
                if "temperature" in data or "soil_moisture" in data:
                    return ip, data
        except Exception:
            pass
    return None, None

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
    st.session_state.use_demo     = st.toggle("Use Demo Data",  value=st.session_state.use_demo)
    st.session_state.auto_refresh = st.toggle("Auto-refresh",   value=st.session_state.auto_refresh)
    server_input = st.text_input(
        "Data Server URL",
        value=f"http://{st.session_state.auto_detected_ip}" if st.session_state.auto_detected_ip else SERVER_URL,
        help="Auto-filled when ESP32 is detected. Override manually if needed.",
    )

    st.markdown(f"<hr style='border:none;border-top:1px solid {T['border']};margin:0.8rem 0'>", unsafe_allow_html=True)

    # ── Device Info / Auto-detect ─────────────────────────────
    st.markdown(f"<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{T['text_muted']};margin:0 0 0.4rem'>Device Info</p>", unsafe_allow_html=True)

    detected = st.session_state.auto_detected_ip
    if detected:
        st.markdown(f"<div style='font-size:0.81rem;line-height:1.7;color:{T['text_muted']}'>"
                    f"<b>Auto-detected:</b> <span style='color:{T['accent']};font-weight:600'>{detected}</span><br>"
                    f"<b>Device:</b> ESP32 WROOM<br><b>Firmware:</b> v1.0.0<br>"
                    f"<b>Protocol:</b> HTTP GET<br><b>Interval:</b> 5 s</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='font-size:0.81rem;color:{T['text_muted']}'>No ESP32 detected yet.</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    subnet = st.text_input("Subnet prefix", value="192.168.1",
                           help="First three octets of your LAN, e.g. 192.168.1")
    if st.button("Scan for ESP32", use_container_width=True):
        with st.spinner("Scanning LAN for ESP32…"):
            found_ip, found_data = scan_for_esp32(subnet)
        if found_ip:
            st.session_state.auto_detected_ip = found_ip
            # Patch SERVER_URL so the main loop picks it up immediately
            SERVER_URL = f"http://{found_ip}"
            st.success(f"Found ESP32 at {found_ip}")
            st.rerun()
        else:
            st.warning("No ESP32 found. Check subnet or enable Demo Mode.")

    st.markdown(f"<hr style='border:none;border-top:1px solid {T['border']};margin:0.8rem 0'>", unsafe_allow_html=True)

    # ── Sensor Pins ───────────────────────────────────────────
    st.markdown(f"<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{T['text_muted']};margin:0 0 0.4rem'>Sensor Pins</p>", unsafe_allow_html=True)
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
  <h1>AgriSense Dashboard</h1>
  <p>Real-time IoT Agriculture Monitoring &amp; Plant Recommendation System</p>
</div>
""", unsafe_allow_html=True)

# ── Datetime + Connection Weather Card ───────────────────────
now          = datetime.now()
time_str     = now.strftime("%H:%M")
seconds_str  = now.strftime(":%S")
weekday_str  = now.strftime("%A")
date_str     = now.strftime("%B %d, %Y")

# Connection state for badge
if st.session_state.use_demo:
    conn_dot_cls = "demo"
    conn_label   = "Demo Mode"
    conn_ip      = "Simulated data"
elif st.session_state.auto_detected_ip:
    conn_dot_cls = "live"
    conn_label   = "ESP32 Connected"
    conn_ip      = st.session_state.auto_detected_ip
else:
    conn_dot_cls = "offline"
    conn_label   = "No Device"
    conn_ip      = "Run scan or enter URL"

st.markdown(f"""
<div class="dt-card">
  <div class="dt-left">
    <div class="dt-time">{time_str}<span style="font-size:1.8rem;opacity:0.65">{seconds_str}</span></div>
    <div class="dt-date">{weekday_str} · {date_str}</div>
  </div>
  <div class="dt-right">
    <div>
      <span class="dt-conn-badge">
        <span class="dt-conn-dot {conn_dot_cls}"></span>
        {conn_label}
      </span>
    </div>
    <div class="dt-ip">{conn_ip}</div>
  </div>
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
    st.markdown(f'<div class="status-banner status-live">Live — Last update: {ts} · Device: {data.get("device_id","–")}</div>', unsafe_allow_html=True)
elif source == "demo":
    st.markdown('<div class="status-banner status-demo">Demo Mode — Simulated sensor data</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-banner status-offline">Offline — Cannot reach data server. Enable Demo Mode or check connection.</div>', unsafe_allow_html=True)

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
st.markdown('<div class="section-title">Current Sensor Readings</div>', unsafe_allow_html=True)

g1, g2, g3, g4 = st.columns(4)
with g1: st.plotly_chart(make_gauge(temp,  "Temperature",  -10, 50,  "°C", "#e07a5f", [18, 32]), width='stretch')
with g2: st.plotly_chart(make_gauge(humid, "Humidity",       0, 100, "%",  "#22c55e", [40, 80]), width='stretch')
with g3: st.plotly_chart(make_gauge(soil,  "Soil Moisture",  0, 100, "%",  "#a3e635", [30, 70]), width='stretch')
with g4: st.plotly_chart(make_gauge(light, "Light Level",    0, 100, "%",  "#facc15", [20, 85]), width='stretch')

m1, m2, m3, m4 = st.columns(4)
for col, cls, label, val, unit, lo, hi in [
    (m1, "temp",  "Temperature",   temp,  "°C", 18, 32),
    (m2, "humid", "Humidity",      humid, "%",  40, 80),
    (m3, "soil",  "Soil Moisture", soil,  "%",  30, 70),
    (m4, "light", "Light Level",   light, "%",  20, 85),
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
    st.markdown('<div class="section-title">Historical Trend</div>', unsafe_allow_html=True)
    trend_fig = make_trend_chart(st.session_state.history)
    if trend_fig:
        st.plotly_chart(trend_fig, width='stretch')

# ══════════════════════════════════════════════════════════════
#  SECTION 3 – PLANT RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Plant Category Recommendations</div>', unsafe_allow_html=True)
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
st.markdown('<div class="section-title">Suitability Comparison</div>', unsafe_allow_html=True)

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

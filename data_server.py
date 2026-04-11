"""
data_server.py
──────────────
Lightweight FastAPI bridge server.
Receives JSON POST from ESP32 → stores latest reading in memory
Streamlit app polls GET /latest to display live data.

Run with:  uvicorn data_server:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import time
import json
from collections import deque

app = FastAPI(title="AgriSense Data Bridge", version="1.0.0")

# Allow all origins (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory store (last 100 readings) ──────────────────────
MAX_HISTORY = 100
readings_history: deque = deque(maxlen=MAX_HISTORY)
latest_reading: dict = {}

# ── Pydantic model for incoming ESP32 data ───────────────────
class SensorData(BaseModel):
    temperature: float = Field(..., ge=-40, le=80, description="°C")
    humidity: float = Field(..., ge=0, le=100, description="%")
    soil_moisture: int = Field(..., ge=0, le=100, description="%")
    light_level: int = Field(..., ge=0, le=100, description="%")
    timestamp: Optional[int] = None
    device_id: Optional[str] = "ESP32-AGRI-001"

# ── Endpoints ────────────────────────────────────────────────

@app.post("/data", status_code=201)
async def receive_data(data: SensorData):
    """ESP32 posts sensor readings here."""
    global latest_reading
    record = data.dict()
    record["server_time"] = time.time()
    latest_reading = record
    readings_history.append(record)
    return {"status": "ok", "received": record}


@app.get("/latest")
async def get_latest():
    """Streamlit polls this to get the most recent reading."""
    if not latest_reading:
        raise HTTPException(status_code=404, detail="No data received yet")
    return latest_reading


@app.get("/history")
async def get_history():
    """Returns last N readings as a list."""
    return list(readings_history)


@app.get("/health")
async def health():
    return {"status": "running", "readings_stored": len(readings_history)}

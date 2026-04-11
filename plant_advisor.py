"""
plant_advisor.py
────────────────
Recommendation engine for 3 broad plant categories:
  1. Leafy Greens
  2. Root Crops
  3. Fruiting Plants

Each category has ideal ranges for temperature, humidity,
soil moisture, and light. A suitability score (0–100%) is
computed and actionable tips are returned.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


# ── Ideal Ranges (min, max) ───────────────────────────────────
@dataclass
class PlantCategory:
    name:          str
    icon:          str
    description:   str
    temp_range:    Tuple[float, float]    # °C
    humid_range:   Tuple[float, float]    # %
    soil_range:    Tuple[float, float]    # %
    light_range:   Tuple[float, float]    # %
    examples:      List[str]             = field(default_factory=list)


PLANT_CATEGORIES = [
    PlantCategory(
        name        = "Leafy Greens",
        icon        = "🥬",
        description = "Cool-season crops that thrive in moderate temperatures with consistent moisture and partial to full sunlight.",
        temp_range  = (15, 25),
        humid_range = (50, 80),
        soil_range  = (40, 70),
        light_range = (40, 80),
        examples    = ["Lettuce", "Spinach", "Kale", "Pechay", "Kangkong", "Chard"],
    ),
    PlantCategory(
        name        = "Root Crops",
        icon        = "🥕",
        description = "Underground-producing crops that need well-drained soil, moderate moisture, and good light for photosynthesis.",
        temp_range  = (18, 28),
        humid_range = (45, 75),
        soil_range  = (35, 60),
        light_range = (50, 90),
        examples    = ["Carrot", "Radish", "Beet", "Turnip", "Sweet Potato", "Cassava"],
    ),
    PlantCategory(
        name        = "Fruiting Plants",
        icon        = "🍅",
        description = "Warm-season crops that demand high light intensity, warm temperatures, and balanced soil moisture for fruit set.",
        temp_range  = (22, 35),
        humid_range = (55, 85),
        soil_range  = (45, 75),
        light_range = (65, 100),
        examples    = ["Tomato", "Pepper", "Eggplant", "Okra", "Cucumber", "Squash"],
    ),
]


# ── Scoring Logic ─────────────────────────────────────────────

def _score_value(value: float, lo: float, hi: float) -> float:
    """
    Returns 0–100 score for how well `value` fits within [lo, hi].
    - Inside range          → 100
    - Within 20% outside   → linear decay to 0
    """
    if lo <= value <= hi:
        return 100.0
    span = hi - lo if hi != lo else 1
    margin = 0.20 * span
    if value < lo:
        distance = lo - value
    else:
        distance = value - hi
    score = max(0.0, 100.0 * (1 - distance / margin))
    return round(score, 1)


def _overall_score(scores: List[float]) -> int:
    """Weighted average of 4 parameter scores (equal weight)."""
    return round(sum(scores) / len(scores))


def _build_tips(
    temp: float, humid: float, soil: float, light: float,
    cat: PlantCategory
) -> List[str]:
    tips = []
    tl, th = cat.temp_range
    hl, hh = cat.humid_range
    sl, sh = cat.soil_range
    ll, lh = cat.light_range

    if temp < tl:
        tips.append(f"Temperature too low ({temp}°C). Use row covers or a greenhouse to warm the microclimate above {tl}°C.")
    elif temp > th:
        tips.append(f"Temperature too high ({temp}°C). Provide shade cloth or irrigate during heat to cool below {th}°C.")
    else:
        tips.append(f"Temperature ({temp}°C) is ideal for {cat.name.lower()}.")

    if humid < hl:
        tips.append(f"Low humidity ({humid}%). Mulch the soil or mist foliage to raise humidity toward {hl}%.")
    elif humid > hh:
        tips.append(f"High humidity ({humid}%). Improve air circulation to reduce fungal disease risk.")
    else:
        tips.append(f"Humidity ({humid}%) is within the optimal range.")

    if soil < sl:
        tips.append(f"Soil too dry ({soil}%). Increase irrigation frequency to maintain moisture above {sl}%.")
    elif soil > sh:
        tips.append(f"Soil too wet ({soil}%). Improve drainage and reduce watering to prevent root rot.")
    else:
        tips.append(f"Soil moisture ({soil}%) is excellent for {cat.name.lower()}.")

    if light < ll:
        tips.append(f"Insufficient light ({light}%). Move to a brighter spot or use grow lights.")
    elif light > lh:
        tips.append(f"Intense light ({light}%). Provide 30–50% shade cloth to prevent leaf scorch.")
    else:
        tips.append(f"Light level ({light}%) is perfect — no adjustment needed.")

    return tips[:3]   # Return top 3 most important tips


# ── Public API ────────────────────────────────────────────────

def get_plant_recommendations(
    temp: float, humid: float, soil: float, light: float
) -> List[dict]:
    """
    Returns a list of 3 dicts, one per plant category, sorted by score desc.
    Each dict contains: category, icon, description, score, suited_plants, tips, radar_scores.
    """
    results = []
    for cat in PLANT_CATEGORIES:
        s_temp  = _score_value(temp,  *cat.temp_range)
        s_humid = _score_value(humid, *cat.humid_range)
        s_soil  = _score_value(soil,  *cat.soil_range)
        s_light = _score_value(light, *cat.light_range)
        overall = _overall_score([s_temp, s_humid, s_soil, s_light])
        tips    = _build_tips(temp, humid, soil, light, cat)

        # Select examples based on score
        if overall >= 70:
            suited = cat.examples[:4]
        elif overall >= 45:
            suited = cat.examples[:2]
        else:
            suited = [cat.examples[0]]

        results.append({
            "category":     cat.name,
            "icon":         cat.icon,
            "description":  cat.description,
            "score":        overall,
            "suited_plants": suited,
            "tips":         tips,
            "radar_scores": [s_temp, s_humid, s_soil, s_light],
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def classify_conditions(
    temp: float, humid: float, soil: float, light: float
) -> dict:
    """Return human-readable condition classification for the status pills."""
    def label_range(val, lo, hi, low_lbl, high_lbl, ok_lbl):
        if val < lo:
            return low_lbl, False
        elif val > hi:
            return high_lbl, False
        return ok_lbl, True

    t_lbl, t_ok = label_range(temp,  15, 35, "Too Cold", "Too Hot",  "Optimal")
    h_lbl, h_ok = label_range(humid, 40, 85, "Too Dry",  "Too Humid","Optimal")
    s_lbl, s_ok = label_range(soil,  25, 75, "Dry",      "Waterlogged","Optimal")
    l_lbl, l_ok = label_range(light, 20, 90, "Low",      "Intense", "Optimal")

    return {
        "temp_label":  t_lbl, "temp_ok":  t_ok,
        "humid_label": h_lbl, "humid_ok": h_ok,
        "soil_label":  s_lbl, "soil_ok":  s_ok,
        "light_label": l_lbl, "light_ok": l_ok,
    }

"""
Parsers Utility

Common parsing helpers to handle number sanitization, keyword splitting, and raw text extraction
of nutritive value macros.
"""

import math
import re
from typing import Any, Dict, List

def _to_number(x: Any, fallback: float = 0.0) -> float:
    if isinstance(x, (int, float)) and math.isfinite(float(x)):
        return float(x)
    text = str(x or "").strip().replace(",", "")
    if not text:
        return fallback
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return fallback
    try:
        n = float(m.group(0))
        return n if math.isfinite(n) else fallback
    except Exception:
        return fallback

def split_keywords(raw: Any) -> List[str]:
    s = str(raw or "").lower()
    parts = re.split(r"[,;/]|\band\b", s)
    return [p.strip() for p in parts if p and p.strip()]

def parse_nutritive_values(text: Any) -> Dict[str, float]:
    t = str(text or "")
    def m(rx: str) -> float:
        match = re.search(rx, t, flags=re.IGNORECASE)
        return _to_number(match.group(1)) if match else 0.0
    return {
        "caloriesKcal": m(r"(\d+(?:\.\d+)?)\s*kcal"),
        "proteinG": m(r"protein\s*(\d+(?:\.\d+)?)\s*g"),
        "carbsG": m(r"(?:carbs?|carbohydrates?)\s*(\d+(?:\.\d+)?)\s*g"),
        "fatG": m(r"fat\s*(\d+(?:\.\d+)?)\s*g"),
        "fiberG": m(r"(?:fiber|fibre)\s*(\d+(?:\.\d+)?)\s*g"),
    }

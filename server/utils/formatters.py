"""
Formatters Utility

Common utilities for formatting numbers, portion strings, and nutritive macro summaries.
"""

from typing import Any, Dict
from utils.parsers import _to_number

def _fmt_num(x: float) -> str:
    """
    Formats a float value into a clean, human-readable string. 
    Trims trailing decimals and zeroes where appropriate.
    """
    f = float(x)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return f"{f:.2f}".rstrip("0").rstrip(".")

def format_nutritive_values(macros: Dict[str, Any]) -> str:
    """
    Constructs a formatted summary string showing the key macro nutrient metrics.
    """
    kcal = _to_number(macros.get("caloriesKcal"), 0.0)
    protein = _to_number(macros.get("proteinG"), 0.0)
    carbs = _to_number(macros.get("carbsG"), 0.0)
    fat = _to_number(macros.get("fatG"), 0.0)
    fiber = _to_number(macros.get("fiberG"), 0.0)

    out = f"{_fmt_num(kcal)} kcal | Protein {_fmt_num(protein)} g | Carbs {_fmt_num(carbs)} g | Fat {_fmt_num(fat)} g"
    if fiber > 0:
        out += f" | Fiber {_fmt_num(fiber)} g"
    return out

"""
Conversion Engine Module

Responsible for normalizing non-standard recipe units (e.g. tsp, tbsp, cup, pieces) 
into their corresponding gram weights. Supports standardized global fallsbacks 
and ingredient-specific conversions.
"""

from typing import Any, Dict, Optional

UNIT_TO_GRAMS: Dict[str, float] = {
    "tsp": 5.0,
    "tbsp": 15.0,
    "cup": 240.0,
    "pinch": 0.5,
    "clove": 3.0,
    "piece": 100.0,
    "slice": 30.0,
    "handful": 25.0,
    "small": 60.0,
    "medium": 120.0,
    "large": 180.0,
}

def _unit_is_gram(unit: str) -> bool:
    return str(unit or "").strip().lower() in {"g", "gram", "grams", "ml", "milliliter", "milliliters"}

def convert_to_grams(
    qty: float,
    unit: str,
    default_unit: str = "g",
    conversions: Optional[Dict[str, float]] = None
) -> float:
    """
    Converts quantity and unit of an ingredient into grams.
    Supports future extensibility using ingredient-specific conversions.
    """
    if qty <= 0:
        return 0.0
        
    unit_lower = str(unit or "").strip().lower()
    default_unit_lower = str(default_unit or "g").strip().lower()
    
    # If both are gram-based or ml-based, it's already in grams/ml
    if _unit_is_gram(default_unit_lower) and _unit_is_gram(unit_lower):
        return qty

    # Check ingredient-specific conversion metadata first
    if conversions and unit_lower in conversions:
        return qty * float(conversions[unit_lower])
        
    # Check standardized global conversion fallback
    if unit_lower in UNIT_TO_GRAMS:
        return qty * UNIT_TO_GRAMS[unit_lower]
        
    # Default fallback: return quantity directly (assume 1 unit = 1g/100g basis)
    return qty

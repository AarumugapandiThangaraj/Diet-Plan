"""
Normalizers Utility

Provides data normalization helpers for cuisine types, meal timing sessions, goals, tags, 
diet preferences, and search keys.
"""

import re
from typing import Any, List
from config.constants import VALID_CUISINES

def normalize_tag(value: Any) -> str:
    s = str(value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = re.sub(r"^_+|_+$", "", s)
    return s

def _normalize_cuisine(value: Any) -> str:
    s = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    s = re.sub(r"_+", "_", s).strip("_")
    if s in VALID_CUISINES:
        return s
    aliases = {
        "north": "north_indian", "north_india": "north_indian",
        "south": "south_indian", "south_india": "south_indian",
        "emirati": "uae",
        "western": "continental", "american": "continental",
        "mediterr": "mediterranean", "med": "mediterranean",
        "africa": "african", "african": "african",
        "america": "americas", "americas": "americas", "latin_american": "americas",
        "east_asia": "east_asian", "east_asian": "east_asian", "chinese": "east_asian", "japanese": "east_asian", "korean": "east_asian",
        "southeast_asia": "southeast_asian", "southeast_asian": "southeast_asian", "thai": "southeast_asian", "vietnamese": "southeast_asian",
        "south_asia": "south_asian", "south_asian": "south_asian", "indian": "south_asian",
        "middle_east": "middle_eastern", "middle_eastern": "middle_eastern", "saudi": "middle_eastern", "arab": "middle_eastern",
        "nordic": "nordic", "scandinavian": "nordic",
        "oceania": "oceania", "australian": "oceania", "pacific": "oceania",
        "central": "central", "central_asian": "central",
        "russia": "russian", "russian": "russian",
        "fusion": "fusion", "global": "fusion", "fusion_global": "fusion",
    }
    return aliases.get(s, "north_indian")

def normalize_goal(goal: Any) -> str:
    g = normalize_tag(goal)
    if g in {"skin_repair", "hair_repair"}:
        return g
    return g

def normalize_goal_list(value: Any) -> List[str]:
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            g = normalize_goal(item)
            if g:
                out.append(g)
        return out
    g = normalize_goal(value)
    return [g] if g else []

def _normalize_meal_time(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if len(value) > 0 else ""
    s = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    mapping = {
        "early morning": "early_morning",
        "breakfast": "breakfast",
        "mid morning": "mid_morning",
        "lunch": "lunch",
        "evening": "evening",
        "evening snack": "evening",
        "snack": "evening",
        "dinner": "dinner",
        "bedtime": "bedtime",
        "bed time": "bedtime",
    }
    return mapping.get(s, "")

def _normalize_diet_type(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if len(value) > 0 else ""
    s = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if s in {"veg", "vegetarian", "vegan"}:
        return "veg"
    if s in {"non veg", "non vegetarian", "nonvegetarian", "eggetarian", "egg"}:
        return "non_veg"
    if s in {"non_veg", "nonveg"}:
        return "non_veg"
    return "any"

def normalize_ingredient_key(value: Any) -> str:
    s = str(value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_food_key(value: Any) -> str:
    return normalize_ingredient_key(value)

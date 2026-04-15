import re
import logging
from typing import List, Dict, Any, Tuple, Set

logger = logging.getLogger(__name__)

# Standardized synonym/allergen map
ALLERGEN_GROUPS = {
    "dairy": ["milk", "curd", "paneer", "cheese", "butter", "ghee", "khoya", "mawa", "whey", "casein", "dairy", "yogurt"],
    "soy": ["soy", "soya", "soybean", "tofu", "soy milk"],
    "gluten": ["wheat", "barley", "rye", "semolina", "gluten", "maida", "flour"],
    "nuts": ["peanut", "cashew", "almond", "walnut", "hazelnut", "pistachio", "nuts", "seeds"],
    "seafood": ["fish", "prawns", "shrimp", "seafood", "crab", "lobster"],
    "meat": ["chicken", "mutton", "meat", "lamb", "beef", "pork"],
    "eggs": ["egg", "eggs", "omelet", "omelette"]
}

def normalize_text(text: str) -> str:
    """Basic normalization for ingredient matching."""
    if not text:
        return ""
    # Lowercase and strip
    text = text.lower().strip()
    # Remove common punctuation that might interfere with word boundaries
    text = re.sub(r'[(),:;]', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text

def expand_avoid_list(avoid_list: List[str]) -> Set[str]:
    """Expands specific ingredients to their group synonyms."""
    expanded = set()
    for item in avoid_list:
        clean_item = normalize_text(item)
        if not clean_item:
            continue
        expanded.add(clean_item)
        
        # Check if this item is a key or belongs to a group
        for group, members in ALLERGEN_GROUPS.items():
            if clean_item == group or clean_item in members:
                expanded.update(members)
    return expanded

def filter_meals(meals: List[Dict[str, Any]], avoid_list: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Strictly filters out meals containing any ingredient in the avoid_list.
    Returns (allowed_meals, metadata).
    """
    if not avoid_list:
        return meals, {"filtered_count": 0, "reasons": {}}

    expanded_avoid = expand_avoid_list(avoid_list)
    if not expanded_avoid:
        return meals, {"filtered_count": 0, "reasons": {}}

    # Pre-compile regex patterns for performance and accuracy (whole word matching)
    # Using plural-friendly patterns: word -> \bword(s|es)?\b
    patterns = []
    for item in expanded_avoid:
        # Escape for regex and allow for common plurals
        escaped = re.escape(item)
        # Handle simple plural variations
        if item.endswith('y'):
            # e.g., berry -> berry or berries
            pattern_str = rf"\b{escaped[:-1]}(?:y|ies)\b"
        else:
            pattern_str = rf"\b{escaped}(?:s|es)?\b"
        patterns.append(re.compile(pattern_str, re.IGNORECASE))

    allowed = []
    filtered_count = 0
    reasons = {}

    for meal in meals:
        meal_name = normalize_text(meal.get("meal_name", ""))
        ingredients = normalize_text(meal.get("ingredients", ""))
        caution = normalize_text(meal.get("caution", ""))
        
        combined_text = f"{meal_name} {ingredients} {caution}"
        
        is_rejected = False
        reject_reason = ""
        
        for i, pattern in enumerate(patterns):
            if pattern.search(combined_text):
                is_rejected = True
                reject_reason = list(expanded_avoid)[i]
                break
        
        if is_rejected:
            filtered_count += 1
            # Log specific rejections (limited to avoid spam)
            if meal.get("Meal_ID") and filtered_count < 100:
                logger.debug(f"Meal {meal.get('Meal_ID')} ({meal.get('meal_name')}) rejected due to: {reject_reason}")
            continue
            
        allowed.append(meal)

    metadata = {
        "filtered_count": filtered_count,
        "avoided_ingredients_used": list(expanded_avoid)
    }
    
    return allowed, metadata

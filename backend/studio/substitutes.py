from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from .food_engine import get_engine, ErrorResponse

def extract_ingredient_name(token: Any) -> str:
    t = str(token or "").strip()
    if not t: return ""
    no_paren = re.sub(r"\(.*?\)", " ", t).strip()
    units = r'(?:ml|g|kg|tsp|tbsp|cup|glasses|katori|medium|small|big|large|pieces|whole|raw|cooked|baked|boiled|juice|powder|decoction)'
    clean = re.sub(rf'\b\d+(?:\.\d+)?\s*{units}?\b', '', no_paren, flags=re.I).strip()
    clean = re.sub(r'^(?:with|and|a|an|the)\s+', '', clean, flags=re.I)
    return clean or no_paren

def suggest_for_ingredients_text(ingredients: Any) -> Dict[str, Any]:
    text = str(ingredients or "")
    tokens = [t.strip() for t in re.split(r"[,\n;]", text) if t and t.strip()]
    
    engine = get_engine()
    unique_choices = []
    substitutes_by_key = {}
    seen_indices = set()

    for tok in tokens:
        clean_name = extract_ingredient_name(tok)
        if not clean_name: continue
            
        # extract quantity
        qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:g|ml)', tok, re.I)
        qty = float(qty_match.group(1)) if qty_match else 100.0

        resp = engine.find(clean_name, qty=qty)
        
        if not isinstance(resp, ErrorResponse):
            label = resp.original
            key = label.lower() # use label as key for frontend mapping
            if key not in seen_indices:
                seen_indices.add(key)
                unique_choices.append({
                    "token": tok,
                    "key": key,
                    "label": label
                })
                substitutes_by_key[key] = [s.model_dump() for s in resp.results]

    return {
        "choices": unique_choices,
        "substitutesByKey": substitutes_by_key,
    }

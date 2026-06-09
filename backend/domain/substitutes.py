from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from repositories.substitute_repository import (
    substitute_repository,
    normalize_key,
    extract_ingredient_name
)

def build_substitute_index():
    return {
        "names_by_norm": substitute_repository.names_by_norm,
        "neighbors_by_norm": substitute_repository.neighbors_by_norm,
        "details_by_norm": substitute_repository.details_by_norm,
    }

def suggest_for_ingredients_text(ingredients: Any) -> Dict[str, Any]:
    text = str(ingredients or "")
    tokens = [t.strip() for t in re.split(r"[,\n;]", text) if t and t.strip()]

    names_by_norm = substitute_repository.names_by_norm
    neighbors_by_norm = substitute_repository.neighbors_by_norm
    details_by_norm = substitute_repository.details_by_norm

    def find_ingredient_key(token: Any) -> Optional[str]:
        raw = extract_ingredient_name(token)
        norm = normalize_key(raw)
        if not norm:
            return None
        if norm in neighbors_by_norm:
            return norm

        best = None
        for key in neighbors_by_norm.keys():
            if norm == key:
                return key
            if norm in key or key in norm:
                if not best or len(key) > len(best):
                    best = key
        return best

    def get_substitutes_for_key(norm_key: str) -> List[Dict[str, Any]]:
        key = str(norm_key or "")
        if not key:
            return []
        neighbors = neighbors_by_norm.get(key) or set()
        if not neighbors:
            return []
        out = []
        for n in neighbors:
            out.append({"norm": n, "name": names_by_norm.get(n) or n, "details": details_by_norm.get(n)})
        out.sort(key=lambda x: str(x.get("name") or ""))
        return out

    out_choices = []
    for tok in tokens:
        key = find_ingredient_key(tok)
        if not key:
            continue
        label = names_by_norm.get(key) or extract_ingredient_name(tok)
        out_choices.append({"token": tok, "key": key, "label": label})

    seen = set()
    unique_choices = []
    for c in out_choices:
        k = c.get("key")
        if not k or k in seen:
            continue
        seen.add(k)
        unique_choices.append(c)

    substitutes_by_key = {c["key"]: get_substitutes_for_key(c["key"]) for c in unique_choices}

    return {
        "choices": unique_choices,
        "substitutesByKey": substitutes_by_key,
    }

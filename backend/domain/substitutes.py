from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

def _diet_plan_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _data_path(*parts: str) -> Path:
    return _diet_plan_root().joinpath(*parts)

def _normalize_name(value: Any) -> str:
    return str(value or "").lower().strip().replace("(", " ").replace(")", " ")

def normalize_key(value: Any) -> str:
    s = _normalize_name(value)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_ingredient_name(token: Any) -> str:
    t = str(token or "").strip()
    if not t:
        return ""
    no_paren = re.sub(r"\([^)]*\)", " ", t).strip()
    cut_at_number = re.sub(r"\b\d+(?:\.\d+)?\b.*$", "", no_paren, flags=re.I).strip()
    return cut_at_number or no_paren

@lru_cache(maxsize=1)
def load_master_substituents() -> List[Dict[str, Any]]:
    path = _data_path("data", "master_substituents.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []

@lru_cache(maxsize=1)
def build_substitute_index():
    names_by_norm: Dict[str, str] = {}
    details_by_norm: Dict[str, Any] = {}
    neighbors_by_norm: Dict[str, Set[str]] = {}

    def add_name(name: Any) -> Optional[str]:
        norm = normalize_key(name)
        if not norm:
            return None
        if norm not in names_by_norm:
            names_by_norm[norm] = str(name).strip()
        neighbors_by_norm.setdefault(norm, set())
        return norm

    def add_edge(a: str, b: str):
        if not a or not b or a == b:
            return
        neighbors_by_norm.setdefault(a, set()).add(b)
        neighbors_by_norm.setdefault(b, set()).add(a)

    for row in load_master_substituents():
        if not isinstance(row, dict):
            continue
        base = add_name(row.get("allergen_name"))
        subs = row.get("substitutes")
        subs = subs if isinstance(subs, list) else []
        sub_norms: List[str] = []

        for s in subs:
            if not isinstance(s, dict):
                continue
            n = add_name(s.get("name"))
            if not n:
                continue
            sub_norms.append(n)
            if n not in details_by_norm:
                details_by_norm[n] = s

        group = [x for x in [base, *sub_norms] if x]
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                add_edge(group[i], group[j])

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

    return {
        "names_by_norm": names_by_norm,
        "neighbors_by_norm": neighbors_by_norm,
        "details_by_norm": details_by_norm,
        "find_ingredient_key": find_ingredient_key,
        "get_substitutes_for_key": get_substitutes_for_key,
    }

def suggest_for_ingredients_text(ingredients: Any) -> Dict[str, Any]:
    text = str(ingredients or "")
    tokens = [t.strip() for t in re.split(r"[,\n;]", text) if t and t.strip()]

    idx = build_substitute_index()
    out_choices = []

    for tok in tokens:
        key = idx["find_ingredient_key"](tok)
        if not key:
            continue
        label = idx["names_by_norm"].get(key) or extract_ingredient_name(tok)
        out_choices.append({"token": tok, "key": key, "label": label})

    seen = set()
    unique_choices = []
    for c in out_choices:
        k = c.get("key")
        if not k or k in seen:
            continue
        seen.add(k)
        unique_choices.append(c)

    substitutes_by_key = {c["key"]: idx["get_substitutes_for_key"](c["key"]) for c in unique_choices}

    return {
        "choices": unique_choices,
        "substitutesByKey": substitutes_by_key,
    }

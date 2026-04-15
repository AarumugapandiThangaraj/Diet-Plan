from __future__ import annotations
import re
import pandas as pd
import numpy as np
import json
from pathlib import Path
from rapidfuzz import process, fuzz
from pydantic import BaseModel, Field
from typing import List, Dict, Union, Optional, Any

# =========================================================
# Configuration & Constants (from sub_master08.py)
# =========================================================
ALLERGEN_MAP = {
    "dairy": ["milk", "curd", "paneer", "cheese", "butter", "ghee", "khoya mawa", "whey casein", "dairy"],
    "soy": ["soy", "soya", "soybean", "soya bean", "tofu", "soy milk"],
    "gluten and cereals": ["wheat", "barley", "rye", "semolina", "gluten and cereals"],
    "nuts and seeds": ["peanut", "cashew", "almond", "sesame seeds", "nuts and seeds"],
    "fruits": ["banana", "mango", "apple", "grapes", "kiwi", "fruits"],
    "pulses and legumes": ["bengal gram", "black gram", "green gram", "soybean", "pulses and legumes"],
    "eggs": ["egg white", "egg yolk", "eggs"],
    "seafood": ["fish", "prawns shrimp", "seafood"],
    "spices": ["coriander", "cumin", "mustard", "spices"],
    "oils": ["peanut oil", "sesame oil", "oils"],
    "meat": ["chicken", "mutton", "meat"]
}

# =========================================================
# Pydantic Models
# =========================================================
class MacroOutput(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float

class SubstituteOutput(BaseModel):
    name: str
    quantity: float
    macros: MacroOutput
    group: str
    distance: float

class SubstituteResponse(BaseModel):
    original: str
    original_macros: MacroOutput
    group: str
    results: List[SubstituteOutput]

class ErrorResponse(BaseModel):
    error: str
    suggestion: Optional[str] = None
    did_you_mean: Optional[str] = None
    confidence: Optional[float] = None

# =========================================================
# DATA LOADER
# =========================================================
class DataLoader:
    @staticmethod
    def load(file_path: Union[str, Path]) -> pd.DataFrame:
        path = Path(file_path)
        if path.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(path)
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)

        # Normalize column names
        df.columns = (
            df.columns
            .str.lower()
            .str.replace("\xa0", "", regex=False)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

        def clean_text(text):
            return str(text).lower().strip().replace("(", "").replace(")", "")

        for col in ["ingredient name", "main name", "alias"]:
            if col in df.columns:
                df[col] = df[col].fillna("").apply(clean_text)

        if "alias" in df.columns:
            df["alias_list"] = df["alias"].apply(lambda x: [s.strip() for s in x.split("|") if s.strip()])
        else:
            df["alias_list"] = [[] for _ in range(len(df))]

        return df

class ExclusionResolver:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.all_names = []
        for _, row in df.iterrows():
            names = [row["ingredient name"], row["main name"]] + row["alias_list"]
            for name in names:
                if name:
                    self.all_names.append(self.normalize(name))

    def normalize(self, text):
        return str(text).lower().strip().replace("(", "").replace(")", "")

    def resolve(self, exclude_list: List[str]) -> Set[str]:
        resolved = set()
        for ex in exclude_list:
            ex = self.normalize(ex)
            match = process.extractOne(ex, self.all_names, scorer=fuzz.WRatio)
            if match and match[1] >= 80:
                resolved.add(match[0])
        
        expanded = set()
        for ex in resolved:
            expanded.add(ex)
            for _, items in ALLERGEN_MAP.items():
                if ex in items:
                    expanded.update(items)
        return expanded

class IngredientMatcher:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def find(self, query: str) -> Union[int, Dict[str, Any], None]:
        q = query.lower().strip().replace("(", "").replace(")", "")
        
        # 1. Exact
        exact = self.df[self.df["ingredient name"] == q]
        if not exact.empty: return exact.index[0]
        
        # 2. Main Name
        exact_main = self.df[self.df["main name"] == q]
        if not exact_main.empty: return exact_main.index[0]

        # 3. Alias Fuzzy
        best_score = 0
        best_idx = None
        for row_idx, row in self.df.iterrows():
            for alias in row["alias_list"]:
                score = fuzz.ratio(q, alias)
                if score > best_score:
                    best_score = score
                    best_idx = row_idx
        if best_score >= 90: return best_idx

        # 4. Global Fuzzy
        choices, mapping = [], []
        for idx, row in self.df.iterrows():
            names = [row["ingredient name"], row["main name"]] + row["alias_list"]
            for name in names:
                if name:
                    choices.append(name)
                    mapping.append(idx)
        
        result = process.extractOne(q, choices, scorer=fuzz.WRatio)
        if not result: return None
        match, score, match_idx = result
        if score < 90:
            return {"status": "low_confidence", "match": match, "score": score}
            
        return mapping[match_idx]

class FilterEngine:
    @staticmethod
    def normalize(text):
        return str(text).lower().strip().replace(r"\s+", " ")

    @staticmethod
    def normalize_series(series):
        return series.fillna("").str.lower().str.strip().str.replace(r"\s+", " ", regex=True)

    @staticmethod
    def apply(df: pd.DataFrame, original_row: pd.Series, exclude_list: List[str] = None, cuisine: str = None) -> pd.DataFrame:
        orig_name = FilterEngine.normalize(original_row["ingredient name"])
        orig_main = FilterEngine.normalize(original_row.get("main name", ""))
        category = FilterEngine.normalize(original_row.get("category", ""))
        state = FilterEngine.normalize(original_row.get("food _state", ""))
        group = FilterEngine.normalize(original_row.get("grup", ""))

        candidates = df[FilterEngine.normalize_series(df["ingredient name"]) != orig_name]

        # Remove same ingredient
        def is_same(row):
            name = FilterEngine.normalize(row["ingredient name"])
            main = FilterEngine.normalize(row.get("main name", ""))
            if category == "ingredient":
                return name == orig_name or (orig_main and main == orig_main)
            return name == orig_name
        candidates = candidates[~candidates.apply(is_same, axis=1)]

        # Filters
        if state and state != "nan":
            candidates = candidates[FilterEngine.normalize_series(candidates["food _state"]) == state]
        if group and group not in ["nan", "miscellaneous foods"]:
            candidates = candidates[FilterEngine.normalize_series(candidates["grup"]) == group]
        candidates = candidates[FilterEngine.normalize_series(candidates["category"]) == category]

        # Cuisine
        if "cuisine" in candidates.columns:
            target_cuisine = cuisine.lower() if cuisine else FilterEngine.normalize(original_row.get("cuisine", "all"))
            if target_cuisine != "all":
                CUISINE_MAP = {
                    "south india": {"south indian", "pan india", "all"},
                    "north india": {"north indian", "pan india", "all"},
                    "continental": {"continental", "all"},
                }
                allowed = CUISINE_MAP.get(target_cuisine, {"all"})
                candidates = candidates[FilterEngine.normalize_series(candidates["cuisine"]).isin(allowed)]

        # Exclusions
        if exclude_list:
            resolver = ExclusionResolver(df)
            resolved = resolver.resolve(exclude_list)
            def should_exclude(row):
                in_name = FilterEngine.normalize(row["ingredient name"])
                mn_name = FilterEngine.normalize(row["main name"])
                for ex in resolved:
                    if ex == in_name or ex == mn_name: return True
                return False
            candidates = candidates[~candidates.apply(should_exclude, axis=1)]

        return candidates

class NutritionEngine:
    @staticmethod
    def vector(row, qty):
        f = qty / 100.0
        return np.array([
            row["energy (kcal)"] * f,
            row["protein (g)"] * f,
            row["carbohydrates (g)"] * f,
            row["fat (g)"] * f,
            row.get("dietary fiber (g)", 0) * f
        ])

    @staticmethod
    def adjust_qty(original, candidate, qty):
        orig_cal = original["energy (kcal)"] * (qty / 100)
        cand_cal = candidate["energy (kcal)"]
        if orig_cal < 1 or cand_cal < 1: return qty
        adj = (orig_cal / cand_cal) * 100
        return round(max(qty * 0.8, min(qty * 1.2, adj)), 2)

class DiversityEngine:
    @staticmethod
    def filter(results, top_n=3):
        selected, seen = [], []
        for row, dist in results:
            name = row["ingredient name"]
            if any(fuzz.partial_ratio(name, s) > 80 for s in seen): continue
            selected.append((row, dist))
            seen.append(name)
            if len(selected) == top_n: break
        return selected

class SubstituteEngine:
    def __init__(self):
        root = Path(__file__).resolve().parents[2]
        path = root / "data" / "nutrition_db.json"
        self.df = DataLoader.load(path)
        self.matcher = IngredientMatcher(self.df)

    def find(self, ingredient: str, qty: float = 100.0, exclude: List[str] = None, cuisine: str = None) -> Union[SubstituteResponse, ErrorResponse]:
        idx = self.matcher.find(ingredient)
        if isinstance(idx, dict):
            return ErrorResponse(error="Low confidence", did_you_mean=idx["match"], confidence=idx["score"])
        if idx is None:
            # Try global fuzzy search if not found
            return ErrorResponse(error="Not found")

        original = self.df.loc[idx]
        filtered = FilterEngine.apply(self.df, original, exclude, cuisine)
        if filtered.empty: return ErrorResponse(error="No valid substitutes")

        orig_vec = NutritionEngine.vector(original, qty)
        ranked = []
        for _, row in filtered.iterrows():
            vec = NutritionEngine.vector(row, qty)
            dist = np.linalg.norm(orig_vec - vec)
            ranked.append((row, dist))
        
        ranked = sorted(ranked, key=lambda x: x[1])
        diverse = DiversityEngine.filter(ranked, top_n=5)
        
        output = []
        for row, dist in diverse:
            adj_qty = NutritionEngine.adjust_qty(original, row, qty)
            f = adj_qty / 100.0
            output.append(SubstituteOutput(
                name=row["ingredient name"].title(),
                quantity=adj_qty,
                macros=MacroOutput(
                    calories=round(row["energy (kcal)"] * f, 1),
                    protein=round(row["protein (g)"] * f, 1),
                    carbs=round(row["carbohydrates (g)"] * f, 1),
                    fat=round(row["fat (g)"] * f, 1),
                    fiber=round(row.get("dietary fiber (g)", 0) * f, 1),
                ),
                group=row["grup"],
                distance=round(dist, 2)
            ))

        return SubstituteResponse(
            original=original["ingredient name"].title(),
            original_macros=MacroOutput(
                calories=round(original["energy (kcal)"] * (qty/100), 1),
                protein=round(original["protein (g)"] * (qty/100), 1),
                carbs=round(original["carbohydrates (g)"] * (qty/100), 1),
                fat=round(original["fat (g)"] * (qty/100), 1),
                fiber=round(original.get("dietary fiber (g)", 0) * (qty/100), 1)
            ),
            group=original["grup"],
            results=output
        )

    def search_food(self, query: str, limit: int = 10):
        choices = self.df["ingredient name"].tolist()
        results = process.extract(query, choices, scorer=fuzz.WRatio, limit=limit)
        out = []
        for name, score, idx in results:
            row = self.df.iloc[idx]
            out.append({
                "name": name.title(),
                "group": row.get("grup", ""),
                "macros": {
                    "calories": row.get("energy (kcal)", 0),
                    "protein": row.get("protein (g)", 0),
                    "carbs": row.get("carbohydrates (g)", 0),
                    "fat": row.get("fat (g)", 0),
                    "fiber": row.get("dietary fiber (g)", 0)
                },
                "score": score
            })
        return out

# Global Instance
_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = SubstituteEngine()
    return _engine

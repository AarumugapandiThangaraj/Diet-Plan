import logging
import re
import time
from typing import Any, Dict, List, Set
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models.substitute import Substitute

logger = logging.getLogger(__name__)

def _normalize_name(value: Any) -> str:
    """
    Performs simple lowercase normalization and replaces parentheses with spaces.
    """
    return str(value or "").lower().strip().replace("(", " ").replace(")", " ")

def normalize_key(value: Any) -> str:
    """
    Fully normalizes a name key by removing non-alphanumeric characters and extra spaces.
    """
    s = _normalize_name(value)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_ingredient_name(token: Any) -> str:
    """
    Extracts the base ingredient name by stripping parenthetical info and numeric amounts/units.
    """
    t = str(token or "").strip()
    if not t:
        return ""
    no_paren = re.sub(r"\([^)]*\)", " ", t).strip()
    cut_at_number = re.sub(r"\b\d+(?:\.\d+)?\b.*$", "", no_paren, flags=re.I).strip()
    return cut_at_number or no_paren

class SubstituteRepository:
    """
    In-memory repository caching allergen ingredient substitutes loaded from the database.
    """
    def __init__(self):
        """
        Initializes default caching indexes.
        """
        self.names_by_norm: Dict[str, str] = {}
        self.details_by_norm: Dict[str, Any] = {}
        self.neighbors_by_norm: Dict[str, Set[str]] = {}
        self.initialized: bool = False

    async def initialize_cache(self) -> None:
        """
        Initializes the repository cache by loading records from PostgreSQL.
        """
        await self.refresh_cache()

    async def refresh_cache(self) -> None:
        """
        Refreshes the in-memory cache lookup maps by fetching latest records from database.
        """
        start_time = time.perf_counter()
        
        async with AsyncSessionLocal() as session:
            stmt = select(Substitute)
            res = await session.execute(stmt)
            records = res.scalars().all()
            
        if not records:
            raise RuntimeError("Database 'substitutes' table is empty or missing data.")
            
        new_names_by_norm: Dict[str, str] = {}
        new_details_by_norm: Dict[str, Any] = {}
        new_neighbors_by_norm: Dict[str, Set[str]] = {}

        def add_name(name: Any) -> str:
            if not name:
                return ""
            name_str = str(name).strip()
            norm = normalize_key(name_str)
            if not norm:
                return ""
            if norm not in new_names_by_norm:
                new_names_by_norm[norm] = name_str
            new_neighbors_by_norm.setdefault(norm, set())
            return norm

        def add_edge(a: str, b: str):
            if not a or not b or a == b:
                return
            new_neighbors_by_norm.setdefault(a, set()).add(b)
            new_neighbors_by_norm.setdefault(b, set()).add(a)

        allergen_categories = len(records)
        total_substitutes = 0

        for record in records:
            allergen_name = record.allergen_name
            if not allergen_name:
                continue
            base = add_name(allergen_name)
            
            subs = record.substitutes
            subs_list = subs if isinstance(subs, list) else []
            sub_norms: List[str] = []
            
            for s in subs_list:
                if not isinstance(s, dict):
                    continue
                name = s.get("name")
                if not name:
                    continue
                n = add_name(name)
                if not n:
                    continue
                sub_norms.append(n)
                if n not in new_details_by_norm:
                    new_details_by_norm[n] = s
                    total_substitutes += 1

            group = [x for x in [base, *sub_norms] if x]
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    add_edge(group[i], group[j])

        # Atomically swap the cache reference
        self.names_by_norm = new_names_by_norm
        self.details_by_norm = new_details_by_norm
        self.neighbors_by_norm = new_neighbors_by_norm
        self.initialized = True

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Loaded {total_substitutes} substitute mappings")
        logger.info(f"Loaded {allergen_categories} allergen categories")
        logger.info(f"Cache initialization completed in {duration_ms}ms")
        
        # Explicitly print to console for startup validation
        print(f"Loaded {total_substitutes} substitute mappings")
        print(f"Loaded {allergen_categories} allergen categories")
        print(f"Cache initialization completed in {duration_ms}ms")

substitute_repository = SubstituteRepository()

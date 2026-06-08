from __future__ import annotations

from typing import Any, Dict
from services.nutrition_service import calculate_daily_targets as _calc_targets

def calculate_daily_targets(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Compatibility wrapper redirecting to services.nutrition_service."""
    return _calc_targets(profile)

import sys
import os
import json
from pathlib import Path

# Setup pathing
root = Path(r"e:\IAgami\Bioart\NutriLLM\Abhis code\Diet-Plan-main")
sys.path.append(str(root))

from backend.studio.expansion import evaluate_and_stage_substitution

def test_swap():
    # Attempt to swap Butter for Tofu in MEAL_000006 (Chicken Sandwich)
    original_id = "MEAL_000006"
    # Original ingredients: "Whole wheat bread 50 g, cooked chicken 120 g, butter 5 g"
    new_ingredients = "Whole wheat bread 50 g, cooked chicken 120 g, tofu 20 g"
    subst_name = "Tofu"
    
    print(f"Testing substitution: {original_id} -> {subst_name}...")
    result = evaluate_and_stage_substitution(original_id, new_ingredients, subst_name)
    print("\nResult:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_swap()

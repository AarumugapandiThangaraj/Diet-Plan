# SOP: AI-Guided Magic Pick with User Preference

## Goal
To select meals that not only fit the user's nutritional targets but also align with their natural language taste preferences.

## Inputs
- `user_preference_text`: Natural language string (e.g., "I like chicken, high protein").
- `meal_pool`: List of candidate meals filtered by meal time and diet type.
- `user_goal`: The user's primary nutrition goal.

## Execution Workflow
1. **Preference Parsing**:
   - Send the `user_preference_text` to the AI Gateway.
   - Extract: `preferred_ingredients`, `avoid_ingredients`, `macro_bias` (e.g., more protein).
2. **Deterministic Pre-filtering**:
   - Filter `meal_pool` by `dietType` (Strict) and `mealTime`.
3. **Scoring & Ranking**:
   - Calculate a "Match Score" for each meal:
     - **Ingredient Boost**: +50 for each preferred ingredient found in the name or ingredients list.
     - **Goal Alignment**: +20 if keywords match the user's stated goal (e.g., "Skin Repair").
     - **Macro Delta**: Penalty for being far from macro targets (existing logic).
4. **Final Selection**:
   - Select the Top 3 meals per slot and assign them to the plan days.

## Output
- A structured list of assigned meals that reflect both "Heal" (nutrients) and "Taste" (preference).

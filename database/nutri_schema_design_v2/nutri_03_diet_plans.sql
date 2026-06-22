-- ============================================================
-- nutri_03_diet_plans.sql   (v2 — UI-aligned revamp)
-- Nutri — Diet-plan storage + swap/consumption history
-- Schema: "Twellr_Nutri"
--
-- Creates:
--   • "Twellr_Nutri".diet_plans                       (header + computed targets)
--   • "Twellr_Nutri".diet_plan_days                   (day_number + day totals)
--   • "Twellr_Nutri".diet_plan_meals                  (per session-slot)
--   • "Twellr_Nutri".diet_plan_meal_foods             (food row per plan meal)
--   • "Twellr_Nutri".diet_plan_meal_food_ingredients  (post-scale ingredient row)
--   • "Twellr_Nutri".diet_plan_meal_swaps             (NEW — swap audit trail)
--   • "Twellr_Nutri".diet_plan_meal_consumption       (NEW — "I ate this" check-ins)
--
-- Design principles applied per user feedback + UI:
--   1. NO snapshot (_snap_*) columns. The catalog is the source of truth;
--      a plan that references a now-deleted food simply gets food_id = NULL
--      (ON DELETE SET NULL) and the UI falls back to "deprecated food".
--      Trade-off: historical plans CAN drift if you delete catalog rows.
--      Mitigation: catalog uses soft delete (is_active = FALSE) — only
--      truly purged rows ever lose their snapshot.
--
--   2. NO LLM provenance columns on diet_plans. Generation metadata
--      (model, prompt id, raw payload) is captured in a separate audit
--      log outside the schema (out of scope here).
--
--   3. meal_slot is now meal_session_id — references the meal_sessions
--      reference table from nutri_01. That keeps the slot list in one
--      place and lets the planner sort meals on the day card naturally.
--
--   4. diet_plan_meal_swaps and diet_plan_meal_consumption are NEW —
--      they back the Swap.png / Swap-1.png "Swap food" CTA history and
--      the dashboard "Today's meals" + "I ate this" check-ins.
--
--   5. NO is_replaceable / is_swapable on plan rows — those flags belong
--      on the catalog (foods.meal_foods.is_replaceable,
--      food_ingredients.is_swapable) and are read at swap-drawer time.
--
-- Prerequisites:
--   • nutri_01_schema_catalog.sql      (foods / meals / meal_sessions)
--   • nutri_02_user_data.sql           (user_health_profiles)
--
-- All use IF NOT EXISTS — safe to re-run.
-- Run with:  SET search_path TO "Twellr_Nutri", wellness_platform, public;
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- 1. diet_plans
--    Header / envelope for one generated multi-day plan.
--    Mirrors the top-level diet_plan.json keys: days, targets{}, totalsAll{}.
--
--    Per user feedback: dropped LLM provenance (generator/model_name/
--    model_request_id/locale/title). The plan envelope is now just the
--    user-facing targets + scheduling window.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".diet_plans (
    id                          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                     UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    health_profile_id           UUID          NULL
        REFERENCES "Twellr_Nutri".user_health_profiles (id) ON DELETE SET NULL,
    -- envelope
    days                        SMALLINT      NOT NULL CHECK (days BETWEEN 1 AND 90),
    status                      VARCHAR(30)   NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','active','completed','archived','cancelled')),
    -- targets (the `targets` block from diet_plan.json — what the UI's
    -- "Daily intake" pill row renders on Planner.png)
    target_calories_kcal        INT           NULL,
    target_protein_g            NUMERIC(6,2)  NULL, --doubt Min and Max target need to be added in the table
    target_carbs_g              NUMERIC(6,2)  NULL,
    target_carbs_g_min          NUMERIC(6,2)  NULL,
    target_carbs_g_max          NUMERIC(6,2)  NULL,
    target_fat_g                NUMERIC(6,2)  NULL,
    target_fat_g_min            NUMERIC(6,2)  NULL,
    target_fat_g_max            NUMERIC(6,2)  NULL,
    target_fiber_g              NUMERIC(6,2)  NULL,
    target_fiber_g_min          NUMERIC(6,2)  NULL,
    target_water_l              NUMERIC(4,2)  NULL,
    target_water_l_min          NUMERIC(4,2)  NULL,
    target_water_l_max          NUMERIC(4,2)  NULL,
    -- physiological snapshot at generation time
    bmi_snapshot                NUMERIC(4,1)  NULL, -- doubt May not be needed if we store user_health_profiles
    bmi_category_snapshot       VARCHAR(30)   NULL, -- doubt
    bmr_kcal_snapshot           INT           NULL, -- doubt
    tdee_kcal_snapshot          INT           NULL, -- doubt
    activity_level_snapshot     VARCHAR(30)   NULL, -- doubt
    -- totalsAll{}
    totals_calories_kcal        NUMERIC(10,2) NULL,
    totals_protein_g            NUMERIC(10,2) NULL,
    totals_carbs_g              NUMERIC(10,2) NULL,
    totals_fat_g                NUMERIC(10,2) NULL,
    totals_fiber_g              NUMERIC(10,2) NULL,
    -- scheduling window (UI: Planner.png "Week 1 ▾" — `starts_on` is the
    -- Monday of week 1, `ends_on = starts_on + days - 1`)
    starts_on                   DATE          NULL,
    ends_on                     DATE          NULL,
    -- audit
    created_at                  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    archived_at                 TIMESTAMPTZ   NULL
);
CREATE INDEX        IF NOT EXISTS idx_dp_user_status ON "Twellr_Nutri".diet_plans (user_id, status, created_at DESC);
-- a user follows at most one active plan at a time
CREATE UNIQUE INDEX IF NOT EXISTS idx_dp_user_active ON "Twellr_Nutri".diet_plans (user_id) WHERE status = 'active';
CREATE INDEX        IF NOT EXISTS idx_dp_profile    ON "Twellr_Nutri".diet_plans (health_profile_id);


-- ────────────────────────────────────────────────────────────
-- 2. diet_plan_days
--    One row per day in the plan. Carries the per-day totals
--    (matches diet_plan.json `totalsByDay[i]`).
--    UI: the Day pills (Day 1 / Day 2 / ...) on Planner.png.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".diet_plan_days (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id             UUID          NOT NULL
        REFERENCES "Twellr_Nutri".diet_plans (id) ON DELETE CASCADE,
    day_number          SMALLINT      NOT NULL CHECK (day_number BETWEEN 1 AND 90),
    plan_date           DATE          NULL,                    -- = plan.starts_on + day_number - 1
    -- per-day totals (still kept here because the planner runs target-fit
    -- diagnostics per day before persisting — easier than recomputing)
    calories_kcal       NUMERIC(10,2) NULL,
    protein_g           NUMERIC(10,2) NULL,
    carbs_g             NUMERIC(10,2) NULL,
    fat_g               NUMERIC(10,2) NULL,
    fiber_g             NUMERIC(10,2) NULL,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dpd_plan_day UNIQUE (plan_id, day_number)
);
CREATE INDEX IF NOT EXISTS idx_dpd_plan ON "Twellr_Nutri".diet_plan_days (plan_id, day_number);
CREATE INDEX IF NOT EXISTS idx_dpd_date ON "Twellr_Nutri".diet_plan_days (plan_date) WHERE plan_date IS NOT NULL;


-- ────────────────────────────────────────────────────────────
-- 3. diet_plan_meals
--    One row per (day, meal_session). Holds the meal-level totals
--    (rendered as the 4 chips on each meal card in Planner.png:
--     kcal / Protein / Carb / Fats / Fiber) and the scale factor.
--
--    meal_id → catalog. ON DELETE SET NULL means deleted catalog
--    rows are tolerated.
--    meal_session_id → meal_sessions reference table.
--    UNIQUE (plan_day_id, meal_session_id) — one meal per session per day.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".diet_plan_meals (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_day_id         UUID          NOT NULL
        REFERENCES "Twellr_Nutri".diet_plan_days (id) ON DELETE CASCADE,
    meal_session_id     BIGINT        NOT NULL --remove
        REFERENCES "Twellr_Nutri".meal_sessions (id) ON DELETE RESTRICT,
    meal_id             BIGINT        NULL
        REFERENCES "Twellr_Nutri".meals (id) ON DELETE SET NULL,
    -- macros (snapshot at plan-build time — rendered on the meal card)
    calories_kcal       NUMERIC(10,2) NULL,
    protein_g           NUMERIC(10,2) NULL,
    carbs_g             NUMERIC(10,2) NULL,
    fat_g               NUMERIC(10,2) NULL,
    fiber_g             NUMERIC(10,2) NULL,
    -- scaling applied by the planner so the meal hits its session target
    scale_applied       NUMERIC(6,4)  NULL,
    sort_order          SMALLINT      NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dpm_day_session UNIQUE (plan_day_id, meal_session_id)
);
CREATE INDEX IF NOT EXISTS idx_dpm_plan_day ON "Twellr_Nutri".diet_plan_meals (plan_day_id);
CREATE INDEX IF NOT EXISTS idx_dpm_meal     ON "Twellr_Nutri".diet_plan_meals (meal_id);
CREATE INDEX IF NOT EXISTS idx_dpm_session  ON "Twellr_Nutri".diet_plan_meals (meal_session_id);


-- ────────────────────────────────────────────────────────────
-- 4. diet_plan_meal_foods
--    Foods on a single plan meal (a meal has 1..N foods).
--    Just the catalog FK + post-scale quantity + macros.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".diet_plan_meal_foods (
    id                       UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_meal_id             UUID          NOT NULL
        REFERENCES "Twellr_Nutri".diet_plan_meals (id) ON DELETE CASCADE,
    food_id                  BIGINT        NULL
        REFERENCES "Twellr_Nutri".foods (id) ON DELETE SET NULL,
    -- portion (after LLM/planner scaling)
    quantity                 DOUBLE PRECISION NOT NULL CHECK (quantity >= 0),
    unit                     VARCHAR(50)   NOT NULL,
    -- macros snapshot (so we don't have to re-derive on every plan render)
    calories_kcal            NUMERIC(10,2) NULL,
    protein_g                NUMERIC(10,2) NULL,
    carbs_g                  NUMERIC(10,2) NULL,
    fat_g                    NUMERIC(10,2) NULL,
    fiber_g                  NUMERIC(10,2) NULL,
    -- concerns the planner used to pick this food (rec-engine training signal)
    supports                 JSONB         NULL,
    supports_normalized      TEXT[]        NOT NULL DEFAULT '{}',
    sort_order               SMALLINT      NOT NULL DEFAULT 0,
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dpmf_meal     ON "Twellr_Nutri".diet_plan_meal_foods (plan_meal_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_dpmf_food     ON "Twellr_Nutri".diet_plan_meal_foods (food_id);
CREATE INDEX IF NOT EXISTS idx_dpmf_supp_gin ON "Twellr_Nutri".diet_plan_meal_foods USING GIN (supports_normalized);


-- ────────────────────────────────────────────────────────────
-- 5. diet_plan_meal_food_ingredients
--    Per-ingredient breakdown (post-scaling).
--    UI: the "Ingredients" list on meal prep.png (Daily Serv list:
--    Rolled oats 80g / Soft-fruit fat oil-grilled 100ml / etc).
--    Per user feedback — no snap_*, no per100g_*, no is_swapable.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".diet_plan_meal_food_ingredients (
    id                       UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_meal_food_id        UUID          NOT NULL
        REFERENCES "Twellr_Nutri".diet_plan_meal_foods (id) ON DELETE CASCADE,
    ingredient_id            BIGINT        NULL
        REFERENCES "Twellr_Nutri".ingredients_master (id) ON DELETE SET NULL,
    quantity                 DOUBLE PRECISION NOT NULL CHECK (quantity >= 0),
    unit                     VARCHAR(50)   NOT NULL,
    -- macros at this scaled quantity (4-decimal precision keeps the
    -- per-meal sum accurate to the gram even for small ingredients)
    calories_kcal            NUMERIC(10,4) NULL,
    protein_g                NUMERIC(10,4) NULL,
    carbs_g                  NUMERIC(10,4) NULL,
    fat_g                    NUMERIC(10,4) NULL,
    fiber_g                  NUMERIC(10,4) NULL,
    sort_order               SMALLINT      NOT NULL DEFAULT 0,
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dpmfi_meal_food  ON "Twellr_Nutri".diet_plan_meal_food_ingredients (plan_meal_food_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_dpmfi_ingredient ON "Twellr_Nutri".diet_plan_meal_food_ingredients (ingredient_id);


-- ────────────────────────────────────────────────────────────
-- 6. diet_plan_meal_swaps   (NEW)
--    Audit trail for every "Swap whole meal" / "Swap ingredient"
--    interaction (Swap.png, Swap-1.png, meal prep.png).
--
--    Polymorphic by swap_type:
--      • 'meal'        → from_meal_id        → to_meal_id
--      • 'food'        → from_food_id        → to_food_id
--      • 'ingredient'  → from_ingredient_id  → to_ingredient_id
--
--    plan_meal_id is the slot where the swap happened.
--    plan_meal_food_id / plan_meal_food_ingredient_id are filled in
--    when the swap was scoped narrower than the whole meal.
--
--    Used by:
--      • The UI to render "Your food has been swapped successfully" toast
--        + reverse-swap.
--      • The rec engine as explicit negative signal on the `from` item
--        and positive on the `to` item.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".diet_plan_meal_swaps ( -- remove 
    id                              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                         UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    plan_id                         UUID          NOT NULL
        REFERENCES "Twellr_Nutri".diet_plans (id) ON DELETE CASCADE,
    plan_meal_id                    UUID          NOT NULL
        REFERENCES "Twellr_Nutri".diet_plan_meals (id) ON DELETE CASCADE,
    plan_meal_food_id               UUID          NULL
        REFERENCES "Twellr_Nutri".diet_plan_meal_foods (id) ON DELETE CASCADE,
    plan_meal_food_ingredient_id    UUID          NULL
        REFERENCES "Twellr_Nutri".diet_plan_meal_food_ingredients (id) ON DELETE CASCADE,
    swap_type                       VARCHAR(20)   NOT NULL
        CHECK (swap_type IN ('meal','food','ingredient')),
    -- polymorphic from/to refs — exactly one pair populated based on swap_type
    from_meal_id                    BIGINT        NULL REFERENCES "Twellr_Nutri".meals (id)               ON DELETE SET NULL,
    to_meal_id                      BIGINT        NULL REFERENCES "Twellr_Nutri".meals (id)               ON DELETE SET NULL,
    from_food_id                    BIGINT        NULL REFERENCES "Twellr_Nutri".foods (id)               ON DELETE SET NULL,
    to_food_id                      BIGINT        NULL REFERENCES "Twellr_Nutri".foods (id)               ON DELETE SET NULL,
    from_ingredient_id              BIGINT        NULL REFERENCES "Twellr_Nutri".ingredients_master (id)  ON DELETE SET NULL,
    to_ingredient_id                BIGINT        NULL REFERENCES "Twellr_Nutri".ingredients_master (id)  ON DELETE SET NULL,
    reason                          VARCHAR(50)   NULL
        CHECK (reason IS NULL OR reason IN
            ('user_preference','allergy','availability','taste','cuisine_filter','calorie_match','other')),
    notes                           TEXT          NULL,
    swapped_at                      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- consistency: each swap_type must populate the matching pair
    CONSTRAINT chk_swap_polymorphism CHECK (
        (swap_type = 'meal'        AND from_meal_id       IS NOT NULL AND to_meal_id       IS NOT NULL)
     OR (swap_type = 'food'        AND from_food_id       IS NOT NULL AND to_food_id       IS NOT NULL)
     OR (swap_type = 'ingredient'  AND from_ingredient_id IS NOT NULL AND to_ingredient_id IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_dpms_user_plan ON "Twellr_Nutri".diet_plan_meal_swaps (user_id, plan_id, swapped_at DESC);
CREATE INDEX IF NOT EXISTS idx_dpms_plan_meal ON "Twellr_Nutri".diet_plan_meal_swaps (plan_meal_id);
CREATE INDEX IF NOT EXISTS idx_dpms_type      ON "Twellr_Nutri".diet_plan_meal_swaps (swap_type);


-- ────────────────────────────────────────────────────────────
-- 7. diet_plan_meal_consumption   (NEW)
--    "I ate this meal" check-ins. Drives:
--      • Dashboard.png "Today's meals" list — strikes through eaten meals.
--      • user_daily_intake roll-up (nutri_02) — every check-in row gets
--        aggregated into the matching intake_date row.
--      • Adherence metrics (% of planned meals actually eaten).
--
--    consumed_at lets the UI surface "had this at 14:05 instead of the
--    scheduled 13:30".
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".diet_plan_meal_consumption (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    plan_meal_id        UUID          NOT NULL
        REFERENCES "Twellr_Nutri".diet_plan_meals (id) ON DELETE CASCADE,
    state               VARCHAR(20)   NOT NULL DEFAULT 'eaten'
        CHECK (state IN ('eaten','partial','skipped','planned')),
    portion_factor      NUMERIC(4,2)  NOT NULL DEFAULT 1.0  -- doubt Need to discuss
        CHECK (portion_factor BETWEEN 0.0 AND 5.0),         -- 0 = skipped, 1 = full
    consumed_at         TIMESTAMPTZ   NULL,
    consumed_date       DATE          NOT NULL DEFAULT CURRENT_DATE,
    notes               TEXT          NULL,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- one check-in per plan_meal per user (re-tap updates the existing row)
    CONSTRAINT uq_dpmc_plan_meal UNIQUE (user_id, plan_meal_id)
);
CREATE INDEX IF NOT EXISTS idx_dpmc_user_date ON "Twellr_Nutri".diet_plan_meal_consumption (user_id, consumed_date DESC);
CREATE INDEX IF NOT EXISTS idx_dpmc_state     ON "Twellr_Nutri".diet_plan_meal_consumption (state);

-- ============================================================
-- End nutri_03_diet_plans.sql  (v2)
-- ============================================================

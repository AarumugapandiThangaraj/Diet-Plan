-- ============================================================
-- nutri_02_user_data.sql   (v2 — UI-aligned revamp)
-- Nutri — User-scoped tables (profile, goals, gut survey, food prefs, logs)
-- Schema: "Twellr_Nutri"   (cross-schema FK to wellness_platform.users)
--
-- Creates:
--   • "Twellr_Nutri".user_health_profiles    (slim — demographics + computed targets)
--   • "Twellr_Nutri".user_goals              (NEW — primary + secondary goals)
--   • "Twellr_Nutri".user_gut_assessments    (NEW — gut symptom survey: input 19.png)
--   • "Twellr_Nutri".user_food_preferences   (NEW — "Pick foods you like" gallery)
--   • "Twellr_Nutri".user_weight_logs        (NEW — BMI Calculator "Previous readings",
--                                              "My Progress" nav item)
--   • "Twellr_Nutri".user_daily_intake       (NEW — dashboard calories vs target)
--   • "Twellr_Nutri".user_hydration_log      (NEW — dashboard hydration grid)
--
-- Out of scope for this batch:
--   • user_nutri_preferences (likes/dislikes/allergies blob) — replaced by
--     the structured user_food_preferences + user_health_profiles.allergies.
--   • Chat tables — out of scope until the nutrition assistant ships.
--
-- Design principles applied per user feedback + UI designs:
--   1. Multiple goals are first-class. The UI (Primary & Secondary goal.png)
--      lets the user pick ONE primary (skin/hair/skin_hair) and N secondary
--      goals — so we store one row per goal with a `goal_tier`.
--      Each goal links to wellness_platform.concern_taxonomy.
--   2. Latest-flag pattern used everywhere a "current snapshot" is needed
--      (user_health_profiles.is_latest, user_gut_assessments.is_latest) —
--      mirrors wellness_platform.ai_assessments.is_latest.
--   3. dietary_restrictions / medical_conditions removed per user feedback.
--   4. Soft "follow this plan" state lives on diet_plans (nutri_03), not here.
--
-- Prerequisites:
--   • nutri_01_schema_catalog.sql            ("Twellr_Nutri" schema + foods table)
--   • wellness_platform.users                (Twellr core)
--   • wellness_platform.concern_taxonomy     (extended in nutri_04)
--
-- Run with: SET search_path TO "Twellr_Nutri", wellness_platform, public;
-- All use IF NOT EXISTS — safe to re-run.
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- 1. user_health_profiles
--    Demographic + anthropometric snapshot used to compute the daily
--    nutrition target (BMI / BMR / TDEE / macros / water).
--
--    Slimmed per user feedback:
--      • dietary_restrictions removed (lives on user_food_preferences now).
--      • medical_conditions removed (deferred — handled by AI assessments
--        on the Twellr side via ai_assessment_results).
--
--    Latest-row pattern: at most one is_latest=TRUE per user (partial
--    unique index). Older rows are kept for the BMI Calculator's
--    "Previous readings" list (BMI Calculator.png) — but user_weight_logs
--    below is the dedicated time-series for that.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".user_health_profiles (
    id                         UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                    UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    legacy_user_identifier     VARCHAR(100)  NULL,
    -- demographics
    age                        SMALLINT      NULL CHECK (age IS NULL OR age BETWEEN 1 AND 120),
    gender                     VARCHAR(20)   NULL
        CHECK (gender IS NULL OR gender IN ('male','female','non_binary','prefer_not_to_say')),
    -- anthropometrics (snapshot at submission time)
    height_cm                  NUMERIC(5,2)  NULL CHECK (height_cm IS NULL OR height_cm BETWEEN 50 AND 260),
    weight_kg                  NUMERIC(5,2)  NULL CHECK (weight_kg IS NULL OR weight_kg BETWEEN 10 AND 400),
    target_weight_kg           NUMERIC(5,2)  NULL,
    bmi                        NUMERIC(4,1)  NULL,
    bmi_category               VARCHAR(30)   NULL,
    -- activity + calculated energy needs
    activity_level             VARCHAR(30)   NULL
        CHECK (activity_level IS NULL OR activity_level IN  -- doubt We can bring new table.
            ('sedentary','lightly_active','moderately_active','very_active','extra_active')),
    bmr_kcal                   INT           NULL,
    tdee_kcal                  INT           NULL,
    -- target water (legacy, computed from weight) — also tracked in user_daily_intake
    target_water_l             NUMERIC(4,2)  NULL,
    -- allergies (the only structured list kept on the profile)
    allergies                  JSONB         NULL,
    allergies_normalized       TEXT[]        NOT NULL DEFAULT '{}',
    -- lifecycle
    is_latest                  BOOL          NOT NULL DEFAULT TRUE,
    created_at                 TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX        IF NOT EXISTS idx_uhp_user        ON "Twellr_Nutri".user_health_profiles (user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_uhp_latest      ON "Twellr_Nutri".user_health_profiles (user_id) WHERE is_latest = TRUE;
CREATE INDEX        IF NOT EXISTS idx_uhp_allerg_gin  ON "Twellr_Nutri".user_health_profiles USING GIN (allergies_normalized);


-- ────────────────────────────────────────────────────────────
-- 2. user_goals   (NEW)
--    Primary + secondary goals the user picked on the
--    "Your inner wellness shapes your outer glow" screen
--    (Primary & Secondary goal.png).
--
--    Primary (radio): Skin / Hair / Skin & Hair
--    Secondary (multi-select): More Energy, Weight Management,
--      Mental Clarity, Better Sleep, Gut Health, Mental Calmness
--
--    concern_id links each goal to wellness_platform.concern_taxonomy
--    so the rec engine can rank foods/meals by the same key it uses
--    for products and services.
--
--    Partial unique index enforces "exactly one primary per user".
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".user_goals (
    id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    concern_id   BIGINT        NOT NULL
        REFERENCES wellness_platform.concern_taxonomy (id) ON DELETE RESTRICT, -- doubt Need to change according to the requirement.
    goal_tier    VARCHAR(20)   NOT NULL
        CHECK (goal_tier IN ('primary','secondary')),
    sort_order   SMALLINT      NOT NULL DEFAULT 0,
    is_active    BOOL          NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ug_user_concern UNIQUE (user_id, concern_id)
);
CREATE INDEX        IF NOT EXISTS idx_ug_user_active ON "Twellr_Nutri".user_goals (user_id, is_active);
CREATE INDEX        IF NOT EXISTS idx_ug_concern     ON "Twellr_Nutri".user_goals (concern_id);
-- enforce: at most one ACTIVE primary goal per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_ug_one_primary
    ON "Twellr_Nutri".user_goals (user_id)
    WHERE goal_tier = 'primary' AND is_active = TRUE;


-- ────────────────────────────────────────────────────────────
-- 3. user_gut_assessments   (NEW)
--    Captures the 5 multi-choice answers from input 19.png:
--      1. How often do you feel bloated after meals?
--         rarely | sometimes_2_3_week | often_4_5_week | almost_every_meal
--      2. How's your energy 30 minutes after eating?
--         energised | neutral | slightly_sluggish | energy_crash
--      3. Mental clarity after meals?
--         sharp_focused | slightly_foggy | heavy_brain_fog
--      4. How regular is your digestion?
--         very_regular | very_unpredictable | occasionally_off | often_irregular
--      5. Have you noticed your skin reacting to certain foods?
--         never | rarely | sometimes | definitely_yes
--
--    Used by the animation.png pipeline:
--      "Analysing gut symptom profile" → "Mapping gut-skin-hair
--      connections" → "Identifying nutrient absorption gaps" →
--      "Building your personalised gut protocol"
--
--    Latest-flag pattern (partial unique index on is_latest = TRUE).
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".user_gut_assessments ( -- remove Not within the scope in phase 1
    id                          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                     UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    bloating_frequency          VARCHAR(40)   NULL
        CHECK (bloating_frequency IS NULL OR bloating_frequency IN
            ('rarely','sometimes_2_3_week','often_4_5_week','almost_every_meal')),
    energy_30min_after_eating   VARCHAR(40)   NULL
        CHECK (energy_30min_after_eating IS NULL OR energy_30min_after_eating IN
            ('energised','neutral','slightly_sluggish','energy_crash')),
    mental_clarity_after_meals  VARCHAR(40)   NULL
        CHECK (mental_clarity_after_meals IS NULL OR mental_clarity_after_meals IN
            ('sharp_focused','slightly_foggy','heavy_brain_fog')),
    digestion_regularity        VARCHAR(40)   NULL
        CHECK (digestion_regularity IS NULL OR digestion_regularity IN
            ('very_regular','very_unpredictable','occasionally_off','often_irregular')),
    skin_reactions_to_food      VARCHAR(40)   NULL
        CHECK (skin_reactions_to_food IS NULL OR skin_reactions_to_food IN
            ('never','rarely','sometimes','definitely_yes')),
    -- escape hatch for any extra Qs the UI grows in future without a migration
    raw_answers                 JSONB         NULL,
    is_latest                   BOOL          NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX        IF NOT EXISTS idx_uga_user   ON "Twellr_Nutri".user_gut_assessments (user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_uga_latest ON "Twellr_Nutri".user_gut_assessments (user_id) WHERE is_latest = TRUE;


-- ────────────────────────────────────────────────────────────
-- 4. user_food_preferences   (NEW)
--    Per-food likes / dislikes / allergies the user picked on the
--    "Pick the foods you like" gallery (Nutri sample 27.png and
--    Nutri sample 8 - Expanded.png).
--
--    One row per (user, food) — UNIQUE constraint enforces it.
--    `preference` is a strict enum CHECK so the planner can filter
--    cleanly: liked → boost, disliked → exclude, allergic → hard exclude.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".user_food_preferences ( -- remove Not within the scope in phase 1
    id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    food_id      BIGINT        NOT NULL
        REFERENCES "Twellr_Nutri".foods (id) ON DELETE CASCADE,
    preference   VARCHAR(20)   NOT NULL
        CHECK (preference IN ('liked','disliked','allergic')),
    source       VARCHAR(30)   NOT NULL DEFAULT 'user'
        CHECK (source IN ('user','llm','onboarding','imported')),
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ufp_user_food UNIQUE (user_id, food_id)
);
CREATE INDEX IF NOT EXISTS idx_ufp_user_pref ON "Twellr_Nutri".user_food_preferences (user_id, preference);
CREATE INDEX IF NOT EXISTS idx_ufp_food      ON "Twellr_Nutri".user_food_preferences (food_id);


-- ────────────────────────────────────────────────────────────
-- 5. user_weight_logs   (NEW)
--    Time-series weight / BMI / BMR / water-target / target-weight
--    captures. Drives:
--      • BMI Calculator.png — "Previous readings" cards.
--      • Nav Bar.png "My Progress" item — the weight curve.
--      • Dashboard.png — "Weight Progress" gauge.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".user_weight_logs (  -- doubt We thinking, it is repeating the data from user_health_profiles
    id                UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    weight_kg         NUMERIC(5,2)  NOT NULL CHECK (weight_kg BETWEEN 10 AND 400),
    bmi               NUMERIC(4,1)  NULL,
    bmi_category      VARCHAR(30)   NULL,
    bmr_kcal          INT           NULL,
    target_weight_kg  NUMERIC(5,2)  NULL,
    water_l           NUMERIC(4,2)  NULL,
    notes             TEXT          NULL,
    recorded_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_uwl_user_at ON "Twellr_Nutri".user_weight_logs (user_id, recorded_at DESC);


-- ────────────────────────────────────────────────────────────
-- 6. user_daily_intake   (NEW)
--    Aggregated nutrition consumed per day per user. Drives the
--    dashboard "Calories — Lack of physical activity" panel and
--    the macro chips at the bottom (Dashboard.png — 2040 kcal,
--    Carbs 200 / Protein 45 / Fiber 25 / Fat 35).
--
--    UNIQUE (user_id, intake_date) — at most one summary row per day.
--    Computed by an event handler on every meal-eaten check-in
--    (no business logic enforced here — this is a storage row).
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".user_daily_intake (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    intake_date         DATE          NOT NULL,
    -- consumed
    calories_consumed   NUMERIC(10,2) NOT NULL DEFAULT 0,
    protein_consumed_g  NUMERIC(8,2)  NOT NULL DEFAULT 0,
    carbs_consumed_g    NUMERIC(8,2)  NOT NULL DEFAULT 0,
    fat_consumed_g      NUMERIC(8,2)  NOT NULL DEFAULT 0,
    fiber_consumed_g    NUMERIC(8,2)  NOT NULL DEFAULT 0,
    -- target snapshot (denormalised from the active diet_plan on that date)
    calories_target     INT           NULL,
    protein_target_g    NUMERIC(8,2)  NULL,
    carbs_target_g      NUMERIC(8,2)  NULL,
    fat_target_g        NUMERIC(8,2)  NULL,
    fiber_target_g      NUMERIC(8,2)  NULL,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_udi_user_date UNIQUE (user_id, intake_date)
);
CREATE INDEX IF NOT EXISTS idx_udi_user_date ON "Twellr_Nutri".user_daily_intake (user_id, intake_date DESC);


-- ────────────────────────────────────────────────────────────
-- 7. user_hydration_log   (NEW)
--    Each row = one tap on the hydration grid (Dashboard.png
--    "Hydration Status — 7-day grid"). Each tap logs one glass
--    (≈ 250 ml) at the current timestamp.
--
--    We store the timestamp (not just date) so the UI can:
--      • Render today's intake hour-by-hour.
--      • Backfill weekly totals (rendered as a 4×7 grid).
--      • Drive nudge notifications later.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".user_hydration_log (
    id           BIGSERIAL     PRIMARY KEY,
    user_id      UUID          NOT NULL
        REFERENCES wellness_platform.users (id) ON DELETE CASCADE,
    logged_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    glasses      SMALLINT      NOT NULL DEFAULT 1 CHECK (glasses BETWEEN 1 AND 20),
    volume_ml    INT           NULL CHECK (volume_ml IS NULL OR volume_ml BETWEEN 1 AND 5000),
    source       VARCHAR(30)   NOT NULL DEFAULT 'manual'
        CHECK (source IN ('manual','imported','wearable'))
);
CREATE INDEX IF NOT EXISTS idx_uhl_user_at ON "Twellr_Nutri".user_hydration_log (user_id, logged_at DESC);
CREATE INDEX IF NOT EXISTS idx_uhl_user_date ON "Twellr_Nutri".user_hydration_log (user_id, ((logged_at AT TIME ZONE 'UTC')::date) DESC);

-- ============================================================
-- End nutri_02_user_data.sql  (v2)
-- ============================================================

-- ============================================================
-- nutri_01_schema_catalog.sql   (v2 — UI-aligned revamp)
-- Nutri / Diet-Plan integration — Schema + Catalog tables
-- Schema: "Twellr_Nutri"  (double-quoted — mixed case, mirrors "Twellr_Rec_Engine")
--
-- Creates:
--   • SCHEMA "Twellr_Nutri"
--   • "Twellr_Nutri".cuisines
--   • "Twellr_Nutri".meal_sessions            (NEW — extracted out of meals)
--   • "Twellr_Nutri".ingredients_master       (slimmed per user edits)
--   • "Twellr_Nutri".foods                    (slimmed — no materialized macros)
--   • "Twellr_Nutri".food_ingredients
--   • "Twellr_Nutri".meals                    (slimmed — no macros / no embedded session)
--   • "Twellr_Nutri".meal_session_assignments (NEW — many-to-many meals ↔ sessions)
--   • "Twellr_Nutri".meal_foods               (no quantity/unit — lives on the food)
--   • "Twellr_Nutri".substitutes
--
-- Design principles applied per user feedback:
--   1. CATALOG TABLES ARE THE SINGLE SOURCE OF TRUTH.
--      No materialized macros on foods/meals, no _snap_* fields in plan tables.
--      Macros are derived from food_ingredients on read (or via a v_food_macros
--      materialized view added later if read latency becomes an issue).
--   2. MEAL SESSIONS ARE A FIRST-CLASS REFERENCE TABLE.
--      A meal can be served at multiple sessions (e.g. an oats bowl can fit
--      breakfast OR mid-morning). The UI also paginates "Pick the foods you
--      like" by session — making this a real table makes that query trivial.
--   3. INGREDIENT_ALIASES IS GONE.
--      The legacy ING-XXXXX client IDs are an artefact of the research dump;
--      the LLM and the planner both reference master ingredients by integer id.
--   4. LLM PROVENANCE / CHAT TABLES STAY OUT OF SCOPE.
--      No `generator` / `model_name` / chat tables until the assistant ships.
--   5. BILINGUAL CONTRACT KEPT.
--      Every visible string column has an _ar twin — name_ar, description_ar,
--      preparation_ar.
--   6. SOFT DELETE KEPT (is_active + deleted_at).
--
-- Prerequisites: none (foundation file).
--
-- IMPORTANT: run with the following search path:
--   SET search_path TO "Twellr_Nutri", wellness_platform, public;
--
-- All use IF NOT EXISTS — safe to re-run.
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- 0. Schema
-- ────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS "Twellr_Nutri";


-- ────────────────────────────────────────────────────────────
-- 1. cuisines
--    Master list of cuisines (north_indian, continental, gulf …).
--    `code` is the snake_case form used in the diet_plan.json
--    (`"cuisine_type": "north_indian"`) and the swap drawer's
--    cuisine dropdown (UI: Swap.png — "South Indian ▼").
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".cuisines (
    id           BIGSERIAL     PRIMARY KEY,
    code         VARCHAR(50)   NOT NULL UNIQUE,
    name_en      VARCHAR(100)  NOT NULL,
    name_ar      VARCHAR(100)  NULL,
    -- country_code VARCHAR(2)    NULL,
    sort_order   SMALLINT      NOT NULL DEFAULT 0,
    is_active    BOOL          NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cuis_code   ON "Twellr_Nutri".cuisines (code);
CREATE INDEX        IF NOT EXISTS idx_cuis_active ON "Twellr_Nutri".cuisines (is_active);


-- ────────────────────────────────────────────────────────────
-- 2. meal_sessions   (NEW — per user feedback)
--    Fixed catalog of meal time slots the UI uses:
--      early_morning, breakfast, mid_morning, lunch, evening,
--      snack, dinner, bedtime, supper.
--    The Planner UI (Planner.png) groups the day's meals by
--    these. The "Pick the foods you like" screen (Nutri sample
--    8 - Expanded.png) lists them as the right-hand timeline.
--    A row's `default_time` lets the dashboard suggest a time
--    even when the user has not customised it.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".meal_sessions (
    id            BIGSERIAL     PRIMARY KEY,
    code          VARCHAR(40)   NOT NULL UNIQUE, -- doubt Purpose of the Code?
    name_en       VARCHAR(60)   NOT NULL,
    name_ar       VARCHAR(60)   NULL,
    start_time    TIME          NULL,
    end_time      TIME          NULL,
    sort_order    SMALLINT      NOT NULL DEFAULT 0,         -- governs display order
    is_active     BOOL          NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_msess_sort ON "Twellr_Nutri".meal_sessions (sort_order) WHERE is_active = TRUE;

-- Seed the 8 slots the UI cycles through (matches the existing Nutri
-- meal_times list: ["early_morning", "breakfast", "mid_morning",
-- "lunch", "evening", "dinner", "bedtime"] + "snack" used in the
-- legacy meals dataset).
INSERT INTO "Twellr_Nutri".meal_sessions (code, name_en, name_ar, start_time, end_time, sort_order)
VALUES
    ('early_morning', 'Early Morning', 'الصباح الباكر', '05:00', '07:00', 10),
    ('breakfast',     'Breakfast',     'الإفطار',       '07:30', '09:30', 20),
    ('mid_morning',   'Mid Morning',   'منتصف الصباح',  '10:30', '11:30', 30),
    ('lunch',         'Lunch',         'الغداء',         '12:30', '14:30', 40),
    ('evening',       'Evening',       'المساء',         '16:00', '18:00', 50),
    ('snack',         'Snack',         'وجبة خفيفة',    '17:00', '18:30', 55),
    ('dinner',        'Dinner',        'العشاء',         '19:30', '21:30', 60),
    ('bedtime',       'Bedtime',       'وقت النوم',     '21:30', '23:30', 70)
ON CONFLICT (code) DO NOTHING;


-- ────────────────────────────────────────────────────────────
-- 3. ingredients_master
--    Canonical, deduplicated, language-neutral ingredient row.
--
--    Slimmed per user feedback — removed classifier columns
--    (category / main_name / food_group / food_type /
--    food_state / allergens / conversions). The slim shape is
--    enough for the planner (it needs name, default_unit, and
--    per-100g macros to scale meals) and the UI doesn't expose
--    those classifiers anywhere in the new designs.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".ingredients_master (
    id              BIGSERIAL     PRIMARY KEY,
    name_en         VARCHAR(255)  NOT NULL,
    name_ar         VARCHAR(255)  NULL,
    default_unit    VARCHAR(50)   NOT NULL,                  -- 'g', 'ml', 'tsp', 'piece' …
    -- per-100g macros (the per100g block in the plan JSON)
    calories_kcal   DOUBLE PRECISION NOT NULL DEFAULT 0,
    protein_g       DOUBLE PRECISION NOT NULL DEFAULT 0,
    carbs_g         DOUBLE PRECISION NOT NULL DEFAULT 0,
    fat_g           DOUBLE PRECISION NOT NULL DEFAULT 0,
    fiber_g         DOUBLE PRECISION NOT NULL DEFAULT 0,
    -- variable-shape nutrition data (kept whole, jsonb)
    micronutrients  JSONB         NULL,
    benefits        JSONB         NULL, -- doubt 
    caution         TEXT          NULL,
    notes           TEXT          NULL,
    -- soft delete + audit
    is_active       BOOL          NOT NULL DEFAULT TRUE,
    deleted_at      TIMESTAMPTZ   NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_im_name_en ON "Twellr_Nutri".ingredients_master (LOWER(name_en));
CREATE INDEX        IF NOT EXISTS idx_im_active  ON "Twellr_Nutri".ingredients_master (is_active);


-- ────────────────────────────────────────────────────────────
-- 4. foods
--    A "food" is a preparable item (Phulka, Chole, Snack Stackers …).
--    A meal contains 1..N foods; a food contains 1..N ingredients.
--
--    Slimmed per user feedback:
--      • Materialised macros (calories_kcal, protein_g, …) removed.
--        They are computed from food_ingredients via:
--          SUM( ingredient.macro_per100g * fi.quantity / 100 )
--        across all rows with fi.unit = ingredient.default_unit.
--        For UI hot-paths we will add v_food_macros (materialized
--        view) in a follow-up file once the cardinality settles.
--      • `warning` boolean removed (replaced by row-level caution
--        text inherited from contained ingredients).
--
--    Kept:
--      • diet_types JSONB + diet_types_normalized TEXT[] for the
--        rec-engine and the "Pick the foods you like" filter chips.
--      • supports JSONB + supports_normalized TEXT[] for the
--        rec-engine concern matching.
--      • food_role CHECK for plate composition ranking.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".foods (
    id                      BIGSERIAL     PRIMARY KEY,
    cuisine_id              BIGINT        NOT NULL
        REFERENCES "Twellr_Nutri".cuisines (id) ON DELETE RESTRICT,
    client_food_id          VARCHAR(100)  NOT NULL,            -- e.g. "FOOD_BF_043"
    name_en                 VARCHAR(255)  NOT NULL,
    name_ar                 VARCHAR(255)  NULL,
    description_en          TEXT          NULL,
    description_ar          TEXT          NULL,
    preparation_en          TEXT          NULL,                 -- step-by-step (meal prep.png)
    preparation_ar          TEXT          NULL,
    notes                   TEXT          NULL,
    food_role               VARCHAR(30)   NULL
        CHECK (food_role IN ('base','side','snack','dessert','beverage','condiment','other')),  -- doubt Bring as new table
    -- portion (per serving)
    quantity                DOUBLE PRECISION NOT NULL,
    min_quantity            DOUBLE PRECISION NULL,
    max_quantity            DOUBLE PRECISION NULL,
    unit                    VARCHAR(50)   NOT NULL,
    -- classifiers (for rec-engine + UI filter chips)
    diet_types              JSONB         NULL,                 -- raw LLM array
    diet_types_normalized   TEXT[]        NOT NULL DEFAULT '{}',
    supports                JSONB         NULL,                 -- ["Skin Repair","Hair Repair"]
    supports_normalized     TEXT[]        NOT NULL DEFAULT '{}',
    image_url               VARCHAR(1024) NULL,
    -- soft delete + audit
    is_active               BOOL          NOT NULL DEFAULT TRUE,
    deleted_at              TIMESTAMPTZ   NULL,
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_foods_cuisine_client UNIQUE (cuisine_id, client_food_id),
    CONSTRAINT chk_foods_qty_bounds CHECK (
        (min_quantity IS NULL OR max_quantity IS NULL OR min_quantity <= max_quantity)
    )
);
CREATE INDEX IF NOT EXISTS idx_foods_name              ON "Twellr_Nutri".foods (LOWER(name_en));
CREATE INDEX IF NOT EXISTS idx_foods_cuisine_active    ON "Twellr_Nutri".foods (cuisine_id, is_active);
CREATE INDEX IF NOT EXISTS idx_foods_role              ON "Twellr_Nutri".foods (food_role);
CREATE INDEX IF NOT EXISTS idx_foods_diet_norm_gin     ON "Twellr_Nutri".foods USING GIN (diet_types_normalized);
CREATE INDEX IF NOT EXISTS idx_foods_supports_norm_gin ON "Twellr_Nutri".foods USING GIN (supports_normalized);


-- ────────────────────────────────────────────────────────────
-- 5. food_ingredients
--    Junction: food ↔ ingredients_master, with portion size per
--    ingredient. Composite PK (food_id, ingredient_id).
--
--    KEEPING `unit` on the junction even though every ingredient
--    has a `default_unit` — because the same ingredient can be
--    measured differently across recipes (e.g. Coconut Oil is
--    `tsp` in tempering but `g` in a dressing). The diet_plan.json
--    sample confirms this: the same ingredient ID appears with
--    different units in different foods.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".food_ingredients (
    food_id         BIGINT           NOT NULL
        REFERENCES "Twellr_Nutri".foods (id) ON DELETE CASCADE,
    ingredient_id   BIGINT           NOT NULL
        REFERENCES "Twellr_Nutri".ingredients_master (id) ON DELETE RESTRICT,
    quantity        DOUBLE PRECISION NOT NULL CHECK (quantity >= 0),
    -- change Unit comes form ingredients and Is Swapable is not in the scope of phase 1.
    -- unit            VARCHAR(50)      NOT NULL,                 -- see comment above
    -- is_swapable     BOOL             NOT NULL DEFAULT FALSE,
    sort_order      SMALLINT         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    PRIMARY KEY (food_id, ingredient_id)
);
CREATE INDEX IF NOT EXISTS idx_fi_ingredient ON "Twellr_Nutri".food_ingredients (ingredient_id);
-- CREATE INDEX IF NOT EXISTS idx_fi_swapable   ON "Twellr_Nutri".food_ingredients (food_id) WHERE is_swapable = TRUE;


-- ────────────────────────────────────────────────────────────
-- 6. meals
--    A meal is a complete plate composed of 1..N foods.
--
--    Slimmed per user feedback:
--      • Materialised macros removed (derived from meal_foods +
--        food_ingredients).
--      • image_url removed (UI renders the primary food's image —
--        Planner.png shows one food image per meal card).
--      • Embedded `meal_session` column removed — moved to its own
--        many-to-many table (meal_session_assignments) so a meal
--        can legitimately fit multiple sessions.
--      • sessions / tags / allergens JSONB blobs removed (replaced
--        by the proper many-to-many on sessions; allergens are
--        derived from contained ingredients; tags are folded into
--        diet_types / supports).
--
--    Kept:
--      • goal JSONB + goal_normalized TEXT[] for rec-engine.
--      • diet_types JSONB + normalized TEXT[].
--      • scheduled_time TIME (legacy preferred time; can be NULL).
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".meals (
    id                      BIGSERIAL     PRIMARY KEY,
    cuisine_id              BIGINT        NOT NULL
        REFERENCES "Twellr_Nutri".cuisines (id) ON DELETE RESTRICT,
    client_meal_id          VARCHAR(100)  NOT NULL,             -- e.g. "MEAL_7A9F0F73"
    name_en                 VARCHAR(255)  NOT NULL,
    name_ar                 VARCHAR(255)  NULL,
    description_en          TEXT          NULL,
    description_ar          TEXT          NULL,

    -- change Brings from the meal sessions table and sheduled time is migrated to the meal_sessions table
    meal_session_id         BIGINT          NOT NULL
        REFERENCES "Twellr_Nutri".meal_sessions (id) ON DELETE RESTRICT,    
    -- scheduled_time          TIME          NULL,                 -- preferred time of day
    
    prep_time_minutes       INT           NULL CHECK (prep_time_minutes IS NULL OR prep_time_minutes >= 0),
    -- classifiers
    goal                    JSONB         NULL,                 -- ["Hair Repair", …]
    goal_normalized         TEXT[]        NOT NULL DEFAULT '{}',
    -- change secondary goal is added in the schema
    secondary_goal          JSONB         NULL,                 -- ["Weight loss", …]
    secondary_goal_normalized TEXT[]        NOT NULL DEFAULT '{}',

    diet_types              JSONB         NULL,
    diet_types_normalized   TEXT[]        NOT NULL DEFAULT '{}',
    -- soft delete + audit
    is_active               BOOL          NOT NULL DEFAULT TRUE,
    deleted_at              TIMESTAMPTZ   NULL,
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_meals_cuisine_client UNIQUE (cuisine_id, client_meal_id)
);
CREATE INDEX IF NOT EXISTS idx_meals_name          ON "Twellr_Nutri".meals (LOWER(name_en));
CREATE INDEX IF NOT EXISTS idx_meals_cuisine       ON "Twellr_Nutri".meals (cuisine_id, is_active);
CREATE INDEX IF NOT EXISTS idx_meals_goal_norm_gin ON "Twellr_Nutri".meals USING GIN (goal_normalized);
CREATE INDEX IF NOT EXISTS idx_meals_diet_norm_gin ON "Twellr_Nutri".meals USING GIN (diet_types_normalized);


-- ────────────────────────────────────────────────────────────
-- 7. meal_session_assignments   (NEW — replaces `meals.meal_session`)
--    Many-to-many between meals and meal_sessions.
--    Driven by the UI:
--      • Planner.png groups meals into per-session rows.
--      • Nutri sample 8 - Expanded.png pages "Pick foods you
--        like" by session (Early Morning · Mid AM · Breakfast · Lunch …).
--    Some meals (a fruit bowl, a smoothie) legitimately belong to
--    multiple sessions — a row per (meal, session) handles that.
--    `is_primary` lets the planner choose the canonical slot when
--    nothing else is specified.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".meal_session_assignments (  -- doubt If we bring them in the meals table, we don't need junction table.
    meal_id      BIGINT       NOT NULL
        REFERENCES "Twellr_Nutri".meals (id) ON DELETE CASCADE,
    session_id   BIGINT       NOT NULL
        REFERENCES "Twellr_Nutri".meal_sessions (id) ON DELETE RESTRICT,
    is_primary   BOOL         NOT NULL DEFAULT FALSE,
    sort_order   SMALLINT     NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (meal_id, session_id)
);
CREATE INDEX IF NOT EXISTS idx_msa_session ON "Twellr_Nutri".meal_session_assignments (session_id);
-- enforce at most one primary session per meal
CREATE UNIQUE INDEX IF NOT EXISTS idx_msa_primary ON "Twellr_Nutri".meal_session_assignments (meal_id) WHERE is_primary = TRUE;


-- ────────────────────────────────────────────────────────────
-- 8. meal_foods
--    Junction: meal ↔ food, no per-meal quantity/unit (per user
--    feedback) — the food itself defines its portion. This matches
--    the meals.json shape:
--        "Foods": [{ "ID": "FOOD_0002", "Replaceable": true }]
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".meal_foods (
    meal_id         BIGINT       NOT NULL
        REFERENCES "Twellr_Nutri".meals (id) ON DELETE CASCADE,
    food_id         BIGINT       NOT NULL
        REFERENCES "Twellr_Nutri".foods (id) ON DELETE RESTRICT,
    is_replaceable  BOOL         NOT NULL DEFAULT FALSE,
    sort_order      SMALLINT     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (meal_id, food_id)
);
CREATE INDEX IF NOT EXISTS idx_mf_food ON "Twellr_Nutri".meal_foods (food_id);


-- ────────────────────────────────────────────────────────────
-- 9. substitutes
--    Allergen-driven ingredient substitution lookups
--    (e.g. dairy → almond_milk / coconut_milk).
--    Powers the "Swap ingredient" CTA on meal prep.png.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".substitutes (
    id                 BIGSERIAL     PRIMARY KEY,
    allergen_category  VARCHAR(100)  NULL,
    allergen_code      VARCHAR(100)  NOT NULL,                  -- lower_snake (was allergen_name)
    name_en            VARCHAR(150)  NOT NULL,
    name_ar            VARCHAR(150)  NULL,
    substitutes        JSONB         NOT NULL,
    is_active          BOOL          NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_subs_allergen UNIQUE (allergen_code)
);
CREATE INDEX IF NOT EXISTS idx_subs_category ON "Twellr_Nutri".substitutes (allergen_category, is_active);
CREATE INDEX IF NOT EXISTS idx_subs_gin      ON "Twellr_Nutri".substitutes USING GIN (substitutes);

-- ============================================================
-- End nutri_01_schema_catalog.sql  (v2)
-- ============================================================

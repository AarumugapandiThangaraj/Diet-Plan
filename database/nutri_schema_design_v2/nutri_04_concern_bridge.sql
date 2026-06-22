-- ============================================================
-- nutri_04_concern_bridge.sql   (v2 — UI-aligned seed list)
-- Nutri ↔ Twellr concern taxonomy bridge
-- Schemas: "Twellr_Nutri"  +  wellness_platform.concern_taxonomy
--
-- Creates / extends:
--   • wellness_platform.concern_taxonomy (ALTER — accept 'nutrition' domain)
--   • Seed rows for the goals the new UI exposes
--   • "Twellr_Nutri".food_concern_tags    (foods ↔ concern)
--   • "Twellr_Nutri".meal_concern_tags    (meals ↔ concern)
--   • "Twellr_Nutri".v_concern_tagged_items   (UNION view)
--
-- The seed list now matches Primary & Secondary goal.png:
--   PRIMARY    →  skin · hair · skin_hair
--   SECONDARY  →  more_energy · weight_management · mental_clarity ·
--                 better_sleep · gut_health · mental_calmness
--
-- `skin` and `hair` already exist on concern_taxonomy (added by
-- platform_concern_taxonomy.sql). We add the rest under
-- domain = 'nutrition'.
--
-- Prerequisites:
--   • nutri_01_schema_catalog.sql                  ("Twellr_Nutri".foods/meals)
--   • platform_concern_taxonomy.sql                (concern_taxonomy table)
--   • recengine_schema_views.sql                   (concern_taxonomy.domain column)
--
-- Run with:  SET search_path TO "Twellr_Nutri", wellness_platform, public;
-- All use IF NOT EXISTS — safe to re-run.
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- 1. ALTER wellness_platform.concern_taxonomy
--    Extend the `domain` CHECK to accept 'nutrition'.
-- ────────────────────────────────────────────────────────────
DO $$
DECLARE
    drop_sql TEXT;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'wellness_platform'
          AND table_name   = 'concern_taxonomy'
          AND column_name  = 'domain'
    ) THEN
        SELECT string_agg('ALTER TABLE wellness_platform.concern_taxonomy DROP CONSTRAINT ' || quote_ident(c.conname) || ';', E'\n')
        INTO drop_sql
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'wellness_platform'
          AND t.relname = 'concern_taxonomy'
          AND c.contype = 'c'
          AND pg_get_constraintdef(c.oid) ILIKE '%domain%';

        IF drop_sql IS NOT NULL THEN
            EXECUTE drop_sql;
        END IF;

        ALTER TABLE wellness_platform.concern_taxonomy
            ADD CONSTRAINT concern_taxonomy_domain_check
            CHECK (domain IS NULL OR domain IN
                ('skin','body','wellness','hair','nail','general','nutrition'));
    END IF;
END;
$$;


-- ────────────────────────────────────────────────────────────
-- 2. food_concern_tags
--    Maps "Twellr_Nutri".foods to wellness_platform.concern_taxonomy.
--    Mirrors product_concern_tags / service_concern_tags.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".food_concern_tags (
    id           BIGSERIAL      PRIMARY KEY,
    food_id      BIGINT         NOT NULL
        REFERENCES "Twellr_Nutri".foods (id) ON DELETE CASCADE,
    concern_id   BIGINT         NOT NULL
        REFERENCES wellness_platform.concern_taxonomy (id) ON DELETE CASCADE,
    tag_weight   NUMERIC(3,2)   NOT NULL DEFAULT 1.0
        CHECK (tag_weight BETWEEN 0.0 AND 1.0),
    source       VARCHAR(30)    NOT NULL DEFAULT 'llm'
        CHECK (source IN ('llm','manual','dietician','imported')),
    is_active    BOOL           NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fct_food_concern UNIQUE (food_id, concern_id)
);
CREATE INDEX IF NOT EXISTS idx_fct_food    ON "Twellr_Nutri".food_concern_tags (food_id, is_active);
CREATE INDEX IF NOT EXISTS idx_fct_concern ON "Twellr_Nutri".food_concern_tags (concern_id, is_active);


-- ────────────────────────────────────────────────────────────
-- 3. meal_concern_tags
--    Same shape, for meals.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS "Twellr_Nutri".meal_concern_tags (
    id           BIGSERIAL      PRIMARY KEY,
    meal_id      BIGINT         NOT NULL
        REFERENCES "Twellr_Nutri".meals (id) ON DELETE CASCADE,
    concern_id   BIGINT         NOT NULL
        REFERENCES wellness_platform.concern_taxonomy (id) ON DELETE CASCADE,
    tag_weight   NUMERIC(3,2)   NOT NULL DEFAULT 1.0
        CHECK (tag_weight BETWEEN 0.0 AND 1.0),
    source       VARCHAR(30)    NOT NULL DEFAULT 'llm'
        CHECK (source IN ('llm','manual','dietician','imported')),
    is_active    BOOL           NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mct_meal_concern UNIQUE (meal_id, concern_id)
);
CREATE INDEX IF NOT EXISTS idx_mct_meal    ON "Twellr_Nutri".meal_concern_tags (meal_id, is_active);
CREATE INDEX IF NOT EXISTS idx_mct_concern ON "Twellr_Nutri".meal_concern_tags (concern_id, is_active);


-- ────────────────────────────────────────────────────────────
-- 4. Seed concern_taxonomy with the UI's goal list
--    Primary tile: Skin / Hair / Skin & Hair (Primary & Secondary goal.png).
--    Secondary chips: the 6 chips shown below the primary row.
--
--    `skin` and `hair` already exist (seeded by
--    platform_concern_taxonomy.sql). We only insert what's new.
-- ────────────────────────────────────────────────────────────
INSERT INTO wellness_platform.concern_taxonomy
    (code, name_en, name_ar, parent_id, sort_order, domain, recommendation_mode)
VALUES
    -- combined primary goal (the third tile)
    ('skin_hair',          'Skin & Hair',        'البشرة والشعر',   NULL, 5,  'nutrition', 'none'),
    -- secondary chips
    ('more_energy',        'More Energy',        'مزيد من الطاقة',  NULL, 60, 'nutrition', 'none'),
    ('weight_management',  'Weight Management',  'إدارة الوزن',     NULL, 61, 'nutrition', 'none'),
    ('mental_clarity',     'Mental Clarity',     'صفاء الذهن',      NULL, 62, 'nutrition', 'none'),
    ('better_sleep',       'Better Sleep',       'نوم أفضل',         NULL, 63, 'nutrition', 'none'),
    ('gut_health',         'Gut Health',         'صحة الأمعاء',     NULL, 64, 'nutrition', 'none'),
    ('mental_calmness',    'Mental Calmness',    'هدوء نفسي',       NULL, 65, 'nutrition', 'none')
ON CONFLICT (code) DO NOTHING;


-- ────────────────────────────────────────────────────────────
-- 5. v_concern_tagged_items
--    UNION view exposing foods + meals as (item_type, item_id, concern_id,
--    tag_weight) — used by the rec engine when ranking cross-domain results
--    against the user's primary/secondary goals.
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW "Twellr_Nutri".v_concern_tagged_items AS
    SELECT
        'food'::text                     AS item_type,
        f.id::text                       AS item_id,
        f.client_food_id                 AS item_code,
        f.name_en                        AS item_name,
        fct.concern_id                   AS concern_id,
        fct.tag_weight                   AS tag_weight,
        fct.is_active                    AS is_active
    FROM "Twellr_Nutri".food_concern_tags fct
    JOIN "Twellr_Nutri".foods f ON f.id = fct.food_id
    WHERE fct.is_active = TRUE AND f.is_active = TRUE
    UNION ALL
    SELECT
        'meal'::text                     AS item_type,
        m.id::text                       AS item_id,
        m.client_meal_id                 AS item_code,
        m.name_en                        AS item_name,
        mct.concern_id                   AS concern_id,
        mct.tag_weight                   AS tag_weight,
        mct.is_active                    AS is_active
    FROM "Twellr_Nutri".meal_concern_tags mct
    JOIN "Twellr_Nutri".meals m ON m.id = mct.meal_id
    WHERE mct.is_active = TRUE AND m.is_active = TRUE;

-- ============================================================
-- End nutri_04_concern_bridge.sql  (v2)
-- ============================================================

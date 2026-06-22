-- ============================================================
-- nutri_05_data_migration.sql   (v2 — UI-aligned)
-- One-shot data move: legacy public.*  →  "Twellr_Nutri".*
--
-- OPTIONAL — only run if the Nutri research database has been restored
-- into the same Postgres instance under the `public` schema.
--
-- What this v2 file does NOT migrate (intentionally removed in v2 schema):
--   • public.ingredient_aliases                  — table dropped from target
--   • public.user_preferences                    — table dropped from target
--   • public.ingredients (alphanumeric ING-XXX)  — was already skipped in v1
--   • Ingredient classifier columns (category/grup/food_type/food_state/
--     allergens/conversions)                     — dropped from target schema
--   • Materialised macros on foods/meals         — dropped from target schema
--   • meals.sessions / meals.tags / meals.allergens — dropped from target;
--     `sessions` is migrated into meal_session_assignments instead.
--
-- What this v2 file DOES migrate:
--   • cuisines (preserving integer PKs)
--   • master_ingredients → ingredients_master (slim columns only)
--   • foods (slim — no macros)
--   • food_ingredients (rename swapable → is_swapable)
--   • meals (slim — no macros / no image_url)
--   • meals.sessions JSONB → meal_session_assignments many-to-many
--   • meal_foods (rename replaceable → is_replaceable, drop quantity/unit)
--   • substitutes (recoded with allergen_code)
--
-- Run with:  SET search_path TO "Twellr_Nutri", wellness_platform, public;
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- Pre-flight: detect legacy tables; bail cleanly if not present.
-- ────────────────────────────────────────────────────────────
DO $$
DECLARE
    has_legacy bool;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   IN ('cuisines','master_ingredients','foods','meals',
                               'food_ingredients','meal_foods','substitutes')
    ) INTO has_legacy;

    IF NOT has_legacy THEN
        RAISE NOTICE 'No legacy public.* nutri tables detected — skipping data migration.';
        RETURN;
    END IF;
END;
$$;


-- ────────────────────────────────────────────────────────────
-- 1. cuisines
-- ────────────────────────────────────────────────────────────
INSERT INTO "Twellr_Nutri".cuisines (id, code, name_en, created_at, updated_at)
OVERRIDING SYSTEM VALUE
SELECT
    c.id,
    LOWER(REGEXP_REPLACE(c.name, '[^A-Za-z0-9]+', '_', 'g')) AS code,
    c.name,
    c.created_at,
    c.updated_at
FROM public.cuisines c
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('"Twellr_Nutri".cuisines', 'id'),
    COALESCE((SELECT MAX(id) FROM "Twellr_Nutri".cuisines), 1),
    true
);


-- ────────────────────────────────────────────────────────────
-- 2. ingredients_master  (from public.master_ingredients — slim shape)
--    Classifier columns dropped per v2 schema.
-- ────────────────────────────────────────────────────────────
INSERT INTO "Twellr_Nutri".ingredients_master (
    id, name_en, default_unit,
    calories_kcal, protein_g, carbs_g, fat_g, fiber_g,
    micronutrients, benefits,
    caution, notes,
    created_at, updated_at
)
OVERRIDING SYSTEM VALUE
SELECT
    mi.id, mi.name, mi.default_unit,
    mi.calories, mi.protein, mi.carbs, mi.fat, mi.fiber,
    mi.micronutrients::jsonb, mi.benefits::jsonb,
    mi.caution, mi.notes,
    mi.created_at, mi.updated_at
FROM public.master_ingredients mi
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('"Twellr_Nutri".ingredients_master', 'id'),
    COALESCE((SELECT MAX(id) FROM "Twellr_Nutri".ingredients_master), 1),
    true
);


-- ────────────────────────────────────────────────────────────
-- 3. foods  (slim shape — no materialised macros)
--    diet_types / supports JSONB + a normalized text[] derived inline.
--    `type` (free text) → `food_role` (CHECK; unknown values → 'other').
-- ────────────────────────────────────────────────────────────
INSERT INTO "Twellr_Nutri".foods (
    id, cuisine_id, client_food_id, name_en, description_en,
    diet_types, diet_types_normalized,
    quantity, min_quantity, max_quantity, unit,
    supports, supports_normalized,
    preparation_en, notes,
    food_role, image_url, created_at, updated_at
)
OVERRIDING SYSTEM VALUE
SELECT
    f.id, f.cuisine_id, f.client_food_id, f.name, f.description,
    f.diet_types::jsonb,
    CASE WHEN f.diet_types IS NULL THEN '{}'::text[]
         ELSE ARRAY(
            SELECT LOWER(REGEXP_REPLACE(elem, '[^A-Za-z0-9]+', '_', 'g'))
            FROM jsonb_array_elements_text(f.diet_types::jsonb) elem
         )
    END,
    f.quantity, f.min_quantity, f.max_quantity, f.unit,
    f.supports::jsonb,
    CASE WHEN f.supports IS NULL THEN '{}'::text[]
         ELSE ARRAY(
            SELECT LOWER(REGEXP_REPLACE(elem, '[^A-Za-z0-9]+', '_', 'g'))
            FROM jsonb_array_elements_text(f.supports::jsonb) elem
         )
    END,
    f.preparation, f.notes,
    CASE LOWER(COALESCE(f.type, ''))
        WHEN 'base'      THEN 'base'
        WHEN 'side'      THEN 'side'
        WHEN 'snack'     THEN 'snack'
        WHEN 'dessert'   THEN 'dessert'
        WHEN 'beverage'  THEN 'beverage'
        WHEN 'condiment' THEN 'condiment'
        ELSE 'other'
    END,
    f.image_url, f.created_at, f.updated_at
FROM public.foods f
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('"Twellr_Nutri".foods', 'id'),
    COALESCE((SELECT MAX(id) FROM "Twellr_Nutri".foods), 1),
    true
);


-- ────────────────────────────────────────────────────────────
-- 4. food_ingredients  (rename `swapable` → `is_swapable`)
-- ────────────────────────────────────────────────────────────
INSERT INTO "Twellr_Nutri".food_ingredients (food_id, ingredient_id, quantity, unit, is_swapable)
SELECT fi.food_id, fi.master_ingredient_id, fi.quantity, fi.unit, fi.swapable
FROM public.food_ingredients fi
ON CONFLICT (food_id, ingredient_id) DO NOTHING;


-- ────────────────────────────────────────────────────────────
-- 5. meals  (slim shape)
--    scheduled_time was VARCHAR(50) "13:30" → coerced to TIME.
--    No more meal_session column — sessions are migrated separately below.
-- ────────────────────────────────────────────────────────────
INSERT INTO "Twellr_Nutri".meals (
    id, cuisine_id, client_meal_id, name_en, description_en,
    scheduled_time, prep_time_minutes,
    goal, goal_normalized,
    diet_types, diet_types_normalized,
    created_at, updated_at
)
OVERRIDING SYSTEM VALUE
SELECT
    m.id, m.cuisine_id, m.client_meal_id, m.name, m.description,
    CASE WHEN m.scheduled_time ~ '^\d{1,2}:\d{2}'
         THEN (m.scheduled_time)::time
         ELSE NULL
    END,
    NULLIF(REGEXP_REPLACE(COALESCE(m.prep_time, ''), '[^0-9]', '', 'g'), '')::int,
    m.goal::jsonb,
    CASE WHEN m.goal IS NULL THEN '{}'::text[]
         ELSE ARRAY(SELECT LOWER(REGEXP_REPLACE(elem,'[^A-Za-z0-9]+','_','g'))
                    FROM jsonb_array_elements_text(m.goal::jsonb) elem)
    END,
    m.diet_types::jsonb,
    CASE WHEN m.diet_types IS NULL THEN '{}'::text[]
         ELSE ARRAY(SELECT LOWER(REGEXP_REPLACE(elem,'[^A-Za-z0-9]+','_','g'))
                    FROM jsonb_array_elements_text(m.diet_types::jsonb) elem)
    END,
    m.created_at, m.updated_at
FROM public.meals m
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('"Twellr_Nutri".meals', 'id'),
    COALESCE((SELECT MAX(id) FROM "Twellr_Nutri".meals), 1),
    true
);


-- ────────────────────────────────────────────────────────────
-- 6. meal_session_assignments
--    Migrate the legacy meals.sessions JSONB array into the
--    new many-to-many junction. The first element of the array
--    (if any) is marked as is_primary.
-- ────────────────────────────────────────────────────────────
INSERT INTO "Twellr_Nutri".meal_session_assignments (meal_id, session_id, is_primary, sort_order)
SELECT DISTINCT
    m.id                       AS meal_id,
    ms.id                      AS session_id,
    (elem.ord = 1)             AS is_primary,
    elem.ord::smallint         AS sort_order
FROM public.meals m
CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(m.sessions::jsonb, '[]'::jsonb))
    WITH ORDINALITY AS elem(value, ord)
JOIN "Twellr_Nutri".meal_sessions ms
    ON ms.code = LOWER(REGEXP_REPLACE(elem.value, '[^A-Za-z0-9]+', '_', 'g'))
ON CONFLICT (meal_id, session_id) DO NOTHING;


-- ────────────────────────────────────────────────────────────
-- 7. meal_foods  (rename `replaceable` → `is_replaceable`,
--                drop quantity/unit — they live on the food now)
-- ────────────────────────────────────────────────────────────
INSERT INTO "Twellr_Nutri".meal_foods (meal_id, food_id, is_replaceable)
SELECT mf.meal_id, mf.food_id, mf.replaceable
FROM public.meal_foods mf
ON CONFLICT (meal_id, food_id) DO NOTHING;


-- ────────────────────────────────────────────────────────────
-- 8. substitutes  (VARCHAR PK → BIGSERIAL; allergen_name → allergen_code)
-- ────────────────────────────────────────────────────────────
INSERT INTO "Twellr_Nutri".substitutes (
    allergen_category, allergen_code, name_en, substitutes,
    created_at, updated_at
)
SELECT
    s.allergen_category,
    LOWER(REGEXP_REPLACE(COALESCE(NULLIF(s.id, ''), s.allergen_name), '[^A-Za-z0-9]+', '_', 'g')),
    s.allergen_name,
    s.substitutes,
    s.created_at, s.updated_at
FROM public.substitutes s
ON CONFLICT (allergen_code) DO NOTHING;


-- ────────────────────────────────────────────────────────────
-- 9. Backfill food_concern_tags / meal_concern_tags from
--    `supports` / `goal` JSONB arrays.
--    Skipped if nutri_04_concern_bridge.sql hasn't been run yet.
-- ────────────────────────────────────────────────────────────
DO $$
DECLARE
    bridge_present bool;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'Twellr_Nutri'
          AND table_name   = 'food_concern_tags'
    ) INTO bridge_present;

    IF NOT bridge_present THEN
        RAISE NOTICE 'food_concern_tags not present — skipping tag backfill. Run nutri_04_concern_bridge.sql first.';
        RETURN;
    END IF;

    INSERT INTO "Twellr_Nutri".food_concern_tags (food_id, concern_id, tag_weight, source)
    SELECT DISTINCT f.id, ct.id, 1.0, 'imported'
    FROM "Twellr_Nutri".foods f
    CROSS JOIN LATERAL unnest(f.supports_normalized) AS supp(code)
    JOIN wellness_platform.concern_taxonomy ct ON ct.code = supp.code
    ON CONFLICT (food_id, concern_id) DO NOTHING;

    INSERT INTO "Twellr_Nutri".meal_concern_tags (meal_id, concern_id, tag_weight, source)
    SELECT DISTINCT m.id, ct.id, 1.0, 'imported'
    FROM "Twellr_Nutri".meals m
    CROSS JOIN LATERAL unnest(m.goal_normalized) AS g(code)
    JOIN wellness_platform.concern_taxonomy ct ON ct.code = g.code
    ON CONFLICT (meal_id, concern_id) DO NOTHING;
END;
$$;


-- ────────────────────────────────────────────────────────────
-- 10. Validation report (read-only — copy into a log)
-- ────────────────────────────────────────────────────────────
DO $$
DECLARE
    n_cuisines     int;
    n_ingredients  int;
    n_foods        int;
    n_meals        int;
    n_sess_assign  int;
    n_subs         int;
BEGIN
    SELECT COUNT(*) INTO n_cuisines    FROM "Twellr_Nutri".cuisines;
    SELECT COUNT(*) INTO n_ingredients FROM "Twellr_Nutri".ingredients_master;
    SELECT COUNT(*) INTO n_foods       FROM "Twellr_Nutri".foods;
    SELECT COUNT(*) INTO n_meals       FROM "Twellr_Nutri".meals;
    SELECT COUNT(*) INTO n_sess_assign FROM "Twellr_Nutri".meal_session_assignments;
    SELECT COUNT(*) INTO n_subs        FROM "Twellr_Nutri".substitutes;

    RAISE NOTICE 'Migration counts: cuisines=%, ingredients=%, foods=%, meals=%, meal_session_assignments=%, substitutes=%',
        n_cuisines, n_ingredients, n_foods, n_meals, n_sess_assign, n_subs;
END;
$$;

-- ============================================================
-- End nutri_05_data_migration.sql  (v2)
-- ============================================================

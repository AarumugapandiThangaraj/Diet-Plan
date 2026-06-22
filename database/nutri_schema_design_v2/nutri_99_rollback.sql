-- ============================================================
-- nutri_99_rollback.sql
-- DESTRUCTIVE — drops the entire Nutri integration.
--
-- Run only if you need to start the Nutri integration over from scratch.
-- All data in the "Twellr_Nutri" schema will be lost.
--
-- Run with a superuser role, e.g.:
--   SET search_path TO "Twellr_Nutri", wellness_platform, public;
--   \i nutri_99_rollback.sql
-- ============================================================

-- 1. Drop the view first (it depends on bridge tables).
DROP VIEW IF EXISTS "Twellr_Nutri".v_concern_tagged_items;

-- 2. Drop the schema cascade — wipes every table, sequence, and FK rooted here.
DROP SCHEMA IF EXISTS "Twellr_Nutri" CASCADE;

-- 3. Restore the concern_taxonomy.domain CHECK to its pre-nutri form
--    (skin/body/wellness/hair/nail/general). Safe to keep the
--    seeded nutrition codes — they will just be orphaned of bridge
--    references after the CASCADE above.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'wellness_platform'
          AND table_name   = 'concern_taxonomy'
          AND column_name  = 'domain'
    ) THEN
        EXECUTE (
            SELECT string_agg('ALTER TABLE wellness_platform.concern_taxonomy DROP CONSTRAINT ' || quote_ident(c.conname) || ';', E'\n')
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'wellness_platform'
              AND t.relname = 'concern_taxonomy'
              AND c.contype = 'c'
              AND pg_get_constraintdef(c.oid) ILIKE '%domain%'
        );

        ALTER TABLE wellness_platform.concern_taxonomy
            ADD CONSTRAINT concern_taxonomy_domain_check
            CHECK (domain IS NULL OR domain IN ('skin','body','wellness','hair','nail','general'));
    END IF;
END;
$$;

-- 4. Optional: remove the nutrition-specific seed codes too. Commented out
--    by default so any other dependent rows (rec engine views, future
--    services) are not silently broken.
-- DELETE FROM wellness_platform.concern_taxonomy
--  WHERE code IN ('weight_loss','weight_gain','muscle_gain','energy_boost','gut_health','immunity_boost');

-- ============================================================
-- End nutri_99_rollback.sql
-- ============================================================

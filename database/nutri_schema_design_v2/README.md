# Nutri Integration — DB Migrations (v2)

This folder contains the SQL migrations that fold the standalone **Nutri**
diet-plan app into the main **Twellr** Postgres instance.

**v2 = UI-aligned revamp**, driven by:
- The 15 new design images under
  `_internal/Nutri - Existing Details/images - new designs/`
- The user's pre-edits to the v1 schema (commented-out fields)
- The existing Nutri reference code at
  `D:/BioArt/Codebase/Nutri/Usr-local/Diet-Plan/`

Conventions inherited from the parent `backend/db/migrations/README.md`:
- All tables created directly via SQL (Django models are `managed=False`).
- All statements use `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` — safe to
  re-run, except `nutri_05_data_migration.sql` (one-shot per restore).
- Run with the right `search_path` set first (see each file's header).

---

## Order of execution

| #   | File                              | What it does                                                                                                                | Required? |
| --- | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | --------- |
| 1   | `nutri_01_schema_catalog.sql`     | Creates schema `"Twellr_Nutri"` + 9 catalog tables (cuisines, **meal_sessions**, ingredients_master, foods, meals, …).      | ✅ Yes    |
| 2   | `nutri_02_user_data.sql`          | User-scoped tables: `user_health_profiles`, **`user_goals`**, **`user_gut_assessments`**, **`user_food_preferences`**, **`user_weight_logs`**, **`user_daily_intake`**, **`user_hydration_log`**. | ✅ Yes    |
| 3   | `nutri_03_diet_plans.sql`         | Diet-plan storage + **`diet_plan_meal_swaps`** + **`diet_plan_meal_consumption`**.                                          | ✅ Yes    |
| 4   | `nutri_04_concern_bridge.sql`     | Links foods/meals to `wellness_platform.concern_taxonomy`. Seeds the UI's primary + secondary goals.                        | ✅ Yes    |
| 5   | `nutri_05_data_migration.sql`     | One-shot data import from legacy `public.*` Nutri tables. Skip if you have nothing to migrate.                              | ⚪ Optional |
| 99  | `nutri_99_rollback.sql`           | DESTRUCTIVE — drops the entire `"Twellr_Nutri"` schema.                                                                     | ⚠️ Only on rollback |

```sql
SET search_path TO "Twellr_Nutri", wellness_platform, public;
\i nutri_01_schema_catalog.sql
\i nutri_02_user_data.sql
\i nutri_03_diet_plans.sql
\i nutri_04_concern_bridge.sql
-- only if importing legacy research data:
\i nutri_05_data_migration.sql
```

---

## What changed v1 → v2

### Dropped from the v1 design

| v1 element                          | Why dropped                                                                                                                  |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `ingredient_aliases`                | Legacy ING-XXXXX client IDs were an artefact of the research dump; the LLM and planner reference master ingredients by integer id. |
| `user_nutri_preferences` blob       | Replaced by the structured `user_food_preferences` (per-food likes/dislikes/allergies) + `user_health_profiles.allergies`.   |
| `diet_plan_feedback`                | Out of scope for v2 — replaced by `diet_plan_meal_consumption` (eat/skip) and `diet_plan_meal_swaps` (rejection signal).      |
| All `_snap_*` columns on plan rows  | Catalog FK is the source of truth; soft-delete handles the "deleted catalog row" case.                                       |
| Materialised macros on `foods` / `meals` / `meal_foods` | Derived from `food_ingredients` on read. Will add `v_food_macros` materialized view if read latency demands.   |
| Ingredient classifiers (`category`, `food_group`, `food_type`, `food_state`, `main_name`, `allergens`, `conversions`) | Not exposed in the new UI; can be added back as a follow-up if a feature needs them. |
| `meals.meal_session` single value   | Moved to `meal_session_assignments` (many-to-many) — a meal can fit multiple sessions.                                       |
| `meals.image_url`                   | UI renders the primary food's image (Planner.png shows one food image per meal card).                                        |
| `meal_foods.quantity` / `unit`      | Quantity lives on the food itself; matches the `meals.json` shape `{ID, Replaceable}`.                                       |
| `diet_plans.generator` / `model_name` / `model_request_id` / `locale` / `title` | Generation metadata captured in a separate audit log outside the schema. |
| `user_health_profiles.dietary_restrictions` / `medical_conditions` | Restrictions live on `user_food_preferences`; medical conditions handled by Twellr AI assessments. |
| `diet_plan_meal_food_ingredients.per100g_*` and `caution` / `notes` | Read from `ingredients_master` at render time.                                                                  |

### Added in v2 (driven by the new UI designs)

| Table                                 | UI screen                                                                  | What it backs                                                                                                  |
| ------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `meal_sessions`                       | Nav Bar.png, Planner.png, Nutri sample 8 - Expanded.png                    | Reference list of slots: early_morning / breakfast / mid_morning / lunch / evening / snack / dinner / bedtime. |
| `meal_session_assignments`            | Planner.png, Nutri sample 8 - Expanded.png                                 | Many-to-many "this meal fits these sessions" — drives the meal-card grouping and the slot timeline.            |
| `user_goals`                          | Primary & Secondary goal.png                                               | Primary radio (skin / hair / skin&hair) + secondary multi-select (more_energy / weight_management / mental_clarity / better_sleep / gut_health / mental_calmness). |
| `user_gut_assessments`                | input 19.png, animation.png                                                | Persists the 5-question gut symptom survey. `is_latest` is the row the planner uses.                           |
| `user_food_preferences`               | Nutri sample 27.png, Nutri sample 8 - Expanded.png                         | Per-food preference rows (`liked` / `disliked` / `allergic`).                                                  |
| `user_weight_logs`                    | BMI Calculator.png "Previous readings", Nav Bar.png "My Progress"          | Time-series of weight / BMI / BMR / target — drives the curve + previous-reading cards.                       |
| `user_daily_intake`                   | Dashboard.png "Calories — Lack of physical activity", macro chips          | Per-day rollup of consumed vs target calories + macros.                                                        |
| `user_hydration_log`                  | Dashboard.png "Hydration Status" 4×7 grid                                  | One row per "+1 glass" tap; weekly grid built by counting per (user, date).                                   |
| `diet_plan_meal_swaps`                | Swap.png, Swap-1.png, meal prep.png                                        | Audit trail for `meal` / `food` / `ingredient` swaps (with reason + reverse-swap support).                     |
| `diet_plan_meal_consumption`          | Dashboard.png "Today's meals"                                              | "I ate this" check-ins. Aggregated nightly into `user_daily_intake`.                                          |
| 7 new concern_taxonomy rows           | Primary & Secondary goal.png                                               | `skin_hair`, `more_energy`, `weight_management`, `mental_clarity`, `better_sleep`, `gut_health`, `mental_calmness`. |

### Kept unchanged from v1

- Schema `"Twellr_Nutri"` (mirrors `"Twellr_Rec_Engine"`).
- Cross-schema FKs to `wellness_platform.users` (UUID) and
  `wellness_platform.concern_taxonomy` (BIGINT).
- Bilingual contract (`name_en` / `name_ar`, `description_en` / `description_ar`,
  `preparation_en` / `preparation_ar`).
- `food_concern_tags` / `meal_concern_tags` bridges with `tag_weight` —
  same shape as `product_concern_tags` / `service_concern_tags`.
- `is_active` + `deleted_at` soft delete; `BIGSERIAL` PKs for catalog,
  `UUID` PKs for user-scoped + plan tables.
- `v_concern_tagged_items` UNION view for cross-domain ranking.

---

## How the schema maps to the new UI screens

| Screen                                       | Tables that back it                                                                                                                          |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Dashboard.png** (calories, macros, hydration, today's meals, energy goal, weight progress) | `diet_plans` (targets) · `user_daily_intake` (today's totals) · `user_hydration_log` (grid) · `diet_plan_meals` + `diet_plan_meal_consumption` (today's meals list) · `user_weight_logs` (Weight Progress) |
| **BMI Calculator.png** (BMI / BMR / Water / Target + Previous readings) | `user_health_profiles` (latest) · `user_weight_logs` (previous readings)                                                                     |
| **Nav Bar.png** (Planner / Choose meals / BMI Calculator / Gut-ingestible / My Progress) | Everything; "Gut-ingestible" = `user_gut_assessments` + the rec engine query against `meal_concern_tags`                                       |
| **Planner.png / Planner-1.png** (Week N · Day pills · meal cards) | `diet_plans` · `diet_plan_days` · `diet_plan_meals` · `diet_plan_meal_foods` · `meal_sessions`                                               |
| **Primary & Secondary goal.png**             | `user_goals` (FK → `concern_taxonomy`)                                                                                                       |
| **Nutri sample 27.png / 8 - Expanded.png** ("Pick the foods you like") | `foods` · `meal_sessions` · `meal_session_assignments` · `user_food_preferences` (writes)                                                    |
| **Swap.png / Swap-1.png** (Replace Kanda Poha) | `meals` · `meal_concern_tags` (find candidates with same concerns) · `diet_plan_meal_swaps` (audit)                                          |
| **meal prep.png** (expanded meal view + ingredient list) | `diet_plan_meals` · `diet_plan_meal_foods` · `diet_plan_meal_food_ingredients` · `foods.preparation_en`                                       |
| **input 17 / 18 / 19.png** (onboarding gut survey + diet preference) | `user_health_profiles` (BMR/BMI computation) · `user_goals` · `user_gut_assessments`                                                         |
| **animation.png** ("Building Your Protocol") | Pure UI animation — reads `user_gut_assessments.is_latest`, `user_goals`, `user_food_preferences` and writes a new `diet_plans`              |

---

## Naming-convention summary (unchanged from v1)

- **Schema**: `"Twellr_Nutri"` — double-quoted, mixed-case (mirrors `"Twellr_Rec_Engine"`).
- **PKs**: `BIGSERIAL` for catalog (cuisines, ingredients_master, foods, meals, meal_sessions, substitutes), `UUID` for user-scoped + plan tables, composite PK on junctions.
- **Timestamps**: `created_at` + `updated_at` `TIMESTAMPTZ NOT NULL DEFAULT NOW()` on every table; long-lived rows also get `is_active BOOL` + `deleted_at TIMESTAMPTZ`.
- **Bilingual**: every visible string column has `_ar` twin.
- **JSON**: every JSON column is `jsonb`; rec-engine-joined arrays have a `_normalized text[]` twin with GIN indexes.
- **Cross-schema FKs**: `user_id → wellness_platform.users(id)` (UUID), `concern_id → wellness_platform.concern_taxonomy(id)` (BIGINT). Catalog FK from plan tables uses `ON DELETE SET NULL`.
- **Indexes**: `idx_<table_abbrev>_<cols>` — matches existing rec-engine and services index naming.

---

## What is intentionally NOT in this batch

- **Chat assistant tables** — out of scope until the nutrition assistant ships.
- **Diet-plan JSON importer** — the SQL here defines storage; the importer that reads `diet_plan.json` files into the diet_plan_* tables is a Python service (to be added under `apps/nutri/services/`).
- **Django models** — to be added under `backend/apps/nutri/models.py` with `managed=False`, mirroring `apps/users/models.py` and `apps/services/models.py`.
- **Materialised view `v_food_macros`** — if read latency on the dashboard becomes an issue, we'll add it in a follow-up file. For v2 we compute macros at read time.
- **Recommendation logic / scoring** — the bridge view `v_concern_tagged_items` exposes the data; ranking lives in `"Twellr_Rec_Engine"`.

---

## Status tracker

| #   | File                              | Status   | Date run |
| --- | --------------------------------- | -------- | -------- |
| 1   | `nutri_01_schema_catalog.sql`     | ⏳ Pending | —        |
| 2   | `nutri_02_user_data.sql`          | ⏳ Pending | —        |
| 3   | `nutri_03_diet_plans.sql`         | ⏳ Pending | —        |
| 4   | `nutri_04_concern_bridge.sql`     | ⏳ Pending | —        |
| 5   | `nutri_05_data_migration.sql`     | ⏳ Pending | —        |

Legend: ✅ Done · 🔄 In Progress · ⏳ Pending · ❌ Blocked

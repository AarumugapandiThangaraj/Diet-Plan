-- Seed Idli + Sambar and Idli + Chuttney
SET search_path TO "Twellr_Nutri";

-- Insert foods
INSERT INTO foods (id, name_en) VALUES (10001, 'Idli') ON CONFLICT DO NOTHING;
INSERT INTO foods (id, name_en) VALUES (10002, 'Sambar') ON CONFLICT DO NOTHING;
INSERT INTO foods (id, name_en) VALUES (10003, 'Chuttney') ON CONFLICT DO NOTHING;

-- Insert meals
INSERT INTO meals (id, cuisine_id, meal_session_id, name_en) VALUES (20001, 13, 2, 'Idli + Sambar') ON CONFLICT DO NOTHING;
INSERT INTO meals (id, cuisine_id, meal_session_id, name_en) VALUES (20002, 13, 2, 'Idli + Chuttney') ON CONFLICT DO NOTHING;

-- Map meal foods
INSERT INTO meal_foods (meal_id, food_id, quantity) VALUES (20001, 10001, 2) ON CONFLICT DO NOTHING;
INSERT INTO meal_foods (meal_id, food_id, quantity) VALUES (20001, 10002, 1) ON CONFLICT DO NOTHING;

INSERT INTO meal_foods (meal_id, food_id, quantity) VALUES (20002, 10001, 2) ON CONFLICT DO NOTHING;
INSERT INTO meal_foods (meal_id, food_id, quantity) VALUES (20002, 10003, 1) ON CONFLICT DO NOTHING;

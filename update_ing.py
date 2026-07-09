import json

with open("new core models/data/south indian cuisine/meal_ingredient.json", "r") as f:
    data = json.load(f)

# Base ingredients from M036 (Idli with Sambar, Moringa Shot, Almonds)
m036_ingredients = [d for d in data if d["meal_id"] == "M036"]

m300_ingredients = []
m301_ingredients = []

for ing in m036_ingredients:
    if ing["ingredient_name"] == "Idli":
        # Replace Idli with Ragi Dosa for M300
        m300_ingredients.append({
            "meal_id": "M300",
            "ingredient_name": "Fermented ragi dosa batter",
            "quantity": 120,
            "unit": "g"
        })
        m300_ingredients.append({
            "meal_id": "M300",
            "ingredient_name": "Olive oil",
            "quantity": 5,
            "unit": "g"
        })
        
        # Replace Idli with Palak Dosa for M301
        m301_ingredients.append({
            "meal_id": "M301",
            "ingredient_name": "Palak dosa batter",
            "quantity": 120,
            "unit": "g"
        })
        m301_ingredients.append({
            "meal_id": "M301",
            "ingredient_name": "Olive oil",
            "quantity": 5,
            "unit": "g"
        })
    else:
        # Keep other ingredients (Sambar, Shot, Almonds)
        new_ing_300 = dict(ing)
        new_ing_300["meal_id"] = "M300"
        m300_ingredients.append(new_ing_300)
        
        new_ing_301 = dict(ing)
        new_ing_301["meal_id"] = "M301"
        m301_ingredients.append(new_ing_301)

# Remove any existing M300/M301 to avoid duplicates if rerun
data = [d for d in data if d["meal_id"] not in ("M300", "M301")]

data.extend(m300_ingredients)
data.extend(m301_ingredients)

with open("new core models/data/south indian cuisine/meal_ingredient.json", "w") as f:
    json.dump(data, f, indent=2)

print("Added ingredients for M300 and M301.")

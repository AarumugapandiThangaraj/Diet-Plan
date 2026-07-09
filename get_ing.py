import json

with open("new core models/data/south indian cuisine/meal_ingredient.json", "r") as f:
    data = json.load(f)

print("M036:")
for d in data:
    if d["meal_id"] == "M036":
        print(d)

print("\nM041:")
for d in data:
    if d["meal_id"] == "M041":
        print(d)

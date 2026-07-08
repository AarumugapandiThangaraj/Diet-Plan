import os
import re

# Resolve catalog.py
catalog_path = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\server\database\models\catalog.py"
with open(catalog_path, "r", encoding="utf-8") as f:
    catalog_content = f.read()

# We want to keep the Upstream block.
catalog_content = re.sub(
    r"<<<<<<< Updated upstream\n(.*?)\n=======\n.*?\n>>>>>>> Stashed changes\n",
    r"\1\n",
    catalog_content,
    flags=re.DOTALL
)

with open(catalog_path, "w", encoding="utf-8") as f:
    f.write(catalog_content)


# Resolve schemas.py
schemas_path = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\server\schemas.py"
with open(schemas_path, "r", encoding="utf-8") as f:
    schemas_content = f.read()

# For schemas.py, we want the Recipe* classes from upstream, and the Active* / Draft* classes from Stash.
# The Stash also contains the replacement for DraftPlanResponse.
def schemas_resolver(match):
    upstream = match.group(1)
    stash = match.group(2)
    # Extract Recipe classes from upstream
    recipes = []
    for line in upstream.split('\n'):
        if "DraftPlanResponse" in line or "targets:" in line or "mealTimes:" in line or "rankedByTime:" in line or "planId:" in line or "version:" in line or "status:" in line:
            if "class DraftPlanResponse(BuildPlanResponse):" in line:
                continue
            if "status: str = Field" in line or "version: int" in line or "planId:" in line or "rankedByTime:" in line or "mealTimes:" in line or "targets: Dict" in line:
                continue
        recipes.append(line)
    
    recipes_str = '\n'.join(recipes).strip()
    return recipes_str + "\n\n" + stash

schemas_content = re.sub(
    r"<<<<<<< Updated upstream\n(.*?)=======\n(.*?)\n>>>>>>> Stashed changes",
    schemas_resolver,
    schemas_content,
    flags=re.DOTALL
)

with open(schemas_path, "w", encoding="utf-8") as f:
    f.write(schemas_content)


# Resolve router.py
router_path = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\server\studio\router.py"
with open(router_path, "r", encoding="utf-8") as f:
    router_content = f.read()

def router_resolver(match):
    upstream = match.group(1)
    stash = match.group(2)
    # The stash contains the correct logic for /plan/latest
    # The upstream contains the return payload for /plan/latest AND the new studio_get_meal_details endpoint.
    # We want the stash logic, followed by the studio_get_meal_details endpoint from upstream.
    
    # Find the start of the new endpoint in upstream
    endpoint_start = upstream.find("@router.get(\n    \"/meal-plans/meals/")
    if endpoint_start == -1:
        # fallback
        endpoint_start = upstream.find("@router.get(")
        
    if endpoint_start != -1:
        new_endpoint = upstream[endpoint_start:]
    else:
        new_endpoint = ""
        
    return stash + "\n\n" + new_endpoint

router_content = re.sub(
    r"<<<<<<< Updated upstream\n(.*?)=======\n(.*?)\n>>>>>>> Stashed changes",
    router_resolver,
    router_content,
    flags=re.DOTALL
)

with open(router_path, "w", encoding="utf-8") as f:
    f.write(router_content)

print("Conflicts resolved!")

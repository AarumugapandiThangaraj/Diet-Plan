import os

filepath = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\server\schemas.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace DraftPlanResponse with our new definitions
old_draft_str = """class DraftPlanResponse(BuildPlanResponse):
    targets: Dict[str, Any] = Field(..., description="The calculated daily target profile (full DailyTargetsResponse on creation, StoredPlanTargets on re-fetch).")
    mealTimes: Optional[List[str]] = Field(default=None, description="List of meal times included in the plan.")
    rankedByTime: Optional[Dict[str, List[Dict[str, Any]]]] = Field(default=None, description="Not used for draft fetch.")
    planId: str = Field(..., description="The unique ID of the draft plan.")
    version: int = Field(..., description="The version number of the draft plan.")
    status: str = Field(..., description="The status of the plan (draft, active, archived).")"""

new_schemas_str = """
class ActiveMealItem(BaseModel):
    mealId: str
    name: str
    imageUrl: str = ""
    session: str
    scheduledTime: str
    macros: MacroTotals
    foods: List[Dict[str, Any]]
    completed: bool = False
    
class ActiveDayPlan(BaseModel):
    dayNumber: int
    planDayId: Optional[str] = None
    totals: MacroTotals
    meals: List[ActiveMealItem]

class ActiveWeek(BaseModel):
    weekNumber: int
    days: List[ActiveDayPlan]

class ActivePlanResponse(BaseModel):
    planId: str
    version: int
    status: str
    targets: Dict[str, Any]
    totalsAll: MacroTotals
    weeks: List[ActiveWeek]

class DraftDayPlan(BaseModel):
    dayNumber: int
    planDayId: Optional[str] = None
    totals: MacroTotals
    model_config = ConfigDict(extra='allow')

class DraftPlanResponse(BaseModel):
    planId: str
    version: int
    status: str
    targets: Dict[str, Any]
    totalsAll: MacroTotals
    days: List[DraftDayPlan]
"""

content = content.replace(old_draft_str, new_schemas_str.strip())

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("schemas.py updated with active and draft response models!")

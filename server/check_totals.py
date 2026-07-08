import sys
sys.path.append(".")
import asyncio
from database.session import async_session
from repositories.draft_plan_repository import get_draft_plan

async def main():
    async with async_session() as session:
        plan_id = "f0c5620f-8e7f-4ece-b1f3-7f1e2fab3646" 
        try:
            plan = await get_draft_plan(session, plan_id)
            if plan:
                payload = plan.get("plan_payload", {})
                print(f"Days: {payload.get('days')}")
                if payload.get("days") == 1:
                     print(f"Single Day Totals: {payload.get('totals')}")
                else:
                     print(f"Totals By Day Count: {len(payload.get('totalsByDay', []))}")
                     if payload.get('totalsByDay'):
                         print(f"Day 1 Totals: {payload.get('totalsByDay')[0]}")
            else:
                print("Plan not found")
        except Exception as e:
            print(f"Exception: {e}")
            
if __name__ == "__main__":
    asyncio.run(main())

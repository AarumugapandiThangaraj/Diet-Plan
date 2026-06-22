import json
from pathlib import Path

data_root = Path('d:/IAgami/Bioart Dataset/Diet Plan Updated/Diet-Plan-Pull Only/Diet-Plan/migration_backup/original_json_datasets')
meal_files = list(data_root.rglob('*meal*.json'))

for p in meal_files:
    if 'southeast' in p.name.lower():
        print(f'Checking {p.name}')
        data = json.loads(p.read_text(encoding='utf-8'))
        bedtime_meals = []
        for meal_id, m in data.items():
            sessions = m.get('Session') or m.get('sessions') or m.get('session') or []
            if isinstance(sessions, str):
                sessions = [sessions]
            
            for s in sessions:
                if 'bed' in str(s).lower():
                    bedtime_meals.append((m['Name'], s))
        
        print(f'Found {len(bedtime_meals)} meals with "bed" in session')
        for n, s in bedtime_meals[:10]:
            print(f'  {n}: {s}')

        all_sessions = {}
        for meal_id, m in data.items():
            sessions = m.get('Session') or m.get('sessions') or m.get('session') or []
            if isinstance(sessions, str):
                sessions = [sessions]
            for s in sessions:
                all_sessions[s] = all_sessions.get(s, 0) + 1
        print("All unique sessions:", all_sessions)

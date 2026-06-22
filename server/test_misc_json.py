import json
from pathlib import Path

data_root = Path('d:/IAgami/Bioart Dataset/Diet Plan Updated/Diet-Plan-Pull Only/Diet-Plan/migration_backup/original_json_datasets')
meal_files = list(data_root.rglob('*meal*.json'))

for p in meal_files:
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(data, list):
            for m in data:
                if m.get('ID') == 'MEAL_SEA_MISC_006':
                    print(f"Found MEAL_SEA_MISC_006 in {p.parent.name}/{p.name}: {m.get('Name')}, Session: {m.get('Session')}")
        elif isinstance(data, dict):
            for m_id, m in data.items():
                if m_id == 'MEAL_SEA_MISC_006' or m.get('ID') == 'MEAL_SEA_MISC_006':
                    print(f"Found MEAL_SEA_MISC_006 in {p.parent.name}/{p.name}: {m.get('Name')}, Session: {m.get('Session')}")
    except Exception as e:
        pass

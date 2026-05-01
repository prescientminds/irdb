#!/usr/bin/env python3
"""Fix restaurant status for closed locations discovered during group expansion."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
APP_SRC = os.path.join(ROOT, 'src')

def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)

def save(name, data):
    for d in [DATA, APP_SRC]:
        path = os.path.join(d, name)
        if os.path.isdir(d):
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write('\n')

restaurants = load('restaurants.json')
rest_by_id = {r['id']: r for r in restaurants}

fixes = {
    'rest_pearl_river_deli': {'status': 'closed', 'close_year': 2024},
    'rest_sotto': {'status': 'closed', 'close_year': 2019},
    'rest_bouchon_bh': {'status': 'closed', 'close_year': 2017},
    'rest_maude': {'status': 'closed', 'close_year': 2024},
    'rest_animal': {'status': 'closed', 'close_year': 2023},
    'rest_son_of_a_gun': {'status': 'closed', 'close_year': 2024},
    'rest_lucques': {'status': 'closed', 'close_year': 2020},
    'rest_dialogue': {'status': 'closed', 'close_year': 2020},
    'rest_nightshade': {'status': 'closed', 'close_year': 2020},
    'rest_broken_spanish': {'status': 'closed', 'close_year': 2020},
    'rest_otium': {'status': 'closed', 'close_year': 2024},
    'rest_locol': {'status': 'closed', 'close_year': 2017},
    'rest_simone': {'status': 'closed', 'close_year': 2019},
    'rest_native': {'status': 'closed', 'close_year': 2025},
    'rest_bicyclette': {'status': 'closed', 'close_year': 2024},
    'rest_cassia': {'status': 'closed', 'close_year': 2025},
    'rest_trois_mec': {'status': 'closed', 'close_year': 2020},
}

count = 0
for rid, update in fixes.items():
    if rid in rest_by_id:
        r = rest_by_id[rid]
        if r.get('status') != 'closed':
            old = r.get('status', '?')
            r.update(update)
            print(f"  {r['name']:35s} {old} → closed ({update['close_year']})")
            count += 1
        else:
            print(f"  {r['name']:35s} already closed")
    else:
        print(f"  {rid:35s} NOT FOUND")

save('restaurants.json', restaurants)
print(f"\nFixed {count} restaurants. Saved to data/ and app/src/.")

#!/usr/bin/env python3
"""
IRDB Batch Intake Script
━━━━━━━━━━━━━━━━━━━━━━━━
Reads a YAML intake file of chef candidates and writes valid entries into
chefs.json, restaurants.json, and stops.json.

Usage:
  python3 scripts/batch-intake.py data/intake-batch.yaml
  python3 scripts/batch-intake.py data/intake-batch.yaml --dry-run
  python3 scripts/batch-intake.py data/intake-batch.yaml --dry-run --verbose

Input format: see data/intake-template.yaml
"""

import json, os, re, sys, argparse
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
APP_SRC = os.path.join(ROOT, 'src')  # Next.js app reads from here

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def load_json(name):
    path = os.path.join(DATA, name)
    with open(path) as f:
        return json.load(f)

def save_json(name, data):
    """Write to data/ and sync to app/src/ so the Next.js build picks it up."""
    for directory in [DATA, APP_SRC]:
        path = os.path.join(directory, name)
        if os.path.isdir(directory):
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write('\n')

def make_chef_id(display_name):
    parts = display_name.lower().split()
    slug = '_'.join(re.sub(r'[^\w]', '', p) for p in parts if p)
    return f"chef_{slug}"

def make_rest_id(name):
    slug = re.sub(r'[^\w\s]', '', name.lower())
    slug = '_'.join(slug.split())
    return f"rest_{slug}"

def next_stop_id(stops):
    """Find the highest numeric stop ID and return the next one."""
    max_num = 0
    for s in stops:
        m = re.match(r'stop_(\d+)', s['id'])
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num + 1

# ─────────────────────────────────────────────
# Load YAML (with fallback to basic parser if PyYAML not installed)
# ─────────────────────────────────────────────

def load_yaml(path):
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        print("  PyYAML not installed — using JSON fallback.")
        print("  Install with: pip3 install pyyaml")
        print("  Or provide a .json file instead.")
        # Try JSON as fallback
        if path.endswith('.json'):
            with open(path) as f:
                return json.load(f)
        sys.exit(1)

# ─────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────

def validate_candidate(c, existing_chef_ids, existing_rest_ids, idx):
    """Validate a single candidate entry. Returns list of warnings."""
    warnings = []
    name = c.get('name', '')
    if not name:
        warnings.append(f"  Candidate #{idx}: missing 'name'")
        return warnings

    chef_id = make_chef_id(name)
    if chef_id in existing_chef_ids:
        warnings.append(f"  {name}: DUPLICATE — {chef_id} already exists in chefs.json")

    stops = c.get('stops', [])
    if not stops:
        warnings.append(f"  {name}: no stops listed")

    for i, stop in enumerate(stops):
        if not stop.get('restaurant'):
            warnings.append(f"  {name}: stop #{i+1} missing 'restaurant'")
        if not stop.get('position'):
            warnings.append(f"  {name}: stop #{i+1} missing 'position'")

    return warnings

# ─────────────────────────────────────────────
# Entry generation
# ─────────────────────────────────────────────

def build_chef_entry(c):
    """Build a chef JSON entry from a candidate dict."""
    name = c['name']
    parts = name.split()
    first = parts[0] if parts else ''
    last = ' '.join(parts[1:]) if len(parts) > 1 else ''

    return {
        'id': make_chef_id(name),
        'name': {
            'first': first,
            'last': last,
            'display': name,
            'nickname': c.get('nickname'),
        },
        'bio': c.get('bio', ''),
        'birth_year': c.get('birth_year'),
        'birth_country': c.get('birth_country', 'US'),
        'birth_city': c.get('birth_city'),
        'cuisine_tags': c.get('cuisine_tags', []),
        'photo_url': None,
        'instagram': c.get('instagram'),
        'website': c.get('website'),
        'status': c.get('status', 'active'),
        'tier': c.get('tier', 'lineage'),
        'education': [
            {
                'institution': e.get('institution', e) if isinstance(e, dict) else e,
                'city': e.get('city') if isinstance(e, dict) else None,
                'year': e.get('year') if isinstance(e, dict) else None,
                'credential': e.get('credential') if isinstance(e, dict) else None,
            }
            for e in c.get('education', [])
        ],
    }

def build_restaurant_entry(stop, existing_rest_ids, default_city='Los Angeles', default_state='CA'):
    """Build a restaurant JSON entry from a stop dict, if the restaurant is new."""
    name = stop['restaurant']
    rest_id = make_rest_id(name)
    if rest_id in existing_rest_ids:
        return None  # already exists

    return {
        'id': rest_id,
        'name': name,
        'address': stop.get('address'),
        'city': stop.get('city', default_city),
        'neighborhood': stop.get('neighborhood'),
        'state': stop.get('state', default_state),
        'cuisine_tags': stop.get('cuisine_tags', []),
        'status': stop.get('restaurant_status', 'open'),
        'open_year': stop.get('open_year'),
        'close_year': stop.get('close_year'),
        'price_range': stop.get('price_range'),
        'seats': None,
        'format': stop.get('format'),
        'group_id': stop.get('group_id'),
        'ratings': stop.get('ratings', {}),
        'website': None,
    }

def build_stop_entry(stop, chef_id, stop_num, existing_chef_ids):
    """Build a stop JSON entry."""
    rest_id = make_rest_id(stop['restaurant'])

    # Resolve mentor_id from mentor name
    mentor_id = None
    mentor_name = stop.get('mentor')
    if mentor_name:
        candidate_id = make_chef_id(mentor_name)
        if candidate_id in existing_chef_ids:
            mentor_id = candidate_id
        else:
            print(f"    WARNING: mentor '{mentor_name}' ({candidate_id}) not found in DB")

    entry = {
        'id': f'stop_{stop_num:03d}',
        'chef_id': chef_id,
        'restaurant_id': rest_id,
        'position': stop.get('position', ''),
        'start_year': stop.get('start_year'),
        'end_year': stop.get('end_year'),
        'is_current': stop.get('is_current', False),
        'verification': 'unverified',
        'mentor_id': mentor_id,
    }

    if stop.get('notes'):
        entry['notes'] = stop['notes']

    return entry

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='IRDB batch intake')
    parser.add_argument('input', help='YAML or JSON intake file')
    parser.add_argument('--dry-run', action='store_true', help='Validate only, do not write')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print all generated entries')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}")
        sys.exit(1)

    # Load existing data
    print("Loading existing IRDB data...")
    chefs = load_json('chefs.json')
    restaurants = load_json('restaurants.json')
    stops = load_json('stops.json')

    existing_chef_ids = {c['id'] for c in chefs}
    existing_rest_ids = {r['id'] for r in restaurants}
    existing_rest_names = {r['name'].lower(): r['id'] for r in restaurants}

    print(f"  {len(chefs)} chefs, {len(restaurants)} restaurants, {len(stops)} stops")

    # Load intake file
    print(f"\nLoading intake file: {args.input}")
    intake = load_yaml(args.input)
    candidates = intake.get('chefs', [])
    default_city = intake.get('default_city', 'Los Angeles')
    default_state = intake.get('default_state', 'CA')
    if default_city != 'Los Angeles':
        print(f"  Default city: {default_city}, {default_state}")
    print(f"  {len(candidates)} candidates")

    # Validate
    print("\nValidating...")
    all_warnings = []
    duplicates = []
    for i, c in enumerate(candidates, 1):
        w = validate_candidate(c, existing_chef_ids, existing_rest_ids, i)
        for warning in w:
            if 'DUPLICATE' in warning:
                duplicates.append(c['name'])
            else:
                all_warnings.append(warning)

    if duplicates:
        print(f"\n  SKIPPING {len(duplicates)} duplicates: {', '.join(duplicates)}")

    if all_warnings:
        print(f"\n  WARNINGS:")
        for w in all_warnings:
            print(w)

    # Filter out duplicates
    candidates = [c for c in candidates if make_chef_id(c['name']) not in existing_chef_ids]
    print(f"\n  {len(candidates)} new candidates to process")

    if not candidates:
        print("\nNothing to do.")
        return

    # Build entries
    print("\nGenerating entries...")
    stop_counter = next_stop_id(stops)
    new_chefs = []
    new_restaurants = []
    new_stops = []

    # Track restaurants added in this batch to avoid duplicates within the batch
    batch_rest_ids = set()

    for c in candidates:
        chef_entry = build_chef_entry(c)
        new_chefs.append(chef_entry)
        chef_id = chef_entry['id']

        # Add this chef to existing set so mentors within the same batch resolve
        existing_chef_ids.add(chef_id)

        for stop in c.get('stops', []):
            # Restaurant — check both existing and batch-added
            rest_id = make_rest_id(stop['restaurant'])

            # Handle name→ID mismatch (restaurant exists under different ID)
            rest_name_lower = stop['restaurant'].lower()
            if rest_id not in existing_rest_ids and rest_name_lower in existing_rest_names:
                rest_id = existing_rest_names[rest_name_lower]
            elif rest_id not in existing_rest_ids and rest_id not in batch_rest_ids:
                rest_entry = build_restaurant_entry(stop, existing_rest_ids, default_city, default_state)
                if rest_entry:
                    new_restaurants.append(rest_entry)
                    batch_rest_ids.add(rest_id)

            # Stop
            stop_entry = build_stop_entry(stop, chef_id, stop_counter, existing_chef_ids)
            # Override restaurant_id if we resolved it via name match
            stop_entry['restaurant_id'] = rest_id
            new_stops.append(stop_entry)
            stop_counter += 1

    print(f"  Generated: {len(new_chefs)} chefs, {len(new_restaurants)} restaurants, {len(new_stops)} stops")
    print(f"  Stop IDs: stop_{stop_counter - len(new_stops):03d} through stop_{stop_counter - 1:03d}")

    if args.verbose:
        print("\n─── NEW CHEFS ───")
        for c in new_chefs:
            print(f"  {c['id']}: {c['name']['display']}")
        print("\n─── NEW RESTAURANTS ───")
        for r in new_restaurants:
            print(f"  {r['id']}: {r['name']} ({r['city']})")
        print("\n─── NEW STOPS ───")
        for s in new_stops:
            mentor = f" ← {s['mentor_id']}" if s.get('mentor_id') else ''
            print(f"  {s['id']}: {s['chef_id']} @ {s['restaurant_id']} ({s['position']}){mentor}")

    if args.dry_run:
        print(f"\n  DRY RUN — no files modified.")
        return

    # Write
    print("\nWriting to data files...")
    chefs.extend(new_chefs)
    restaurants.extend(new_restaurants)
    stops.extend(new_stops)

    save_json('chefs.json', chefs)
    save_json('restaurants.json', restaurants)
    save_json('stops.json', stops)

    print(f"\n{'='*50}")
    print(f"BATCH INTAKE COMPLETE")
    print(f"{'='*50}")
    print(f"  Chefs:       {len(chefs)} (+{len(new_chefs)})")
    print(f"  Restaurants: {len(restaurants)} (+{len(new_restaurants)})")
    print(f"  Stops:       {len(stops)} (+{len(new_stops)})")
    print(f"  Date:        {date.today().isoformat()}")

if __name__ == '__main__':
    main()

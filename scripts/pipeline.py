#!/usr/bin/env python3
"""
IRDB Intake Pipeline
━━━━━━━━━━━━━━━━━━━
Cross-references ChefDb scraped data against quality signals (LA Times 101,
Michelin, JBF) to produce a ranked intake queue of chefs not yet in IRDB.

Usage: python3 scripts/pipeline.py
Output: data/intake_queue.json — ranked list of chef candidates with draft entries
"""

import json, os, re, sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)

# ─────────────────────────────────────────────
# PHASE 1: Load all data
# ─────────────────────────────────────────────
print("Phase 1: Loading data...")
chefdb = load('chefdb_scraped.json')
irdb_chefs = load('chefs.json')
irdb_rests = load('restaurants.json')
irdb_stops = load('stops.json')

chefdb_rests = chefdb.get('la_restaurants', [])
chefdb_rprof = chefdb.get('restaurant_profiles', {})
chefdb_cprof = chefdb.get('chef_profiles', {})

def norm_name(n):
    """Normalize name for matching — collapse whitespace, lowercase."""
    return ' '.join(n.lower().split())

irdb_chef_names = {norm_name(c['name']['display']) for c in irdb_chefs}
irdb_rest_names = {r['name'].lower() for r in irdb_rests}
irdb_chef_ids = {c['id'] for c in irdb_chefs}

print(f"  ChefDb: {len(chefdb_rests)} restaurants, {len(chefdb_cprof)} chefs")
print(f"  IRDB:   {len(irdb_chefs)} chefs, {len(irdb_rests)} restaurants")

# ─────────────────────────────────────────────
# PHASE 2: Parse quality signals (LA Times 101 with Michelin/JBF/F&W badges)
# ─────────────────────────────────────────────
print("\nPhase 2: Parsing quality signals...")

LAT101_RAW = """
Holbox|JB,MICH
Baroo|
Dunsmoor|
Hayato|MICH,F&W
Morihiro|MICH
Antico Nuovo|
Restaurant Ki|MICH
Anajak Thai|JB,F&W
Azizam|NYT
SELINE|
Destroyer|
Here's Looking at You|JB
Quarter Sheets|F&W,NYT
Bavel|
Perilla L.A.|NYT
Funke|
Camélia|NYT
Damian|F&W
République Café Bakery|JB
Mélisse Restaurant|MICH
Sushi Kaneyoshi|MICH
Orsa & Winston|MICH
Sonoratown|
Kismet|
Saffy's|
Sushi Inaba|MICH
Holy Basil|F&W
Vespertine|MICH
Pasjoli|
Knife Pleat|MICH
Yangban|JB
Causita|
Tsubaki|
KOMAL|
Chi Spacca|MICH
A.O.C.|
Moo's Craft Barbecue|JB
Felix Trattoria|
Alta Adams|JB
Shin Sushi|MICH
Rustic Canyon|
Birdie G's|
Bestia|
Mori Nozomi|MICH,NYT
Bridgetown Roti|JB
All Day Baby|F&W
Majordōmo|
Camphor|MICH,F&W
Found Oyster|
Petit Trois L'Original|
Gjelina|
n/soto|
Angry Egret Dinette|JB
Bar Amá|
Post & Beam|JB
Mother Wolf|
Connie and Ted's|
Crossroads Kitchen|
LocoL|
Pijja Palace|JB
Rocio's Mexican Kitchen|JB
Kuya Lord|JB
Jitlada|JB
Dulan's Soul Food Kitchen|JB
Rossoblu|
Baby Bistro|NYT
Night + Market|F&W
Providence|MICH,JB
n/naka|MICH
Kato|MICH
Le Comptoir|MICH
Spago|
Osteria Mozza|MICH
Pizzeria Mozza|
Republique|JB
Kali|MICH
88 Club|
Guerrilla Tacos|
Father's Office|
Jar|
"""

quality_restaurants = {}
for line in LAT101_RAW.strip().split('\n'):
    if '|' not in line:
        continue
    name, badges = line.split('|', 1)
    name = name.strip()
    signals = set()
    signals.add('LAT101')
    if badges.strip():
        for b in badges.split(','):
            b = b.strip()
            if b:
                signals.add(b)
    quality_restaurants[name.lower()] = {
        'name': name,
        'signals': signals,
        'score': len(signals)
    }

print(f"  Quality restaurants: {len(quality_restaurants)}")
michelin_count = sum(1 for v in quality_restaurants.values() if 'MICH' in v['signals'])
jbf_count = sum(1 for v in quality_restaurants.values() if 'JB' in v['signals'])
print(f"  With Michelin: {michelin_count}, With JBF: {jbf_count}")

# ─────────────────────────────────────────────
# PHASE 3: Fuzzy-match ChefDb restaurants to quality signals
# ─────────────────────────────────────────────
print("\nPhase 3: Matching ChefDb restaurants to quality signals...")

def normalize(name):
    name = name.lower().strip()
    for suffix in [' restaurant', ' los angeles', ' la', ' - los angeles', ' café', ' cafe']:
        name = name.replace(suffix, '')
    name = re.sub(r'[^\w\s]', '', name)
    return name.strip()

def fuzzy_match(name1, name2, threshold=0.8):
    n1, n2 = normalize(name1), normalize(name2)
    if n1 == n2:
        return 1.0
    if n1 in n2 or n2 in n1:
        return 0.9
    return SequenceMatcher(None, n1, n2).ratio()

quality_matched = {}
for rest in chefdb_rests:
    rname = rest['name']
    for qname, qinfo in quality_restaurants.items():
        score = fuzzy_match(rname, qinfo['name'])
        if score >= 0.75:
            quality_matched[rest['chefdb_id']] = {
                'chefdb_name': rname,
                'quality_name': qinfo['name'],
                'signals': qinfo['signals'],
                'match_score': score
            }
            break

print(f"  Matched {len(quality_matched)} ChefDb restaurants to quality list")

# ─────────────────────────────────────────────
# PHASE 4: Find chefs at quality restaurants NOT yet in IRDB
# ─────────────────────────────────────────────
print("\nPhase 4: Finding new quality chefs...")

chef_names_db = {}
for rpid, rprof in chefdb_rprof.items():
    for staff in rprof.get('staff', []):
        cid = staff.get('chef_chefdb_id')
        if cid:
            chef_names_db[cid] = staff.get('chef_name', 'Unknown')

chef_scores = {}
for cid, cprof in chefdb_cprof.items():
    positions = cprof.get('positions', [])
    if not positions:
        continue

    chef_name = chef_names_db.get(cid, f'Unknown ({cid})')

    if norm_name(chef_name) in irdb_chef_names:
        continue

    quality_signals = set()
    quality_restaurant_names = []
    all_restaurants = []
    la_restaurants = []

    for pos in positions:
        rname = pos.get('restaurant_name', '')
        rcid = pos.get('restaurant_chefdb_id', '')
        city = pos.get('city', '')

        all_restaurants.append({
            'name': rname,
            'chefdb_id': rcid,
            'city': city,
            'position': pos.get('position', ''),
            'start_year': pos.get('start_year'),
            'end_year': pos.get('end_year'),
            'is_current': pos.get('is_current', False),
        })

        if city and any(c in city for c in ['Los Angeles', 'Santa Monica', 'Beverly Hills', 'West Hollywood', 'Culver City', 'Pasadena']):
            la_restaurants.append(rname)

        if rcid in quality_matched:
            qm = quality_matched[rcid]
            quality_signals.update(qm['signals'])
            quality_restaurant_names.append(qm['quality_name'])
        else:
            for qname, qinfo in quality_restaurants.items():
                if fuzzy_match(rname, qinfo['name']) >= 0.75:
                    quality_signals.update(qinfo['signals'])
                    quality_restaurant_names.append(qinfo['name'])
                    break

    # Check for positions at IRDB restaurants
    irdb_restaurant_overlaps = []
    for pos in positions:
        rname = pos.get('restaurant_name', '')
        for irest in irdb_rests:
            if fuzzy_match(rname, irest['name']) >= 0.8:
                irdb_restaurant_overlaps.append({
                    'restaurant': irest['name'],
                    'restaurant_id': irest['id'],
                    'position': pos.get('position', ''),
                    'start_year': pos.get('start_year'),
                    'end_year': pos.get('end_year'),
                })
                break

    # Score
    score = 0
    if quality_signals:
        score += len(quality_signals) * 10
    if 'MICH' in quality_signals:
        score += 20
    if 'JB' in quality_signals:
        score += 15
    score += len(la_restaurants) * 2
    score += min(len(all_restaurants), 10)
    score += len(irdb_restaurant_overlaps) * 5

    if score > 0:
        chef_scores[cid] = {
            'name': chef_name,
            'chefdb_id': cid,
            'score': score,
            'quality_signals': sorted(quality_signals),
            'quality_restaurants': quality_restaurant_names,
            'la_restaurants': la_restaurants,
            'total_positions': len(all_restaurants),
            'positions': all_restaurants,
            'irdb_overlaps': irdb_restaurant_overlaps,
            'education': cprof.get('education', []),
            'tags': cprof.get('tags', {}),
        }

ranked = sorted(chef_scores.values(), key=lambda x: -x['score'])
print(f"  Found {len(ranked)} quality chef candidates")

# ─────────────────────────────────────────────
# PHASE 5: Detect mentor connections via temporal overlap
# ─────────────────────────────────────────────
print("\nPhase 5: Detecting mentor connections...")

irdb_chef_timelines = defaultdict(list)
irdb_chef_name_map = {c['id']: c['name']['display'] for c in irdb_chefs}

for stop in irdb_stops:
    irdb_chef_timelines[stop['restaurant_id']].append({
        'chef_id': stop['chef_id'],
        'chef_name': irdb_chef_name_map.get(stop['chef_id'], stop['chef_id']),
        'position': stop.get('position', ''),
        'start_year': stop.get('start_year'),
        'end_year': stop.get('end_year'),
        'is_current': stop.get('is_current', False),
    })

for chef in ranked[:50]:
    suggested_mentors = []
    for overlap in chef.get('irdb_overlaps', []):
        rid = overlap['restaurant_id']
        chef_start = overlap.get('start_year')
        chef_end = overlap.get('end_year')

        for irdb_stop in irdb_chef_timelines.get(rid, []):
            senior_positions = ['chef & owner', 'chef & co-owner', 'executive chef', 'head chef',
                              'chef & founder', 'founder', 'chef de cuisine', 'managing partner',
                              'opening chef', 'culinary director']
            is_senior = any(sp in irdb_stop['position'].lower() for sp in senior_positions)

            if is_senior:
                overlaps = True
                if chef_start and irdb_stop.get('end_year') and chef_start > irdb_stop['end_year']:
                    overlaps = False
                if chef_end and irdb_stop.get('start_year') and chef_end < irdb_stop['start_year']:
                    overlaps = False

                if overlaps:
                    suggested_mentors.append({
                        'mentor_name': irdb_stop['chef_name'],
                        'mentor_id': irdb_stop['chef_id'],
                        'restaurant': overlap['restaurant'],
                        'restaurant_id': rid,
                        'confidence': 'high' if (chef_start and irdb_stop.get('start_year')) else 'medium',
                    })

    chef['suggested_mentors'] = suggested_mentors

# ─────────────────────────────────────────────
# PHASE 6: Generate draft entries
# ─────────────────────────────────────────────
print("\nPhase 6: Generating draft entries...")

def make_chef_id(name):
    parts = name.lower().split()
    slug = '_'.join(re.sub(r'[^\w]', '', p) for p in parts if p)
    return f"chef_{slug}"

def make_rest_id(name):
    slug = re.sub(r'[^\w\s]', '', name.lower())
    slug = '_'.join(slug.split())
    return f"rest_{slug}"

draft_entries = []
for chef in ranked[:50]:
    chef_id = make_chef_id(chef['name'])

    draft_chef = {
        'id': chef_id,
        'name': {
            'first': chef['name'].split()[0] if chef['name'].split() else '',
            'last': ' '.join(chef['name'].split()[1:]) if len(chef['name'].split()) > 1 else '',
            'display': chef['name'],
            'nickname': None,
        },
        'bio': f"[DRAFT — needs editorial bio. Quality signals: {', '.join(chef['quality_signals'])}. {chef['total_positions']} career positions.]",
        'birth_year': None,
        'birth_country': chef.get('tags', {}).get('birth_country'),
        'birth_city': None,
        'cuisine_tags': [],
        'photo_url': None, 'instagram': None, 'website': None,
        'status': 'active',
        'education': [{'institution': e, 'city': None, 'year': None, 'credential': None}
                      for e in chef.get('education', []) if e and 'james beard' not in e.lower() and 'bon appetit' not in e.lower() and 'food & wine' not in e.lower()],
    }

    draft_stops = []
    for pos in chef['positions']:
        rest_id = make_rest_id(pos['name'])
        draft_stops.append({
            'chef_id': chef_id,
            'restaurant_id': rest_id,
            'restaurant_name': pos['name'],
            'city': pos.get('city', ''),
            'position': pos.get('position', ''),
            'start_year': pos.get('start_year'),
            'end_year': pos.get('end_year'),
            'is_current': pos.get('is_current', False),
        })

    draft_entries.append({
        'rank': len(draft_entries) + 1,
        'score': chef['score'],
        'chefdb_id': chef['chefdb_id'],
        'quality_signals': chef['quality_signals'],
        'quality_restaurants': chef['quality_restaurants'],
        'suggested_mentors': chef.get('suggested_mentors', []),
        'irdb_overlaps': chef['irdb_overlaps'],
        'draft_chef': draft_chef,
        'draft_stops': draft_stops,
    })

# ─────────────────────────────────────────────
# PHASE 7: Write output
# ─────────────────────────────────────────────
output_path = os.path.join(DATA, 'intake_queue.json')
with open(output_path, 'w') as f:
    json.dump(draft_entries, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"PIPELINE COMPLETE")
print(f"{'='*60}")
print(f"  Output: data/intake_queue.json")
print(f"  Candidates: {len(draft_entries)}")
print(f"  With mentor suggestions: {sum(1 for d in draft_entries if d.get('suggested_mentors'))}")
print(f"\n  Top 30 intake queue:")
print(f"  {'Rank':>4s}  {'Score':>5s}  {'Chef':30s}  {'Signals':20s}  {'Mentors':30s}")
print(f"  {'─'*4}  {'─'*5}  {'─'*30}  {'─'*20}  {'─'*30}")
for d in draft_entries[:30]:
    name = d['draft_chef']['name']['display']
    sigs = ','.join(d['quality_signals'])
    mentors = ', '.join(m['mentor_name'] for m in d.get('suggested_mentors', [])[:2])
    if not mentors:
        mentors = '—'
    print(f"  {d['rank']:4d}  {d['score']:5d}  {name:30s}  {sigs:20s}  {mentors:30s}")

print(f"\n  Quality signal distribution:")
all_sigs = Counter()
for d in draft_entries:
    for s in d['quality_signals']:
        all_sigs[s] += 1
for sig, ct in all_sigs.most_common():
    print(f"    {sig}: {ct} chefs")

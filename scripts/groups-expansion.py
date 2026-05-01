#!/usr/bin/env python3
"""
IRDB Restaurant Group Expansion
================================
1. Enriches existing groups with new schema fields (founded_year, model, notable_alumni, etc.)
2. Adds 23 new restaurant groups
3. Adds 20 new restaurants (from group portfolios)
4. Backfills group_id on all restaurants in group portfolios
5. Syncs to app/src/
6. Prints chef leads report

Usage:
  python3 scripts/groups-expansion.py
  python3 scripts/groups-expansion.py --dry-run
"""

import json, os, sys, argparse
from datetime import date

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

# ─────────────────────────────────────────────
# Load existing data
# ─────────────────────────────────────────────

groups = load('groups.json')
restaurants = load('restaurants.json')

rest_by_id = {r['id']: r for r in restaurants}
group_by_id = {g['id']: g for g in groups}

print(f"Loaded: {len(groups)} groups, {len(restaurants)} restaurants")

# ─────────────────────────────────────────────
# PHASE 1: Enrich existing groups
# ─────────────────────────────────────────────

enrichments = {
    'group_sprout_la': {
        'founded_year': 2010,
        'model': 'development',
        'total_locations': None,
        'notable_alumni': ['chef_ori_menashe', 'chef_walter_manzke', 'chef_ray_garcia', 'chef_tim_hollingsworth', 'chef_steve_samson', 'chef_ricardo_zarate'],
        'website': None,
        # Sprout was an incubator — chefs went independent. Clear portfolio.
        'portfolio': [],
        'description': "Bill Chait's restaurant incubator (2010-2018). Launched Bestia, Republique, Broken Spanish, Otium, Sotto, Picca, Redbird, Short Order. Chefs went independent. The most important development entity in modern LA dining.",
        'active': False,
    },
    'group_thinkfoodgroup': {
        'founded_year': 1993,
        'model': 'chef-restaurateur',
        'total_locations': 30,
        'notable_alumni': [],
        'website': None,
    },
    'group_bb_hospitality': {
        'founded_year': 2007,
        'model': 'chef-partner',
        'total_locations': 15,
        'notable_alumni': ['chef_elizabeth_hong', 'chef_chad_colby'],
        'website': None,
        'description': "Bastianich family + Nancy Silverton. Osteria Mozza (1 Michelin star + Green Star), Pizzeria Mozza, chi SPACCA, Mozza2Go. Elizabeth Hong is culinary director. Max & Helen's (with Phil Rosenthal) opening 2025. Expanding globally: Newport Beach, DC, London, Singapore.",
    },
    'group_last_word': {
        'founded_year': 2014,
        'model': 'operator',
        'total_locations': 6,
        'notable_alumni': [],
        'website': None,
        'portfolio': ['rest_rasarumah', 'rest_pearl_river_deli', 'rest_found_oyster'],
        'description': "Founded 2014 by Holly Fox & Adam Weisblatt. Found Oyster, Rasarumah, Pearl River Deli, Barra Santos, Queen St., Shin's Pizza, The Copper Room. 2026 JBF semifinalist: Outstanding Restaurateur.",
    },
    'group_shook_dotolo': {
        'founded_year': 2008,
        'model': 'chef-restaurateur',
        'total_locations': 12,
        'notable_alumni': [],
        'website': None,
        'portfolio': ['rest_jon_vinnys'],
        'description': "Animal (closed 2023), Son of a Gun (closed 2024), Jon & Vinny's (5 LA locations + Saudi Arabia), Cookbook Market (3 locations), Helen's Wines. Kismet partnership ended May 2021. Petit Trois partnership with Ludo Lefebvre.",
    },
    'group_francis_miranda': {
        'founded_year': None,
        'model': 'restaurateur',
        'total_locations': 3,
        'notable_alumni': [],
        'website': None,
    },
    'group_tkrg': {
        'founded_year': 1994,
        'model': 'chef-restaurateur',
        'total_locations': 10,
        'notable_alumni': ['chef_eric_ziebold', 'chef_gary_menes', 'chef_tim_hollingsworth', 'chef_corey_lee'],
        'website': None,
    },
    'group_alinea_group': {
        'founded_year': 2005,
        'model': 'chef-restaurateur',
        'total_locations': 5,
        'notable_alumni': ['chef_dave_beran', 'chef_jordan_kahn'],
        'website': None,
    },
    'group_wolfgang_puck': {
        'founded_year': 1982,
        'model': 'chef-restaurateur',
        'total_locations': 100,
        'notable_alumni': ['chef_nancy_silverton', 'chef_lee_hefter', 'chef_jon_shook', 'chef_vinny_dotolo', 'chef_walter_manzke', 'chef_govind_armstrong', 'chef_daniel_son'],
        'website': None,
        'description': "Spago, CUT, Chinois on Main, Merois, Wolfgang Puck Bar & Grill. 100+ restaurants worldwide (fine dining + casual + airport). Current Spago EC: Ari Rosenson. Current CUT EC: Drew Rosenberg. Training ground for a generation of LA chefs.",
    },
    'group_lucques': {
        'founded_year': 1998,
        'model': 'chef-restaurateur',
        'total_locations': 3,
        'notable_alumni': [],
        'website': None,
        'description': "Suzanne Goin & Caroline Styne. A.O.C. (W. Hollywood), Hollywood Bowl Food + Wine (seasonal). Lucques (closed 2020), Tavern/A.O.C. Brentwood (closed Aug 2025), Caldo Verde + Cara Cara at Proper Hotel (closed). JBF Outstanding Chef (Goin 2016) and Outstanding Restaurateur (Styne 2018).",
        'portfolio': ['rest_aoc'],
    },
    'group_rustic_canyon': {
        'founded_year': 2006,
        'model': 'chef-restaurateur',
        'total_locations': 8,
        'notable_alumni': ['chef_bryant_ng'],
        'website': None,
        'description': "Josh Loeb, Zoe Nathan, Colby Goff. Santa Monica-based. Rustic Canyon (Jeremy Fox), Birdie G's, Huckleberry, Milo+Olive, Sweet Rose Creamery, Esters, The Dutchess (Ojai, chef Saw Naing). Cassia closed Feb 2025.",
        'portfolio': ['rest_rustic_canyon', 'rest_birdie_gs', 'rest_huckleberry'],
    },
    'group_patina': {
        'founded_year': 1989,
        'model': 'operator',
        'total_locations': 60,
        'notable_alumni': ['chef_walter_manzke', 'chef_tony_esnault'],
        'website': None,
        'description': "Founded by Joachim Splichal. Grew from Patina to 60+ restaurants, catering, and venue operations (performing arts centers, Disney). Acquired by Sodexo's Centerplate. Current Patina EC: Andreas Roller. Training ground for a generation of LA French chefs.",
    },
    'group_sugarfish': {
        'founded_year': 2008,
        'model': 'chef-brand',
        'total_locations': 30,
        'notable_alumni': [],
        'website': None,
    },
    'group_gjelina': {
        'founded_year': 2008,
        'model': 'operator',
        'total_locations': 6,
        'notable_alumni': ['chef_travis_lett'],
        'website': None,
        'description': "Fran Camaj (named for his mother). Gjelina, GTA, Gjusta, Gjusta Goods, Gjusta Grocer, Gjelina Hotel. Expanding to NYC and Las Vegas (2025). Travis Lett co-founded, sold stake 2019, now operates RVR independently.",
    },
}

enriched_count = 0
for gid, fields in enrichments.items():
    if gid in group_by_id:
        for k, v in fields.items():
            group_by_id[gid][k] = v
        enriched_count += 1

print(f"\nPhase 1: Enriched {enriched_count} existing groups")

# ─────────────────────────────────────────────
# PHASE 2: Add new groups
# ─────────────────────────────────────────────

new_groups = [
    {
        'id': 'group_cimarusti',
        'name': 'Michael Cimarusti Restaurants',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Michael Cimarusti', 'Donato Poto'],
        'city': 'Los Angeles',
        'founded_year': 2005,
        'portfolio': ['rest_providence', 'rest_connie_teds', 'rest_cape_seafood'],
        'total_locations': 3,
        'notable_alumni': ['chef_jessica_largey'],
        'description': "Providence (3 Michelin stars — first in LA history), Connie & Ted's, Cape Seafood & Provisions. Business partner Donato Poto. CIA-trained, shaped by Le Cirque and Arpège.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_nakayama',
        'name': 'Niki Nakayama & Carole Iida-Nakayama',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Niki Nakayama', 'Carole Iida-Nakayama'],
        'city': 'Los Angeles',
        'founded_year': 2011,
        'portfolio': ['rest_nnaka', 'rest_nsoto'],
        'total_locations': 2,
        'notable_alumni': [],
        'description': "n/naka (2 Michelin stars, modern kaiseki) and n/soto (1 star, izakaya led by chef Yoji Tajima).",
        'active': True,
        'website': None
    },
    {
        'id': 'group_beran',
        'name': 'Dave Beran Restaurants',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Dave Beran'],
        'city': 'Santa Monica',
        'founded_year': 2017,
        'portfolio': ['rest_pasjoli', 'rest_seline'],
        'total_locations': 2,
        'notable_alumni': [],
        'description': "Pasjoli (1 Michelin star, French bistro) and Seline (tasting menu). Ex-Alinea/Next executive chef.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_menashe_gergis',
        'name': 'Ori Menashe & Genevieve Gergis',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Ori Menashe', 'Genevieve Gergis', 'Leah Bunch'],
        'city': 'Los Angeles',
        'founded_year': 2012,
        'portfolio': ['rest_bestia', 'rest_bavel', 'rest_saffys'],
        'total_locations': 3,
        'notable_alumni': [],
        'description': "Bestia (Arts District), Bavel (Middle Eastern), Saffy's (East Hollywood). Originally incubated by Sprout LA, now independent.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_funke',
        'name': 'Evan Funke / Gusto 54',
        'type': 'chef-partner',
        'model': 'chef-partner',
        'key_people': ['Evan Funke', 'Janet Zuccarini'],
        'city': 'Los Angeles',
        'founded_year': 2017,
        'portfolio': ['rest_felix', 'rest_mother_wolf', 'rest_funke'],
        'total_locations': 6,
        'notable_alumni': [],
        'description': "Felix (Venice), Mother Wolf (Hollywood + Las Vegas + Miami), Funke (Beverly Hills, Michelin). Partnership with Janet Zuccarini's Toronto-based Gusto 54.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_citrin',
        'name': 'Citrin Hospitality',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Josiah Citrin'],
        'city': 'Santa Monica',
        'founded_year': 1999,
        'portfolio': ['rest_melisse', 'rest_citrin', 'rest_charcoal', 'rest_dear_johns'],
        'total_locations': 6,
        'notable_alumni': [],
        'description': "Mélisse (2 Michelin stars), Citrin (1 star), Charcoal (Venice), Dear John's (Culver City, with Rockenwagners), Augie's on Main, Dear Jane's. Westside empire.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_stone',
        'name': 'Curtis Stone Restaurants',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Curtis Stone', 'Luke Stone'],
        'city': 'Los Angeles',
        'founded_year': 2014,
        'portfolio': ['rest_gwen'],
        'total_locations': 2,
        'notable_alumni': ['chef_chad_colby'],
        'description': "Gwen (1 Michelin star, relocating to Westside Aug 2025). Maude closed Sept 2024, replaced by The Pie Room. Co-owned with brother Luke Stone.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_lefebvre',
        'name': 'Ludo Lefebvre Restaurants',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Ludo Lefebvre'],
        'city': 'Los Angeles',
        'founded_year': 2013,
        'portfolio': ['rest_petit_trois'],
        'total_locations': 3,
        'notable_alumni': [],
        'description': "Petit Trois (Hollywood + Sherman Oaks + Aspen). Trois Mec (1 star, closed 2020) was partnership with Shook & Dotolo.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_centeno',
        'name': 'Josef Centeno Restaurants',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Josef Centeno'],
        'city': 'Los Angeles',
        'founded_year': 2011,
        'portfolio': ['rest_baco_mercat', 'rest_orsa_winston'],
        'total_locations': 2,
        'notable_alumni': [],
        'description': "Bäco Mercat (DTLA) and Orsa & Winston (DTLA). Multi-concept downtown operator.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_manzke',
        'name': 'Manzke Hospitality Group',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Walter Manzke', 'Margarita Manzke'],
        'city': 'Los Angeles',
        'founded_year': 2013,
        'portfolio': ['rest_republique'],
        'total_locations': 1,
        'notable_alumni': [],
        'description': "République (La Brea). Originally Sprout LA, now independent. Manzke tasting menu + Bicyclette bistro both closed March 2024. Margarita: JBF Outstanding Pastry Chef/Baker 2023. Wildflour (17 locations, Philippines).",
        'active': True,
        'website': None
    },
    {
        'id': 'group_choi',
        'name': '10 Grand Hospitality / Roy Choi',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Roy Choi'],
        'city': 'Los Angeles',
        'founded_year': 2008,
        'portfolio': ['rest_kogi'],
        'total_locations': 3,
        'notable_alumni': [],
        'description': "Kogi BBQ trucks (pioneered gourmet food truck movement). Kogi Taqueria (2 locations). LocoL, A-Frame, POT, Commissary all closed. Best Friend at Park MGM (Las Vegas).",
        'active': True,
        'website': None
    },
    {
        'id': 'group_yenbamroong',
        'name': 'Night + Market',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Kris Yenbamroong'],
        'city': 'Los Angeles',
        'founded_year': 2010,
        'portfolio': ['rest_night_market', 'rest_night_market_song', 'rest_night_market_sahm'],
        'total_locations': 4,
        'notable_alumni': [],
        'description': "Night + Market (WeHo), Song (Silver Lake), Sahm (Venice). F&W Best New Chef 2016. Also at Virgin Hotels Las Vegas.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_hwood',
        'name': 'h.wood Group',
        'type': 'operator',
        'model': 'operator',
        'key_people': ['John Terzian', 'Brian Toll'],
        'city': 'Los Angeles',
        'founded_year': 2008,
        'portfolio': ['rest_delilah', 'rest_the_nice_guy'],
        'total_locations': 14,
        'notable_alumni': [],
        'description': "Delilah, The Nice Guy, Harriet's, Slab. Nightlife-forward hospitality, supper club format. 9-figure valuation (2026 DIAFA investment). Expanding to Dallas, NYC.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_idg',
        'name': 'Innovative Dining Group',
        'type': 'operator',
        'model': 'operator',
        'key_people': ['Lee Maen', 'Philip Cummins', 'Craig Katz'],
        'city': 'Los Angeles',
        'founded_year': 1997,
        'portfolio': ['rest_sushi_roku', 'rest_boa_steakhouse', 'rest_katana'],
        'total_locations': 7,
        'notable_alumni': [],
        'description': "Sushi Roku, BOA Steakhouse, Katana, ROKU. Corp exec chef Tyson Wong. Sunset Strip institution since 1997.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_nobu',
        'name': 'Nobu Hospitality',
        'type': 'chef-brand',
        'model': 'chef-brand',
        'key_people': ['Nobu Matsuhisa', 'Robert De Niro', 'Meir Teper'],
        'city': 'Global',
        'founded_year': 1994,
        'portfolio': ['rest_matsuhisa', 'rest_nobu_malibu', 'rest_nobu_la'],
        'total_locations': 50,
        'notable_alumni': [],
        'description': "Matsuhisa (Beverly Hills, 1987 — Nobu's personal restaurant), Nobu Malibu, Nobu LA. 50+ restaurants, 17+ hotels worldwide. Founded with Robert De Niro.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_mina',
        'name': 'The Mina Group',
        'type': 'chef-partner',
        'model': 'chef-partner',
        'key_people': ['Michael Mina'],
        'city': 'San Francisco',
        'founded_year': 2002,
        'portfolio': ['rest_bourbon_steak_la', 'rest_orla'],
        'total_locations': 39,
        'notable_alumni': [],
        'description': "Bourbon Steak (Glendale), Orla (Regent Santa Monica). 39 restaurants globally. Chef-partner model pairs Mina brand with local executive chefs.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_momofuku',
        'name': 'Momofuku',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['David Chang'],
        'city': 'New York',
        'founded_year': 2004,
        'portfolio': ['rest_majordomo'],
        'total_locations': 10,
        'notable_alumni': [],
        'description': "Majordomo (Arts District, since 2018). David Chang's only LA concept. Large-format dishes, California-Korean cooking.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_sbe',
        'name': 'sbe / Disruptive Restaurant Group',
        'type': 'development',
        'model': 'development',
        'key_people': ['Sam Nazarian'],
        'city': 'Beverly Hills',
        'founded_year': 2002,
        'portfolio': ['rest_katsuya'],
        'total_locations': 15,
        'notable_alumni': [],
        'description': "Katsuya (4 LA locations, chef Katsuya Uechi), Casa Dani (Century City, chef Dani Garcia). Global hotel-restaurant platform. Previously operated The Bazaar by Jose Andres at SLS Hotel.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_wywh',
        'name': 'Wish You Were Here Group',
        'type': 'operator',
        'model': 'operator',
        'key_people': ['Nick Mathers'],
        'city': 'Los Angeles',
        'founded_year': 2018,
        'portfolio': ['rest_elephante'],
        'total_locations': 6,
        'notable_alumni': [],
        'description': "Elephante (Santa Monica rooftop, coastal Italian). Expanding to Scottsdale, Dallas, Las Vegas, NYC.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_williamson',
        'name': 'Brooke Williamson & Nick Roberts',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Brooke Williamson', 'Nick Roberts'],
        'city': 'Los Angeles',
        'founded_year': 2012,
        'portfolio': ['rest_playa_provisions', 'rest_hudson_house'],
        'total_locations': 2,
        'notable_alumni': [],
        'description': "Playa Provisions (Playa del Rey) and Hudson House (Redondo Beach). Top Chef Season 14 winner.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_samson',
        'name': 'Steve Samson Restaurants',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Steve Samson'],
        'city': 'Los Angeles',
        'founded_year': 2011,
        'portfolio': ['rest_rossoblu', 'rest_sotto'],
        'total_locations': 2,
        'notable_alumni': [],
        'description': "Rossoblu (DTLA) and Sotto. Italian-focused. Trained at Angelini Osteria. Sotto originally incubated by Sprout LA.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_jean_georges',
        'name': 'Jean-Georges Management',
        'type': 'chef-brand',
        'model': 'chef-brand',
        'key_people': ['Jean-Georges Vongerichten'],
        'city': 'New York',
        'founded_year': 1997,
        'portfolio': ['rest_the_rooftop_by_jg'],
        'total_locations': 40,
        'notable_alumni': [],
        'description': "The Rooftop by JG (Waldorf Astoria Beverly Hills). Exec chef Steve Benjamin. 40+ restaurants worldwide.",
        'active': True,
        'website': None
    },
    {
        'id': 'group_kahn',
        'name': 'Jordan Kahn Restaurants',
        'type': 'chef-owned',
        'model': 'chef-restaurateur',
        'key_people': ['Jordan Kahn'],
        'city': 'Los Angeles',
        'founded_year': 2016,
        'portfolio': ['rest_vespertine', 'rest_destroyer', 'rest_meteora'],
        'total_locations': 3,
        'notable_alumni': [],
        'description': "Vespertine (2 Michelin stars + Green Star), Destroyer (breakfast/lunch), Meteora (1 star). All in Culver City/Hancock Park. Ex-Alinea. Vespertine closed 2020, reopened April 2024.",
        'active': True,
        'website': None
    },
]

# Check for duplicate group IDs
new_group_ids = {g['id'] for g in new_groups}
existing_group_ids = {g['id'] for g in groups}
dupes = new_group_ids & existing_group_ids
if dupes:
    print(f"  WARNING: Duplicate group IDs, skipping: {dupes}")
    new_groups = [g for g in new_groups if g['id'] not in existing_group_ids]

groups.extend(new_groups)
group_by_id.update({g['id']: g for g in new_groups})
print(f"Phase 2: Added {len(new_groups)} new groups (total: {len(groups)})")

# ─────────────────────────────────────────────
# PHASE 3: Add new restaurants
# ─────────────────────────────────────────────

def make_rest(id, name, city='Los Angeles', neighborhood=None, cuisine_tags=None, status='open',
              open_year=None, price_range=None, format=None, group_id=None, ratings=None):
    return {
        'id': id,
        'name': name,
        'address': None,
        'city': city,
        'neighborhood': neighborhood,
        'state': 'CA',
        'cuisine_tags': cuisine_tags or [],
        'status': status,
        'open_year': open_year,
        'close_year': None,
        'price_range': price_range,
        'seats': None,
        'format': format,
        'group_id': group_id,
        'ratings': ratings or {},
        'website': None,
    }

new_restaurants = [
    make_rest('rest_cape_seafood', 'Cape Seafood & Provisions',
              neighborhood='Mid-City', cuisine_tags=['seafood', 'market'],
              open_year=2020, price_range='$$', format='market',
              group_id='group_cimarusti'),

    make_rest('rest_funke', 'Funke',
              neighborhood='Beverly Hills', cuisine_tags=['italian', 'fine-dining', 'pasta'],
              open_year=2023, price_range='$$$$', format='a-la-carte',
              group_id='group_funke',
              ratings={'michelin_stars': None, 'jbf': [], 'other': ['Michelin Guide']}),

    make_rest('rest_citrin', 'Citrin',
              city='Santa Monica', cuisine_tags=['california', 'fine-dining'],
              open_year=2019, price_range='$$$', format='a-la-carte',
              group_id='group_citrin',
              ratings={'michelin_stars': 1, 'michelin_year': 2025}),

    make_rest('rest_dear_johns', "Dear John's",
              neighborhood='Culver City', cuisine_tags=['american', 'steakhouse'],
              open_year=2019, price_range='$$$', format='a-la-carte',
              group_id='group_citrin'),

    make_rest('rest_night_market_song', 'Night + Market Song',
              neighborhood='Silver Lake', cuisine_tags=['thai', 'street-food'],
              open_year=2014, price_range='$$', format='casual',
              group_id='group_yenbamroong'),

    make_rest('rest_night_market_sahm', 'Night + Market Sahm',
              neighborhood='Venice', cuisine_tags=['thai', 'street-food'],
              open_year=2017, price_range='$$', format='casual',
              group_id='group_yenbamroong'),

    make_rest('rest_delilah', 'Delilah',
              neighborhood='West Hollywood', cuisine_tags=['american', 'supper-club'],
              open_year=2016, price_range='$$$$', format='supper-club',
              group_id='group_hwood'),

    make_rest('rest_the_nice_guy', 'The Nice Guy',
              neighborhood='West Hollywood', cuisine_tags=['italian', 'supper-club'],
              open_year=2015, price_range='$$$', format='supper-club',
              group_id='group_hwood'),

    make_rest('rest_sushi_roku', 'Sushi Roku',
              city='Santa Monica', cuisine_tags=['japanese', 'sushi'],
              open_year=1997, price_range='$$$', format='a-la-carte',
              group_id='group_idg'),

    make_rest('rest_boa_steakhouse', 'BOA Steakhouse',
              neighborhood='West Hollywood', cuisine_tags=['steakhouse', 'fine-dining'],
              open_year=2004, price_range='$$$$', format='a-la-carte',
              group_id='group_idg'),

    make_rest('rest_katana', 'Katana',
              neighborhood='West Hollywood', cuisine_tags=['japanese', 'robata'],
              open_year=2001, price_range='$$$', format='a-la-carte',
              group_id='group_idg'),

    make_rest('rest_nobu_malibu', 'Nobu Malibu',
              city='Malibu', cuisine_tags=['japanese', 'sushi', 'fine-dining'],
              open_year=1999, price_range='$$$$', format='a-la-carte',
              group_id='group_nobu'),

    make_rest('rest_nobu_la', 'Nobu Los Angeles',
              neighborhood='West Hollywood', cuisine_tags=['japanese', 'sushi', 'fine-dining'],
              open_year=2008, price_range='$$$$', format='a-la-carte',
              group_id='group_nobu'),

    make_rest('rest_bourbon_steak_la', 'Bourbon Steak Los Angeles',
              city='Glendale', cuisine_tags=['steakhouse', 'fine-dining'],
              open_year=2023, price_range='$$$$', format='a-la-carte',
              group_id='group_mina'),

    make_rest('rest_orla', 'Orla',
              city='Santa Monica', cuisine_tags=['mediterranean', 'fine-dining'],
              open_year=2023, price_range='$$$$', format='a-la-carte',
              group_id='group_mina'),

    make_rest('rest_majordomo', 'Majordomo',
              neighborhood='Arts District', cuisine_tags=['korean', 'california', 'large-format'],
              open_year=2018, price_range='$$$', format='a-la-carte',
              group_id='group_momofuku'),

    make_rest('rest_katsuya', 'Katsuya',
              neighborhood='Hollywood', cuisine_tags=['japanese', 'sushi'],
              open_year=2006, price_range='$$$', format='a-la-carte',
              group_id='group_sbe'),

    make_rest('rest_elephante', 'Elephante',
              city='Santa Monica', cuisine_tags=['italian', 'coastal'],
              open_year=2018, price_range='$$$', format='a-la-carte',
              group_id='group_wywh'),

    make_rest('rest_sotto', 'Sotto',
              neighborhood='Downtown', cuisine_tags=['italian', 'southern-italian'],
              open_year=2011, price_range='$$$', format='a-la-carte',
              group_id='group_samson'),

    make_rest('rest_the_rooftop_by_jg', 'The Rooftop by JG',
              neighborhood='Beverly Hills', cuisine_tags=['california', 'fine-dining'],
              open_year=2017, price_range='$$$$', format='a-la-carte',
              group_id='group_jean_georges'),
]

# Filter out any that already exist
new_restaurants = [r for r in new_restaurants if r['id'] not in rest_by_id]
restaurants.extend(new_restaurants)
rest_by_id.update({r['id']: r for r in new_restaurants})
print(f"Phase 3: Added {len(new_restaurants)} new restaurants (total: {len(restaurants)})")

# ─────────────────────────────────────────────
# PHASE 4: Backfill group_id from ALL group portfolios
# ─────────────────────────────────────────────

backfill_count = 0
missing_rest = []

for g in groups:
    gid = g['id']
    for rid in g.get('portfolio', []):
        if rid in rest_by_id:
            old_gid = rest_by_id[rid].get('group_id')
            if old_gid != gid:
                rest_by_id[rid]['group_id'] = gid
                backfill_count += 1
                if old_gid:
                    print(f"  {rid}: {old_gid} → {gid}")
        else:
            missing_rest.append((gid, rid))

# Additional group_id assignments for restaurants NOT in portfolios
# (restaurants that belong to chef-owned groups but weren't in a portfolio before)
additional_assignments = {
    'rest_88_club': 'group_francis_miranda',
    'rest_daybird': 'group_francis_miranda',
    'rest_nightshade': 'group_francis_miranda',
    'rest_dialogue': 'group_beran',
    'rest_bicyclette': 'group_manzke',
    'rest_sari_sari': 'group_manzke',
    'rest_trois_mec': 'group_lefebvre',
    'rest_maude': 'group_stone',
    'rest_animal': 'group_shook_dotolo',
    'rest_son_of_a_gun': 'group_shook_dotolo',
    'rest_kismet': None,  # Independent since May 2021
    'rest_locol': 'group_choi',
    'rest_broken_spanish': None,  # Closed, was Sprout LA
    'rest_otium': None,  # Closed, was Sprout LA
}

for rid, gid in additional_assignments.items():
    if rid in rest_by_id:
        old = rest_by_id[rid].get('group_id')
        if gid is None and old:
            rest_by_id[rid]['group_id'] = None
            backfill_count += 1
        elif gid and old != gid:
            rest_by_id[rid]['group_id'] = gid
            backfill_count += 1

print(f"Phase 4: Backfilled group_id on {backfill_count} restaurants")
if missing_rest:
    print(f"  WARNING: {len(missing_rest)} portfolio restaurants not found in DB:")
    for gid, rid in missing_rest:
        print(f"    {gid} → {rid}")

# ─────────────────────────────────────────────
# PHASE 5: Save everything
# ─────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true')
args = parser.parse_args()

if args.dry_run:
    print(f"\nDRY RUN — no files modified.")
else:
    save('groups.json', groups)
    save('restaurants.json', restaurants)
    print(f"\nSaved groups.json ({len(groups)} groups) and restaurants.json ({len(restaurants)} restaurants)")
    print(f"  Synced to both data/ and app/src/")

# ─────────────────────────────────────────────
# PHASE 6: Chef leads report
# ─────────────────────────────────────────────

# Load stops + chefs for the leads analysis
stops = load('stops.json')
chefs = load('chefs.json')
chef_by_id = {c['id']: c for c in chefs}

# Find all restaurants in groups
grouped_rest_ids = set()
for g in groups:
    for rid in g.get('portfolio', []):
        grouped_rest_ids.add(rid)
for r in restaurants:
    if r.get('group_id'):
        grouped_rest_ids.add(r['id'])

# Find which grouped restaurants have a chef stop (current)
covered = set()
for s in stops:
    if s.get('is_current') and s['restaurant_id'] in grouped_rest_ids:
        covered.add(s['restaurant_id'])

uncovered = grouped_rest_ids - covered
uncovered_open = [rid for rid in uncovered if rid in rest_by_id and rest_by_id[rid].get('status') == 'open']

print(f"\n{'='*60}")
print(f"CHEF LEADS REPORT")
print(f"{'='*60}")
print(f"Grouped restaurants: {len(grouped_rest_ids)}")
print(f"With current chef stop: {len(covered)}")
print(f"Open restaurants needing head chef: {len(uncovered_open)}")
print()

# Known head chefs from research (not yet in DB)
known_leads = [
    ('rest_boa_steakhouse', 'Brendan Collins', 'Executive Chef', 'group_idg', 'Trained in UK. Ran Waterloo & City (Culver City) and Larry\'s (Venice) before IDG.'),
    ('rest_sushi_roku', 'Hiroshi Shima', 'Executive Sushi Chef', 'group_idg', 'Corp sushi chef for all IDG Japanese concepts.'),
    ('rest_katana', 'Jose Melendez', 'Executive Chef', 'group_idg', 'Junior Melendez. Runs Katana on Sunset.'),
    ('rest_nobu_malibu', 'Gregorio Stephenson', 'Executive Chef', 'group_nobu', 'Trained under Nobu Matsuhisa.'),
    ('rest_majordomo', 'James Bailey', 'Executive Chef', 'group_momofuku', 'Runs Majordomo under David Chang.'),
    ('rest_the_rooftop_by_jg', 'Steve Benjamin', 'Executive Chef', 'group_jean_georges', 'Exec chef at Waldorf Astoria BH under Jean-Georges Vongerichten.'),
    ('rest_nsoto', 'Yoji Tajima', 'Head Chef', 'group_nakayama', 'Leads n/soto izakaya under Niki Nakayama.'),
    ('rest_spago', 'Ari Rosenson', 'Executive Chef & VP of F&B', 'group_wolfgang_puck', 'Current Spago executive chef. VP of Food & Beverage for Wolfgang Puck Fine Dining.'),
    ('rest_cut', 'Drew Rosenberg', 'Executive Chef', 'group_wolfgang_puck', 'Current CUT Beverly Hills executive chef.'),
    ('rest_patina', 'Andreas Roller', 'Executive Chef', 'group_patina', 'Current Patina exec chef under Splichal.'),
    ('rest_katsuya', 'Katsuya Uechi', 'Master Chef', 'group_sbe', 'Brand chef for all Katsuya locations. Sushi master.'),
]

print("KNOWN HEAD CHEF LEADS (not yet in IRDB):")
print("-" * 60)
for rest_id, name, position, gid, notes in known_leads:
    rest_name = rest_by_id[rest_id]['name'] if rest_id in rest_by_id else rest_id
    group_name = group_by_id[gid]['name'] if gid in group_by_id else gid
    print(f"  {name:25s} | {position:20s} | {rest_name}")
    print(f"  {'':25s} | Group: {group_name}")
    print(f"  {'':25s} | {notes}")
    print()

print("\nOPEN GROUPED RESTAURANTS STILL NEEDING CHEF IDENTIFICATION:")
print("-" * 60)
known_rest_ids = {k[0] for k in known_leads}
for rid in sorted(uncovered_open):
    if rid not in known_rest_ids:
        r = rest_by_id[rid]
        gid = r.get('group_id', '?')
        gname = group_by_id.get(gid, {}).get('name', gid) if gid else 'none'
        print(f"  {r['name']:35s} | {gname}")

print(f"\n{'='*60}")
print(f"EXPANSION SUMMARY — {date.today().isoformat()}")
print(f"{'='*60}")
print(f"  Groups:      {len(groups)} (+{len(new_groups)} new, {enriched_count} enriched)")
print(f"  Restaurants: {len(restaurants)} (+{len(new_restaurants)} new, {backfill_count} group_id updates)")
print(f"  Chef leads:  {len(known_leads)} identified, {len(uncovered_open) - len(known_rest_ids)} restaurants still need research")

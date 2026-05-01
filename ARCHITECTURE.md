# IRDB — Internet Restaurant Database

## What This Is

A credentialing and intelligence system for the restaurant industry. Tracks chefs, their verified career histories, the restaurants they've built, and the networks that connect them.

**Core insight:** The chef network that determines which restaurants succeed has always been informal — passed around in kitchens, known by insiders, invisible to investors and the public. IRDB makes it legible.

## Who It's For

1. **Restaurant investors / groups** — Evaluate chef pedigree before backing a concept. See track record, training lineage, who mentored whom.
2. **Food journalists / media** — Research chef backgrounds, trace lineage, find story angles.
3. **Restaurateurs** — Recruit talent with verified experience. Understand who's coming up.
4. **Chefs themselves** — Build a verified career profile. A sous chef's 4 years at Providence becomes a portable credential.
5. **Serious diners** — Understand what you're eating and who made it.

## The Killer Feature: Verified Stops

A "stop" is a confirmed position at a specific restaurant during a specific period. Verification levels:

| Level | Meaning | How Verified |
|-------|---------|-------------|
| **Unverified** | Sourced from media, ChefDb, or public records | Default for scraped/editorial data |
| **Self-Reported** | Chef claimed their profile and added/confirmed this stop | Account creation + self-attestation |
| **Peer-Verified** | Another chef who worked at the same restaurant during overlapping dates confirms | Cross-referencing from another verified account |
| **Restaurant-Verified** | The restaurant or restaurant group confirms this person worked there | Restaurant account confirmation |

A chef with 6 verified stops at recognized kitchens carries a signal that no resume or LinkedIn profile currently provides.

## Data Model

Four entities stored as flat JSON files. Relationships are derived from stops, not stored redundantly.

### Entity: Chef

```json
{
  "id": "chef_michael_cimarusti",
  "name": {
    "first": "Michael",
    "last": "Cimarusti",
    "display": "Michael Cimarusti",
    "nickname": null
  },
  "bio": "Short factual blurb — training, lineage, key positions.",
  "birth_year": null,
  "birth_country": "US",
  "birth_city": "New Brunswick, NJ",
  "cuisine_tags": ["seafood", "californian", "fine-dining", "french-classical"],
  "photo_url": null,
  "instagram": null,
  "website": null,
  "status": "active",
  "education": [
    {
      "institution": "Culinary Institute of America",
      "city": "Hyde Park, NY",
      "year": 1990,
      "credential": "Culinary Arts (honors)"
    }
  ],
  "tier": "lineage"
}
```

**Field notes:**
- `status`: `"active"` | `"retired"` | `"deceased"`
- `tier`: `"lineage"` (verified training pedigree) | `"notable"` (significant but no lineage data yet)
- `education`: array of objects, empty `[]` if unknown
- Mentor/protégé relationships are derived from `stops.json` via `mentor_id`, not stored on the chef

### Entity: Stop (the core unit)

A stop is a chef's tenure at a specific restaurant in a specific role. This is the atomic unit of the database — everything else is built from stops.

```json
{
  "id": "stop_001",
  "chef_id": "chef_michael_cimarusti",
  "restaurant_id": "rest_providence",
  "position": "Executive Chef & Co-Owner",
  "start_year": 2005,
  "end_year": null,
  "is_current": true,
  "verification": "unverified",
  "mentor_id": null,
  "notes": null
}
```

**Field notes:**
- `id`: sequential numeric (`stop_NNN`)
- `mentor_id`: references a `chef_*` id — the senior chef at this restaurant who mentored this chef during this stop
- `notes`: optional context (null when empty)
- `is_current` and `end_year` must be consistent: `is_current: true` → `end_year: null`

### Entity: Restaurant

```json
{
  "id": "rest_providence",
  "name": "Providence",
  "address": "5955 Melrose Ave",
  "city": "Los Angeles",
  "neighborhood": "Hollywood",
  "state": "CA",
  "cuisine_tags": ["seafood", "californian", "fine-dining"],
  "status": "open",
  "open_year": 2005,
  "close_year": null,
  "price_range": "$$$$",
  "seats": null,
  "format": "tasting-menu",
  "group_id": "group_cimarusti",
  "ratings": {
    "michelin_stars": 3,
    "michelin_year": 2025,
    "bib_gourmand": false,
    "jbf": ["Best Chef: West 2019 (winner)"],
    "other": ["Green Michelin Star", "World's 50 Best North America 2025"]
  },
  "website": null,
  "notes": null
}
```

**Field notes:**
- `status`: `"open"` | `"closed"`
- `price_range`: `"$"` | `"$$"` | `"$$$"` | `"$$$$"` | `null`
- `format`: `"a-la-carte"` | `"tasting-menu"` | `"casual"` | `"fine-dining"` | `"omakase"` | `"counter"` | `"bistro"` | `"fast-casual"` | `"bakery"` | `"supper-club"` | `null`
- `ratings`: object with optional keys. `bib_gourmand: true` for Michelin Bib Gourmand restaurants. `jbf` is an array of strings. `michelin_year` = year of most recent star rating.
- `group_id`: references a `group_*` id, or `null` for independents
- `notes`: optional context (null when empty)

### Entity: Restaurant Group / Investor

```json
{
  "id": "group_sprout_la",
  "name": "Sprout LA",
  "type": "development",
  "key_people": ["Bill Chait"],
  "city": "Los Angeles",
  "portfolio": [],
  "description": "Restaurant development and incubation.",
  "active": true,
  "founded_year": 2010,
  "model": "development",
  "total_locations": null,
  "notable_alumni": ["chef_ori_menashe"],
  "website": null,
  "notes": null
}
```

**Field notes:**
- `type`: ownership structure — `"chef-owned"` | `"restaurant-group"` | `"operator"` | `"development"` | `"chef-partner"` | `"chef-brand"` | `"restaurateur"`
- `model`: operational model — `"chef-restaurateur"` | `"operator"` | `"chef-partner"` | `"chef-brand"` | `"development"` | `"restaurateur"`
- `portfolio`: array of `rest_*` ids
- `notable_alumni`: array of `chef_*` ids

### Relationships (derived from stops)

The network graph is implicit in the stops data:

- **Mentor → Protégé:** `stop.mentor_id` links a junior chef's stop to the senior chef who trained them
- **Peer:** Two chefs held positions at the same restaurant during overlapping years
- **Kitchen Diaspora:** All chefs who have a stop at Restaurant X
- **Chef Tree:** Starting from a mentor, trace all protégés, then their protégés (recursive)

These are computed by `app/src/lib/data.ts`, not stored separately. The stops table IS the graph.

## ID Conventions

| Entity | Prefix | Format | Example |
|--------|--------|--------|---------|
| Chef | `chef_` | `chef_{first}_{last}` | `chef_michael_cimarusti` |
| Restaurant | `rest_` | `rest_{name_slug}` | `rest_providence` |
| Stop | `stop_` | `stop_{NNN}` (sequential) | `stop_001` |
| Group | `group_` | `group_{name_slug}` | `group_sprout_la` |

## Cuisine Tags

Tags describe what a chef cooks or what a restaurant serves. Use lowercase, hyphenated.

**Canonical form:** `californian` (not `california`). Cuisine descriptors only — format-like concepts (`tasting-menu`, `casual`, `fine-dining`) belong in the `format` field on restaurants, though they may also appear as cuisine tags on chefs to describe their cooking style.

## File Structure

```
irdb/
├── ARCHITECTURE.md          # This file
├── data/
│   ├── chefs.json           # 235 chef profiles
│   ├── restaurants.json     # 317 restaurant profiles
│   ├── stops.json           # 532 career stops (the graph edges)
│   ├── groups.json          # 37 restaurant groups and investors
│   ├── chefdb_scraped.json  # Raw ChefDb scrape (source data)
│   ├── intake_queue.json    # Pipeline output — ranked candidates
│   └── intake-*.yaml        # Batch intake files (manual research)
├── app/                     # Next.js frontend
│   └── src/lib/data.ts      # Data loading + relationship queries
└── scripts/
    ├── pipeline.py          # Intake pipeline (ChefDb → ranked queue)
    ├── batch-intake.py      # YAML batch → JSON merger
    └── scrape-chefdb.mjs    # ChefDb scraper (Playwright)
```

Flat JSON files. No database yet. Get the data right first.

## Verification Flywheel

1. **Seed with editorial data** — Scrape ChefDb, JBF, Michelin. Mark everything "unverified."
2. **Invite chefs to claim profiles** — "Your career history is already here. Claim it, correct it, verify it."
3. **Cross-verification** — When Chef A verifies their stop at Restaurant X, and Chef B also verifies a stop at Restaurant X during overlapping dates, both stops gain credibility.
4. **Restaurant accounts** — Restaurant groups can verify all current and past staff in bulk.

The more chefs verify, the more the network solidifies. Verification is the moat.

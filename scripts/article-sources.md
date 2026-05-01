# IRDB Article Extraction Sources

## How it works
1. Feed article URL to WebFetch (or Puppeteer for blocked sites) with extraction prompt
2. LLM extracts: chef name, restaurant, neighborhood, previous restaurants, mentor mentions, cuisine
3. Cross-reference against existing IRDB
4. Add new chefs/connections via `scripts/batch-intake.py`

## Key insight
Every dated list is a **timestamped career record**. "Chef X at Restaurant Y as of March 2026" = a verified stop. The volume play is scraping as many lists as possible. Not just "best new" — every neighborhood list, cuisine list, annual list.

## Extraction prompt template
```
Extract every restaurant and chef mentioned. For each: restaurant name, chef name,
neighborhood, any pedigree/training mentions (where chef previously worked, who they
trained under, "formerly of", "alum of"), cuisine. Return ALL entries.
```

## Accessible via WebFetch (confirmed working)

### Timeout LA (rich pedigree data)
- **Best Restaurants:** https://www.timeout.com/los-angeles/restaurants/best-restaurants-in-los-angeles
- **Best New:** https://www.timeout.com/los-angeles/restaurants/best-new-restaurants-los-angeles
- **Young Chefs:** https://www.timeout.com/los-angeles/restaurants/best-young-chefs
- **Japanese:** https://www.timeout.com/los-angeles/restaurants/best-japanese-restaurants-in-los-angeles
- **Korean:** https://www.timeout.com/los-angeles/restaurants/best-korean-restaurants-in-los-angeles
- **Thai:** https://www.timeout.com/los-angeles/restaurants/best-thai-restaurants-in-los-angeles
- **Tacos:** https://www.timeout.com/los-angeles/restaurants/best-tacos-in-los-angeles
- **Arts District:** https://www.timeout.com/los-angeles/restaurants/best-restaurants-in-the-arts-district
- NOTE: Many Timeout neighborhood URLs 404. Pattern is `/best-restaurants-in-{neighborhood}` but inconsistent.

### Resy
- **Year-defining:** https://blog.resy.com/2025/12/la-restaurants-2025/

### LA Mag (deep individual profiles)
- **Best New:** https://lamag.com/food/best-new-los-angeles-restaurants-winter-2025-2026-wildes-henrietta-lapaba/
- **Coming Attractions:** https://lamag.com/food/best-new-restaurants-los-angeles-coming-attractions-2025/

### Other
- **TheBestRestaurantsGuide — LA Times 101:** https://thebestrestaurantsguide.com/awards/101-la-times (multi-year, JSON-LD)
- **The Infatuation LA — New Openings:** https://www.theinfatuation.com/los-angeles/guides/new-la-restaurants-openings
- **The Infatuation LA — Best New 2025:** https://www.theinfatuation.com/los-angeles/guides/best-new-restaurants-los-angeles-2025
- NOTE: Infatuation rarely includes chef names or pedigree. Low value for lineage extraction.

## Accessible via Puppeteer MCP (blocked by WebFetch)

### Eater LA (UNLOCKED 2026-03-18 via Puppeteer MCP)
- **Heatmap (Best New, monthly):** https://la.eater.com/maps/best-new-restaurants-los-angeles-heatmap
- **Essential 38:** https://la.eater.com/maps/best-los-angeles-restaurants-eater-38-essential
- **South LA:** https://la.eater.com/maps/best-food-restaurants-south-los-angeles
- **Venice:** https://la.eater.com/maps/best-essential-venice-restaurants-los-angeles
- **SFV:** https://la.eater.com/maps/san-fernando-valley-best-restaurants-los-angeles-studio-city-sherman-oaks-encino-northridge-reseda
- **Santa Monica:** https://la.eater.com/maps/best-santa-monica-restaurants-los-angeles
- **Glendale:** https://la.eater.com/maps/best-glendale-california-restaurants
- **Brunch:** https://la.eater.com/maps/best-new-brunch-restaurants-los-angeles
- **Maps index:** https://la.eater.com/maps (discover all current maps)
- NOTE: Eater Heatmap updates monthly. Rich chef data + neighborhood attribution. Puppeteer works even with Chrome open (uses bundled Chromium).

### Bon Appétit (UNLOCKED 2026-03-18 via Puppeteer MCP)
- **Best New 2025:** https://www.bonappetit.com/story/best-new-restaurants-2025
- NOTE: National list, usually 1-3 LA entries per year. Very rich pedigree data per entry.

### Still blocked
- **LA Times** — latimes.com (paywall + bot detection, not tested with Puppeteer yet)

## Signal quality ranking
1. **Eater Heatmap/Essential 38** — Best overall: chef names, neighborhoods, pedigree, monthly timestamps
2. **Timeout Best/Japanese/Korean/Thai** — Rich pedigree ("formerly of", "trained under"), good chef coverage
3. **Resy** — Annual, deep pedigree in write-ups
4. **Bon Appétit** — Deepest per-restaurant profiles but few LA entries
5. **LA Mag** — Good individual profiles
6. **Infatuation** — Rarely names chefs. Low extraction value.

## Scrape history
- **2026-03-18:** Scraped 20+ lists across 5 sites via Puppeteer + WebFetch. Unlocked Eater + Bon Appétit. 28 chefs, 31 restaurants, 39 stops, 5 mentor connections added via batch-intake.
- **2026-03-17:** First article extraction. Fetched Resy/Timeout/Infatuation/LA Mag. 7 chefs, 7 restaurants, 14 stops.

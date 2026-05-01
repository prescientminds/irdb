#!/usr/bin/env node
/**
 * ChefDb.com LA Scraper
 *
 * Scrapes chef and restaurant data from ChefDb for Los Angeles.
 * No dependencies — uses built-in Node.js fetch + regex parsing.
 *
 * Usage:
 *   node scrape-chefdb.mjs                    # Scrape all LA restaurants + staff + chef careers
 *   node scrape-chefdb.mjs --restaurants-only  # Just get restaurant list
 *   node scrape-chefdb.mjs --chef 1045         # Scrape a single chef by ID
 *   node scrape-chefdb.mjs --restaurant 2882   # Scrape a single restaurant by ID
 *
 * Output: ../data/chefdb_scraped.json
 */

import { writeFileSync, readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, '..', 'data');
const OUTPUT_FILE = join(DATA_DIR, 'chefdb_scraped.json');

const BASE_URL = 'https://www.chefdb.com';
const LA_CITY_ID = 19;
const DELAY_MS = 1500; // Be polite — 1.5s between requests

// --- Utilities ---

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchPage(path) {
  const url = `${BASE_URL}${path}`;
  console.log(`  Fetching: ${url}`);
  const res = await fetch(url, {
    headers: {
      'User-Agent': 'IRDB-Research/1.0 (chef database research project)',
      'Accept': 'text/html',
    }
  });
  if (!res.ok) {
    console.warn(`  WARNING: ${res.status} for ${url}`);
    return null;
  }
  await sleep(DELAY_MS);
  return await res.text();
}

// --- Parsers ---

/**
 * Parse LA city page — extract restaurant names, IDs, addresses, closed status
 */
function parseRestaurantList(html) {
  const restaurants = [];
  // ChefDb uses href= with AND without quotes: href=/pl/123/Foo or href="/pl/123/Foo"
  const placePattern = /<a\s+href=["']?\/pl\/(\d+)\/([\w\-\[\]%+.]+)["']?[^>]*>\s*([^<]+)<\/a>/g;
  let match;
  const seen = new Set();

  while ((match = placePattern.exec(html)) !== null) {
    const id = match[1];
    const slug = match[2];
    const name = match[3].trim();

    if (seen.has(id)) continue;
    seen.add(id);

    restaurants.push({
      chefdb_id: `pl_${id}`,
      id_num: parseInt(id),
      name,
      slug,
      url: `/pl/${id}/${slug}`,
    });
  }

  return restaurants;
}

/**
 * Parse restaurant profile page — extract staff list, address, status
 */
function parseRestaurantProfile(html, restaurantId) {
  const profile = {
    chefdb_id: `pl_${restaurantId}`,
    staff: [],
    address: null,
    phone: null,
    website: null,
    awards: [],
    notes: [],
  };

  // Extract address — ChefDb uses href= with or without quotes
  const addrMatch = html.match(/<a\s+href=["']?\/addr\/\d+["']?[^>]*>([^<]+)<\/a>/);
  if (addrMatch) profile.address = addrMatch[1].trim();

  // Extract phone
  const phoneMatch = html.match(/(\(\d{3}\)\s*\d{3}[-.]?\d{4})/);
  if (phoneMatch) profile.phone = phoneMatch[1];

  // Extract staff entries
  // Pattern in staff table: year range, then chef link, then position
  // The table rows contain: Years | Name (link) | Position
  // ChefDb uses <a href="/nm/{id}/{slug}"> for chef links

  const staffPattern = /<tr[^>]*>[\s\S]*?<\/tr>/g;
  const rowMatches = html.match(staffPattern) || [];

  for (const row of rowMatches) {
    // Look for rows with chef links
    const chefLink = row.match(/<a\s+href=["']?\/nm\/(\d+)\/([\w\-%.+]+)["']?[^>]*>\s*([^<]+)<\/a>/);
    if (!chefLink) continue;

    const chefId = chefLink[1];
    const chefSlug = chefLink[2];
    const chefName = chefLink[3].trim();

    // Extract years — look for patterns like "2005-Present", "2010-2015", "2005-", "--"
    const yearMatch = row.match(/((?:19|20)\d{2})\s*[-–]\s*(Present|(?:19|20)\d{2})?/i);
    let startYear = null, endYear = null, isCurrent = false;
    if (yearMatch) {
      startYear = parseInt(yearMatch[1]);
      if (yearMatch[2] && yearMatch[2].toLowerCase() === 'present') {
        isCurrent = true;
      } else if (yearMatch[2]) {
        endYear = parseInt(yearMatch[2]);
      }
    }

    // Extract position — usually in a <td> after the name
    // This is tricky because positions appear as plain text in cells
    // We'll grab all text content and try to identify the position
    const cells = row.match(/<td[^>]*>([\s\S]*?)<\/td>/g) || [];
    let position = null;
    // Position is typically the last cell with text content (not a link)
    for (const cell of cells) {
      const text = cell.replace(/<[^>]+>/g, '').trim();
      // Skip cells that are just years, names we already captured, or empty
      if (!text || text === '--' || text === chefName) continue;
      if (/^(19|20)\d{2}/.test(text)) continue;
      if (text.length > 2 && text.length < 100) {
        position = text;
      }
    }

    profile.staff.push({
      chef_chefdb_id: `nm_${chefId}`,
      chef_id_num: parseInt(chefId),
      chef_name: chefName,
      chef_slug: chefSlug,
      position,
      start_year: startYear,
      end_year: endYear,
      is_current: isCurrent,
    });
  }

  return profile;
}

/**
 * Parse chef profile page — extract career history, education, awards
 */
function parseChefProfile(html, chefId) {
  const profile = {
    chefdb_id: `nm_${chefId}`,
    positions: [],
    education: [],
    awards: [],
    publications: [],
    tags: {},
  };

  // Extract positions (restaurant history)
  // Pattern: year range | restaurant link | city link | position text
  const placeLinks = html.match(/<a\s+href=["']?\/pl\/(\d+)\/([\w\-\[\]%+.]+)["']?[^>]*>\s*([^<]+)<\/a>/g) || [];
  const cityLinks = html.match(/<a\s+href=["']?\/city\/(\d+)\/([\w\-%.+]+)["']?[^>]*>\s*([^<]+)<\/a>/g) || [];

  // Parse table rows for positions
  const rowPattern = /<tr[^>]*>([\s\S]*?)<\/tr>/g;
  let rowMatch;

  while ((rowMatch = rowPattern.exec(html)) !== null) {
    const row = rowMatch[1];

    // Look for restaurant links in this row
    const placeMatch = row.match(/<a\s+href=["']?\/pl\/(\d+)\/([\w\-\[\]%+.]+)["']?[^>]*>\s*([^<]+)<\/a>/);
    if (!placeMatch) continue;

    const restId = placeMatch[1];
    const restSlug = placeMatch[2];
    const restName = placeMatch[3].trim();

    // Extract city
    const cityMatch = row.match(/<a\s+href="\/city\/(\d+)\/([^"]+)"[^>]*>([^<]+)<\/a>/);
    const city = cityMatch ? cityMatch[3].trim() : null;

    // Extract years
    const yearMatch = row.match(/((?:19|20)\d{2})\s*[-–]\s*(Present|(?:19|20)\d{2})?/i);
    let startYear = null, endYear = null, isCurrent = false;
    if (yearMatch) {
      startYear = parseInt(yearMatch[1]);
      if (yearMatch[2] && yearMatch[2].toLowerCase() === 'present') {
        isCurrent = true;
      } else if (yearMatch[2]) {
        endYear = parseInt(yearMatch[2]);
      }
    }

    // Extract position text
    const cells = row.match(/<td[^>]*>([\s\S]*?)<\/td>/g) || [];
    let position = null;
    for (const cell of cells) {
      const text = cell.replace(/<[^>]+>/g, '').trim();
      if (!text || text === '--' || text === restName || text === city) continue;
      if (/^(19|20)\d{2}/.test(text)) continue;
      if (text.length > 2 && text.length < 150 && !text.includes('/pl/') && !text.includes('/city/')) {
        position = text;
      }
    }

    profile.positions.push({
      restaurant_chefdb_id: `pl_${restId}`,
      restaurant_id_num: parseInt(restId),
      restaurant_name: restName,
      restaurant_slug: restSlug,
      city,
      position,
      start_year: startYear,
      end_year: endYear,
      is_current: isCurrent,
    });
  }

  // Extract education — look for school/institution links or text
  const eduSection = html.match(/Education[\s\S]*?(?=<h|Honors|Publications|$)/i);
  if (eduSection) {
    const eduPattern = /<a[^>]*>([^<]+)<\/a>/g;
    let eduMatch;
    while ((eduMatch = eduPattern.exec(eduSection[0])) !== null) {
      profile.education.push(eduMatch[1].trim());
    }
  }

  // Extract awards
  const awardsSection = html.match(/Honors[\s\S]*?(?=<h|Publications|Education|$)/i);
  if (awardsSection) {
    const awardLines = awardsSection[0].match(/>([^<]{10,})</g) || [];
    for (const line of awardLines) {
      const text = line.replace(/^>/, '').trim();
      if (text && !text.includes('Honors') && text.length > 5) {
        profile.awards.push(text);
      }
    }
  }

  // Extract Instagram
  const igMatch = html.match(/instagram\.com\/([a-zA-Z0-9_.]+)/);
  if (igMatch) profile.tags.instagram = igMatch[1];

  // Extract birth info
  const birthMatch = html.match(/Born\s+(?:in\s+)?(\d{4})?/i);
  if (birthMatch && birthMatch[1]) profile.tags.birth_year = parseInt(birthMatch[1]);

  const countryMatch = html.match(/Born[\s\S]*?<a[^>]*>([^<]+)<\/a>/i);
  if (countryMatch) profile.tags.birth_country = countryMatch[1].trim();

  return profile;
}

// --- Main Scraping Logic ---

async function scrapeAllLARestaurants() {
  console.log('=== Scraping ChefDb LA Restaurant List ===\n');
  const allRestaurants = [];

  // LA has ~16 pages of 50 restaurants each
  for (let offset = 0; offset <= 800; offset += 50) {
    console.log(`\nPage ${(offset / 50) + 1} (offset ${offset}):`);
    const html = await fetchPage(`/city/${LA_CITY_ID}/Los-Angeles//${offset}`);
    if (!html) break;

    const restaurants = parseRestaurantList(html);
    if (restaurants.length === 0) break;

    allRestaurants.push(...restaurants);
    console.log(`  Found ${restaurants.length} restaurants (total: ${allRestaurants.length})`);
  }

  return allRestaurants;
}

async function scrapeRestaurantProfile(idNum) {
  const html = await fetchPage(`/pl/${idNum}/profile`);
  if (!html) return null;
  return parseRestaurantProfile(html, idNum);
}

async function scrapeChefProfile(idNum) {
  const html = await fetchPage(`/nm/${idNum}/profile`);
  if (!html) return null;
  return parseChefProfile(html, idNum);
}

async function main() {
  const args = process.argv.slice(2);

  // Load existing data if available
  let data = {
    scrape_date: new Date().toISOString().split('T')[0],
    source: 'chefdb.com',
    la_restaurants: [],
    restaurant_profiles: {},
    chef_profiles: {},
  };

  if (existsSync(OUTPUT_FILE)) {
    try {
      data = JSON.parse(readFileSync(OUTPUT_FILE, 'utf-8'));
      console.log(`Loaded existing data: ${data.la_restaurants.length} restaurants, ${Object.keys(data.chef_profiles).length} chefs\n`);
    } catch (e) {
      console.log('Starting fresh.\n');
    }
  }

  // --- Mode: Single chef ---
  if (args.includes('--chef')) {
    const chefId = parseInt(args[args.indexOf('--chef') + 1]);
    console.log(`Scraping chef ID ${chefId}...`);
    const profile = await scrapeChefProfile(chefId);
    if (profile) {
      data.chef_profiles[profile.chefdb_id] = profile;
      console.log(`  Found ${profile.positions.length} positions`);
    }
    writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2));
    console.log(`\nSaved to ${OUTPUT_FILE}`);
    return;
  }

  // --- Mode: Single restaurant ---
  if (args.includes('--restaurant')) {
    const restId = parseInt(args[args.indexOf('--restaurant') + 1]);
    console.log(`Scraping restaurant ID ${restId}...`);
    const profile = await scrapeRestaurantProfile(restId);
    if (profile) {
      data.restaurant_profiles[profile.chefdb_id] = profile;
      console.log(`  Found ${profile.staff.length} staff members`);
    }
    writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2));
    console.log(`\nSaved to ${OUTPUT_FILE}`);
    return;
  }

  // --- Mode: Restaurants only ---
  if (args.includes('--restaurants-only')) {
    data.la_restaurants = await scrapeAllLARestaurants();
    writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2));
    console.log(`\nSaved ${data.la_restaurants.length} restaurants to ${OUTPUT_FILE}`);
    return;
  }

  // --- Mode: Full scrape ---
  console.log('=== FULL LA SCRAPE ===\n');
  console.log('Step 1: Get all LA restaurant listings...');
  data.la_restaurants = await scrapeAllLARestaurants();
  console.log(`\nFound ${data.la_restaurants.length} total LA restaurants.\n`);

  // Save progress
  writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2));

  console.log('Step 2: Scrape each restaurant profile for staff lists...');
  let restaurantCount = 0;
  for (const rest of data.la_restaurants) {
    const key = `pl_${rest.id_num}`;
    if (data.restaurant_profiles[key]) {
      console.log(`  Skipping ${rest.name} (already scraped)`);
      continue;
    }

    const profile = await scrapeRestaurantProfile(rest.id_num);
    if (profile) {
      data.restaurant_profiles[key] = profile;
      restaurantCount++;
      console.log(`  ${rest.name}: ${profile.staff.length} staff`);

      // Save every 10 restaurants
      if (restaurantCount % 10 === 0) {
        writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2));
        console.log(`  [Saved progress: ${restaurantCount} restaurants]`);
      }
    }
  }
  writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2));

  console.log('\nStep 3: Scrape unique chef profiles...');
  // Collect all unique chef IDs from restaurant staff lists
  const chefIds = new Set();
  for (const profile of Object.values(data.restaurant_profiles)) {
    for (const staff of profile.staff) {
      chefIds.add(staff.chef_id_num);
    }
  }
  console.log(`Found ${chefIds.size} unique chefs across all restaurants.\n`);

  let chefCount = 0;
  for (const chefId of chefIds) {
    const key = `nm_${chefId}`;
    if (data.chef_profiles[key]) continue;

    const profile = await scrapeChefProfile(chefId);
    if (profile) {
      data.chef_profiles[key] = profile;
      chefCount++;
      console.log(`  Chef ${chefId}: ${profile.positions.length} positions`);

      if (chefCount % 20 === 0) {
        writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2));
        console.log(`  [Saved progress: ${chefCount} chefs]`);
      }
    }
  }

  writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2));
  console.log(`\n=== DONE ===`);
  console.log(`Restaurants: ${data.la_restaurants.length}`);
  console.log(`Restaurant profiles: ${Object.keys(data.restaurant_profiles).length}`);
  console.log(`Chef profiles: ${Object.keys(data.chef_profiles).length}`);
  console.log(`Output: ${OUTPUT_FILE}`);
}

main().catch(console.error);

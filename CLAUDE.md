# International Basketball Project - Development Guide

## Project Goal
Track American basketball players across international leagues, with focus on finding players who attended American high schools. Display their current season statistics, game logs, and upcoming games.

## Current Status (January 2026)

### Active Leagues
| League | Players | Data Source | Notes |
|--------|---------|-------------|-------|
| EuroLeague | 109 | EuroLeague API | Best data quality, official API |
| Liga ACB (Spain) | 28 | ACB.com scraping + TheSportsDB | Box scores from acb.com |
| Turkish BSL | 32 | TBLStat.net + TheSportsDB | Uses TBLStat as primary source |

### Pending Leagues (Need Scrapers)
- Lega Basket Serie A (Italy) - legabasket.it
- LNB Pro A (France) - lnb.fr
- Basketball Bundesliga (Germany) - easycredit-bbl.de
- Greek Basket League (ESAKE) - esake.gr
- NBL Australia - nbl.com.au
- CBA China - cbaleague.com

---

## Architecture

### Data Flow
```
1. Scraper (league-specific)
   → Fetches rosters, box scores, schedules from source
   → Saves raw data to scrapers/{league}/output/json/

2. join_data.py (per league)
   → Combines scraped data with TheSportsDB player info
   → Enriches with Wikipedia hometown/college data
   → Produces unified_american_players_latest.json

3. Copy to output/json/
   → {league}_american_players_latest.json (summary for list view)
   → {league}_unified_players_latest.json (full data for detail view)

4. dashboard.py
   → Flask app loads from output/json/
   → Serves web interface with league toggle
```

### Key Files
```
unified/
├── dashboard.py              # Main Flask application
├── positions.py              # Position number-to-name lookup (shared)
├── output/json/              # Data files dashboard reads from
│   ├── euroleague_american_players_latest.json
│   ├── acb_american_players_latest.json
│   └── bsl_american_players_latest.json
└── scrapers/
    ├── euroleague/
    │   ├── euroleague_scraper.py   # Fetches from EuroLeague API
    │   ├── daily_scraper.py        # TheSportsDB + Wikipedia
    │   └── join_data.py            # Combines all sources
    ├── acb/
    │   ├── acb_scraper.py          # Scrapes ACB.com box scores
    │   ├── daily_scraper.py        # TheSportsDB + Wikipedia
    │   └── join_data.py            # Combines all sources
    └── bsl/
        ├── bsl_scraper.py          # Scrapes TBLStat.net
        ├── daily_scraper.py        # TheSportsDB + Wikipedia
        └── join_data.py            # Uses BSL as PRIMARY source
```

---

## Lessons Learned

### 1. Data Source Strategy
- **TheSportsDB** provides player bios (birthplace, height, photos) but limited coverage
- **League-specific scrapers** are more complete for stats and game data
- **Best approach**: Use league scraper as PRIMARY source, enrich with TheSportsDB when available

### 2. Turkish BSL Example (Best Practice)
The BSL scraper finds 32 Americans but TheSportsDB only has 15. Solution:
```python
# In join_data.py - Use BSL data as primary source
bsl_players, bsl_lookup = load_bsl_stats()  # PRIMARY: All 32 players
thesportsdb_data = load_latest_json(...)     # ENRICHMENT: Bio info

for bsl_player in bsl_players:  # Loop through ALL BSL players
    tsdb_player = match_by_name(bsl_player, thesportsdb_lookup)  # Enrich if found
```

### 3. Name Matching
Different sources use different name formats:
- ACB.com: "T. Kalinoski" (abbreviated)
- TheSportsDB: "Tyler Kalinoski" (full)
- Solution: Match by normalized last name
```python
import unicodedata
name_norm = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
name_norm = name_norm.lower().strip()
```

### 4. Position Conversion
Some sources use numbers (1-5), others use names. Use shared positions.py:
```python
from positions import get_position_name
position = get_position_name(player.get('position'))  # Handles 1, "1", "PG", "Point Guard"
```

### 5. File Naming Convention
- Timestamped files: `{prefix}_{YYYYMMDD_HHMMSS}.json` (for history)
- Latest files: `{prefix}_latest.json` (for dashboard)
- Always save both!

---

## Adding a New League

### Step 1: Research Data Sources
1. Find official league website
2. Check for public API (inspect network tab)
3. Identify:
   - Roster/player list endpoint
   - Schedule/results endpoint
   - Box score/statistics endpoint
4. Check if TheSportsDB has the league

### Step 2: Create Scraper Directory
```bash
mkdir -p scrapers/{league_code}/output/json
```

### Step 3: Create League Scraper
Create `{league_code}_scraper.py`:
```python
"""
Scraper for {League Name}
Source: {website}
"""
import requests
from bs4 import BeautifulSoup
import json
import logging
from datetime import datetime

def scrape_rosters():
    """Fetch all team rosters and identify American players."""
    pass

def scrape_schedule():
    """Fetch season schedule with results."""
    pass

def scrape_boxscores():
    """Fetch individual game box scores for American players."""
    pass

def main():
    # Run all scrapers
    # Save to output/json/
    pass
```

### Step 4: Create daily_scraper.py (TheSportsDB)
Copy from existing league, update:
- League ID in TheSportsDB
- Team name mappings

### Step 5: Create join_data.py
Use BSL pattern (league data as primary source):
```python
# 1. Load league scraper data as PRIMARY
league_players = load_league_stats()

# 2. Load TheSportsDB for enrichment
thesportsdb_lookup = build_lookup(load_thesportsdb())

# 3. Loop through league players, enrich with TheSportsDB
for player in league_players:
    tsdb = match_player(player, thesportsdb_lookup)
    unified = build_unified_record(player, tsdb)
```

### Step 6: Update dashboard.py
Add league to LEAGUES dict:
```python
LEAGUES = {
    # ...existing...
    'lba': {
        'name': 'Lega Basket Serie A',
        'country': 'Italy',
        'color': '#009246',
        'data_file': 'lba_american_players_latest.json',
    },
}
```

### Step 7: Test Locally
```bash
cd scrapers/{league_code}
python {league_code}_scraper.py
python daily_scraper.py  # if using TheSportsDB
python join_data.py

# Copy to dashboard output
cp output/json/unified_american_players_latest.json ../../output/json/{league_code}_american_players_latest.json
cp output/json/unified_american_players_latest.json ../../output/json/{league_code}_unified_players_latest.json

# Test dashboard
cd ../..
python dashboard.py
```

### Step 8: Commit and Deploy
```bash
git add .
git commit -m "Add {League Name} scraper and data"
git push origin master
# Render auto-deploys
```

---

## Data Schema

### Unified Player Record
```json
{
  "code": "12345678",           // Unique ID (TheSportsDB or league ID)
  "name": "John Smith",
  "team": "Team Name",
  "team_code": "TEAM",
  "position": "Point Guard",    // Full name, not number
  "jersey": "23",
  "height_cm": 195,
  "height_feet": 6,
  "height_inches": 5,
  "weight": "210 lb",
  "birth_date": "1995-08-03",   // YYYY-MM-DD format
  "nationality": "United States",
  "birth_location": "Chicago, Illinois",
  "hometown_city": "Chicago",
  "hometown_state": "Illinois",
  "hometown": "Chicago, Illinois",
  "college": "Duke",
  "high_school": "Whitney Young",
  "headshot_url": "https://...",
  "games_played": 15,
  "ppg": 12.5,
  "rpg": 4.2,
  "apg": 3.1,
  "spg": 1.0,
  "game_log": [
    {
      "date": "2026-01-25",
      "opponent": "Other Team",
      "home_away": "Home",
      "minutes": "28:30",
      "points": 18,
      "rebounds": 5,
      "assists": 4
    }
  ],
  "past_games": [...],          // Team's past games
  "upcoming_games": [...],      // Team's upcoming games
  "season": "2025-26",
  "league": "League Name"
}
```

---

## Common Issues & Solutions

### Issue: Players showing 0 games
**Cause**: Name matching failed between league data and TheSportsDB
**Solution**: Check name normalization, try matching by last name only

### Issue: "Team None" in output
**Cause**: Using wrong data source as primary (e.g., box scores without roster context)
**Solution**: Ensure roster data includes team assignments

### Issue: Missing recent games
**Cause**: Scraper not running or API rate limited
**Solution**: Check scraper logs, add delays between requests

### Issue: Render deploy not updating
**Cause**: Files not committed or webhook not triggered
**Solution**:
```bash
git add output/json/*.json
git commit -m "Update data"
git push
# Or trigger manually via Render API
```

---

## Deployment

### Render Configuration
- Service: international-basketball-unified
- URL: https://international-basketball-unified.onrender.com
- Auto-deploy: Enabled on push to master
- Build: `pip install -r requirements.txt`
- Start: `gunicorn --bind 0.0.0.0:5000 --timeout 120 dashboard:app`

### Manual Deploy Trigger
```python
# Via Render MCP tool
mcp__render__update_environment_variables(
    serviceId="srv-...",
    envVars=[{"key": "DEPLOY_TRIGGER", "value": "timestamp"}]
)
```

---

## GitHub Actions (Daily Scraping)
File: `.github/workflows/daily-scrape.yml`
- Runs daily at midnight UTC
- Executes all league scrapers
- Commits and pushes updated data
- Render auto-deploys on push

---

## API Rate Limiting

| Source | Limit | Recommendation |
|--------|-------|----------------|
| EuroLeague API | Unknown | 0.5s delay between requests |
| ACB.com | ~100/min | 1s delay between requests |
| TBLStat.net | ~60/min | 1s delay between requests |
| TheSportsDB | 100/day (free) | Cache aggressively |
| Wikipedia | Generous | 0.5s delay, respect robots.txt |

---

## Next Steps (Priority Order)

1. **Italian LBA** - Large league, many Americans, good data at legabasket.it
2. **French LNB** - Strong league, lnb.fr has good data
3. **German BBL** - Growing destination, easycredit-bbl.de
4. **Greek ESAKE** - Traditional destination, esake.gr
5. **Australian NBL** - English-language, easier to scrape
6. **Chinese CBA** - Fewer Americans recently, cbaleague.com

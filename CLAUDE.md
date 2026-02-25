# International Basketball Project - Development Guide

## Project Goal
Track American basketball players across international leagues, with focus on finding players who attended American high schools. Display their current season statistics, game logs, and upcoming games.

## Current Status (February 2026)

### Active Leagues
| League | Players | Data Source | Notes |
|--------|---------|-------------|-------|
| EuroLeague | 109 | EuroLeague API | Best data quality, official API |
| Liga ACB (Spain) | 28 | ACB.com scraping + TheSportsDB | Box scores from acb.com |
| Turkish BSL | 32 | TBLStat.net + TheSportsDB | Uses TBLStat as primary source |
| Lega Basket Serie A (Italy) | 43 | legabasket.it | Uses embedded JSON from Next.js |
| LNB Pro A (France) | 17 | Atrium Sports API + TheSportsDB | Box scores via lnb.fr API, hometown via Wikipedia |
| Greek Basket League (ESAKE) | 17 | esake.gr scraping + TheSportsDB | Greek name matching, hometown via Wikipedia |
| Basketball Bundesliga (Germany) | ~20 | TheSportsDB + Wikipedia | Hometown/college via Wikipedia |

### Pending Leagues (Need Scrapers)
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
├── positions.py              # Position lookup - NBA convention (shared by ACB, BSL, LBA)
├── requirements.txt          # Includes pytest>=7.0.0
├── output/json/              # Data files dashboard reads from
│   ├── euroleague_american_players_latest.json
│   ├── acb_american_players_latest.json
│   └── bsl_american_players_latest.json
├── tests/
│   ├── test_positions.py     # Position mapping unit tests (20 tests)
│   └── test_data_quality.py  # Scraped data validation (skips without data)
└── scrapers/
    ├── euroleague/
    │   ├── daily_scraper.py        # EuroLeague API (prefers positionName over integer)
    │   ├── positions.py            # EuroLeague 3-category (1=Guard, 2=Forward, 3=Center)
    │   └── join_data.py            # Combines all sources
    ├── acb/
    │   ├── acb_scraper.py          # Scrapes ACB.com box scores
    │   ├── daily_scraper.py        # TheSportsDB + Wikipedia
    │   └── join_data.py            # Combines all sources
    ├── bsl/
    │   ├── bsl_scraper.py          # Scrapes TBLStat.net
    │   ├── daily_scraper.py        # TheSportsDB + Wikipedia
    │   └── join_data.py            # Uses BSL as PRIMARY source
    └── lba/
        ├── lba_scraper.py          # Scrapes legabasket.it embedded JSON
        ├── daily_scraper.py        # TheSportsDB + Wikipedia
        └── join_data.py            # Uses LBA scraper as PRIMARY source
```

---

## CRITICAL: Requirements for Every New League

**BEFORE MARKING A LEAGUE AS COMPLETE**, verify it has ALL THREE:

1. **Player Roster with Nationality**
   - List of all American players in the league
   - Team assignments
   - Basic bio info (position, height, etc.)

2. **Box Score Stats (PER GAME)**
   - Points, rebounds, assists per game
   - Game-by-game log for each player
   - Calculate season averages from game logs

3. **Complete Schedule (PAST AND FUTURE)**
   - All past games with scores
   - All upcoming games with dates
   - Must show on player detail pages

**Common Mistake**: Using TheSportsDB alone - it provides rosters but NO box scores and LIMITED schedule. Always find a secondary source for stats.

| League | Stats Source | Schedule Source |
|--------|-------------|-----------------|
| EuroLeague | EuroLeague API | EuroLeague API |
| Liga ACB | ACB.com box scores | ACB.com |
| Turkish BSL | TBLStat.net | TBLStat.net |
| Italian LBA | legabasket.it embedded JSON | legabasket.it |

---

## Lessons Learned

### 1. Data Source Strategy
- **TheSportsDB** provides player bios (birthplace, height, photos) but limited coverage
- **League-specific scrapers** are more complete for stats and game data
- **Best approach**: Use league scraper as PRIMARY source, enrich with TheSportsDB when available

### 2. Italian LBA Example (Next.js Embedded JSON)
legabasket.it uses Next.js with embedded JSON data in `__NEXT_DATA__` script tags:
```python
# In lba_scraper.py
from bs4 import BeautifulSoup
import json

soup = BeautifulSoup(response.text, 'html.parser')
script = soup.find('script', id='__NEXT_DATA__')
data = json.loads(script.string)
game = data['props']['pageProps']['game']

# Player stats are in game['scores']['ht']['rows'] (home team)
# and game['scores']['vt']['rows'] (visitor team)
for player in game['scores']['ht']['rows']:
    points = player.get('pun', 0)  # Italian abbreviations!
    rebounds = player.get('rimbalzi_t', 0)
    assists = player.get('ass', 0)
```

Key insight: Fetch games by ID range (e.g., 25009-25300) rather than trying to navigate the website.

### 3. Turkish BSL Example (Best Practice)
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
**IMPORTANT**: Position integer mappings differ by league!

- **Root `positions.py`**: NBA 5-position convention (1=PG, 2=SG, 3=SF, 4=PF, 5=C)
  - Used by ACB, BSL, LBA (via their local copies)
- **`scrapers/euroleague/positions.py`**: EuroLeague 3-category system (1=Guard, 2=Forward, 3=Center)
  - EuroLeague API returns integers 1-3, NOT 1-5
  - `daily_scraper.py` prefers `positionName` string from API over integer `position`
- **LNB, ESAKE, BBL**: Don't use positions.py at all (raw strings pass through from TheSportsDB/scrape)

```python
from positions import get_position_name
position = get_position_name(player.get('position'))  # Handles 1, "1", "PG", "Point Guard"
```

**Never assume all leagues use the same integer-to-position mapping.** Always check the API docs for the league's position system before adding integer mappings.

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
  "position": "Guard",           // Full name, not number (EuroLeague: Guard/Forward/Center)
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
- Runs daily at 6 AM UTC + manual trigger (workflow_dispatch)
- **`test` job runs first** (`pytest tests/test_positions.py -v`) — gates all scrapers
- All 7 scraper jobs have `needs: [test]` so bad mappings fail fast
- Commits and pushes updated data
- Render auto-deploys on push (but may need manual API trigger)

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

## Completed Fixes

### EuroLeague Position Mapping (Feb 2026, PR #1)
- **Problem**: EuroLeague API returns position integers 1-3 (Guard/Forward/Center), but positions.py assumed NBA's 1-5 convention, causing ~100 players to have wrong positions
- **Fix**: `daily_scraper.py` now prefers `positionName` string; `scrapers/euroleague/positions.py` maps 1→Guard, 2→Forward, 3→Center
- **Verification**: All 103 EuroLeague players show Guard/Forward/Center (zero NBA-specific positions)

## Next Steps (Priority Order)

1. **Australian NBL** - nbl.com.au, English-language, easier to scrape
2. **Chinese CBA** - cbaleague.com, fewer Americans recently

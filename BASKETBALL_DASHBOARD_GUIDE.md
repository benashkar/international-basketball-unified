# International Basketball Dashboard - Implementation Guide

A comprehensive guide for building web dashboards that track American players in international basketball leagues. This template was developed for Liga ACB (Spain) and Turkish BSL, and can be adapted for any league.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Directory Structure](#directory-structure)
4. [Core Components](#core-components)
5. [Data Sources](#data-sources)
6. [Step-by-Step Implementation](#step-by-step-implementation)
7. [Deployment](#deployment)
8. [Maintenance](#maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Project Overview

### What This System Does

- Scrapes player rosters from league websites to identify American players
- Fetches box score statistics from official league sources
- Enriches player data with hometown/college info from Wikipedia
- Combines all data into unified player records
- Serves a Flask-based dashboard with player profiles and game logs
- Auto-deploys via GitHub Actions and Render

### Live Examples

- Liga ACB: https://liga-acb.onrender.com
- Turkish BSL: https://turkish-bsl.onrender.com
- EuroLeague: https://euroleague-basketball.onrender.com

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  League Website │     │   TheSportsDB   │     │    Wikipedia    │
│   (Box Scores)  │     │  (Team/Player)  │     │   (Hometowns)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         SCRAPERS                                 │
│  • league_scraper.py (box scores, schedules)                    │
│  • daily_scraper.py (TheSportsDB teams/players)                 │
│  • wikipedia_scraper.py (hometowns, colleges)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      JSON DATA FILES                             │
│  output/json/                                                    │
│  • american_players_*.json                                       │
│  • league_boxscores_*.json                                       │
│  • league_schedule_*.json                                        │
│  • american_hometowns_found_*.json                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       JOIN_DATA.PY                               │
│  Combines all sources into unified_american_players_latest.json │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DASHBOARD.PY                               │
│  Flask app serving player list and detail pages                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RENDER DEPLOYMENT                           │
│  Docker container auto-deployed on git push                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
league_name/
├── .github/
│   └── workflows/
│       └── daily_scrape.yml      # GitHub Actions for daily updates
├── output/
│   └── json/
│       ├── *_latest.json         # Current data (used by dashboard)
│       └── *_YYYYMMDD_*.json     # Timestamped backups
├── acb_scraper.py                # League-specific box score scraper
├── daily_scraper.py              # TheSportsDB API scraper
├── wikipedia_scraper.py          # Hometown/college scraper
├── join_data.py                  # Data combination logic
├── dashboard.py                  # Flask web application
├── Dockerfile                    # Container configuration
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```

---

## Core Components

### 1. League Scraper (`acb_scraper.py` / `bsl_scraper.py`)

Scrapes the official league website for:
- Team rosters with player nationalities
- Game schedules with dates and scores
- Box scores with individual player statistics

**Key Functions:**
```python
def fetch_schedule():
    """Get all games for the season with dates, teams, scores."""

def fetch_box_score(match_id):
    """Get detailed stats for a specific game."""

def identify_american_players(rosters):
    """Filter players by USA nationality."""
```

**Statistics to Extract:**
- Points, rebounds (offensive/defensive), assists
- Field goals: 2PT made/attempted, 3PT made/attempted
- Free throws: made/attempted
- Steals, blocks, turnovers, fouls
- Minutes played

**Date Format Handling:**
European leagues often use DD/MM/YYYY format. Convert to YYYY-MM-DD:
```python
def parse_euro_date(date_str):
    """Convert European date DD/MM/YYYY to YYYY-MM-DD format."""
    import re
    match = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})', date_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return None
```

### 2. TheSportsDB Scraper (`daily_scraper.py`)

Uses the free TheSportsDB API to get:
- League teams with logos
- Player profiles with headshots
- Basic biographical info

**API Endpoints:**
```
# Get all teams in a league
https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=Spanish%20Liga%20ACB

# Get players on a team
https://www.thesportsdb.com/api/v1/json/3/searchplayers.php?t=Real%20Madrid%20Baloncesto
```

### 2b. BSL Stats Scraper (`bsl_scraper.py`) - Turkish BSL Only

Scrapes player statistics from TBLStat.net (since tbf.org.tr blocks requests):

```python
# Key configuration
SEASON_CODE = '2526'  # TBLStat uses YYXX format
BASE_URL = 'https://bsl.tblstat.net'

# Known American players for matching
KNOWN_AMERICANS = [
    'anthony brown', 'bonzie colson', 'devon hall', 'pj dozier',
    'jalen lecque', 'jonah mathews', 'jordan crawford', ...
]

def get_all_players():
    """Fetch player list from /players/2526, returns ~267 players"""

def get_player_stats(player_id, player_name):
    """Fetch season stats from /player/{id}"""
    # Returns: team, games, minutes, ppg, rpg, apg, spg, efficiency,
    #          ft_pct, fg2_pct, fg3_pct

def is_likely_american(player_name):
    """Match against known Americans list by last name"""
```

**Output:** `bsl_american_stats_latest.json`

### 3. Wikipedia Scraper (`wikipedia_scraper.py`)

Enriches player data with:
- Hometown (city, state)
- College attended
- High school

Uses Wikipedia infobox parsing to extract structured data.

### 4. Data Joiner (`join_data.py`)

Combines all data sources into unified player records:

```python
unified = {
    # Basic info (TheSportsDB)
    'code': player_id,
    'name': 'Darius Thompson',
    'team': 'Valencia Basket',
    'position': 'Point Guard',
    'headshot_url': '...',

    # Physical (TheSportsDB)
    'height_cm': 188,
    'height_feet': 6,
    'height_inches': 2,

    # Personal (Wikipedia)
    'hometown': 'Murfreesboro, Tennessee',
    'college': 'Western Kentucky',

    # Stats (League scraper)
    'games_played': 15,
    'ppg': 9.4,
    'rpg': 2.8,
    'apg': 4.1,
    'game_log': [
        {
            'date': '2025-10-05',
            'opponent': 'Barça',
            'points': 16,
            'rebounds': 5,
            'fg2_made': 2, 'fg2_attempted': 4,
            'fg3_made': 3, 'fg3_attempted': 3,
            'ft_made': 3, 'ft_attempted': 3,
        },
        # ... more games
    ],

    # Schedule
    'upcoming_games': [...],
    'past_games': [...],
}
```

**Team Name Normalization:**
League websites often have garbled or abbreviated team names. Create a mapping:
```python
TEAM_MAPPING = {
    'unicaja': 'Baloncesto Málaga',
    'surne bilbao': 'Bilbao Basket',
    'baskonia': 'Baskonia',
    'real madrid': 'Real Madrid Baloncesto',
    # ... etc
}
```

### 5. Dashboard (`dashboard.py`)

Flask application with:
- Player list page with filtering/sorting
- Player detail pages with stats and game logs
- Responsive CSS styling

**Key Templates:**
```python
INDEX_TEMPLATE = """
{% for player in players %}
<div class="player-card">
    <img src="{{ player.headshot_url }}">
    <h3>{{ player.name }}</h3>
    <p>{{ player.team }} | {{ player.position }}</p>
    <p>{{ player.ppg }} PPG | {{ player.rpg }} RPG</p>
</div>
{% endfor %}
"""

PLAYER_TEMPLATE = """
<h1>{{ player.name }}</h1>
<table class="game-log">
    {% for game in player.game_log %}
    <tr>
        <td>{{ game.date }}</td>
        <td>{{ game.opponent }}</td>
        <td>{{ game.points }}</td>
        <td>{{ game.rebounds }}</td>
        <td>{{ (game.fg2_made or 0) + (game.fg3_made or 0) }}-{{ (game.fg2_attempted or 0) + (game.fg3_attempted or 0) }}</td>
        <td>{{ game.fg3_made }}-{{ game.fg3_attempted }}</td>
        <td>{{ game.ft_made }}-{{ game.ft_attempted }}</td>
    </tr>
    {% endfor %}
</table>
"""
```

---

## Data Sources

### Primary Sources by League

| League | Box Scores | Schedule | Teams/Players |
|--------|------------|----------|---------------|
| Liga ACB | acb.com | acb.com | TheSportsDB |
| Turkish BSL | TBLStat.net | TBLStat.net | TheSportsDB |
| EuroLeague | euroleaguebasketball.net API | API | API |
| VTB United | vtb-league.com | vtb-league.com | TheSportsDB |

### TBLStat.net (Turkish BSL Stats)

TBLStat.net provides comprehensive Turkish Basketball Super League statistics:
- **Base URL:** `https://bsl.tblstat.net`
- **Players list:** `/players/2526` (season code YYXX format)
- **Player detail:** `/player/{id}` (e.g., `/player/3065` for Bonzie Colson)

**URL Patterns:**
```
Players index: https://bsl.tblstat.net/players/2526
Player stats:  https://bsl.tblstat.net/player/{player_id}
Teams:         https://bsl.tblstat.net/teams/2526
Games:         https://bsl.tblstat.net/games/2526
```

**Stats columns (Turkish → English):**
| Turkish | English | Description |
|---------|---------|-------------|
| Maç | Games | Games played |
| Dk | Minutes | Minutes per game |
| Sy | Points | Points per game (Sayı) |
| Rib | Rebounds | Rebounds per game |
| Ast | Assists | Assists per game |
| TÇ | Steals | Steals per game (Top Çalma) |
| TK | Turnovers | Turnovers per game (Top Kaybı) |
| VP | Efficiency | Efficiency rating (Val Puan) |
| SA | FT% | Free throw percentage |
| 2Sy | 2P% | 2-point field goal percentage |
| 3Sy | 3P% | 3-point field goal percentage |

### TheSportsDB League IDs

```python
LEAGUE_IDS = {
    'Liga ACB': 4413,
    'Turkish BSL': 4431,
    'EuroLeague': 4401,
    'VTB United League': 4603,
    'Greek Basket League': 4415,
    'Italian Lega Basket': 4414,
}
```

---

## Step-by-Step Implementation

### Step 1: Set Up Project Structure

```bash
mkdir new_league
cd new_league
mkdir -p output/json .github/workflows
```

### Step 2: Create Requirements File

```txt
# requirements.txt
flask==3.0.0
gunicorn==21.2.0
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
```

### Step 3: Implement League Scraper

1. Inspect the league website to find:
   - Schedule/results page URL
   - Box score URL pattern
   - Player nationality indicators

2. Create scraper with BeautifulSoup:
```python
import requests
from bs4 import BeautifulSoup

def fetch_box_score(match_id):
    url = f"https://league-site.com/game/{match_id}/boxscore"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find stats table and parse rows
    stats_table = soup.find('table', class_='box-score')
    # ... extract player stats
```

### Step 4: Create TheSportsDB Scraper

Copy from existing project and update:
- League name for API queries
- Team name mappings

### Step 5: Create Join Data Script

Copy `join_data.py` and customize:
- Team name normalization mapping
- Field name mappings (different leagues use different column headers)

### Step 6: Create Dashboard

Copy `dashboard.py` and update:
- League name in templates
- Color scheme if desired
- Any league-specific display logic

### Step 7: Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./
COPY output/ ./output/

# Use committed JSON data (don't re-scrape during build)
RUN echo "=== Using committed JSON data ===" && \
    ls -la /app/output/json/*_latest.json 2>/dev/null || echo "No data files"

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "dashboard:app"]
```

### Step 8: Create GitHub Actions Workflow

```yaml
# .github/workflows/daily_scrape.yml
name: Daily Data Scrape

on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC daily
  workflow_dispatch:      # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: pip install -r requirements.txt

    - name: Run scrapers
      run: |
        python daily_scraper.py
        python league_scraper.py
        python wikipedia_scraper.py
        python join_data.py

    - name: Commit and push
      run: |
        git config user.name "GitHub Actions"
        git config user.email "actions@github.com"
        git add output/json/*_latest.json
        git diff --staged --quiet || git commit -m "Daily data update"
        git push
```

---

## Deployment

### Render Setup

1. Create account at https://render.com
2. Connect GitHub repository
3. Create new Web Service:
   - **Environment:** Docker
   - **Branch:** master
   - **Auto-Deploy:** Yes
   - **Plan:** Starter ($7/month) or Free

### Environment Variables

Set in Render dashboard if needed:
```
FLASK_ENV=production
```

### Triggering Deploys

Deploys happen automatically on git push. To manually trigger with cache clear:

```bash
curl -X POST "https://api.render.com/v1/services/{SERVICE_ID}/deploys" \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"clearCache": "clear"}'
```

---

## Maintenance

### Daily Operations

GitHub Actions handles daily updates automatically:
1. Scrapes latest box scores
2. Updates player statistics
3. Commits changes to repository
4. Render auto-deploys new version

### Manual Updates

To manually refresh data:
```bash
cd league_directory
python daily_scraper.py      # Get latest from TheSportsDB
python league_scraper.py     # Get box scores from league site
python join_data.py          # Combine all data
git add output/json/*_latest.json
git commit -m "Manual data update"
git push
```

### Monitoring

- Check Render dashboard for deploy status
- Review GitHub Actions logs for scraper issues
- Monitor league website for structure changes

---

## Troubleshooting

### Common Issues

#### 1. Dates showing as null/N/A

**Cause:** Schedule data doesn't have dates, or date format mismatch.

**Solution:**
- Check if dates are in box scores instead of schedule
- Use `load_boxscore_dates()` function to get dates from box scores
- Handle European date format (DD/MM/YYYY)

#### 2. Stats showing as 0-0

**Cause:** Field name mismatch between scraper and dashboard template.

**Solution:**
- Check scraper output for actual field names (fg2_made vs fg_made)
- Update dashboard template to match

#### 3. Team names not matching

**Cause:** League website has different team names than TheSportsDB.

**Solution:**
- Create `TEAM_MAPPING` dictionary in join_data.py
- Use `normalize_team_name()` function

#### 4. Docker build using stale data

**Cause:** Docker layer caching serving old JSON files.

**Solution:**
- Deploy with `clearCache: "clear"`
- Or update Dockerfile to not run scrapers during build

#### 5. Player not found in stats

**Cause:** Name matching issue between data sources.

**Solution:**
- Normalize names (remove accents, lowercase)
- Match on last name only
- Add manual overrides for edge cases

#### 6. Calendar page returns all games (ACB bug - Fixed Feb 2026)

**Cause:** Some league websites (like ACB) return ALL games on a single calendar page, regardless of which jornada/round URL you request. If your scraper iterates through round URLs expecting only that round's games, you'll get duplicates and incorrect round assignments.

**Symptoms:**
- All games categorized as "Round 1"
- Missing recent games despite scraper running
- Dates showing as `null`

**Solution:**
```python
# WRONG: Iterating through each jornada URL
for jornada in range(1, 35):
    url = f"{BASE_URL}/calendario/jornada_numero/{jornada}"
    # This returns ALL games, not just this jornada!

# CORRECT: Fetch once and parse by section
url = f"{BASE_URL}/calendario/jornada_numero/1"  # Any jornada works
soup = BeautifulSoup(fetch_page(url), 'html.parser')

# Find section containers (one per jornada)
listados = soup.find_all('div', class_='listado_partidos')

for i, listado in enumerate(listados):
    jornada = i + 1  # Use index as jornada number
    games = listado.find_all('article', class_='partido')
    # Parse games within this specific section
```

**Key lesson:** Always verify the actual HTML structure of calendar pages. Many sites load all data at once for JavaScript rendering.

### Debug Commands

```bash
# Check unified data for a player
python -c "
import json
data = json.load(open('output/json/unified_american_players_latest.json'))
player = [p for p in data['players'] if 'thompson' in p['name'].lower()][0]
print(f\"Name: {player['name']}\")
print(f\"Games: {len(player.get('game_log', []))}\")
for g in player.get('game_log', [])[:3]:
    print(f\"  {g.get('date')} vs {g.get('opponent')} - {g.get('points')} pts\")
"

# Test dashboard locally
python dashboard.py
# Visit http://localhost:5000
```

---

## Existing Implementations

### Liga ACB (Spain)
- Repository: https://github.com/benashkar/international-basketball-unified
- Live: https://international-basketball-unified.onrender.com (league: acb)
- Scraper: `acb_scraper.py` (BeautifulSoup)

**ACB Scraper Details:**
The ACB website (acb.com) has a calendar page that loads ALL jornadas at once. Key implementation:

```python
# acb_scraper.py key functions:
def fetch_season_matches():
    """
    Fetches single calendar page containing all 34 jornadas.
    Parses div.listado_partidos sections by index (section 0 = Jornada 1).
    """

def parse_jornada_date(header_text):
    """Parses Spanish dates like '31 Ene 2026' from jornada headers."""

def fetch_box_score(match_id):
    """Fetches detailed stats from /partido/estadisticas/id/{match_id}"""
```

**HTML Structure (as of Feb 2026):**
- Team names: `div.equipo.local > span.nombre_largo` / `div.equipo.visitante > span.nombre_largo`
- Scores: `div.resultado.local > a` / `div.resultado.visitante > a`
- Stats link: `a[href*="/partido/estadisticas/id/"]`

**Stats columns:** MIN, PTS, REB (D+O format), AST, ROB (steals), TAP (blocks), T2/T3/T1 (FG made/attempted)

### Turkish BSL
- Repository: https://github.com/benashkar/turkish_bsl
- Live: https://turkish-bsl-prod.onrender.com
- Stats Scraper: `bsl_scraper.py` (BeautifulSoup from TBLStat.net)
- Schedule Scraper: `bsl_scraper.py` (TBLStat.net) + `daily_scraper.py` (TheSportsDB for teams)

**BSL Scraper Details:**
The official TBF website (tbf.org.tr) blocks automated requests with 403 errors. Instead, we use TBLStat.net which provides comprehensive player statistics and game schedules.

```python
# bsl_scraper.py key functions:
def get_all_players():
    """Fetches player list from TBLStat.net /players/2526"""

def get_player_stats(player_id):
    """Fetches individual player stats from /player/{id}"""

def fetch_schedule():
    """Fetches all games from /games/2526, including box scores"""

def fetch_game_details(game_id):
    """Fetches box score from /game/{id} with player stats"""

def build_player_game_logs(games, american_names):
    """Builds game-by-game logs for American players from box scores"""

def parse_turkish_date(date_str):
    """Converts Turkish dates (28 Eylül 2025) to YYYY-MM-DD format"""
```

**Outputs:**
1. `bsl_american_stats_latest.json` with:
   - 32 American players identified
   - Season averages: PPG, RPG, APG, SPG, efficiency
   - Shooting percentages: FT%, 2P%, 3P%
   - game_log: Array of individual game stats

2. `bsl_schedule_latest.json` with:
   - 144 total games (16 teams × 9 rounds each way)
   - Box scores for played games
   - Upcoming games for schedule display

**Team Name Mapping (join_data.py):**
TheSportsDB and TBLStat use different team names. The mapping is required:
```python
TEAM_NAME_MAP = {
    'Anadolu Efes SK': 'Anadolu Efes',
    'Bahçeşehir Koleji SK': 'Bahçeşehir Koleji',
    'Besiktas Basketbol': 'Beşiktaş GAİN',
    'Büyükçekmece Basketbol': 'ONVO Büyükçekmece',
    'Fenerbahçe Basketbol': 'Fenerbahçe Beko',
}
```

### EuroLeague
- Repository: https://github.com/benashkar/international-basketball-unified
- Live: https://international-basketball-unified.onrender.com (league: euroleague)
- Scraper: Uses official EuroLeague API (JSON endpoints via `euroleague-api` package)

### Italian Lega Basket Serie A (LBA)
- Repository: https://github.com/benashkar/international-basketball-unified
- Live: https://international-basketball-unified.onrender.com (league: lba)
- Scraper: `lba_scraper.py` (BeautifulSoup from legabasket.it)

**LBA Scraper Details:**
The official Lega Basket website (legabasket.it) provides player statistics and box scores.

```python
# lba_scraper.py key functions:
def get_all_players():
    """Fetches player list from /campionato/calendario"""

def get_player_stats(player_id):
    """Fetches season stats from player profile page"""

def fetch_schedule():
    """Fetches game schedule with results"""

def fetch_box_score(game_id):
    """Fetches detailed box score for a game"""
```

**URL Patterns:**
```
Schedule: https://www.legabasket.it/campionato/calendario
Player:   https://www.legabasket.it/player/{player_id}
Game:     https://www.legabasket.it/game/{game_id}
```

**Current stats (Feb 2026):** 43 American players tracked

---

## Unified Dashboard

The unified dashboard at https://github.com/benashkar/international-basketball-unified consolidates all leagues:

**Supported Leagues:**
| League | Code | Country | Status |
|--------|------|---------|--------|
| EuroLeague | euroleague | Europe | ✅ Active |
| Liga ACB | acb | Spain | ✅ Active |
| Turkish BSL | bsl | Turkey | ✅ Active |
| Lega Basket | lba | Italy | ✅ Active |
| Greek League | esake | Greece | 🔄 Planned |
| BBL | bbl | Germany | 🔄 Planned |
| LNB Pro A | lnb | France | 🔄 Planned |

**Adding a New League:**
1. Create scraper in `scrapers/{league_code}/`
2. Add league config to `dashboard.py` LEAGUES dict
3. Add scraper job to `.github/workflows/daily-scrape.yml`
4. Run initial scrape and commit data files

---

## League Verification Script

After adding a new league, run the verification script to confirm all data is properly collected:

```bash
cd unified
python scripts/verify_leagues.py
```

**What it checks:**
- American players by league (count, teams)
- Players with season statistics (PPG/RPG/APG)
- Past and upcoming game counts
- Box scores with detailed player stats
- Team/schedule data availability
- Data quality issues and warnings

**Sample output:**
```
====================================================================================================
  SECTION 1: AMERICAN PLAYERS BY LEAGUE
====================================================================================================
----------------------------------------------------------------------------------------------------
League                  Players      Teams      w/Stats   Past Games     Upcoming    Recent 7d
----------------------------------------------------------------------------------------------------
EuroLeague                  109         17           73            0            0            0
Spanish ACB                  29         14           17          452            0            0
Italian LBA                  43         14           19           78           36            3
Turkish BSL                  32         13           32          544           32            3
French LNB                   17         10            0            0            0            0
Greek ESAKE                  17          9            0            0            0            0
----------------------------------------------------------------------------------------------------
TOTAL                       247         77          141         1074           68            6
```

**Adding a new league to the verification script:**

Edit `scripts/verify_leagues.py` and add your league to the `LEAGUES` dictionary:

```python
LEAGUES = {
    # ... existing leagues ...
    'New League': {
        'unified_players': 'output/json/newleague_unified_players_latest.json',
        'box_scores': 'output/json/newleague_boxscores_latest.json',  # or None
        'schedule': 'output/json/newleague_schedule_latest.json',      # or None
    },
}
```

---

## Quick Start Checklist

- [ ] Create project directory structure
- [ ] Identify league website box score URLs
- [ ] Implement league scraper with nationality detection
- [ ] Copy and customize TheSportsDB scraper
- [ ] Copy and customize join_data.py with team mappings
- [ ] Copy and customize dashboard.py
- [ ] Create Dockerfile
- [ ] Create requirements.txt
- [ ] Run scrapers locally to generate initial data
- [ ] Commit all files including output/json/*_latest.json
- [ ] Create GitHub repository and push
- [ ] Set up Render web service
- [ ] Set up GitHub Actions for daily updates
- [ ] **Run verification script:** `python scripts/verify_leagues.py`
- [ ] Test live deployment

---

*Last updated: February 2026*
*Based on Liga ACB, Turkish BSL, EuroLeague, Italian LBA, French LNB, and Greek ESAKE implementations*

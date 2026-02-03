"""
=============================================================================
GERMAN BBL DAILY SCRAPER
=============================================================================

PURPOSE:
    This script collects basketball data for German Basketball Bundesliga (BBL)
    from the official easyCredit BBL website which provides accurate season stats.
    It also enriches data with TheSportsDB for additional player info.

WHAT IT DOES:
    1. Fetches player season stats from official easycredit-bbl.de website
    2. Identifies American players from the stats
    3. Enriches with TheSportsDB data (birthplace, biography, etc.)
    4. Saves everything to JSON files for the dashboard

OUTPUT FILES (saved to output/json/):
    - bbl_american_stats_TIMESTAMP.json: American player stats
    - bbl_american_stats_latest.json: Latest American player stats

DATA SOURCES:
    - Primary: easycredit-bbl.de (official stats)
    - Secondary: TheSportsDB API (player bios)
"""

import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Official BBL stats page
STATS_URL = "https://www.easycredit-bbl.de/statistiken/spieler"

# TheSportsDB for additional player info
SPORTSDB_API = "https://www.thesportsdb.com/api/v1/json/3"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Known American players in BBL (comprehensive list)
KNOWN_AMERICANS = {
    # From TheSportsDB with confirmed USA nationality
    'Aubrey Dawkins', 'Barry Brown', 'JeQuan Lewis', 'Joe Wieskamp',
    'Jordan Hulls', 'Justin Bean', 'Justin Simon', 'Justinian Jessup',
    'Khyri Thomas', 'Mark Ogden', 'Wes Iwundu',
    # From BBL stats and rosters
    'Alonzo Verge Jr.', 'Christopher Clemons', 'Traveon Buchanan',
    'Jordan Roland', 'Jaedon LeDee', 'Dalton Horne', 'Marvin Carr',
    'TJ Crockett Jr.', 'Chandler Ledlum', 'Grant Sherfield', 'DJ Horne',
    'Ryan Mikesell', 'Michael Weathers', 'Javon Bess', 'Jaleen Smith',
    'Corey Davis Jr.', 'Carlos Stewart Jr.', 'Simi Shittu',
    'DeJon Jarreau', 'Chima Moneke', 'Jalin Sly', 'Javon Freeman-Liberty',
    'Saben Lee', 'Trevion Williams', 'Devon Dotson', 'Sterling Brown',
    'Jabari Parker', 'DJ Wilson', 'Kobi Simmons', 'Jaylen Morris',
    'Courtney Stockard', 'Javonte Green', 'Elijah Bryant', 'Dwayne Cohill',
    'Kamar Baldwin', 'Isiaha Mike', 'Rayjon Tucker', 'Nigel Hayes',
}


def fetch_bbl_stats():
    """Fetch player stats from the official BBL website."""
    logger.info(f"Fetching stats from {STATS_URL}")

    try:
        response = requests.get(STATS_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch BBL stats: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find __NEXT_DATA__ script which contains page data
    next_data = soup.find('script', id='__NEXT_DATA__')
    if not next_data:
        logger.error("Could not find __NEXT_DATA__")
        return []

    try:
        data = json.loads(next_data.string)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return []

    props = data.get('props', {}).get('pageProps', {})
    widgets = props.get('preloadedWidgetData', {})

    # Find stats widget
    for key in widgets:
        if 'season-players-statistics' in key.lower():
            stats_data = widgets[key].get('data', [])
            logger.info(f"  Found {len(stats_data)} player entries")
            return stats_data

    return []


def fetch_sportsdb_player_info():
    """Fetch additional player info from TheSportsDB."""
    logger.info("Fetching player info from TheSportsDB...")

    player_info = {}

    # Get all teams in German BBL
    try:
        response = requests.get(
            f"{SPORTSDB_API}/search_all_teams.php",
            params={'l': 'German BBL'},
            timeout=30
        )
        teams_data = response.json()
        teams = teams_data.get('teams', []) or []
    except Exception as e:
        logger.error(f"Failed to fetch teams: {e}")
        return player_info

    logger.info(f"  Found {len(teams)} teams")

    # Get players from each team
    for team in teams:
        team_id = team.get('idTeam')
        if not team_id:
            continue

        try:
            response = requests.get(
                f"{SPORTSDB_API}/lookup_all_players.php",
                params={'id': team_id},
                timeout=30
            )
            players_data = response.json()
            players = players_data.get('player', []) or []

            for player in players:
                name = player.get('strPlayer', '')
                if name:
                    player_info[name.lower()] = {
                        'birthdate': player.get('dateBorn'),
                        'birthplace': player.get('strBirthLocation'),
                        'nationality': player.get('strNationality'),
                        'description': player.get('strDescriptionEN'),
                        'height': player.get('strHeight'),
                        'weight': player.get('strWeight'),
                        'thumb': player.get('strThumb'),
                        'cutout': player.get('strCutout'),
                    }
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Failed to fetch players for team {team_id}: {e}")

    logger.info(f"  Fetched info for {len(player_info)} players")
    return player_info


def is_american(name, sportsdb_info):
    """Check if a player is likely American."""
    # Check known Americans list
    for known in KNOWN_AMERICANS:
        if known.lower() in name.lower() or name.lower() in known.lower():
            return True

    # Check for American suffixes (common in US)
    if any(suffix in name for suffix in ['Jr.', 'Jr', 'III', 'II', 'IV']):
        return True

    # Check TheSportsDB nationality
    sdb_data = sportsdb_info.get(name.lower(), {})
    nationality = sdb_data.get('nationality', '')
    if nationality and ('united states' in nationality.lower() or 'usa' in nationality.lower()):
        return True

    return False


def process_players(raw_stats, sportsdb_info):
    """Process raw stats into player records, filtering for Americans."""
    players = []

    for stat in raw_stats:
        player_info = stat.get('seasonPlayer', {})
        team_info = stat.get('seasonTeam', {})

        if not player_info:
            continue

        first_name = player_info.get('firstName', '')
        last_name = player_info.get('lastName', '')
        full_name = f"{first_name} {last_name}".strip()

        if not full_name:
            continue

        # Check if American
        if not is_american(full_name, sportsdb_info):
            continue

        # Get additional info from TheSportsDB
        sdb_data = sportsdb_info.get(full_name.lower(), {})

        # Parse position
        position = player_info.get('position', '')
        position_map = {
            'POINT_GUARD': 'Point Guard',
            'SHOOTING_GUARD': 'Shooting Guard',
            'SMALL_FORWARD': 'Small Forward',
            'POWER_FORWARD': 'Power Forward',
            'CENTER': 'Center',
        }
        position = position_map.get(position, position.replace('_', ' ').title() if position else '')

        # Calculate height in feet/inches from cm
        height_cm = None
        height_feet = None
        height_inches = None
        height_str = sdb_data.get('height', '')
        if height_str:
            try:
                if 'm' in height_str.lower():
                    height_m = float(height_str.lower().replace('m', '').strip())
                    height_cm = int(height_m * 100)
            except:
                pass

        if height_cm:
            total_inches = height_cm / 2.54
            height_feet = int(total_inches // 12)
            height_inches = int(total_inches % 12)

        player = {
            # Basic info
            'code': str(player_info.get('playerId', '')),
            'name': full_name,
            'team': team_info.get('name', ''),
            'team_logo': team_info.get('logoUrl', ''),
            'position': position,
            'nationality': 'United States',

            # Physical
            'height_cm': height_cm,
            'height_feet': height_feet,
            'height_inches': height_inches,

            # Personal (from TheSportsDB)
            'birthdate': sdb_data.get('birthdate', '')[:10] if sdb_data.get('birthdate') else None,
            'birthplace': sdb_data.get('birthplace'),

            # Images
            'headshot_url': player_info.get('imageUrl') or sdb_data.get('cutout') or sdb_data.get('thumb'),

            # Season stats from official BBL
            'games_played': stat.get('gamesPlayed', 0),
            'ppg': round(stat.get('pointsPerGame', 0), 1),
            'rpg': round(stat.get('totalReboundsPerGame', 0), 1),
            'apg': round(stat.get('assistsPerGame', 0), 1),

            # Empty game log (box scores not available)
            'game_log': [],

            # Description
            'description': sdb_data.get('description'),
        }

        players.append(player)

    # Sort by PPG
    players.sort(key=lambda x: x.get('ppg', 0), reverse=True)

    return players


def save_json(data, filename):
    """Save data to JSON file."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    logger.info(f"Saved: {filepath}")
    return filepath


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("GERMAN BBL DAILY SCRAPER")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Fetch stats from official BBL website
    raw_stats = fetch_bbl_stats()
    if not raw_stats:
        logger.error("No stats data found from BBL website")
        return

    # Fetch additional info from TheSportsDB
    sportsdb_info = fetch_sportsdb_player_info()

    # Process and filter for Americans
    american_players = process_players(raw_stats, sportsdb_info)
    logger.info(f"Found {len(american_players)} American players")

    # Save results
    output = {
        'export_date': datetime.now().isoformat(),
        'season': '2025-26',
        'league': 'German Basketball Bundesliga (BBL)',
        'source': 'easycredit-bbl.de',
        'player_count': len(american_players),
        'players': american_players,
    }

    save_json(output, f'bbl_american_stats_{timestamp}.json')
    save_json(output, 'bbl_american_stats_latest.json')

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"American players: {len(american_players)}")

    if american_players:
        logger.info("\nTop scorers:")
        for p in american_players[:10]:
            logger.info(f"  {p['name']} ({p['team']}): {p['ppg']} PPG, {p['rpg']} RPG, {p['apg']} APG")

        # By team
        teams = {}
        for p in american_players:
            t = p.get('team', 'Unknown')
            teams[t] = teams.get(t, 0) + 1

        logger.info("\nAmericans by team:")
        for t, count in sorted(teams.items(), key=lambda x: -x[1]):
            logger.info(f"  {t}: {count}")


if __name__ == '__main__':
    main()

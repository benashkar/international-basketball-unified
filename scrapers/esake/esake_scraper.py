"""
=============================================================================
ESAKE SCRAPER - GREEK BASKET LEAGUE
=============================================================================

PURPOSE:
    Scrapes player information from TheSportsDB for Greek Basket League (ESAKE).
    Identifies American players and collects their profiles.

DATA SOURCE:
    TheSportsDB API: https://www.thesportsdb.com/
    League ID: 4452 (Greek Basket League)

OUTPUT:
    - esake_american_stats_*.json: American player data
    - esake_schedule_*.json: Team data
"""

import json
import os
import re
import requests
from datetime import datetime
import logging
import time
import unicodedata

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CURRENT_SEASON = '2025-26'
THESPORTSDB_API = 'https://www.thesportsdb.com/api/v1/json/3'
LEAGUE_NAME = 'Greek Basket League'
LEAGUE_ID = 4452

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}


def normalize_name(name):
    """Normalize player name for matching."""
    if not name:
        return ''
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = name.lower().strip()
    name = re.sub(r'\s+(jr\.?|sr\.?|iii|ii|iv)$', '', name, flags=re.IGNORECASE)
    return name


def save_json(data, filename):
    """Save data to JSON file."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    logger.info(f"Saved: {filepath}")
    return filepath


def fetch_api(endpoint, params=None):
    """Fetch data from TheSportsDB API."""
    url = f"{THESPORTSDB_API}/{endpoint}"
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        time.sleep(0.5)  # Rate limiting
        return resp.json()
    except Exception as e:
        logger.warning(f"API error for {endpoint}: {e}")
        return None


def fetch_all_teams():
    """Fetch all teams in the Greek Basket League."""
    logger.info(f"Fetching teams for {LEAGUE_NAME}...")

    data = fetch_api('search_all_teams.php', {'l': LEAGUE_NAME})

    if not data or not data.get('teams'):
        logger.error("Failed to fetch teams")
        return []

    teams = []
    for team in data['teams']:
        teams.append({
            'id': team.get('idTeam'),
            'name': team.get('strTeam'),
            'short_name': team.get('strTeamShort'),
            'stadium': team.get('strStadium'),
            'location': team.get('strStadiumLocation'),
            'logo': team.get('strLogo') or team.get('strBadge'),
            'founded': team.get('intFormedYear'),
        })

    logger.info(f"Found {len(teams)} teams")
    return teams


def fetch_team_players(team_id):
    """Fetch all players for a team."""
    data = fetch_api('lookup_all_players.php', {'id': team_id})

    if not data or not data.get('player'):
        return []

    players = []
    for p in data['player']:
        # Parse height
        height_str = p.get('strHeight', '')
        height_cm = None
        if height_str:
            m_match = re.search(r'(\d+\.?\d*)\s*m', height_str)
            if m_match:
                height_cm = int(float(m_match.group(1)) * 100)
            else:
                ft_match = re.search(r'(\d+)\s*ft\s*(\d+)?', height_str)
                if ft_match:
                    feet = int(ft_match.group(1))
                    inches = int(ft_match.group(2) or 0)
                    height_cm = int((feet * 12 + inches) * 2.54)

        players.append({
            'id': p.get('idPlayer'),
            'name': p.get('strPlayer'),
            'nationality': p.get('strNationality'),
            'position': p.get('strPosition'),
            'birthdate': p.get('dateBorn'),
            'birthplace': p.get('strBirthLocation'),
            'height': height_str,
            'height_cm': height_cm,
            'description': p.get('strDescriptionEN'),
            'thumb': p.get('strThumb'),
            'cutout': p.get('strCutout'),
        })

    return players


def is_american(player):
    """Check if player is American."""
    nationality = (player.get('nationality') or '').lower()
    birthplace = (player.get('birthplace') or '').lower()

    usa_indicators = ['united states', 'usa', 'american', 'u.s.']

    for indicator in usa_indicators:
        if indicator in nationality:
            return True
        if indicator in birthplace:
            return True

    # Check common US states/cities in birthplace
    us_locations = [
        'new york', 'california', 'texas', 'florida', 'chicago', 'los angeles',
        'atlanta', 'houston', 'philadelphia', 'phoenix', 'detroit', 'boston',
        'seattle', 'denver', 'portland', 'las vegas', 'miami', 'brooklyn',
        'oregon', 'ohio', 'michigan', 'georgia', 'tennessee', 'north carolina',
        'south carolina', 'virginia', 'maryland', 'indiana', 'illinois',
        'kentucky', 'alabama', 'mississippi', 'louisiana', 'new jersey',
    ]

    for location in us_locations:
        if location in birthplace:
            return True

    return False


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("ESAKE SCRAPER - Greek Basket League")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Fetch all teams
    teams = fetch_all_teams()

    # Fetch players for each team
    all_players = []
    american_players = []

    for i, team in enumerate(teams):
        logger.info(f"Fetching players for {team['name']} ({i+1}/{len(teams)})...")
        players = fetch_team_players(team['id'])

        for player in players:
            player['team'] = team['name']
            player['team_id'] = team['id']
            player['team_logo'] = team.get('logo')
            all_players.append(player)

            if is_american(player):
                american_players.append(player)
                logger.info(f"  Found American: {player['name']} - {player.get('position')}")

        time.sleep(0.3)

    # Sort Americans by name
    american_players.sort(key=lambda x: x.get('name', ''))

    # Save results
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Greek Basket League (ESAKE)',
        'source': 'thesportsdb.com',
        'player_count': len(american_players),
        'players': american_players
    }, f'esake_american_stats_{timestamp}.json')

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Greek Basket League (ESAKE)',
        'team_count': len(teams),
        'teams': teams
    }, f'esake_schedule_{timestamp}.json')

    # Save latest versions
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Greek Basket League (ESAKE)',
        'source': 'thesportsdb.com',
        'player_count': len(american_players),
        'players': american_players
    }, 'esake_american_stats_latest.json')

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Greek Basket League (ESAKE)',
        'team_count': len(teams),
        'teams': teams
    }, 'esake_schedule_latest.json')

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total teams: {len(teams)}")
    logger.info(f"Total players scraped: {len(all_players)}")
    logger.info(f"American players found: {len(american_players)}")

    if american_players:
        logger.info("\nAmerican players:")
        for p in american_players:
            logger.info(f"  {p['name']} ({p.get('team', 'N/A')}) - {p.get('position', 'N/A')}")


if __name__ == '__main__':
    main()

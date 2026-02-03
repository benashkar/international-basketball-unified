"""
=============================================================================
GERMAN BBL - SEASON STATS SCRAPER
=============================================================================
Scrapes player season statistics from the official easyCredit BBL website.
Extracts data from the __NEXT_DATA__ JSON embedded in the page.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

STATS_URL = "https://www.easycredit-bbl.de/statistiken/spieler"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
}


def fetch_stats_data():
    """Fetch the BBL stats page and extract player stats from NEXT_DATA."""
    logger.info(f"Fetching stats from {STATS_URL}")

    try:
        response = requests.get(STATS_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch stats page: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find __NEXT_DATA__ script tag which contains the page data
    next_data = soup.find('script', id='__NEXT_DATA__')
    if not next_data:
        logger.error("Could not find __NEXT_DATA__ in page")
        return []

    try:
        data = json.loads(next_data.string)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse NEXT_DATA: {e}")
        return []

    props = data.get('props', {}).get('pageProps', {})
    widgets = props.get('preloadedWidgetData', {})

    # Find the season players statistics widget
    stats_data = []
    for key in widgets:
        if 'season-players-statistics' in key.lower():
            stats_data = widgets[key].get('data', [])
            break

    logger.info(f"Found {len(stats_data)} player stats entries")
    return stats_data


def parse_player_stats(raw_stats):
    """Parse raw stats data into a cleaner format."""
    players = []

    for stat in raw_stats:
        player_info = stat.get('seasonPlayer', {})
        team_info = stat.get('seasonTeam', {})

        if not player_info:
            continue

        first_name = player_info.get('firstName', '')
        last_name = player_info.get('lastName', '')

        if not first_name and not last_name:
            continue

        player = {
            'id': str(player_info.get('playerId', '')),
            'name': f"{first_name} {last_name}".strip(),
            'first_name': first_name,
            'last_name': last_name,
            'team': team_info.get('name', ''),
            'team_id': str(team_info.get('teamId', '')),
            'team_logo': team_info.get('logoUrl', ''),
            'position': player_info.get('position', ''),
            'jersey_number': player_info.get('shirtNumber', ''),
            'headshot_url': player_info.get('imageUrl', ''),

            # Season totals
            'games_played': stat.get('gamesPlayed', 0),
            'games_started': stat.get('gamesStarted', 0),
            'total_points': stat.get('points', 0),
            'total_rebounds': stat.get('totalRebounds', 0),
            'total_assists': stat.get('assists', 0),
            'total_steals': stat.get('steals', 0),
            'total_blocks': stat.get('blocks', 0),
            'total_turnovers': stat.get('turnovers', 0),

            # Per game stats
            'ppg': stat.get('pointsPerGame', 0),
            'rpg': stat.get('totalReboundsPerGame', 0),
            'apg': stat.get('assistsPerGame', 0),
            'spg': stat.get('stealsPerGame', 0),
            'bpg': stat.get('blocksPerGame', 0),
            'mpg': round(stat.get('secondsPerGame', 0) / 60, 1),

            # Shooting
            'fg_pct': stat.get('fieldGoalsSuccessPercent', 0),
            'fg3_pct': stat.get('threePointShotSuccessPercent', 0),
            'ft_pct': stat.get('freeThrowsSuccessPercent', 0),

            # Advanced
            'efficiency': stat.get('efficiencyPerGame', 0),
            'plus_minus': stat.get('plusMinusPerGame', 0),
        }

        players.append(player)

    # Sort by PPG descending
    players.sort(key=lambda x: x.get('ppg', 0), reverse=True)

    return players


def identify_americans(players):
    """Identify likely American players based on names and patterns."""
    # Common American-sounding names and patterns
    american_indicators = [
        # Common American first names
        'Jr.', 'Jr', 'III', 'II',
    ]

    # Known American players (partial list, will be expanded by matching)
    known_americans = {
        'Alonzo Verge Jr.', 'Christopher Clemons', 'Traveon Buchanan',
        'Jordan Roland', 'Jaedon LeDee', 'Dalton Horne', 'Marvin Carr',
        'TJ Crockett Jr.', 'Chandler Ledlum', 'Grant Sherfield', 'DJ Horne',
        'Ryan Mikesell', 'Michael Weathers', 'Javon Bess', 'Jaleen Smith',
        'Justin Bean', 'Justinian Jessup', 'Joe Wieskamp', 'Khyri Thomas',
        'Wes Iwundu', 'JeQuan Lewis', 'Justin Simon', 'Barry Brown',
        'Jordan Hulls', 'Aubrey Dawkins', 'Mark Ogden',
        # More Americans
        'Corey Davis Jr.', 'Corey Davis',
    }

    americans = []
    for player in players:
        name = player.get('name', '')

        # Check if in known Americans list
        if any(known in name for known in known_americans):
            player['nationality'] = 'USA'
            americans.append(player)
            continue

        # Check for American indicators (Jr., III, etc. are common in US)
        if any(ind in name for ind in american_indicators):
            player['nationality'] = 'USA'
            americans.append(player)

    return americans


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
    logger.info("GERMAN BBL - SEASON STATS SCRAPER")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Fetch and parse stats
    raw_stats = fetch_stats_data()
    if not raw_stats:
        logger.error("No stats data found")
        return

    players = parse_player_stats(raw_stats)
    logger.info(f"Parsed {len(players)} players with stats")

    # Save all player stats
    all_stats_output = {
        'export_date': datetime.now().isoformat(),
        'season': '2025-26',
        'league': 'German Basketball Bundesliga (BBL)',
        'source': 'easycredit-bbl.de',
        'player_count': len(players),
        'players': players,
    }
    save_json(all_stats_output, f'bbl_all_stats_{timestamp}.json')
    save_json(all_stats_output, 'bbl_all_stats_latest.json')

    # Identify and save American players
    americans = identify_americans(players)
    logger.info(f"Identified {len(americans)} likely American players")

    american_stats_output = {
        'export_date': datetime.now().isoformat(),
        'season': '2025-26',
        'league': 'German Basketball Bundesliga (BBL)',
        'source': 'easycredit-bbl.de',
        'player_count': len(americans),
        'players': americans,
    }
    save_json(american_stats_output, f'bbl_american_stats_{timestamp}.json')
    save_json(american_stats_output, 'bbl_american_stats_latest.json')

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total players: {len(players)}")
    logger.info(f"American players: {len(americans)}")

    if americans:
        logger.info("\nTop American scorers:")
        for p in americans[:10]:
            logger.info(f"  {p['name']} ({p['team']}): {p['ppg']} PPG, {p['rpg']} RPG, {p['apg']} APG")


if __name__ == '__main__':
    main()

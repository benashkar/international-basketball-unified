"""
=============================================================================
LNB BOX SCORE SCRAPER - FRENCH BETCLIC ELITE
=============================================================================

PURPOSE:
    Scrapes game results and box scores from the LNB API.
    Gets detailed player statistics for each game.

DATA SOURCE:
    Atrium Sports API (powers LNB website)
    - Calendar: https://api-prod.lnb.fr/match/getCalendar
    - Match Details: https://eapi.web.prod.cloud.atriumsports.com/v1/embed/12/fixture_detail

OUTPUT:
    - lnb_games_*.json: All games with results
    - lnb_boxscores_*.json: Detailed box scores
"""

import json
import os
import re
import requests
from datetime import datetime
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CURRENT_SEASON = '2025-26'
LNB_API = 'https://api-prod.lnb.fr'
ATRIUM_API = 'https://eapi.web.prod.cloud.atriumsports.com/v1/embed/12'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Origin': 'https://lnb.fr',
    'Referer': 'https://lnb.fr/',
}


def save_json(data, filename):
    """Save data to JSON file."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    logger.info(f"Saved: {filepath}")
    return filepath


def fetch_api(url, params=None):
    """Fetch data from API."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            resp.raise_for_status()
            time.sleep(0.5)
            return resp.json()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(2)
    return None


def parse_duration(duration_str):
    """Parse ISO 8601 duration (e.g., PT26M24S) to minutes string."""
    if not duration_str:
        return '0:00'

    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', str(duration_str))
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        total_minutes = hours * 60 + minutes
        return f'{total_minutes}:{seconds:02d}'

    return '0:00'


def fetch_calendar():
    """Fetch all games from the calendar."""
    logger.info("Fetching game calendar...")

    # Get main competition for current year
    data = fetch_api(f'{LNB_API}/competition/getMainCompetition', {'year': '2025'})
    if not data or not data.get('data'):
        logger.error("Failed to get competition data")
        return []

    competition_id = data['data'].get('competition_external_id', 302)
    logger.info(f"Competition ID: {competition_id}")

    # Fetch calendar data
    # The calendar endpoint might need pagination or different params
    # Let's try the match list approach instead
    return fetch_recent_matches()


def fetch_recent_matches():
    """Fetch recent completed matches using Selenium to get match IDs."""
    logger.info("Fetching recent match IDs...")

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })

        match_ids = set()

        try:
            # Load main page (has recent matches)
            driver.get('https://lnb.fr/fr')
            time.sleep(10)

            # Accept cookies
            try:
                for btn in driver.find_elements(By.TAG_NAME, 'button'):
                    if 'accepter' in btn.text.lower():
                        btn.click()
                        time.sleep(2)
                        break
            except:
                pass

            # Find match links
            links = driver.find_elements(By.TAG_NAME, 'a')
            for link in links:
                href = link.get_attribute('href') or ''
                if '/match-center/' in href:
                    # Extract match ID (UUID format)
                    match = re.search(r'/match-center/([a-f0-9-]{36})', href)
                    if match:
                        match_ids.add(match.group(1))

            logger.info(f"Found {len(match_ids)} match IDs from calendar")

        finally:
            driver.quit()

        return list(match_ids)

    except ImportError:
        logger.warning("Selenium not available, using sample match IDs")
        return []
    except Exception as e:
        logger.error(f"Error fetching match IDs: {e}")
        return []


def fetch_box_score(match_id):
    """Fetch detailed box score for a game."""
    url = f'{ATRIUM_API}/fixture_detail'
    data = fetch_api(url, {'fixtureId': match_id})

    if not data or 'data' not in data:
        return None

    try:
        fixture = data['data']['fixture']

        # Get team info
        home_team = away_team = home_score = away_score = None
        home_entity_id = away_entity_id = None

        for comp in fixture.get('competitors', []):
            if comp.get('isHome'):
                home_team = comp.get('name')
                home_score = comp.get('score')
                home_entity_id = comp.get('entityId')
            else:
                away_team = comp.get('name')
                away_score = comp.get('score')
                away_entity_id = comp.get('entityId')

        box_score = {
            'game_id': match_id,
            'home_team': home_team,
            'away_team': away_team,
            'home_score': home_score,
            'away_score': away_score,
            'date': fixture.get('startTime'),
            'venue': fixture.get('venue'),
            'status': fixture.get('status'),
            'home_players': [],
            'away_players': [],
        }

        # Get player stats
        stats_data = data['data'].get('statistics', {}).get('data', {}).get('base', {})

        for side, players_key in [('home', 'home_players'), ('away', 'away_players')]:
            side_data = stats_data.get(side, {})
            persons = side_data.get('persons', [{}])

            if persons and len(persons) > 0:
                rows = persons[0].get('rows', [])

                for player in rows:
                    name = player.get('personName', '')
                    if not name:
                        continue

                    stats = player.get('statistics', {})

                    player_data = {
                        'name': name,
                        'jersey': player.get('bib', ''),
                        'starter': player.get('starter', False),
                        'minutes': parse_duration(stats.get('minutes')),
                        'points': stats.get('points', 0) or 0,
                        'rebounds': stats.get('reboundsTotal', 0) or 0,
                        'offensive_rebounds': stats.get('reboundsOffensive', 0) or 0,
                        'defensive_rebounds': stats.get('reboundsDefensive', 0) or 0,
                        'assists': stats.get('assists', 0) or 0,
                        'steals': stats.get('steals', 0) or 0,
                        'blocks': stats.get('blocks', 0) or 0,
                        'turnovers': stats.get('turnovers', 0) or 0,
                        'fouls': stats.get('foulsTotal', 0) or 0,
                        'fg_made': stats.get('fieldGoalsMade', 0) or 0,
                        'fg_attempted': stats.get('fieldGoalsAttempted', 0) or 0,
                        'fg_pct': stats.get('fieldGoalsPercentage', 0) or 0,
                        'three_made': stats.get('pointsThreeMade', 0) or 0,
                        'three_attempted': stats.get('pointsThreeAttempted', 0) or 0,
                        'three_pct': stats.get('pointsThreePercentage', 0) or 0,
                        'ft_made': stats.get('freeThrowsMade', 0) or 0,
                        'ft_attempted': stats.get('freeThrowsAttempted', 0) or 0,
                        'ft_pct': stats.get('freeThrowsPercentage', 0) or 0,
                        'plus_minus': stats.get('plusMinus', 0) or 0,
                        'efficiency': stats.get('efficiency', 0) or 0,
                    }

                    box_score[players_key].append(player_data)

        return box_score

    except Exception as e:
        logger.error(f"Error parsing box score for {match_id}: {e}")
        return None


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("LNB BOX SCORE SCRAPER - French Betclic Elite")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Fetch all match IDs
    match_ids = fetch_recent_matches()

    if not match_ids:
        logger.warning("No match IDs found")
        return

    logger.info(f"Total matches found: {len(match_ids)}")

    # Fetch box scores
    all_games = []
    all_box_scores = []

    for i, match_id in enumerate(match_ids):
        logger.info(f"Fetching box score {i+1}/{len(match_ids)}: {match_id}")
        box_score = fetch_box_score(match_id)

        if box_score:
            # Check if game is complete
            if box_score.get('status') == 'CONFIRMED' and box_score.get('home_score'):
                all_box_scores.append(box_score)

                # Create game summary
                all_games.append({
                    'game_id': box_score['game_id'],
                    'date': box_score['date'],
                    'home_team': box_score['home_team'],
                    'away_team': box_score['away_team'],
                    'home_score': box_score['home_score'],
                    'away_score': box_score['away_score'],
                    'played': True,
                })

        time.sleep(0.5)

    # Save results
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'French Betclic Elite (Pro A)',
        'source': 'lnb.fr',
        'game_count': len(all_games),
        'games': all_games
    }, f'lnb_games_{timestamp}.json')

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'French Betclic Elite (Pro A)',
        'source': 'lnb.fr',
        'box_score_count': len(all_box_scores),
        'box_scores': all_box_scores
    }, f'lnb_boxscores_{timestamp}.json')

    # Save latest versions
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'French Betclic Elite (Pro A)',
        'source': 'lnb.fr',
        'game_count': len(all_games),
        'games': all_games
    }, 'lnb_games_latest.json')

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'French Betclic Elite (Pro A)',
        'source': 'lnb.fr',
        'box_score_count': len(all_box_scores),
        'box_scores': all_box_scores
    }, 'lnb_boxscores_latest.json')

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total matches found: {len(match_ids)}")
    logger.info(f"Box scores fetched: {len(all_box_scores)}")

    total_player_stats = sum(
        len(bs.get('home_players', [])) + len(bs.get('away_players', []))
        for bs in all_box_scores
    )
    logger.info(f"Total player stat lines: {total_player_stats}")


if __name__ == '__main__':
    main()

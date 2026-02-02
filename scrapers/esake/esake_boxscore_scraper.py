"""
=============================================================================
ESAKE BOX SCORE SCRAPER - GREEK BASKET LEAGUE
=============================================================================

PURPOSE:
    Scrapes game results and box scores from the official ESAKE website.
    Gets detailed player statistics for each game.

DATA SOURCE:
    Official ESAKE Website: https://www.esake.gr/en/
    - Teams: /en/action/EsakeTeams
    - Team Schedule: /en/action/EsaketeamView?idteam={TEAM_ID}&mode=3
    - Box Scores: /en/action/EsakegameView?idgame={GAME_ID}&mode=3
    - Players: /en/action/EsakePlayers

OUTPUT:
    - esake_games_*.json: All games with results
    - esake_boxscores_*.json: Detailed box scores
"""

import json
import os
import re
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

# Configuration
CURRENT_SEASON = '2025-26'
BASE_URL = 'https://www.esake.gr'
TEAMS_URL = f'{BASE_URL}/en/action/EsakeTeams'
TEAM_SCHEDULE_URL = f'{BASE_URL}/en/action/EsaketeamView'
GAME_URL = f'{BASE_URL}/en/action/EsakegameView'
PLAYERS_URL = f'{BASE_URL}/en/action/EsakePlayers'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
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


def fetch_page(url, params=None):
    """Fetch a webpage with proper encoding."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            time.sleep(0.5)
            return resp.text
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(2)
    return None


def parse_int(value):
    """Parse integer from string, return 0 if invalid."""
    try:
        digits = re.sub(r'[^\d]', '', str(value))
        return int(digits) if digits else 0
    except:
        return 0


def fetch_all_teams():
    """Fetch all team IDs from the teams page."""
    logger.info("Fetching all teams...")
    html = fetch_page(TEAMS_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    teams = []
    seen_ids = set()

    # Team names are in h4 tags, team IDs are in nearby links
    h4_tags = soup.find_all('h4')

    for h4 in h4_tags:
        team_name = h4.get_text(strip=True)
        if not team_name:
            continue

        # Find nearest link with team ID by searching parent divs
        parent = h4.find_parent('div')
        team_link = None

        for _ in range(5):  # Search up to 5 levels
            if parent:
                team_link = parent.find('a', href=re.compile(r'idteam='))
                if team_link:
                    break
                parent = parent.find_parent('div')

        if team_link:
            href = team_link.get('href', '')
            match = re.search(r'idteam=([A-F0-9]+)', href)
            if match:
                team_id = match.group(1)
                if team_id not in seen_ids:
                    seen_ids.add(team_id)
                    teams.append({
                        'id': team_id,
                        'name': team_name
                    })

    logger.info(f"Found {len(teams)} teams")
    return teams


def parse_score(score_text):
    """Parse score from text like '94 - 71' or '94\xa0-\xa071'."""
    if not score_text:
        return None, None

    # Replace non-breaking spaces with regular spaces
    score_text = score_text.replace('\xa0', ' ')

    # Look for score pattern
    match = re.search(r'(\d{2,3})\s*[-–]\s*(\d{2,3})', score_text)
    if match:
        return int(match.group(1)), int(match.group(2))

    return None, None


def fetch_team_schedule(team_id, team_name):
    """Fetch all games for a team (completed and upcoming)."""
    html = fetch_page(TEAM_SCHEDULE_URL, {'idteam': team_id, 'mode': 3})
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    games = []

    # Find all game rows (the structure uses esake-program-game-row-* classes)
    game_rows = soup.find_all('div', class_=re.compile(r'esake-program-game-row'))

    for row in game_rows:
        # Get game ID from link
        game_link = row.find('a', href=re.compile(r'idgame='))
        if not game_link:
            continue

        href = game_link.get('href', '')
        game_id_match = re.search(r'idgame=([A-F0-9]+)', href)
        if not game_id_match:
            continue

        game_id = game_id_match.group(1)

        game_info = {
            'game_id': game_id,
            'date': None,
            'series': None,
            'home_team': None,
            'away_team': None,
            'home_score': None,
            'away_score': None,
            'played': False
        }

        # Get series number
        series_elem = row.find('h5')
        if series_elem:
            series_text = series_elem.get_text(strip=True)
            series_match = re.search(r'(\d+)', series_text)
            if series_match:
                game_info['series'] = int(series_match.group(1))

        # Get date
        date_div = row.find('div', class_='esake-program-game-info')
        if date_div:
            date_text = date_div.get_text(strip=True)
            game_info['date'] = date_text

        # Get score section
        score_wrapper = row.find('div', class_='esake-program-game-final-score')
        if score_wrapper:
            spans = score_wrapper.find_all('span')
            texts = [s.get_text(strip=True) for s in spans]

            if len(texts) >= 3:
                # Format: [home_team, score, away_team]
                game_info['home_team'] = texts[0]
                game_info['away_team'] = texts[2] if len(texts) > 2 else None

                # Check if middle text is a score
                score_text = texts[1]
                home_score, away_score = parse_score(score_text)

                if home_score is not None and away_score is not None:
                    game_info['home_score'] = home_score
                    game_info['away_score'] = away_score
                    game_info['played'] = True

        games.append(game_info)

    return games


def fetch_all_game_ids():
    """Fetch all game IDs by iterating through team schedules."""
    logger.info("Fetching all game IDs from team schedules...")

    teams = fetch_all_teams()
    all_games = {}  # Use dict to deduplicate by game_id

    for i, team in enumerate(teams):
        logger.info(f"Fetching schedule for {team['name']} ({i+1}/{len(teams)})...")
        games = fetch_team_schedule(team['id'], team['name'])

        for game in games:
            game_id = game['game_id']
            if game_id not in all_games:
                all_games[game_id] = game
            else:
                # Merge info if we have more data
                existing = all_games[game_id]
                if game.get('home_score') and not existing.get('home_score'):
                    existing.update(game)
                if game.get('date') and not existing.get('date'):
                    existing['date'] = game['date']

        time.sleep(0.3)

    logger.info(f"Total unique games found: {len(all_games)}")
    return list(all_games.values())


def fetch_box_score(game_id):
    """Fetch detailed box score for a game."""
    url = f"{GAME_URL}?idgame={game_id}&mode=3"
    html = fetch_page(url)

    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    box_score = {
        'game_id': game_id,
        'home_team': None,
        'away_team': None,
        'home_score': None,
        'away_score': None,
        'date': None,
        'venue': None,
        'home_players': [],
        'away_players': [],
    }

    # Find all tables with player stats
    tables = soup.find_all('table')

    team_idx = 0
    for table in tables:
        rows = table.find_all('tr')
        players = []

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 5:
                continue

            first_cell_text = cells[0].get_text(strip=True)

            # Skip header/total rows
            if any(x in first_cell_text.upper() for x in ['PLAYER', 'NAME', 'TOTAL', 'TEAM', 'ΠΑΙΚΤΗΣ', 'MIN', 'PTS']):
                continue

            # Clean up jersey number from name
            name = re.sub(r'^#?\d+\s*', '', first_cell_text)
            if not name or len(name) < 2:
                continue

            player = {
                'name': name,
                'minutes': cells[1].get_text(strip=True) if len(cells) > 1 else '0:00',
                'points': parse_int(cells[2].get_text(strip=True)) if len(cells) > 2 else 0,
                'rebounds': parse_int(cells[3].get_text(strip=True)) if len(cells) > 3 else 0,
                'assists': parse_int(cells[4].get_text(strip=True)) if len(cells) > 4 else 0,
                'steals': parse_int(cells[5].get_text(strip=True)) if len(cells) > 5 else 0,
                'blocks': parse_int(cells[6].get_text(strip=True)) if len(cells) > 6 else 0,
            }

            players.append(player)

        if players:
            if team_idx == 0:
                box_score['home_players'] = players
            else:
                box_score['away_players'] = players
            team_idx += 1

    return box_score


def fetch_american_players():
    """Fetch list of American players."""
    logger.info("Fetching American players list...")

    html = fetch_page(PLAYERS_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    american_players = []

    rows = soup.find_all('tr')

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 2:
            continue

        row_text = row.get_text()
        if 'ΗΠΑ' in row_text or 'USA' in row_text:
            player_link = row.find('a', href=re.compile(r'idplayer='))
            if player_link:
                player_id_match = re.search(r'idplayer=([A-F0-9]+)', player_link.get('href', ''))
                player_name = player_link.get_text(strip=True)

                american_players.append({
                    'player_id': player_id_match.group(1) if player_id_match else None,
                    'name': player_name,
                    'nationality': 'USA',
                })

    logger.info(f"Found {len(american_players)} American players")
    return american_players


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("ESAKE BOX SCORE SCRAPER - Greek Basket League")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Fetch American players
    american_players = fetch_american_players()

    # Fetch all game IDs through team schedules
    all_games = fetch_all_game_ids()

    # Filter to only played games
    played_games = [g for g in all_games if g.get('played', False)]
    logger.info(f"Played games: {len(played_games)}")

    # Fetch box scores for played games
    all_box_scores = []
    for i, game in enumerate(played_games):
        game_id = game['game_id']
        logger.info(f"Fetching box score {i+1}/{len(played_games)}: {game_id}")
        box_score = fetch_box_score(game_id)
        if box_score:
            # Add game metadata from schedule
            box_score['date'] = game.get('date')
            box_score['home_team'] = game.get('home_team')
            box_score['away_team'] = game.get('away_team')
            box_score['home_score'] = game.get('home_score')
            box_score['away_score'] = game.get('away_score')
            box_score['series'] = game.get('series')
            all_box_scores.append(box_score)
        time.sleep(0.5)

    # Save results
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Greek Basket League (ESAKE)',
        'source': 'esake.gr',
        'game_count': len(all_games),
        'played_count': len(played_games),
        'games': all_games
    }, f'esake_games_{timestamp}.json')

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Greek Basket League (ESAKE)',
        'source': 'esake.gr',
        'box_score_count': len(all_box_scores),
        'box_scores': all_box_scores
    }, f'esake_boxscores_{timestamp}.json')

    # Save latest versions
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Greek Basket League (ESAKE)',
        'source': 'esake.gr',
        'game_count': len(all_games),
        'played_count': len(played_games),
        'games': all_games
    }, 'esake_games_latest.json')

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Greek Basket League (ESAKE)',
        'source': 'esake.gr',
        'box_score_count': len(all_box_scores),
        'box_scores': all_box_scores
    }, 'esake_boxscores_latest.json')

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total games found: {len(all_games)}")
    logger.info(f"Played games: {len(played_games)}")
    logger.info(f"Box scores fetched: {len(all_box_scores)}")
    logger.info(f"American players: {len(american_players)}")

    total_player_stats = sum(
        len(bs.get('home_players', [])) + len(bs.get('away_players', []))
        for bs in all_box_scores
    )
    logger.info(f"Total player stat lines: {total_player_stats}")


if __name__ == '__main__':
    main()

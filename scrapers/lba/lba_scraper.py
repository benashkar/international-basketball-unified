"""
=============================================================================
LBA SCRAPER - ITALIAN LEGA BASKET SERIE A
=============================================================================

PURPOSE:
    Scrapes player statistics from legabasket.it for Italian Serie A.
    Identifies American players and collects their season stats and game logs.

DATA SOURCE:
    legabasket.it: https://www.legabasket.it/
    Uses embedded JSON data from Next.js pages (same pattern as EuroLeague)

WHAT IT FETCHES:
    - Full season schedule (past and upcoming games)
    - Box scores for played games
    - Player game-by-game stats
    - Season averages calculated from game logs

OUTPUT:
    - lba_american_stats_*.json: American player statistics with game logs
    - lba_schedule_*.json: Complete schedule with box scores
"""

import json
import os
import re
import requests
from bs4 import BeautifulSoup
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
BASE_URL = 'https://www.legabasket.it'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
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


def fetch_game_data(game_id, game_slug):
    """Fetch box score data for a specific game from legabasket.it."""
    url = f"{BASE_URL}/game/{game_id}/{game_slug}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')

        if not script:
            logger.debug(f"No __NEXT_DATA__ found for game {game_id}")
            return None

        data = json.loads(script.string)
        game = data.get('props', {}).get('pageProps', {}).get('game', {})
        match = game.get('match', {})
        scores = game.get('scores', {})

        if not match or not scores:
            return None

        game_data = {
            'game_id': str(match.get('id')),
            'date': match.get('match_datetime', '')[:10] if match.get('match_datetime') else None,
            'time': f"{match.get('match_hh', '00')}:{match.get('match_mm', '00')}",
            'round': match.get('day_name') or str(match.get('day_serial', '')),
            'home_team': match.get('h_team_name'),
            'away_team': match.get('v_team_name'),
            'home_score': match.get('home_final_score'),
            'away_score': match.get('visitor_final_score'),
            'venue': match.get('plant_name'),
            'spectators': match.get('spectators'),
            # Game is played if there are scores (game_status values can vary)
            'played': bool(match.get('home_final_score') is not None and match.get('visitor_final_score') is not None),
            'box_score': [],
        }

        # Parse player stats from both teams
        for team_key, team_name_key in [('ht', 'h_team_name'), ('vt', 'v_team_name')]:
            team_data = scores.get(team_key, {})
            team_name = match.get(team_name_key)
            rows = team_data.get('rows', [])

            for player in rows:
                # Build player name from surname and first name
                surname = player.get('player_surname', '')
                first_name = player.get('player_name', '')
                full_name = f"{first_name} {surname}".title() if first_name and surname else (surname or first_name).title()

                player_stat = {
                    'player_id': player.get('player_id'),
                    'name': full_name,
                    'team': team_name,
                    'jersey': player.get('player_num'),
                    'minutes': player.get('min', 0),
                    'points': player.get('pun', 0),
                    'rebounds': player.get('rimbalzi_t', 0),
                    'offensive_rebounds': player.get('rimbalzi_o', 0),
                    'defensive_rebounds': player.get('rimbalzi_d', 0),
                    'assists': player.get('ass', 0),
                    'steals': player.get('palle_r', 0),
                    'blocks': player.get('stoppate_dat', 0),
                    'turnovers': player.get('palle_p', 0),
                    'fouls': player.get('falli_c', 0),
                    'plus_minus': player.get('plus_minus', 0),
                    'efficiency': player.get('val_lega', 0),
                    'fg2_made': player.get('t2_r', 0),
                    'fg2_attempted': player.get('t2_t', 0),
                    'fg3_made': player.get('t3_r', 0),
                    'fg3_attempted': player.get('t3_t', 0),
                    'ft_made': player.get('tl_r', 0),
                    'ft_attempted': player.get('tl_t', 0),
                }
                game_data['box_score'].append(player_stat)

        return game_data

    except requests.RequestException as e:
        logger.debug(f"Error fetching game {game_id}: {e}")
        return None


def fetch_schedule():
    """Fetch schedule from legabasket.it."""
    logger.info("Fetching schedule from legabasket.it...")

    games = []

    # Fetch the schedule page
    url = f"{BASE_URL}/lba"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')

        if script:
            data = json.loads(script.string)
            page_props = data.get('props', {}).get('pageProps', {})

            # Look for games/schedule data
            for key in ['games', 'schedule', 'matches', 'calendar', 'rounds', 'days']:
                if key in page_props:
                    logger.info(f"Found {key} in pageProps")

    except requests.RequestException as e:
        logger.warning(f"Error fetching schedule page: {e}")

    # Alternative: Fetch from news/live pages to find game links
    logger.info("Searching for game links on the site...")

    try:
        # Try the results/calendar page
        for page_url in [f"{BASE_URL}/risultati", f"{BASE_URL}/calendario", f"{BASE_URL}/lba"]:
            try:
                response = requests.get(page_url, headers=HEADERS, timeout=30)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Find game links
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        match = re.search(r'/game/(\d+)/([^"\'>\s]+)', href)
                        if match:
                            game_id = match.group(1)
                            game_slug = match.group(2)
                            games.append({'id': game_id, 'slug': game_slug})

                    if games:
                        break
            except:
                continue

    except Exception as e:
        logger.warning(f"Error searching for games: {e}")

    # Remove duplicates
    seen = set()
    unique_games = []
    for g in games:
        if g['id'] not in seen:
            seen.add(g['id'])
            unique_games.append(g)

    logger.info(f"Found {len(unique_games)} unique game links")

    # Fetch details for each game
    full_games = []
    for i, game_info in enumerate(unique_games[:100]):  # Limit to 100 games
        if i > 0 and i % 10 == 0:
            logger.info(f"  Progress: {i}/{len(unique_games)}")

        game_data = fetch_game_data(game_info['id'], game_info['slug'])
        if game_data:
            full_games.append(game_data)
        time.sleep(0.3)

    logger.info(f"Fetched details for {len(full_games)} games")
    return full_games


def fetch_all_games_by_id():
    """Fetch games by ID range from legabasket.it."""
    logger.info("Fetching games by ID range...")

    all_games = []

    # Game IDs for 2025-26 season:
    # - 25009: Round 1 (October 2025)
    # - 25157: Round 18 (February 2026)
    # - Estimated ~240 games for full season (30 rounds * 8 games)
    # Future games will have higher IDs

    start_id = 25009  # First regular season game
    end_id = 25300    # Should cover through playoffs

    consecutive_misses = 0
    max_consecutive_misses = 20

    for game_id in range(start_id, end_id):
        if consecutive_misses >= max_consecutive_misses:
            logger.info(f"  Stopping after {max_consecutive_misses} consecutive misses at ID {game_id}")
            break

        if (game_id - start_id) % 20 == 0:
            logger.info(f"  Progress: ID {game_id} ({len(all_games)} games found)")

        game_data = fetch_game_data(str(game_id), 'game')

        if game_data:
            all_games.append(game_data)
            consecutive_misses = 0
        else:
            consecutive_misses += 1

        time.sleep(0.15)  # Rate limiting

    logger.info(f"Fetched {len(all_games)} games")
    return all_games


def load_thesportsdb_players():
    """Load American players from TheSportsDB data."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    latest_file = os.path.join(output_dir, 'american_players_latest.json')

    if os.path.exists(latest_file):
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                players = data.get('players', [])
                logger.info(f"Loaded {len(players)} American players from TheSportsDB")
                return {normalize_name(p.get('name', '')): p for p in players}
        except Exception as e:
            logger.warning(f"Error loading TheSportsDB players: {e}")

    return {}


def build_player_game_logs(games, american_lookup):
    """Build game-by-game logs for American players from box scores."""
    game_logs = {}  # normalized name -> list of game stats

    for game in games:
        if not game.get('box_score'):
            continue

        game_date = game.get('date')
        home_team = game.get('home_team')
        away_team = game.get('away_team')

        for stat in game['box_score']:
            player_name = stat.get('name', '')
            norm_name = normalize_name(player_name)

            # Check if American
            if norm_name not in american_lookup:
                continue

            # Determine opponent
            player_team = stat.get('team')
            if player_team == home_team:
                opponent = away_team
                home_away = 'Home'
            else:
                opponent = home_team
                home_away = 'Away'

            game_entry = {
                'date': game_date,
                'round': game.get('round'),
                'opponent': opponent,
                'home_away': home_away,
                'minutes': stat.get('minutes', 0),
                'points': stat.get('points', 0),
                'rebounds': stat.get('rebounds', 0),
                'assists': stat.get('assists', 0),
                'steals': stat.get('steals', 0),
                'blocks': stat.get('blocks', 0),
                'turnovers': stat.get('turnovers', 0),
                'plus_minus': stat.get('plus_minus', 0),
                'efficiency': stat.get('efficiency', 0),
            }

            if norm_name not in game_logs:
                game_logs[norm_name] = []
            game_logs[norm_name].append(game_entry)

    # Sort each player's games by date (most recent first)
    for name in game_logs:
        game_logs[name].sort(key=lambda x: x.get('date') or '', reverse=True)

    return game_logs


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("LBA SCRAPER - ITALIAN LEGA BASKET SERIE A")
    logger.info("=" * 60)
    logger.info(f"Source: legabasket.it")
    logger.info(f"Season: {CURRENT_SEASON}")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Load existing TheSportsDB players for American identification
    tsdb_players = load_thesportsdb_players()
    american_lookup = tsdb_players.copy()

    # Fetch games by ID range
    games = fetch_all_games_by_id()

    if not games:
        # Fallback: try fetching from main page links
        games = fetch_schedule()

    # Sort by date
    games.sort(key=lambda x: x.get('date') or '')

    # Get today's date for filtering
    today = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"Today's date: {today}")

    # For future games, clear box scores (they shouldn't have stats yet)
    for game in games:
        game_date = game.get('date', '')
        if game_date > today:
            game['played'] = False
            game['box_score'] = []  # Clear invalid future stats
        elif game.get('home_score') is not None and game.get('away_score') is not None:
            game['played'] = True

    # Count played vs upcoming
    played_games = [g for g in games if g.get('played')]
    upcoming_games = [g for g in games if not g.get('played')]

    logger.info(f"Total games: {len(games)} (played: {len(played_games)}, upcoming: {len(upcoming_games)})")

    # Build game logs for Americans
    game_logs = build_player_game_logs(games, american_lookup)
    logger.info(f"Built game logs for {len(game_logs)} American players")

    # Save schedule
    schedule_data = {
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Lega Basket Serie A',
        'source': 'legabasket.it',
        'total_games': len(games),
        'played': len(played_games),
        'upcoming': len(upcoming_games),
        'games': games
    }
    save_json(schedule_data, f'lba_schedule_{timestamp}.json')
    save_json(schedule_data, 'lba_schedule_latest.json')

    # Build American player stats
    american_stats = []

    for norm_name, tsdb_player in american_lookup.items():
        player_game_log = game_logs.get(norm_name, [])

        # Calculate season averages
        games_played = len(player_game_log)
        ppg = rpg = apg = spg = bpg = 0.0

        if games_played > 0:
            total_pts = sum(g.get('points', 0) for g in player_game_log)
            total_reb = sum(g.get('rebounds', 0) for g in player_game_log)
            total_ast = sum(g.get('assists', 0) for g in player_game_log)
            total_stl = sum(g.get('steals', 0) for g in player_game_log)
            total_blk = sum(g.get('blocks', 0) for g in player_game_log)

            ppg = round(total_pts / games_played, 1)
            rpg = round(total_reb / games_played, 1)
            apg = round(total_ast / games_played, 1)
            spg = round(total_stl / games_played, 1)
            bpg = round(total_blk / games_played, 1)

        player_data = {
            'name': tsdb_player.get('name'),
            'player_code': tsdb_player.get('code'),
            'team': tsdb_player.get('team_name'),
            'games': games_played,
            'ppg': ppg,
            'rpg': rpg,
            'apg': apg,
            'spg': spg,
            'bpg': bpg,
            'game_log': player_game_log,
        }

        american_stats.append(player_data)

    # Sort by PPG
    american_stats.sort(key=lambda x: x.get('ppg', 0), reverse=True)

    logger.info(f"\nTotal American players: {len(american_stats)}")
    logger.info(f"Players with game logs: {len([p for p in american_stats if p.get('game_log')])}")

    # Save results
    results = {
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Lega Basket Serie A',
        'source': 'legabasket.it',
        'player_count': len(american_stats),
        'players': american_stats
    }

    save_json(results, f'lba_american_stats_{timestamp}.json')
    save_json(results, 'lba_american_stats_latest.json')

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Games fetched: {len(games)}")
    logger.info(f"Played: {len(played_games)}")
    logger.info(f"Upcoming: {len(upcoming_games)}")
    logger.info(f"American players: {len(american_stats)}")
    logger.info(f"With game logs: {len([p for p in american_stats if p.get('game_log')])}")

    if american_stats:
        logger.info("\nTop American Scorers:")
        for p in american_stats[:10]:
            games_count = len(p.get('game_log', []))
            if games_count > 0:
                logger.info(f"  {p['name']} ({p.get('team', 'N/A')}) - "
                           f"{p.get('ppg', 0):.1f} PPG, {p.get('rpg', 0):.1f} RPG, "
                           f"{p.get('apg', 0):.1f} APG ({games_count} games)")


if __name__ == '__main__':
    main()

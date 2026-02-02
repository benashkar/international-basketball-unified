"""
=============================================================================
LBA BOX SCORE SCRAPER - ITALIAN LEGA BASKET SERIE A
=============================================================================

PURPOSE:
    Scrapes game results and detailed box scores from legabasket.it.
    Gets player statistics for each game.

DATA SOURCE:
    Official LBA Website: https://www.legabasket.it/
    - Game pages: /game/{game_id}/{slug}
    - Uses embedded __NEXT_DATA__ JSON

OUTPUT:
    - lba_games_*.json: All games with results
    - lba_boxscores_*.json: Detailed box scores with player stats
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
BASE_URL = 'https://www.legabasket.it'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
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


def fetch_box_score(game_id):
    """Fetch detailed box score for a game."""
    # Try with a generic slug first
    url = f"{BASE_URL}/game/{game_id}/game"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')

        if not script:
            return None

        data = json.loads(script.string)
        game = data.get('props', {}).get('pageProps', {}).get('game', {})
        match = game.get('match', {})
        scores = game.get('scores', {})

        if not match:
            return None

        # Check if game has been played
        home_score = match.get('home_final_score')
        away_score = match.get('visitor_final_score')

        if home_score is None or away_score is None:
            return None  # Game not played yet

        box_score = {
            'game_id': str(game_id),
            'date': match.get('match_datetime', '')[:10] if match.get('match_datetime') else None,
            'time': f"{match.get('match_hh', '00')}:{match.get('match_mm', '00')}",
            'round': match.get('day_name') or f"Round {match.get('day_serial', '')}",
            'home_team': match.get('h_team_name'),
            'away_team': match.get('v_team_name'),
            'home_score': home_score,
            'away_score': away_score,
            'venue': match.get('plant_name'),
            'spectators': match.get('spectators'),
            'home_players': [],
            'away_players': [],
        }

        # Parse player stats for home team
        home_data = scores.get('ht', {})
        for player in home_data.get('rows', []):
            surname = player.get('player_surname', '')
            first_name = player.get('player_name', '')
            full_name = f"{first_name} {surname}".strip().title() if first_name or surname else 'Unknown'

            player_stat = {
                'name': full_name,
                'jersey': player.get('player_num', ''),
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
            box_score['home_players'].append(player_stat)

        # Parse player stats for away team
        away_data = scores.get('vt', {})
        for player in away_data.get('rows', []):
            surname = player.get('player_surname', '')
            first_name = player.get('player_name', '')
            full_name = f"{first_name} {surname}".strip().title() if first_name or surname else 'Unknown'

            player_stat = {
                'name': full_name,
                'jersey': player.get('player_num', ''),
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
            box_score['away_players'].append(player_stat)

        return box_score

    except requests.RequestException as e:
        logger.debug(f"Error fetching game {game_id}: {e}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        logger.debug(f"Error parsing game {game_id}: {e}")
        return None


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("LBA BOX SCORE SCRAPER - Italian Lega Basket Serie A")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Game IDs for 2025-26 season:
    # - Regular season starts around ID 25009
    # - Each round has 8 games (16 teams)
    # - ~30 rounds = ~240 games for regular season
    # - Plus playoffs

    start_id = 25009  # First regular season game
    end_id = 25300    # Should cover through current games + buffer

    all_games = []
    all_box_scores = []
    consecutive_misses = 0
    max_consecutive_misses = 30  # Allow more misses since IDs might not be sequential

    logger.info(f"Fetching games from ID {start_id} to {end_id}...")

    for game_id in range(start_id, end_id):
        if consecutive_misses >= max_consecutive_misses:
            logger.info(f"Stopping after {max_consecutive_misses} consecutive misses at ID {game_id}")
            break

        if (game_id - start_id) % 20 == 0:
            logger.info(f"Progress: ID {game_id} ({len(all_box_scores)} box scores found)")

        box_score = fetch_box_score(game_id)

        if box_score:
            all_box_scores.append(box_score)

            # Create game summary
            all_games.append({
                'game_id': box_score['game_id'],
                'date': box_score['date'],
                'round': box_score['round'],
                'home_team': box_score['home_team'],
                'away_team': box_score['away_team'],
                'home_score': box_score['home_score'],
                'away_score': box_score['away_score'],
                'venue': box_score['venue'],
                'played': True,
            })

            consecutive_misses = 0
        else:
            consecutive_misses += 1

        time.sleep(0.2)  # Rate limiting

    logger.info(f"Fetched {len(all_box_scores)} box scores")

    # Sort by date
    all_games.sort(key=lambda x: x.get('date') or '')
    all_box_scores.sort(key=lambda x: x.get('date') or '')

    # Save results
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Lega Basket Serie A (LBA)',
        'source': 'legabasket.it',
        'game_count': len(all_games),
        'games': all_games
    }, f'lba_games_{timestamp}.json')

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Lega Basket Serie A (LBA)',
        'source': 'legabasket.it',
        'box_score_count': len(all_box_scores),
        'box_scores': all_box_scores
    }, f'lba_boxscores_{timestamp}.json')

    # Save latest versions
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Lega Basket Serie A (LBA)',
        'source': 'legabasket.it',
        'game_count': len(all_games),
        'games': all_games
    }, 'lba_games_latest.json')

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': CURRENT_SEASON,
        'league': 'Lega Basket Serie A (LBA)',
        'source': 'legabasket.it',
        'box_score_count': len(all_box_scores),
        'box_scores': all_box_scores
    }, 'lba_boxscores_latest.json')

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total games found: {len(all_games)}")
    logger.info(f"Box scores fetched: {len(all_box_scores)}")

    total_player_stats = sum(
        len(bs.get('home_players', [])) + len(bs.get('away_players', []))
        for bs in all_box_scores
    )
    logger.info(f"Total player stat lines: {total_player_stats}")

    # Show sample game
    if all_box_scores:
        sample = all_box_scores[-1]
        logger.info(f"\nMost recent game:")
        logger.info(f"  {sample['date']}: {sample['home_team']} {sample['home_score']} - {sample['away_score']} {sample['away_team']}")


if __name__ == '__main__':
    main()

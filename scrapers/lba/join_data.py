"""
=============================================================================
JOIN DATA - LEGA BASKET SERIE A (LBA)
=============================================================================

PURPOSE:
    Combines data from multiple JSON sources into unified player records.
    This creates the final "database" that the dashboard reads from.

DATA SOURCES COMBINED:
    - american_players_*.json: Basic player info from TheSportsDB
    - american_hometowns_found_*.json: Wikipedia hometown/college data
    - schedule_*.json: Game schedule for upcoming/past games

OUTPUT:
    - unified_american_players_*.json: Complete player records with stats
    - american_players_summary_*.json: Lightweight version for dashboard list
"""

import json
import os
from glob import glob
from datetime import datetime
import logging
import unicodedata

# positions: For converting position numbers to names (1=PG, 2=SG, etc.)
from positions import get_position_name

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_latest_json(pattern):
    """Load the most recent JSON file matching the pattern."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    files = sorted(glob(os.path.join(output_dir, pattern)))

    if not files:
        logger.warning(f"No files found matching: {pattern}")
        return None

    filepath = files[-1]
    logger.info(f"Loading: {os.path.basename(filepath)}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_best_schedule():
    """Load the schedule file with the most games."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')

    # Try latest schedule first
    schedule_file = os.path.join(output_dir, 'schedule_latest.json')
    if os.path.exists(schedule_file):
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                game_count = len(data.get('games', []))
                logger.info(f"Loading schedule: schedule_latest.json ({game_count} games)")
                return data
        except Exception as e:
            logger.warning(f"Error reading schedule: {e}")

    # Fallback to timestamped files
    files = sorted(glob(os.path.join(output_dir, 'schedule_*.json')))

    if not files:
        logger.warning("No schedule files found")
        return None

    # Find file with most games
    best_file = None
    best_count = 0

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                game_count = len(data.get('games', []))
                if game_count > best_count:
                    best_count = game_count
                    best_file = filepath
        except Exception as e:
            logger.warning(f"Error reading {filepath}: {e}")

    if best_file:
        logger.info(f"Loading schedule: {os.path.basename(best_file)} ({best_count} games)")
        with open(best_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    return None


def save_json(data, filename):
    """Save data to a JSON file."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    logger.info(f"Saved: {filepath}")


def normalize_name(name):
    """Normalize player name for matching."""
    if not name:
        return ''
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    return name.lower().strip()


def cm_to_feet_inches(height_str):
    """Convert height string to feet and inches."""
    if not height_str:
        return None, None

    try:
        # Try to extract cm from string like "6 ft 5 in (196 cm)"
        import re
        cm_match = re.search(r'(\d+)\s*cm', height_str.lower())
        if cm_match:
            cm = int(cm_match.group(1))
            total_inches = cm / 2.54
            feet = int(total_inches // 12)
            inches = int(round(total_inches % 12))
            if inches == 12:
                feet += 1
                inches = 0
            return feet, inches

        # Try feet/inches format like "6 ft 5 in"
        ft_match = re.search(r"(\d+)\s*(?:ft|')", height_str.lower())
        in_match = re.search(r"(\d+)\s*(?:in|\")", height_str.lower())
        if ft_match:
            feet = int(ft_match.group(1))
            inches = int(in_match.group(1)) if in_match else 0
            return feet, inches

        # Try meters format like "1.96 m"
        m_match = re.search(r'(\d+\.?\d*)\s*m', height_str.lower())
        if m_match:
            meters = float(m_match.group(1))
            cm = meters * 100
            total_inches = cm / 2.54
            feet = int(total_inches // 12)
            inches = int(round(total_inches % 12))
            if inches == 12:
                feet += 1
                inches = 0
            return feet, inches

    except Exception as e:
        logger.debug(f"Could not parse height '{height_str}': {e}")

    return None, None


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("LEGA BASKET SERIE A - JOIN DATA")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # =========================================================================
    # Load All Data Sources
    # =========================================================================
    players_data = load_latest_json('american_players_*.json')
    hometowns_data = load_latest_json('american_hometowns_found_*.json')
    schedule_data = load_best_schedule()

    if not players_data:
        logger.error("No player data found. Run daily_scraper.py first.")
        return

    players = players_data.get('players', [])
    logger.info(f"Loaded {len(players)} American players")

    # Build hometown lookup dictionary
    hometown_lookup = {}
    if hometowns_data:
        for p in hometowns_data.get('players', []):
            code = p.get('code')
            if code:
                hometown_lookup[code] = p
        logger.info(f"Loaded {len(hometown_lookup)} hometown records")

    # Build games by team (both past and upcoming)
    past_by_team = {}
    upcoming_by_team = {}
    if schedule_data:
        for game in schedule_data.get('games', []):
            home_team = game.get('home_team')
            away_team = game.get('away_team')
            played = game.get('played', False)

            game_info = {
                'date': game.get('date'),
                'round': game.get('round'),
                'venue': game.get('venue'),
                'home_team': home_team,
                'away_team': away_team,
                'home_score': game.get('home_score'),
                'away_score': game.get('away_score'),
                'played': played,
            }

            target_dict = past_by_team if played else upcoming_by_team

            if home_team:
                if home_team not in target_dict:
                    target_dict[home_team] = []
                target_dict[home_team].append({
                    **game_info,
                    'opponent': away_team,
                    'home_away': 'Home',
                    'team_score': game.get('home_score'),
                    'opponent_score': game.get('away_score'),
                    'result': 'W' if played and (game.get('home_score') or 0) > (game.get('away_score') or 0) else ('L' if played else None),
                })

            if away_team:
                if away_team not in target_dict:
                    target_dict[away_team] = []
                target_dict[away_team].append({
                    **game_info,
                    'opponent': home_team,
                    'home_away': 'Away',
                    'team_score': game.get('away_score'),
                    'opponent_score': game.get('home_score'),
                    'result': 'W' if played and (game.get('away_score') or 0) > (game.get('home_score') or 0) else ('L' if played else None),
                })

        # Sort games
        for team in past_by_team:
            past_by_team[team].sort(key=lambda x: x.get('date') or '', reverse=True)
        for team in upcoming_by_team:
            upcoming_by_team[team].sort(key=lambda x: x.get('date') or '')

        logger.info(f"Built past games for {len(past_by_team)} teams")
        logger.info(f"Built upcoming games for {len(upcoming_by_team)} teams")

    # =========================================================================
    # Build Unified Player Records
    # =========================================================================
    unified_players = []

    for player in players:
        code = player.get('code')
        player_name = player.get('name', '')

        # Get hometown data if available
        hometown = hometown_lookup.get(code, {})

        # Get games for player's team
        team_name = player.get('team_name')
        past_games = past_by_team.get(team_name, [])
        upcoming_games = upcoming_by_team.get(team_name, [])

        # Parse height
        height_feet, height_inches = cm_to_feet_inches(player.get('height_str'))

        # Build unified record
        unified = {
            'code': code,
            'name': player_name,
            'team': team_name,
            'team_code': player.get('team_code'),
            'position': get_position_name(player.get('position')),
            'jersey': player.get('jersey'),
            'height_cm': None,
            'height_feet': height_feet,
            'height_inches': height_inches,
            'weight': player.get('weight'),
            'birth_date': player.get('birth_date'),
            'nationality': player.get('nationality'),
            'birth_location': player.get('birth_location'),
            'hometown_city': hometown.get('hometown_city'),
            'hometown_state': hometown.get('hometown_state'),
            'hometown': f"{hometown.get('hometown_city')}, {hometown.get('hometown_state')}" if hometown.get('hometown_city') and hometown.get('hometown_state') else None,
            'college': hometown.get('college'),
            'high_school': hometown.get('high_school'),
            'headshot_url': player.get('headshot_url'),
            'instagram': player.get('instagram'),
            'twitter': player.get('twitter'),
            # No box score stats yet - would need legabasket.it scraper
            'games_played': 0,
            'ppg': 0.0,
            'rpg': 0.0,
            'apg': 0.0,
            'game_log': [],
            'past_games': past_games,
            'upcoming_games': upcoming_games,
            'season': '2025-26',
            'league': 'Lega Basket Serie A',
        }

        unified_players.append(unified)

    # Sort by name
    unified_players.sort(key=lambda x: x.get('name', ''))

    logger.info(f"Created {len(unified_players)} unified player records")

    # =========================================================================
    # Save Full Unified Data
    # =========================================================================
    unified_data = {
        'export_date': datetime.now().isoformat(),
        'season': '2025-26',
        'league': 'Lega Basket Serie A',
        'player_count': len(unified_players),
        'players': unified_players
    }

    save_json(unified_data, f'unified_american_players_{timestamp}.json')
    save_json(unified_data, 'unified_american_players_latest.json')

    # =========================================================================
    # Save Summary Version
    # =========================================================================
    summary_players = []
    for p in unified_players:
        summary_players.append({
            'code': p['code'],
            'name': p['name'],
            'team': p['team'],
            'team_code': p['team_code'],
            'position': p['position'],
            'jersey': p['jersey'],
            'height_feet': p['height_feet'],
            'height_inches': p['height_inches'],
            'birth_date': p['birth_date'],
            'hometown': p['hometown'],
            'hometown_state': p['hometown_state'],
            'college': p['college'],
            'high_school': p['high_school'],
            'headshot_url': p['headshot_url'],
            'games_played': p['games_played'],
            'ppg': p['ppg'],
            'rpg': p['rpg'],
            'apg': p['apg'],
        })

    summary_data = {
        'export_date': datetime.now().isoformat(),
        'season': '2025-26',
        'league': 'Lega Basket Serie A',
        'player_count': len(summary_players),
        'players': summary_players
    }

    save_json(summary_data, f'american_players_summary_{timestamp}.json')
    save_json(summary_data, 'american_players_summary_latest.json')

    # =========================================================================
    # Summary
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total players: {len(unified_players)}")

    with_hometown = sum(1 for p in unified_players if p.get('hometown'))
    with_college = sum(1 for p in unified_players if p.get('college'))

    logger.info(f"With hometown: {with_hometown}")
    logger.info(f"With college: {with_college}")

    if unified_players:
        logger.info("\nPlayers:")
        for p in unified_players[:15]:
            ht = f"{p['hometown']}" if p.get('hometown') else "Unknown"
            logger.info(f"  {p['name']} - {p['team']} | {ht}")


if __name__ == '__main__':
    main()

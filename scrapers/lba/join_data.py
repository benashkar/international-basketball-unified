"""
=============================================================================
JOIN DATA - LEGA BASKET SERIE A (LBA)
=============================================================================

PURPOSE:
    Combines data from multiple JSON sources into unified player records.
    This creates the final "database" that the dashboard reads from.

DATA SOURCES COMBINED:
    - lba_american_stats_*.json: Stats from eurobasket.com (PRIMARY SOURCE)
    - american_players_*.json: Basic player info from TheSportsDB
    - american_hometowns_found_*.json: Wikipedia hometown/college data
    - lba_schedule_*.json: Full schedule with upcoming games

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


def load_lba_stats():
    """Load LBA scraper stats (PRIMARY SOURCE for stats)."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    latest_file = os.path.join(output_dir, 'lba_american_stats_latest.json')

    if os.path.exists(latest_file):
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                players = data.get('players', [])
                logger.info(f"Loaded {len(players)} players from LBA scraper")
                # Return both full list and lookup dict
                lookup = {normalize_name(p.get('name', '')): p for p in players}
                return players, lookup
        except Exception as e:
            logger.warning(f"Error loading LBA stats: {e}")

    logger.warning("No LBA stats found. Run lba_scraper.py first.")
    return [], {}


def load_lba_schedule():
    """Load LBA schedule from eurobasket.com scraper."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')

    # Try LBA schedule first (from lba_scraper.py)
    lba_file = os.path.join(output_dir, 'lba_schedule_latest.json')
    if os.path.exists(lba_file):
        try:
            with open(lba_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                game_count = len(data.get('games', []))
                upcoming = data.get('upcoming', 0)
                logger.info(f"Loading LBA schedule: {game_count} games ({upcoming} upcoming)")
                return data
        except Exception as e:
            logger.warning(f"Error reading LBA schedule: {e}")

    # Fallback to TheSportsDB schedule
    return load_best_schedule()


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("LEGA BASKET SERIE A - JOIN DATA")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # =========================================================================
    # Load All Data Sources
    # =========================================================================
    # LBA scraper stats - PRIMARY SOURCE for game stats
    lba_players, lba_stats_lookup = load_lba_stats()

    # TheSportsDB players - for enrichment (headshots, position, etc.)
    players_data = load_latest_json('american_players_*.json')
    hometowns_data = load_latest_json('american_hometowns_found_*.json')

    # LBA schedule - for upcoming games
    schedule_data = load_lba_schedule()

    # Build TheSportsDB lookup for enrichment
    tsdb_lookup = {}
    if players_data:
        for p in players_data.get('players', []):
            norm_name = normalize_name(p.get('name', ''))
            if norm_name:
                tsdb_lookup[norm_name] = p
        logger.info(f"Loaded {len(tsdb_lookup)} players from TheSportsDB for enrichment")

    # If no LBA stats, fall back to TheSportsDB
    if not lba_players:
        if not players_data:
            logger.error("No player data found. Run lba_scraper.py or daily_scraper.py first.")
            return
        # Use TheSportsDB as source
        lba_players = players_data.get('players', [])
        logger.warning("Using TheSportsDB as primary source (no LBA stats available)")

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
    # Build Unified Player Records (LBA stats as PRIMARY SOURCE)
    # =========================================================================
    unified_players = []

    for player in lba_players:
        player_name = player.get('name', '')
        norm_name = normalize_name(player_name)

        # Get TheSportsDB data for enrichment
        tsdb_player = tsdb_lookup.get(norm_name, {})
        code = player.get('player_code') or tsdb_player.get('code')

        # Get hometown data if available
        hometown = hometown_lookup.get(code, {})

        # Get team name (prefer LBA data, fallback to TheSportsDB)
        team_name = player.get('team') or tsdb_player.get('team_name')

        # Get games for player's team (try multiple team name formats)
        past_games = past_by_team.get(team_name, [])
        upcoming_games = upcoming_by_team.get(team_name, [])

        # Also try without full name (e.g., "Brescia" instead of "Germani Brescia")
        if not upcoming_games and team_name:
            for team_key in upcoming_by_team:
                if team_name in team_key or team_key in team_name:
                    upcoming_games = upcoming_by_team[team_key]
                    break

        # Parse height from TheSportsDB
        height_feet, height_inches = cm_to_feet_inches(tsdb_player.get('height_str'))

        # Get game log from LBA scraper
        game_log = player.get('game_log', [])

        # Get stats from LBA scraper (or calculate from game log)
        games_played = player.get('games') or len(game_log)
        ppg = player.get('ppg', 0.0)
        rpg = player.get('rpg', 0.0)
        apg = player.get('apg', 0.0)

        # Build unified record
        unified = {
            'code': code,
            'name': player_name,
            'team': team_name,
            'team_code': tsdb_player.get('team_code'),
            'position': get_position_name(tsdb_player.get('position')),
            'jersey': tsdb_player.get('jersey'),
            'height_cm': None,
            'height_feet': height_feet,
            'height_inches': height_inches,
            'weight': tsdb_player.get('weight'),
            'birth_date': (tsdb_player.get('birth_date', '') or '')[:10] or None,  # Truncate to YYYY-MM-DD
            'nationality': tsdb_player.get('nationality') or 'United States',
            'birth_location': tsdb_player.get('birth_location'),
            'hometown_city': hometown.get('hometown_city'),
            'hometown_state': hometown.get('hometown_state'),
            'hometown': f"{hometown.get('hometown_city')}, {hometown.get('hometown_state')}" if hometown.get('hometown_city') and hometown.get('hometown_state') else None,
            'college': hometown.get('college'),
            'high_school': hometown.get('high_school'),
            'headshot_url': tsdb_player.get('headshot_url'),
            'instagram': tsdb_player.get('instagram'),
            'twitter': tsdb_player.get('twitter'),
            # Stats from LBA scraper (eurobasket.com)
            'games_played': games_played,
            'ppg': ppg,
            'rpg': rpg,
            'apg': apg,
            'game_log': game_log,
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

    with_stats = sum(1 for p in unified_players if p.get('ppg', 0) > 0)
    with_game_log = sum(1 for p in unified_players if p.get('game_log'))
    with_upcoming = sum(1 for p in unified_players if p.get('upcoming_games'))

    logger.info(f"With stats: {with_stats}")
    logger.info(f"With game log: {with_game_log}")
    logger.info(f"With upcoming games: {with_upcoming}")

    if unified_players:
        # Sort by PPG for display
        sorted_players = sorted(unified_players, key=lambda x: x.get('ppg', 0), reverse=True)
        logger.info("\nTop Players:")
        for p in sorted_players[:15]:
            games = len(p.get('game_log', []))
            upcoming = len(p.get('upcoming_games', []))
            logger.info(f"  {p['name']} - {p['team']} | {p.get('ppg', 0):.1f} PPG ({games} games, {upcoming} upcoming)")


if __name__ == '__main__':
    main()

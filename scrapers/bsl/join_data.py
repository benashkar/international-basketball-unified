"""
=============================================================================
JOIN DATA - TURKISH BSL
=============================================================================

PURPOSE:
    Combines data from multiple JSON sources into unified player records.
"""

import json
import os
from glob import glob
from datetime import datetime
import logging

# positions: For converting position numbers to names (1=PG, 2=SG, etc.)
from positions import get_position_name

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Team name mapping: TheSportsDB name -> TBLStat name
TEAM_NAME_MAP = {
    'Anadolu Efes SK': 'Anadolu Efes',
    'Bahçeşehir Koleji SK': 'Bahçeşehir Koleji',
    'Besiktas Basketbol': 'Beşiktaş GAİN',
    'Büyükçekmece Basketbol': 'ONVO Büyükçekmece',
    'Fenerbahçe Basketbol': 'Fenerbahçe Beko',
    # These match already
    'Bursaspor Basketbol': 'Bursaspor Basketbol',
}


def load_latest_json(pattern):
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    files = sorted(glob(os.path.join(output_dir, pattern)))

    if not files:
        logger.warning(f"No files found matching: {pattern}")
        return None

    filepath = files[-1]
    logger.info(f"Loading: {os.path.basename(filepath)}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_bsl_stats():
    """Load BSL statistics from bsl_scraper output.

    Returns both the full player list and a lookup dictionary.
    The BSL scraper data is the PRIMARY source for American players
    since it directly scrapes TBLStat.net and finds all 32+ Americans.
    """
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    filepath = os.path.join(output_dir, 'bsl_american_stats_latest.json')

    if not os.path.exists(filepath):
        logger.warning("No BSL stats file found. Run bsl_scraper.py first.")
        return [], {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            players = data.get('players', [])
            logger.info(f"Loaded BSL stats for {len(players)} American players")

            # Build lookup by normalized name for enrichment matching
            import unicodedata
            lookup = {}
            for p in players:
                name = p.get('name', '')
                # Normalize name
                name_norm = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
                name_norm = name_norm.lower().strip()
                lookup[name_norm] = p
            return players, lookup
    except Exception as e:
        logger.warning(f"Error loading BSL stats: {e}")
        return [], {}


def load_best_schedule():
    """Load the schedule file with the most games (BSL preferred over TheSportsDB)."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')

    # Prefer BSL schedule from TBLStat.net (more complete)
    bsl_schedule = os.path.join(output_dir, 'bsl_schedule_latest.json')
    if os.path.exists(bsl_schedule):
        try:
            with open(bsl_schedule, 'r', encoding='utf-8') as f:
                data = json.load(f)
                game_count = len(data.get('games', []))
                logger.info(f"Loading BSL schedule: bsl_schedule_latest.json ({game_count} games)")
                return data
        except Exception as e:
            logger.warning(f"Error reading BSL schedule: {e}")

    # Fallback to TheSportsDB schedule files
    files = sorted(glob(os.path.join(output_dir, 'schedule_*.json')))

    if not files:
        logger.warning("No schedule files found")
        return None

    # Find the file with the most games
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
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    logger.info(f"Saved: {filepath}")


def main():
    logger.info("=" * 60)
    logger.info("TURKISH BSL - JOIN DATA")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # PRIMARY SOURCE: BSL scraper data (finds all 32+ American players)
    bsl_players, bsl_lookup = load_bsl_stats()

    # ENRICHMENT SOURCES: TheSportsDB for bio info, Wikipedia for hometowns
    thesportsdb_data = load_latest_json('american_players_2*.json')
    hometowns_data = load_latest_json('american_hometowns_found_*.json')
    schedule_data = load_best_schedule()

    if not bsl_players:
        logger.error("No BSL player data found. Run bsl_scraper.py first.")
        return

    logger.info(f"Using {len(bsl_players)} American players from BSL scraper as primary source")

    # Build TheSportsDB lookup by normalized name for enrichment
    import unicodedata
    thesportsdb_lookup = {}
    if thesportsdb_data:
        for p in thesportsdb_data.get('players', []):
            name = p.get('name', '')
            name_norm = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
            name_norm = name_norm.lower().strip()
            thesportsdb_lookup[name_norm] = p
        logger.info(f"Loaded {len(thesportsdb_lookup)} players from TheSportsDB for enrichment")

    # Build hometown lookup by TheSportsDB code
    hometown_lookup = {}
    if hometowns_data:
        for p in hometowns_data.get('players', []):
            code = p.get('code')
            if code:
                hometown_lookup[code] = p
        logger.info(f"Loaded {len(hometown_lookup)} hometown records")

    # Build all games by team (both past and upcoming)
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
                    'result': 'W' if played and game.get('home_score', 0) > game.get('away_score', 0) else ('L' if played else None),
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
                    'result': 'W' if played and game.get('away_score', 0) > game.get('home_score', 0) else ('L' if played else None),
                })

        for team in past_by_team:
            past_by_team[team].sort(key=lambda x: x.get('date', ''), reverse=True)
        for team in upcoming_by_team:
            upcoming_by_team[team].sort(key=lambda x: x.get('date', ''))

        logger.info(f"Built past games for {len(past_by_team)} teams")
        logger.info(f"Built upcoming games for {len(upcoming_by_team)} teams")

    unified_players = []

    # Loop through BSL players as primary source (all 32+ Americans)
    for bsl_player in bsl_players:
        player_name = bsl_player.get('name', '')
        team_name = bsl_player.get('team', '')

        # Normalize name for matching to TheSportsDB enrichment
        name_norm = unicodedata.normalize('NFKD', player_name).encode('ASCII', 'ignore').decode('ASCII')
        name_norm = name_norm.lower().strip()

        # Try to find matching TheSportsDB data for enrichment (bio info)
        tsdb_player = thesportsdb_lookup.get(name_norm, {})
        code = tsdb_player.get('code') or bsl_player.get('tblstat_id')

        # Get hometown data if we have a TheSportsDB match
        hometown = hometown_lookup.get(tsdb_player.get('code'), {})

        # Get team schedule - try both BSL team name and TheSportsDB mapped name
        past_games = past_by_team.get(team_name, [])
        upcoming_games = upcoming_by_team.get(team_name, [])

        # If no games found, try reverse mapping (TheSportsDB -> TBLStat)
        if not past_games and not upcoming_games:
            for tsdb_name, bsl_name in TEAM_NAME_MAP.items():
                if bsl_name == team_name:
                    past_games = past_by_team.get(tsdb_name, [])
                    upcoming_games = upcoming_by_team.get(tsdb_name, [])
                    break

        # Stats come directly from BSL data
        games_played = bsl_player.get('games', 0)
        ppg = bsl_player.get('ppg', 0.0)
        rpg = bsl_player.get('rpg', 0.0)
        apg = bsl_player.get('apg', 0.0)
        spg = bsl_player.get('spg', 0.0)
        minutes = bsl_player.get('minutes', 0.0)

        logger.debug(f"  {player_name} ({team_name}): {ppg:.1f} PPG, {games_played} games")

        unified = {
            # Use TheSportsDB code if available, otherwise use TBLStat ID
            'code': code,
            'name': player_name,
            'team': team_name,
            'team_code': tsdb_player.get('team_code'),
            # Position from TheSportsDB if available
            'position': get_position_name(tsdb_player.get('position')),
            'jersey': tsdb_player.get('jersey'),
            # Physical attributes from TheSportsDB
            'height_cm': tsdb_player.get('height_cm'),
            'height_feet': tsdb_player.get('height_feet'),
            'height_inches': tsdb_player.get('height_inches'),
            'weight': tsdb_player.get('weight'),
            # Personal info from TheSportsDB
            'birth_date': tsdb_player.get('birth_date'),
            'nationality': 'United States',  # All are American
            'birth_location': tsdb_player.get('birth_location'),
            # Hometown from Wikipedia scraper
            'hometown_city': hometown.get('hometown_city'),
            'hometown_state': hometown.get('hometown_state'),
            'hometown': f"{hometown.get('hometown_city')}, {hometown.get('hometown_state')}" if hometown.get('hometown_city') and hometown.get('hometown_state') else None,
            'college': hometown.get('college'),
            'high_school': hometown.get('high_school'),
            # Media from TheSportsDB
            'headshot_url': tsdb_player.get('headshot_url'),
            'instagram': tsdb_player.get('instagram'),
            'twitter': tsdb_player.get('twitter'),
            # Stats directly from BSL scraper (TBLStat.net)
            'games_played': games_played,
            'ppg': ppg,
            'rpg': rpg,
            'apg': apg,
            'spg': spg,
            'minutes': minutes,
            'ft_pct': bsl_player.get('ft_pct', 0),
            'fg2_pct': bsl_player.get('fg2_pct', 0),
            'fg3_pct': bsl_player.get('fg3_pct', 0),
            'efficiency': bsl_player.get('efficiency', 0),
            'game_log': bsl_player.get('game_log', []),
            # Team schedule
            'past_games': past_games,
            'upcoming_games': upcoming_games,
            # Season info
            'season': '2025-26',
            'league': 'Turkish BSL',
        }

        unified_players.append(unified)

    unified_players.sort(key=lambda x: x.get('name', ''))

    logger.info(f"Created {len(unified_players)} unified player records")

    unified_data = {
        'export_date': datetime.now().isoformat(),
        'season': '2025-26',
        'league': 'Turkish BSL',
        'player_count': len(unified_players),
        'players': unified_players
    }
    save_json(unified_data, f'unified_american_players_{timestamp}.json')
    save_json(unified_data, 'unified_american_players_latest.json')  # For dashboard

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
        'league': 'Turkish BSL',
        'player_count': len(summary_players),
        'players': summary_players
    }
    save_json(summary_data, f'american_players_summary_{timestamp}.json')
    save_json(summary_data, 'american_players_summary_latest.json')  # For dashboard

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

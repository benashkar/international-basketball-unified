"""
=============================================================================
GREEK BASKET LEAGUE - JOIN DATA
=============================================================================
Combines TheSportsDB player data into unified format for the dashboard.
"""

import json
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_json(filename):
    """Load JSON file from output directory."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}")
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


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
    logger.info("GREEK BASKET LEAGUE - JOIN DATA")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Load American players data
    american_data = load_json('esake_american_stats_latest.json')
    if not american_data:
        logger.error("No American player data found")
        return

    players = american_data.get('players', [])
    logger.info(f"Loaded {len(players)} American players")

    # Load teams data
    teams_data = load_json('esake_schedule_latest.json')
    teams_lookup = {}
    if teams_data:
        for team in teams_data.get('teams', []):
            teams_lookup[team.get('id')] = team
            teams_lookup[team.get('name')] = team

    # Build unified player records
    unified_players = []

    for player in players:
        team_info = teams_lookup.get(player.get('team_id')) or teams_lookup.get(player.get('team')) or {}

        # Parse height to feet/inches
        height_cm = player.get('height_cm')
        height_feet = None
        height_inches = None
        if height_cm:
            total_inches = height_cm / 2.54
            height_feet = int(total_inches // 12)
            height_inches = int(total_inches % 12)

        unified = {
            # Basic info
            'code': player.get('id'),
            'name': player.get('name'),
            'team': player.get('team'),
            'team_logo': player.get('team_logo') or team_info.get('logo'),
            'position': player.get('position'),
            'nationality': player.get('nationality', 'USA'),

            # Physical
            'height_cm': height_cm,
            'height_feet': height_feet,
            'height_inches': height_inches,

            # Personal
            'birthdate': player.get('birthdate'),
            'birthplace': player.get('birthplace'),

            # Images
            'headshot_url': player.get('cutout') or player.get('thumb'),

            # Stats (TheSportsDB doesn't provide game stats)
            'games_played': 0,
            'ppg': 0,
            'rpg': 0,
            'apg': 0,
            'game_log': [],

            # Description
            'description': player.get('description'),
        }

        unified_players.append(unified)

    # Sort by name
    unified_players.sort(key=lambda x: x.get('name', ''))

    # Save unified data
    output = {
        'export_date': datetime.now().isoformat(),
        'season': '2025-26',
        'league': 'Greek Basket League (ESAKE)',
        'player_count': len(unified_players),
        'players': unified_players,
    }

    save_json(output, f'unified_american_players_{timestamp}.json')
    save_json(output, 'unified_american_players_latest.json')

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total players: {len(unified_players)}")

    # Count by team
    teams = {}
    for p in unified_players:
        t = p.get('team', 'Unknown')
        teams[t] = teams.get(t, 0) + 1

    logger.info("\nPlayers by team:")
    for t, count in sorted(teams.items()):
        logger.info(f"  {t}: {count}")


if __name__ == '__main__':
    main()

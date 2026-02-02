"""
=============================================================================
FRENCH LNB - JOIN DATA
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
    logger.info("FRENCH LNB - JOIN DATA")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Load American players data
    american_data = load_json('lnb_american_stats_latest.json')
    if not american_data:
        logger.error("No American player data found")
        return

    players = american_data.get('players', [])
    logger.info(f"Loaded {len(players)} American players")

    # Load teams data
    teams_data = load_json('lnb_schedule_latest.json')
    teams_lookup = {}
    if teams_data:
        for team in teams_data.get('teams', []):
            teams_lookup[team.get('id')] = team
            teams_lookup[team.get('name')] = team

    # Load box scores to build game logs
    boxscores_data = load_json('lnb_boxscores_latest.json')
    player_games = {}  # player_name -> list of game performances

    if boxscores_data:
        for box in boxscores_data.get('box_scores', []):
            game_date = box.get('date')
            home_team = box.get('home_team')
            away_team = box.get('away_team')
            home_score = box.get('home_score')
            away_score = box.get('away_score')

            # Process home players
            for p in box.get('home_players', []):
                name = p.get('name', '').strip()
                if not name:
                    continue
                if name not in player_games:
                    player_games[name] = []
                player_games[name].append({
                    'date': game_date,
                    'opponent': away_team,
                    'home_away': 'Home',
                    'team_score': home_score,
                    'opp_score': away_score,
                    'result': 'W' if (home_score or 0) > (away_score or 0) else 'L',
                    'minutes': p.get('minutes'),
                    'points': p.get('points', 0),
                    'rebounds': p.get('rebounds', 0),
                    'assists': p.get('assists', 0),
                    'steals': p.get('steals', 0),
                    'blocks': p.get('blocks', 0),
                    'turnovers': p.get('turnovers', 0),
                })

            # Process away players
            for p in box.get('away_players', []):
                name = p.get('name', '').strip()
                if not name:
                    continue
                if name not in player_games:
                    player_games[name] = []
                player_games[name].append({
                    'date': game_date,
                    'opponent': home_team,
                    'home_away': 'Away',
                    'team_score': away_score,
                    'opp_score': home_score,
                    'result': 'W' if (away_score or 0) > (home_score or 0) else 'L',
                    'minutes': p.get('minutes'),
                    'points': p.get('points', 0),
                    'rebounds': p.get('rebounds', 0),
                    'assists': p.get('assists', 0),
                    'steals': p.get('steals', 0),
                    'blocks': p.get('blocks', 0),
                    'turnovers': p.get('turnovers', 0),
                })

        # Sort games by date (most recent first)
        for name in player_games:
            player_games[name].sort(key=lambda x: x.get('date') or '', reverse=True)

        logger.info(f"Built game logs for {len(player_games)} players from {len(boxscores_data.get('box_scores', []))} box scores")

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

        # Get game log for this player (try exact name match first, then partial)
        player_name = player.get('name', '')
        game_log = player_games.get(player_name, [])

        # If no exact match, try to find partial matches
        if not game_log:
            name_lower = player_name.lower()
            for box_name, games in player_games.items():
                if name_lower in box_name.lower() or box_name.lower() in name_lower:
                    game_log = games
                    break

        # Calculate stats from game log
        games_played = len(game_log)
        ppg = sum(g.get('points', 0) for g in game_log) / games_played if games_played > 0 else 0
        rpg = sum(g.get('rebounds', 0) for g in game_log) / games_played if games_played > 0 else 0
        apg = sum(g.get('assists', 0) for g in game_log) / games_played if games_played > 0 else 0

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

            # Stats from box scores
            'games_played': games_played,
            'ppg': round(ppg, 1),
            'rpg': round(rpg, 1),
            'apg': round(apg, 1),
            'game_log': game_log,

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
        'league': 'French Betclic Elite (Pro A)',
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

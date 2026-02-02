"""
=============================================================================
GREEK BASKET LEAGUE - JOIN DATA
=============================================================================
Combines TheSportsDB player data into unified format for the dashboard.
"""

import json
import os
import logging
import re
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Manual mapping: English name -> Greek box score name patterns
# The box scores use Greek transliterated names in LASTNAME FIRSTNAME format
AMERICAN_PLAYER_MAPPINGS = {
    'Alec Peters': ['ΠΙΤΕΡΣAΛΕΚ'],
    'Bryn Forbes': ['ΦΟΡΜΠΣΜΠΡAΙAΝ', '##ΦΟΡΜΠΣΜΠΡAΙAΝ'],
    'Darral Willis': ['ΓΟΥΙΛΙΣΝΤΑΡΑΛ', 'ΓΟΥΙΛΛΙΣΝΤΑΡΑΛ'],
    'Daryl Macon': ['ΜΕΪΚΟΝΝΤAΡΙΛ'],
    'Devin Cannady': ['ΚAΝAΝΤΙΝΤΕΒΙΝ'],
    'Donta Hall': ['ΧΟΛΝΤΟΝΤA'],
    'Frank Bartley': ['ΜΠAΡΤΛΕΪΦΡAΝΚ'],
    'Jacob Grandison': ['ΓΚΡΑΝΤΙΣΟΝΤΖΕΪΚΟΜΠ', 'ΓΚΡAΝΤΙΣΟΝΤΖΕΪΚΟΜΠ'],
    'Jerian Grant': ['ΓΚΡAΝΤΤΖΕΡΙAΝ'],
    'Jordan Davis': ['ΝΤΕΪΒΙΣΤΖΟΡΝΤΑΝ', 'ΝΤΑΒΙΣΤΖΟΡΝΤΑΝ'],
    'Justin Wright-Foreman': ['ΡAΪΤ-ΦΟΡΕΜAΝΤΖAΣΤΙΝ'],
    'Kendrick Nunn': ['ΝAΝΚΕΝΤΡΙΚ'],
    'Kenneth Faried': ['ΦAΡΙΝΤΚΕΝΕΘ'],
    'Monté Morris': ['ΜΟΡΙΣΜΟΝΤΕ ΡΟΜΠΕΡΤ', 'ΜΟΡΙΣΜΟΝΤΕ'],
    'RaiQuan Gray': ['ΓΚΡΕΙΡAΙΚΟΥAΝ'],
    'Rayjon Tucker': ['ΤAΚΕΡΡΕΪΤΖΟΝ', 'ΤΑΚΕΡΡΕΪΤΖΟΝ'],
    'Sharife Cooper': ['ΚΟΥΠΕΡΣΑΡΙΦΕ', 'ΚΟΥΠΕΡΣΑΡΗΦΕ'],
}

# Greek to Latin transliteration map
GREEK_TO_LATIN = {
    'Α': 'A', 'Β': 'V', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'I',
    'Θ': 'TH', 'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M', 'Ν': 'N', 'Ξ': 'X',
    'Ο': 'O', 'Π': 'P', 'Ρ': 'R', 'Σ': 'S', 'Τ': 'T', 'Υ': 'Y', 'Φ': 'F',
    'Χ': 'CH', 'Ψ': 'PS', 'Ω': 'O',
    'α': 'a', 'β': 'v', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'i',
    'θ': 'th', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x',
    'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's', 'ς': 's', 'τ': 't', 'υ': 'y',
    'φ': 'f', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
    # Common digraphs
    'ΓΚ': 'G', 'γκ': 'g', 'ΜΠ': 'B', 'μπ': 'b', 'ΝΤ': 'D', 'ντ': 'd',
    'ΟΥ': 'U', 'ου': 'u', 'ΑΙ': 'E', 'αι': 'e', 'ΕΙ': 'I', 'ει': 'i',
    'ΟΙ': 'I', 'οι': 'i', 'ΑΥ': 'AV', 'αυ': 'av', 'ΕΥ': 'EV', 'ευ': 'ev',
}


def transliterate_greek(text):
    """Convert Greek text to Latin characters."""
    if not text:
        return ''

    result = text
    # Handle digraphs first (longer sequences)
    for greek, latin in sorted(GREEK_TO_LATIN.items(), key=lambda x: -len(x[0])):
        result = result.replace(greek, latin)

    # Remove any remaining non-ASCII characters
    result = ''.join(c if ord(c) < 128 else '' for c in result)
    return result.strip()


def normalize_name(name):
    """Normalize a name for comparison."""
    if not name:
        return ''
    # Transliterate if contains Greek
    name = transliterate_greek(name)
    # Lowercase, remove punctuation, extra spaces
    name = re.sub(r'[^a-zA-Z\s]', '', name.lower())
    name = ' '.join(name.split())
    return name


def match_names(english_name, greek_names_dict):
    """
    Try to match an English name to a Greek name in the box scores.
    Returns the matching Greek name key or None.
    """
    if not english_name:
        return None

    # Normalize the English name
    eng_normalized = normalize_name(english_name)
    eng_parts = eng_normalized.split()

    if not eng_parts:
        return None

    # Try each Greek name
    best_match = None
    best_score = 0

    for greek_name in greek_names_dict.keys():
        greek_normalized = normalize_name(greek_name)
        greek_parts = greek_normalized.split()

        if not greek_parts:
            continue

        # Count how many name parts match
        score = 0
        for eng_part in eng_parts:
            for greek_part in greek_parts:
                # Check if parts are similar (one contains the other, or close match)
                if len(eng_part) >= 3 and len(greek_part) >= 3:
                    if eng_part in greek_part or greek_part in eng_part:
                        score += 2
                    elif eng_part[:3] == greek_part[:3]:
                        score += 1

        # Bonus for matching last name (usually listed first in Greek)
        if len(eng_parts) >= 2 and len(greek_parts) >= 1:
            eng_last = eng_parts[-1]
            greek_first = greek_parts[0]
            if len(eng_last) >= 3 and len(greek_first) >= 3:
                if eng_last[:4] == greek_first[:4] or greek_first[:4] == eng_last[:4]:
                    score += 3

        if score > best_score:
            best_score = score
            best_match = greek_name

    # Only return match if score is high enough
    if best_score >= 3:
        return best_match
    return None


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

    # Load box scores to build game logs
    boxscores_data = load_json('esake_boxscores_latest.json')
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

        # Get game log for this player
        player_name = player.get('name', '')
        game_log = []
        matched_name = None

        # First, try manual mapping (most reliable)
        if player_name in AMERICAN_PLAYER_MAPPINGS:
            for greek_pattern in AMERICAN_PLAYER_MAPPINGS[player_name]:
                if greek_pattern in player_games:
                    game_log = player_games[greek_pattern]
                    matched_name = greek_pattern
                    logger.info(f"  Manual match: {player_name} -> {greek_pattern}")
                    break

        # If no manual match, try exact English name match
        if not game_log and player_name in player_games:
            game_log = player_games[player_name]
            matched_name = player_name

        # If still no match, try Greek-to-English fuzzy matching
        if not game_log:
            matched_greek_name = match_names(player_name, player_games)
            if matched_greek_name:
                game_log = player_games[matched_greek_name]
                matched_name = matched_greek_name
                logger.info(f"  Fuzzy match: {player_name} -> {transliterate_greek(matched_greek_name)}")

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

    # Count matched vs unmatched
    matched = [p for p in unified_players if p.get('games_played', 0) > 0]
    unmatched = [p for p in unified_players if p.get('games_played', 0) == 0]
    logger.info(f"Players with game data: {len(matched)}")
    logger.info(f"Players without game data: {len(unmatched)}")

    if unmatched:
        logger.info("\nUnmatched players:")
        for p in unmatched:
            logger.info(f"  - {p.get('name')} ({p.get('team')})")

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

"""
=============================================================================
GERMAN BBL DAILY SCRAPER
=============================================================================

PURPOSE:
    This script collects basketball data for German Basketball Bundesliga (BBL)
    from TheSportsDB API. Tracks American players in the German BBL.

WHAT IT DOES:
    1. Fetches all clubs (teams) in German BBL
    2. Fetches all players with their nationality information
    3. Identifies American players (nationality 'United States')
    4. Fetches game schedules and scores
    5. Saves everything to JSON files for further processing

HOW TO USE:
    python daily_scraper.py              # Full scrape
    python daily_scraper.py --teams-only # Only fetch teams

OUTPUT FILES (saved to output/json/):
    - bbl_clubs_TIMESTAMP.json: All German BBL teams
    - bbl_players_TIMESTAMP.json: All players in the league
    - bbl_american_stats_latest.json: Just American players
    - bbl_schedule_latest.json: Game schedule with scores

DATA SOURCE:
    TheSportsDB API: https://www.thesportsdb.com/api.php
    German BBL League ID: 4441
"""

# =============================================================================
# IMPORTS
# =============================================================================
import argparse
import json
import os
import requests
from datetime import datetime
import logging
import time

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================
# TheSportsDB API base URL (free tier uses key '3')
BASE_URL = 'https://www.thesportsdb.com/api/v1/json/3'

# German BBL League ID in TheSportsDB
LEAGUE_ID = '4441'

# Current season (format: YYYY-YYYY)
SEASON = '2025-2026'

# League name for search
LEAGUE_NAME = 'German BBL'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_american(nationality):
    """
    Check if a player is American based on their nationality.
    """
    if not nationality:
        return False
    return nationality.lower() in ['united states', 'usa', 'american']


def save_json(data, filename):
    """
    Save a Python dictionary to a JSON file.
    """
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    logger.info(f"Saved: {filepath}")
    return filepath


def api_get(endpoint, params=None, retries=3):
    """
    Make a GET request to TheSportsDB API with retry logic.
    """
    url = f"{BASE_URL}{endpoint}"

    for attempt in range(retries):
        try:
            if attempt > 0:
                delay = 2 ** attempt
                logger.info(f"  Retry {attempt + 1}/{retries} after {delay}s delay...")
                time.sleep(delay)

            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            time.sleep(0.5)
            return data
        except Exception as e:
            logger.warning(f"API attempt {attempt + 1}/{retries} failed for {endpoint}: {e}")
            if attempt == retries - 1:
                logger.error(f"API error {endpoint}: {e}")
                return None

    return None


# =============================================================================
# DATA FETCHING FUNCTIONS
# =============================================================================

def fetch_clubs():
    """
    Fetch all clubs (teams) in German BBL.
    """
    logger.info("Fetching clubs...")

    data = api_get('/search_all_teams.php', {'l': LEAGUE_NAME})

    if data and data.get('teams'):
        clubs = data.get('teams', [])
        logger.info(f"  Found {len(clubs)} clubs")
        return clubs

    # Fallback: search for known German BBL teams
    logger.info("  Trying fallback team search...")
    known_teams = [
        'ALBA Berlin', 'Bayern Munich Basketball', 'Brose Bamberg',
        'Ratiopharm Ulm', 'MHP Riesen Ludwigsburg', 'EWE Baskets Oldenburg',
        'Hamburg Towers', 'Telekom Baskets Bonn', 'Niners Chemnitz',
        'Merlins Crailsheim', 'Mitteldeutscher BC', 'Wurzburg Baskets',
        'Veolia Towers Hamburg', 'Skyliners Frankfurt', 'BG Gottingen',
        'Rostock Seawolves', 'Heidelberg', 'Syntainics MBC'
    ]

    clubs = []
    for team_name in known_teams:
        data = api_get('/searchteams.php', {'t': team_name})
        if data and data.get('teams'):
            for team in data['teams']:
                if team.get('strSport') == 'Basketball' and team.get('strCountry') == 'Germany':
                    clubs.append(team)
                    break
        time.sleep(0.3)

    logger.info(f"  Found {len(clubs)} clubs via search")
    return clubs


def fetch_players_for_team(team_id, team_name):
    """
    Fetch all players for a specific team.
    """
    data = api_get('/lookup_all_players.php', {'id': team_id})

    if data and data.get('player'):
        players = data.get('player', [])
        logger.info(f"    {team_name}: {len(players)} players")
        return players

    return []


def fetch_all_players(clubs):
    """
    Fetch all players from all teams.
    """
    logger.info("Fetching players from all teams...")

    all_players = []
    for club in clubs:
        team_id = club.get('idTeam')
        team_name = club.get('strTeam', 'Unknown')
        team_badge = club.get('strBadge') or club.get('strLogo')

        if team_id:
            players = fetch_players_for_team(team_id, team_name)
            for player in players:
                player['team_id'] = team_id
                player['team_name'] = team_name
                player['team_badge'] = team_badge
            all_players.extend(players)
            time.sleep(0.3)

    logger.info(f"  Total players: {len(all_players)}")
    return all_players


def fetch_schedule():
    """
    Fetch the game schedule combining multiple API endpoints for complete data.
    """
    logger.info("Fetching schedule...")
    all_games = {}

    # Fetch from season endpoint
    data = api_get('/eventsseason.php', {'id': LEAGUE_ID, 's': SEASON})
    if data and data.get('events'):
        for game in data['events']:
            if game.get('idLeague') == LEAGUE_ID:
                game_id = game.get('idEvent')
                if game_id:
                    all_games[game_id] = game
        logger.info(f"  Season endpoint: {len(all_games)} games")

    # Fetch recent past games
    data = api_get('/eventspastleague.php', {'id': LEAGUE_ID})
    if data and data.get('events'):
        count = 0
        for game in data['events']:
            if game.get('idLeague') == LEAGUE_ID:
                game_id = game.get('idEvent')
                if game_id:
                    all_games[game_id] = game
                    count += 1
        logger.info(f"  Past events endpoint: {count} games")

    # Fetch upcoming games
    data = api_get('/eventsnextleague.php', {'id': LEAGUE_ID})
    if data and data.get('events'):
        count = 0
        for game in data['events']:
            if game.get('idLeague') == LEAGUE_ID:
                game_id = game.get('idEvent')
                if game_id:
                    all_games[game_id] = game
                    count += 1
        logger.info(f"  Next events endpoint: {count} games")

    games = list(all_games.values())
    logger.info(f"  Total unique games: {len(games)}")

    return games


# =============================================================================
# DATA PROCESSING FUNCTIONS
# =============================================================================

def process_clubs(clubs):
    """
    Process raw club data into a clean format.
    """
    processed = []
    for club in clubs:
        processed.append({
            'id': club.get('idTeam'),
            'name': club.get('strTeam'),
            'short_name': club.get('strTeamShort'),
            'founded': club.get('intFormedYear'),
            'stadium': club.get('strStadium'),
            'stadium_capacity': club.get('intStadiumCapacity'),
            'location': club.get('strLocation'),
            'country': club.get('strCountry'),
            'badge_url': club.get('strBadge'),
            'logo_url': club.get('strLogo'),
            'website': club.get('strWebsite'),
            'description': club.get('strDescriptionEN'),
        })
    return processed


def process_players(players):
    """
    Process raw player data into a clean format for American players.
    """
    processed = []
    for player in players:
        # Parse height
        height_str = player.get('strHeight', '')
        height_cm = None
        if height_str:
            try:
                if 'm' in height_str.lower():
                    # Handle "2.01 m" or "2.01m"
                    height_m = float(height_str.lower().replace('m', '').strip())
                    height_cm = int(height_m * 100)
                elif 'ft' in height_str.lower():
                    parts = height_str.lower().replace('ft', '').replace('in', '').split()
                    if len(parts) >= 2:
                        feet = int(parts[0])
                        inches = int(parts[1])
                        height_cm = int((feet * 12 + inches) * 2.54)
            except:
                pass

        processed.append({
            'id': player.get('idPlayer'),
            'name': player.get('strPlayer'),
            'nationality': player.get('strNationality'),
            'position': player.get('strPosition'),
            'birthdate': player.get('dateBorn', '')[:10] if player.get('dateBorn') else None,
            'birthplace': player.get('strBirthLocation'),
            'height': height_str,
            'height_cm': height_cm,
            'team': player.get('team_name'),
            'team_id': player.get('team_id'),
            'team_logo': player.get('team_badge'),
            'thumb': player.get('strThumb'),
            'cutout': player.get('strCutout'),
            'description': player.get('strDescriptionEN'),
        })
    return processed


def process_schedule(games):
    """
    Process raw schedule data into a clean format.
    """
    processed = []
    for game in games:
        home_score = game.get('intHomeScore')
        away_score = game.get('intAwayScore')
        played = home_score is not None and away_score is not None

        processed.append({
            'game_id': game.get('idEvent'),
            'date': game.get('dateEvent'),
            'time': game.get('strTime'),
            'round': game.get('intRound'),
            'home_team': game.get('strHomeTeam'),
            'away_team': game.get('strAwayTeam'),
            'home_score': int(home_score) if home_score else None,
            'away_score': int(away_score) if away_score else None,
            'played': played,
            'venue': game.get('strVenue'),
            'city': game.get('strCity'),
            'season': game.get('strSeason'),
            'status': game.get('strStatus'),
        })
    return processed


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """
    Main entry point for the scraper.
    """
    parser = argparse.ArgumentParser(description='German BBL Daily Scraper')
    parser.add_argument('--teams-only', action='store_true',
                       help='Only fetch teams')
    parser.add_argument('--players-only', action='store_true',
                       help='Only fetch players')
    parser.add_argument('--schedule-only', action='store_true',
                       help='Only fetch schedule')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("GERMAN BBL DAILY SCRAPER")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # =========================================================================
    # Step 1: Fetch Clubs
    # =========================================================================
    clubs = fetch_clubs()
    processed_clubs = process_clubs(clubs)

    if clubs:
        save_json({
            'export_date': datetime.now().isoformat(),
            'season': SEASON,
            'league': 'German BBL',
            'league_id': LEAGUE_ID,
            'count': len(processed_clubs),
            'teams': processed_clubs
        }, f'bbl_clubs_{timestamp}.json')

    if args.teams_only:
        return

    # =========================================================================
    # Step 2: Fetch Players
    # =========================================================================
    all_players_raw = fetch_all_players(clubs)
    all_players = process_players(all_players_raw)

    # Identify American players
    american_players = [p for p in all_players if is_american(p.get('nationality'))]

    logger.info(f"  American players: {len(american_players)}")

    # Save all players
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': SEASON,
        'league': 'German BBL',
        'count': len(all_players),
        'players': all_players
    }, f'bbl_players_{timestamp}.json')

    # Save American players
    american_data = {
        'export_date': datetime.now().isoformat(),
        'season': SEASON,
        'league': 'German Basketball Bundesliga (BBL)',
        'source': 'thesportsdb.com',
        'player_count': len(american_players),
        'players': american_players
    }
    save_json(american_data, f'bbl_american_stats_{timestamp}.json')
    save_json(american_data, 'bbl_american_stats_latest.json')

    if args.players_only:
        return

    # =========================================================================
    # Step 3: Fetch Schedule
    # =========================================================================
    games_raw = fetch_schedule()
    games = process_schedule(games_raw)

    played_games = [g for g in games if g.get('played')]
    upcoming_games = [g for g in games if not g.get('played')]

    logger.info(f"  Played: {len(played_games)}, Upcoming: {len(upcoming_games)}")

    schedule_data = {
        'export_date': datetime.now().isoformat(),
        'season': SEASON,
        'league': 'German BBL',
        'total_games': len(games),
        'played': len(played_games),
        'upcoming': len(upcoming_games),
        'teams': processed_clubs,
        'games': games
    }
    save_json(schedule_data, f'bbl_schedule_{timestamp}.json')
    save_json(schedule_data, 'bbl_schedule_latest.json')

    # =========================================================================
    # Summary
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Clubs: {len(processed_clubs)}")
    logger.info(f"Total players: {len(all_players)}")
    logger.info(f"American players: {len(american_players)}")
    logger.info(f"Games: {len(games)} (played: {len(played_games)}, upcoming: {len(upcoming_games)})")

    if american_players:
        logger.info("\nAmerican players found:")
        for p in american_players[:15]:
            logger.info(f"  {p['name']} - {p['team']} ({p['position']})")


if __name__ == '__main__':
    main()

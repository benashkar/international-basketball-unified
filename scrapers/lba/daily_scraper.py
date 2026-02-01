"""
=============================================================================
LEGA BASKET SERIE A (LBA) DAILY SCRAPER
=============================================================================

PURPOSE:
    This script collects basketball data for Italian Lega Basket Serie A from:
    - TheSportsDB API: Teams, players, schedule, results

WHAT IT DOES:
    1. Fetches all clubs (teams) in LBA
    2. Fetches all players with their nationality information
    3. Identifies American players (nationality 'United States')
    4. Fetches game schedules and scores
    5. Saves everything to JSON files for further processing

HOW TO USE:
    python daily_scraper.py              # Full scrape

OUTPUT FILES (saved to output/json/):
    - clubs_TIMESTAMP.json: All LBA teams
    - players_TIMESTAMP.json: All players in the league
    - american_players_TIMESTAMP.json: Just American players
    - schedule_TIMESTAMP.json: Game schedule with scores

DATA SOURCES:
    TheSportsDB API: https://www.thesportsdb.com/api.php
    League page: https://www.thesportsdb.com/league/4433-italian-lega-basket
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

# Italian Lega Basket Serie A League ID in TheSportsDB
LEAGUE_ID = '4433'

# Current season (format: YYYY-YYYY)
SEASON = '2025-2026'

# American nationality identifier
AMERICAN_NATIONALITY = 'United States'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_american(nationality):
    """
    Check if a player is American based on their nationality.

    PARAMETERS:
        nationality (str or None): The player's nationality string

    RETURNS:
        bool: True if American, False otherwise
    """
    if not nationality:
        return False
    return nationality.lower() in ['united states', 'usa', 'american']


def save_json(data, filename):
    """
    Save a Python dictionary to a JSON file.

    PARAMETERS:
        data (dict): The data to save
        filename (str): The name of the file

    RETURNS:
        str: The full file path where the data was saved
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

    PARAMETERS:
        endpoint (str): The API endpoint (e.g., '/lookup_all_teams.php')
        params (dict, optional): Query parameters
        retries (int): Number of retry attempts

    RETURNS:
        dict or None: The JSON response, or None if error
    """
    url = f"{BASE_URL}{endpoint}"

    for attempt in range(retries):
        try:
            # Add delay between requests to avoid rate limiting
            if attempt > 0:
                delay = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                logger.info(f"  Retry {attempt + 1}/{retries} after {delay}s delay...")
                time.sleep(delay)

            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # Add small delay after successful request to avoid rate limiting
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
    Fetch all clubs (teams) in Lega Basket Serie A.

    RETURNS:
        list: A list of club dictionaries, or empty list if error

    NOTE:
        Uses search_all_teams.php with league name parameter instead of
        lookup_all_teams.php with ID, as the latter returns incorrect data.
    """
    logger.info("Fetching clubs...")

    # Use league name parameter instead of ID
    data = api_get('/search_all_teams.php', {'l': 'Italian_Lega_Basket'})

    if data and data.get('teams'):
        clubs = data['teams']
        logger.info(f"  Found {len(clubs)} clubs")
        return clubs

    return []


def fetch_players_for_team(team_id):
    """
    Fetch all players for a specific team.

    PARAMETERS:
        team_id (str): The TheSportsDB team ID

    RETURNS:
        list: A list of player dictionaries
    """
    data = api_get('/lookup_all_players.php', {'id': team_id})

    if data and data.get('player'):
        return data['player']

    return []


def fetch_schedule():
    """
    Fetch game schedule for the current season.

    RETURNS:
        list: A list of game dictionaries
    """
    logger.info("Fetching schedule...")

    # Get past events (last 50)
    past_data = api_get('/eventspastleague.php', {'id': LEAGUE_ID})
    past_games = past_data.get('events', []) if past_data else []

    # Get upcoming events (next 50)
    future_data = api_get('/eventsnextleague.php', {'id': LEAGUE_ID})
    future_games = future_data.get('events', []) if future_data else []

    all_games = (past_games or []) + (future_games or [])
    logger.info(f"  Found {len(all_games)} games (past: {len(past_games or [])}, upcoming: {len(future_games or [])})")

    return all_games


def fetch_season_schedule():
    """
    Fetch full season schedule from TheSportsDB.

    RETURNS:
        list: A list of all games in the season
    """
    logger.info("Fetching full season schedule...")

    data = api_get('/eventsseason.php', {'id': LEAGUE_ID, 's': SEASON})

    if data and data.get('events'):
        games = data['events']
        logger.info(f"  Found {len(games)} games in season")
        return games

    return []


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """
    Main entry point for the scraper.
    """
    logger.info("=" * 60)
    logger.info("LEGA BASKET SERIE A DAILY SCRAPER")
    logger.info("=" * 60)

    # Generate timestamp for file names
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # =========================================================================
    # Step 1: Fetch Clubs
    # =========================================================================
    clubs = fetch_clubs()
    if clubs:
        save_json({
            'export_date': datetime.now().isoformat(),
            'season': SEASON,
            'league': 'Lega Basket Serie A',
            'count': len(clubs),
            'clubs': clubs
        }, f'clubs_{timestamp}.json')

    # =========================================================================
    # Step 2: Fetch Players for Each Team
    # =========================================================================
    all_players = []
    american_players = []

    logger.info("Fetching players for each team...")
    for i, club in enumerate(clubs):
        team_id = club.get('idTeam')
        team_name = club.get('strTeam')

        if not team_id:
            continue

        logger.info(f"  [{i+1}/{len(clubs)}] {team_name}...")
        players = fetch_players_for_team(team_id)

        for player in players:
            nationality = player.get('strNationality')

            # Build clean player dictionary
            player_data = {
                'code': player.get('idPlayer'),
                'name': player.get('strPlayer'),
                'nationality': nationality,
                'birth_date': player.get('dateBorn'),
                'birth_location': player.get('strBirthLocation'),
                'height_str': player.get('strHeight'),
                'height_cm': None,  # TheSportsDB doesn't provide numeric height
                'height_feet': None,
                'height_inches': None,
                'weight': player.get('strWeight'),
                'position': player.get('strPosition'),
                'team_code': team_id,
                'team_name': team_name,
                'jersey': player.get('strNumber'),
                'headshot_url': player.get('strThumb') or player.get('strCutout'),
                'description': player.get('strDescriptionEN'),
                'instagram': player.get('strInstagram'),
                'twitter': player.get('strTwitter'),
            }

            all_players.append(player_data)

            # Check if American
            if is_american(nationality):
                american_players.append(player_data)

        # Rate limiting between teams
        time.sleep(0.5)

    logger.info(f"  Total players: {len(all_players)}")
    logger.info(f"  American players: {len(american_players)}")

    # Save all players
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': SEASON,
        'league': 'Lega Basket Serie A',
        'count': len(all_players),
        'players': all_players
    }, f'players_{timestamp}.json')

    # Save American players
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': SEASON,
        'league': 'Lega Basket Serie A',
        'count': len(american_players),
        'players': american_players
    }, f'american_players_{timestamp}.json')

    # Also save as latest
    save_json({
        'export_date': datetime.now().isoformat(),
        'season': SEASON,
        'league': 'Lega Basket Serie A',
        'count': len(american_players),
        'players': american_players
    }, 'american_players_latest.json')

    # =========================================================================
    # Step 3: Fetch Schedule
    # =========================================================================
    games = fetch_season_schedule()

    if not games:
        # Fallback to recent/upcoming games
        games = fetch_schedule()

    # Process games into clean format
    processed_games = []
    for game in games:
        played = game.get('intHomeScore') is not None and game.get('intAwayScore') is not None

        processed_game = {
            'game_id': game.get('idEvent'),
            'date': game.get('dateEvent'),
            'time': game.get('strTime'),
            'round': game.get('intRound'),
            'home_team': game.get('strHomeTeam'),
            'away_team': game.get('strAwayTeam'),
            'home_score': int(game.get('intHomeScore')) if game.get('intHomeScore') else None,
            'away_score': int(game.get('intAwayScore')) if game.get('intAwayScore') else None,
            'played': played,
            'venue': game.get('strVenue'),
        }
        processed_games.append(processed_game)

    # Sort by date
    processed_games.sort(key=lambda x: x.get('date') or '')

    # Count played vs upcoming
    played_games = [g for g in processed_games if g.get('played')]
    upcoming_games = [g for g in processed_games if not g.get('played')]

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': SEASON,
        'league': 'Lega Basket Serie A',
        'total_games': len(processed_games),
        'played': len(played_games),
        'upcoming': len(upcoming_games),
        'games': processed_games
    }, f'schedule_{timestamp}.json')

    save_json({
        'export_date': datetime.now().isoformat(),
        'season': SEASON,
        'league': 'Lega Basket Serie A',
        'total_games': len(processed_games),
        'played': len(played_games),
        'upcoming': len(upcoming_games),
        'games': processed_games
    }, 'schedule_latest.json')

    # =========================================================================
    # Summary
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Clubs: {len(clubs)}")
    logger.info(f"Total players: {len(all_players)}")
    logger.info(f"American players: {len(american_players)}")
    logger.info(f"Games: {len(processed_games)} (played: {len(played_games)}, upcoming: {len(upcoming_games)})")

    if american_players:
        logger.info("\nAmerican players:")
        for p in american_players[:15]:
            logger.info(f"  {p['name']} - {p['team_name']} | {p['position']}")


if __name__ == '__main__':
    main()

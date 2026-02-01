#!/usr/bin/env python3
"""
Unified Basketball Dashboard - League Verification Script

Run this script after adding a new league to verify all data is properly collected.
Usage: python scripts/verify_leagues.py

This script checks:
1. American players by league
2. Players with season statistics
3. Past and upcoming games
4. Box scores with detailed player stats
5. Team/schedule data
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Configuration - Add new leagues here
LEAGUES = {
    'EuroLeague': {
        'unified_players': 'output/json/euroleague_unified_players_latest.json',
        'box_scores': None,
        'schedule': None,
    },
    'Spanish ACB': {
        'unified_players': 'output/json/acb_unified_players_latest.json',
        'box_scores': 'output/json/acb_boxscores_latest.json',
        'schedule': 'output/json/acb_schedule_latest.json',
    },
    'Italian LBA': {
        'unified_players': 'output/json/lba_unified_players_latest.json',
        'box_scores': None,
        'schedule': None,
    },
    'Turkish BSL': {
        'unified_players': 'output/json/bsl_unified_players_latest.json',
        'box_scores': None,
        'schedule': 'output/json/bsl_schedule_latest.json',
    },
    'French LNB': {
        'unified_players': 'output/json/lnb_unified_players_latest.json',
        'box_scores': None,
        'schedule': 'scrapers/lnb/output/json/lnb_schedule_latest.json',
    },
    'Greek ESAKE': {
        'unified_players': 'output/json/esake_unified_players_latest.json',
        'box_scores': None,
        'schedule': 'scrapers/esake/output/json/esake_schedule_latest.json',
    },
}


def find_project_root():
    """Find the project root directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / 'output' / 'json').exists() or (current / 'scrapers').exists():
            return current
        current = current.parent
    return Path.cwd()


def load_json(filepath):
    """Load a JSON file safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def analyze_unified_players(data):
    """Analyze unified players data."""
    if not data:
        return None

    players = data.get('players', [])
    teams = set(p.get('team', '') for p in players if p.get('team'))

    with_stats = 0
    past_games = 0
    upcoming_games = 0
    recent_games = 0

    today = datetime.now()
    seven_days_ago = today - timedelta(days=7)

    for p in players:
        # Check for season stats
        if p.get('ppg', 0) > 0 or p.get('rpg', 0) > 0 or p.get('apg', 0) > 0:
            with_stats += 1

        # Count games
        past = p.get('past_games', [])
        upcoming = p.get('upcoming_games', [])
        past_games += len(past)
        upcoming_games += len(upcoming)

        # Count recent games
        for g in past:
            date_str = g.get('date', '')
            if date_str:
                try:
                    game_date = datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
                    if game_date >= seven_days_ago:
                        recent_games += 1
                except (ValueError, TypeError):
                    pass

    return {
        'player_count': len(players),
        'team_count': len(teams),
        'with_stats': with_stats,
        'past_games': past_games,
        'upcoming_games': upcoming_games,
        'recent_games': recent_games,
        'export_date': data.get('export_date', 'Unknown'),
    }


def analyze_box_scores(data):
    """Analyze box scores data."""
    if not data:
        return None

    box_scores = data.get('box_scores', [])
    player_stats = sum(len(b.get('players', [])) for b in box_scores)

    return {
        'game_count': len(box_scores),
        'player_stat_entries': player_stats,
    }


def analyze_schedule(data):
    """Analyze schedule data."""
    if not data:
        return None

    teams = data.get('teams', [])
    games = data.get('games', []) or data.get('matches', [])
    season = data.get('season', 'Unknown')

    played = sum(1 for g in games if g.get('played', False))
    upcoming = len(games) - played

    return {
        'team_count': len(teams),
        'total_games': len(games),
        'played_games': played,
        'upcoming_games': upcoming,
        'season': season,
    }


def print_header(title):
    """Print a section header."""
    print()
    print('=' * 100)
    print(f'  {title}')
    print('=' * 100)


def print_divider():
    """Print a divider line."""
    print('-' * 100)


def main():
    """Main verification routine."""
    project_root = find_project_root()
    os.chdir(project_root)

    print()
    print_header('INTERNATIONAL BASKETBALL UNIFIED DASHBOARD - VERIFICATION REPORT')
    print(f'  Report Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'  Project Root: {project_root}')
    print('=' * 100)

    # ========== SECTION 1: PLAYER SUMMARY ==========
    print_header('SECTION 1: AMERICAN PLAYERS BY LEAGUE')
    print_divider()
    print(f'{"League":<20} {"Players":>10} {"Teams":>10} {"w/Stats":>12} {"Past Games":>12} {"Upcoming":>12} {"Recent 7d":>12}')
    print_divider()

    totals = {
        'players': 0, 'teams': 0, 'with_stats': 0,
        'past_games': 0, 'upcoming_games': 0, 'recent_games': 0
    }

    league_results = {}

    for league, files in LEAGUES.items():
        unified_path = files['unified_players']
        data = load_json(unified_path)
        stats = analyze_unified_players(data)
        league_results[league] = {'unified': stats}

        if stats:
            print(f'{league:<20} {stats["player_count"]:>10} {stats["team_count"]:>10} '
                  f'{stats["with_stats"]:>12} {stats["past_games"]:>12} '
                  f'{stats["upcoming_games"]:>12} {stats["recent_games"]:>12}')
            totals['players'] += stats['player_count']
            totals['teams'] += stats['team_count']
            totals['with_stats'] += stats['with_stats']
            totals['past_games'] += stats['past_games']
            totals['upcoming_games'] += stats['upcoming_games']
            totals['recent_games'] += stats['recent_games']
        else:
            print(f'{league:<20} {"FILE NOT FOUND":>10}')

    print_divider()
    print(f'{"TOTAL":<20} {totals["players"]:>10} {totals["teams"]:>10} '
          f'{totals["with_stats"]:>12} {totals["past_games"]:>12} '
          f'{totals["upcoming_games"]:>12} {totals["recent_games"]:>12}')

    # ========== SECTION 2: BOX SCORES ==========
    print_header('SECTION 2: BOX SCORES WITH DETAILED PLAYER STATISTICS')
    print_divider()

    total_box_scores = 0
    total_player_stats = 0

    for league, files in LEAGUES.items():
        if files['box_scores']:
            data = load_json(files['box_scores'])
            stats = analyze_box_scores(data)
            league_results[league]['box_scores'] = stats

            if stats:
                print(f'{league}: {stats["game_count"]} games with {stats["player_stat_entries"]} individual player stat lines')
                total_box_scores += stats['game_count']
                total_player_stats += stats['player_stat_entries']

    if total_box_scores == 0:
        print('No box score files found.')
    else:
        print()
        print(f'TOTAL: {total_box_scores} box scores, {total_player_stats} player stat entries')

    # ========== SECTION 3: SCHEDULE/TEAM DATA ==========
    print_header('SECTION 3: SCHEDULE AND TEAM DATA')
    print_divider()

    for league, files in LEAGUES.items():
        if files['schedule']:
            data = load_json(files['schedule'])
            stats = analyze_schedule(data)
            league_results[league]['schedule'] = stats

            if stats:
                if stats['total_games'] > 0:
                    print(f'{league}: {stats["team_count"]} teams, {stats["total_games"]} games '
                          f'({stats["played_games"]} played, {stats["upcoming_games"]} upcoming) - Season: {stats["season"]}')
                else:
                    print(f'{league}: {stats["team_count"]} teams (Season: {stats["season"]})')

    # ========== SECTION 4: DATA QUALITY CHECKS ==========
    print_header('SECTION 4: DATA QUALITY CHECKS')
    print_divider()

    issues = []
    warnings = []

    for league, results in league_results.items():
        unified = results.get('unified')
        if not unified:
            issues.append(f'{league}: Unified players file not found')
        elif unified['player_count'] == 0:
            issues.append(f'{league}: No American players found')
        elif unified['with_stats'] == 0:
            warnings.append(f'{league}: No players have season statistics (PPG/RPG/APG)')

        if unified and unified['past_games'] == 0 and unified['upcoming_games'] == 0:
            warnings.append(f'{league}: No game data (past or upcoming) - may need alternative data source')

    if issues:
        print('ISSUES (require attention):')
        for issue in issues:
            print(f'  [X] {issue}')
        print()

    if warnings:
        print('WARNINGS (informational):')
        for warning in warnings:
            print(f'  [!] {warning}')
        print()

    if not issues and not warnings:
        print('All checks passed - no issues found.')

    # ========== SUMMARY ==========
    print_header('VERIFICATION SUMMARY')
    print_divider()
    print(f'  Total Leagues:           {len(LEAGUES)}')
    print(f'  Total American Players:  {totals["players"]}')
    print(f'  Teams with Americans:    {totals["teams"]}')
    print(f'  Players with Stats:      {totals["with_stats"]}')
    print(f'  Total Past Games:        {totals["past_games"]}')
    print(f'  Total Upcoming Games:    {totals["upcoming_games"]}')
    print(f'  Recent Games (7 days):   {totals["recent_games"]}')
    print(f'  Box Scores Available:    {total_box_scores}')
    print(f'  Player Stat Entries:     {total_player_stats}')
    print_divider()

    if issues:
        print('STATUS: ISSUES FOUND - Review required')
        return 1
    else:
        print('STATUS: ALL LEAGUES OPERATIONAL')
        return 0


if __name__ == '__main__':
    sys.exit(main())

"""
Data quality validation for scraped output.

Checks that EuroLeague player data has correct positions after the fix.
Skips gracefully when data files aren't present (CI without scrape data).
"""
import json
import os
import glob

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EUROLEAGUE_OUTPUT = os.path.join(PROJECT_ROOT, 'scrapers', 'euroleague', 'output', 'json')

# Positions that only exist due to the wrong NBA integer mapping
INVALID_EUROLEAGUE_POSITIONS = {'Shooting Guard', 'Small Forward', 'Power Forward', 'Point Guard'}

VALID_POSITIONS = {
    'Guard', 'Forward', 'Center',
    'Guard-Forward', 'Forward-Guard',
    'Forward-Center', 'Center-Forward',
    'Point Guard', 'Shooting Guard',  # valid from other leagues, not EuroLeague integers
    'Small Forward', 'Power Forward',
    '0',  # non-player records (coaches) that slip through with position=0
}


def _find_latest_file(directory, pattern):
    """Find the most recent file matching a glob pattern."""
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _load_players(filepath):
    """Load player list from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('players', [])


class TestEuroLeagueDataQuality:
    """Validate EuroLeague output data has correct positions."""

    def _get_euroleague_players(self):
        """Try to find freshly scraped EuroLeague player data.

        Only checks the scraper output directory (populated during scraping),
        NOT output/json/ which may contain stale committed data from before fixes.
        """
        for pattern in ['unified_american_players_*.json', 'american_players_*.json']:
            filepath = _find_latest_file(EUROLEAGUE_OUTPUT, pattern)
            if filepath:
                return _load_players(filepath)
        return None

    def test_no_wrong_integer_mapped_positions(self):
        """No EuroLeague player should have positions from wrong NBA integer mapping."""
        players = self._get_euroleague_players()
        if players is None:
            pytest.skip("No EuroLeague player data files found (run scraper first)")

        bad_players = []
        for p in players:
            pos = (p.get('position') or '').strip()
            if pos in INVALID_EUROLEAGUE_POSITIONS:
                bad_players.append(f"{p.get('name', '?')} -> {pos}")

        assert not bad_players, (
            f"Found {len(bad_players)} players with wrong NBA-mapped positions:\n"
            + "\n".join(bad_players[:10])
        )

    def test_all_positions_are_recognized(self):
        """Every position value should be a known basketball position."""
        players = self._get_euroleague_players()
        if players is None:
            pytest.skip("No EuroLeague player data files found (run scraper first)")

        unknown = []
        for p in players:
            pos = (p.get('position') or '').strip()
            if pos and pos not in VALID_POSITIONS:
                unknown.append(f"{p.get('name', '?')} -> {pos}")

        assert not unknown, (
            f"Found {len(unknown)} players with unrecognized positions:\n"
            + "\n".join(unknown[:10])
        )

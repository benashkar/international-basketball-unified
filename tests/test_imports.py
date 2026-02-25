"""
Tests that verify all modules import successfully.

These catch syntax errors, missing dependencies, and broken imports
BEFORE code reaches production. Added after PR #1 exposed gaps in CI.
"""

import importlib
import sys
import os


def test_dashboard_imports():
    """Verify dashboard.py imports and creates the Flask app."""
    from dashboard import app
    assert app is not None


def test_root_positions_imports():
    """Verify root positions.py exports get_position_name."""
    from positions import get_position_name
    assert callable(get_position_name)
    # Smoke test: known mapping works
    assert get_position_name('PG') == 'Point Guard'


def test_euroleague_positions_imports():
    """Verify scrapers/euroleague/positions.py loads via importlib."""
    spec = importlib.util.spec_from_file_location(
        'euroleague_positions',
        os.path.join('scrapers', 'euroleague', 'positions.py')
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, 'get_position_name')
    # EuroLeague uses 3-category: 1=Guard, 2=Forward, 3=Center
    assert mod.get_position_name(1) == 'Guard'


def test_flask_routes_registered():
    """Verify dashboard has routes for /, /player/, /league/."""
    from dashboard import app
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert '/' in rules, 'Missing root route'
    assert any('/player/' in r for r in rules), 'Missing player route'
    assert any('/league/' in r for r in rules), 'Missing league route'

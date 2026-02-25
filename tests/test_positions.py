"""
Tests for position mapping across leagues.

Ensures EuroLeague uses its 3-category system (Guard/Forward/Center)
while the root positions module retains the NBA 5-position convention.
"""
import importlib.util
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_positions_module(filepath, module_name):
    """Load a positions module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Load both modules from their exact file paths
_euroleague_mod = _load_positions_module(
    os.path.join(PROJECT_ROOT, 'scrapers', 'euroleague', 'positions.py'),
    'euroleague_positions',
)
_root_mod = _load_positions_module(
    os.path.join(PROJECT_ROOT, 'positions.py'),
    'root_positions',
)


class TestEuroLeaguePositions:
    """EuroLeague uses a 3-category system: Guard, Forward, Center."""

    def test_integer_1_maps_to_guard(self):
        assert _euroleague_mod.get_position_name(1) == 'Guard'

    def test_integer_2_maps_to_forward(self):
        assert _euroleague_mod.get_position_name(2) == 'Forward'

    def test_integer_3_maps_to_center(self):
        assert _euroleague_mod.get_position_name(3) == 'Center'

    def test_string_1_maps_to_guard(self):
        assert _euroleague_mod.get_position_name('1') == 'Guard'

    def test_string_2_maps_to_forward(self):
        assert _euroleague_mod.get_position_name('2') == 'Forward'

    def test_string_3_maps_to_center(self):
        assert _euroleague_mod.get_position_name('3') == 'Center'

    def test_no_nba_specific_positions_from_integers(self):
        """EuroLeague integers must NOT produce NBA-specific position names."""
        nba_only = {'Point Guard', 'Shooting Guard', 'Small Forward', 'Power Forward'}
        for i in [1, 2, 3, '1', '2', '3']:
            result = _euroleague_mod.get_position_name(i)
            assert result not in nba_only, (
                f"Integer {i} mapped to NBA position '{result}' — "
                f"EuroLeague should use Guard/Forward/Center"
            )

    def test_string_guard_passes_through(self):
        assert _euroleague_mod.get_position_name('Guard') == 'Guard'

    def test_string_forward_passes_through(self):
        assert _euroleague_mod.get_position_name('Forward') == 'Forward'

    def test_string_center_passes_through(self):
        assert _euroleague_mod.get_position_name('Center') == 'Center'

    def test_abbreviation_g_maps_to_guard(self):
        assert _euroleague_mod.get_position_name('G') == 'Guard'

    def test_abbreviation_f_maps_to_forward(self):
        assert _euroleague_mod.get_position_name('F') == 'Forward'

    def test_abbreviation_c_maps_to_center(self):
        assert _euroleague_mod.get_position_name('C') == 'Center'

    def test_none_returns_none(self):
        assert _euroleague_mod.get_position_name(None) is None


class TestRootPositions:
    """Root positions module retains the NBA 5-position convention."""

    def test_integer_1_maps_to_point_guard(self):
        assert _root_mod.get_position_name(1) == 'Point Guard'

    def test_integer_2_maps_to_shooting_guard(self):
        assert _root_mod.get_position_name(2) == 'Shooting Guard'

    def test_integer_3_maps_to_small_forward(self):
        assert _root_mod.get_position_name(3) == 'Small Forward'

    def test_integer_4_maps_to_power_forward(self):
        assert _root_mod.get_position_name(4) == 'Power Forward'

    def test_integer_5_maps_to_center(self):
        assert _root_mod.get_position_name(5) == 'Center'

    def test_none_returns_none(self):
        assert _root_mod.get_position_name(None) is None

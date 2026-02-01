"""
=============================================================================
BASKETBALL POSITIONS LOOKUP
=============================================================================
Standard basketball position codes and their full names.
Used across all leagues for consistent position display.
"""

# Position number to name mapping
POSITION_MAP = {
    1: 'Point Guard',
    2: 'Shooting Guard',
    3: 'Small Forward',
    4: 'Power Forward',
    5: 'Center',
    '1': 'Point Guard',
    '2': 'Shooting Guard',
    '3': 'Small Forward',
    '4': 'Power Forward',
    '5': 'Center',
    # Common abbreviations
    'PG': 'Point Guard',
    'SG': 'Shooting Guard',
    'SF': 'Small Forward',
    'PF': 'Power Forward',
    'C': 'Center',
    'G': 'Guard',
    'F': 'Forward',
    'G-F': 'Guard-Forward',
    'F-G': 'Forward-Guard',
    'F-C': 'Forward-Center',
    'C-F': 'Center-Forward',
    # Already full names (pass through)
    'Point Guard': 'Point Guard',
    'Shooting Guard': 'Shooting Guard',
    'Small Forward': 'Small Forward',
    'Power Forward': 'Power Forward',
    'Center': 'Center',
    'Guard': 'Guard',
    'Forward': 'Forward',
}

# Short abbreviations for display
POSITION_ABBREV = {
    'Point Guard': 'PG',
    'Shooting Guard': 'SG',
    'Small Forward': 'SF',
    'Power Forward': 'PF',
    'Center': 'C',
    'Guard': 'G',
    'Forward': 'F',
    'Guard-Forward': 'G-F',
    'Forward-Guard': 'F-G',
    'Forward-Center': 'F-C',
    'Center-Forward': 'C-F',
}


def get_position_name(position):
    """
    Convert a position code to its full name.

    Args:
        position: Can be int (1-5), string number ('1'-'5'),
                  abbreviation ('PG', 'SG', etc.), or full name

    Returns:
        str: Full position name, or original value if not found

    Examples:
        >>> get_position_name(1)
        'Point Guard'
        >>> get_position_name('2')
        'Shooting Guard'
        >>> get_position_name('PG')
        'Point Guard'
    """
    if position is None:
        return None
    return POSITION_MAP.get(position, str(position))


def get_position_abbrev(position):
    """
    Convert a position to its abbreviation.

    Args:
        position: Any position format (number, abbrev, or full name)

    Returns:
        str: Position abbreviation (PG, SG, SF, PF, C)
    """
    if position is None:
        return None
    full_name = get_position_name(position)
    return POSITION_ABBREV.get(full_name, full_name)

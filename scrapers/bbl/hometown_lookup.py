"""
=============================================================================
GERMAN BBL - HOMETOWN LOOKUP (WIKIPEDIA)
=============================================================================
Finds hometown, high school, and college information for American BBL players
by looking them up on Wikipedia.
"""

import json
import os
import re
import requests
from datetime import datetime
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Wikipedia API
WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {'User-Agent': 'BBLTracker/1.0 (basketball data collection)'}

# US States for validation
US_STATES = {
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
    'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
    'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
    'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
    'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
    'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
    'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
    'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
    'West Virginia', 'Wisconsin', 'Wyoming', 'District of Columbia', 'D.C.'
}

STATE_ABBREVS = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
}

# Manual overrides for players with common names or wrong Wikipedia matches
MANUAL_OVERRIDES = {
    # Add overrides here if needed
    # 'PLAYER NAME': {
    #     'hometown_city': 'City',
    #     'hometown_state': 'State',
    #     'college': 'College Name',
    #     'high_school': 'High School Name',
    # },
}


def clean_name(name):
    """Clean player name for Wikipedia search."""
    # BBL names are already in "First Last" format
    name = name.strip()

    # Convert to title case
    name = name.title()

    # Remove suffixes for search (but keep them in display)
    search_name = re.sub(r'\s+(Ii|Iii|Iv|Jr\.?|Sr\.?)$', '', name, flags=re.IGNORECASE)

    return search_name.strip()


def search_wikipedia(name):
    """Search Wikipedia for a basketball player's article."""
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': f'{name} basketball player',
        'format': 'json',
        'srlimit': 5
    }

    try:
        resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        results = data.get('query', {}).get('search', [])

        name_lower = name.lower()
        for result in results:
            title = result.get('title', '')
            if name_lower in title.lower():
                return title

        if results:
            return results[0].get('title')

    except Exception as e:
        logger.debug(f"Wikipedia search error: {e}")

    return None


def get_wiki_wikitext(title):
    """Get the raw wikitext content of a Wikipedia article."""
    params = {
        'action': 'query',
        'titles': title,
        'prop': 'revisions',
        'rvprop': 'content',
        'rvslots': 'main',
        'format': 'json'
    }

    try:
        resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=15)
        data = resp.json()
        pages = data.get('query', {}).get('pages', {})

        for page_id, page in pages.items():
            if page_id != '-1':
                revisions = page.get('revisions', [])
                if revisions:
                    return revisions[0].get('slots', {}).get('main', {}).get('*', '')

    except Exception as e:
        logger.debug(f"Wiki content error: {e}")

    return None


def parse_infobox(wikitext):
    """Parse Wikipedia infobox for player information."""
    result = {
        'hometown_city': None,
        'hometown_state': None,
        'high_school': None,
        'college': None,
        'lookup_successful': False
    }

    if not wikitext:
        return result

    # Parse birth_place
    birth_match = re.search(r'\|\s*birth_place\s*=\s*(.+?)(?=\n\||\n\}\})', wikitext, re.DOTALL)

    if birth_match:
        birth_text = birth_match.group(1).strip()

        # Clean wiki markup
        birth_text = re.sub(r'\[\[([^\]|]+)\|[^\]]+\]\]', r'\1', birth_text)
        birth_text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', birth_text)
        birth_text = re.sub(r'\{\{[^}]+\}\}', '', birth_text)
        birth_text = birth_text.replace('U.S.', '').replace('USA', '').strip().rstrip(',')

        parts = [p.strip() for p in birth_text.split(',') if p.strip()]

        if len(parts) >= 2:
            city = parts[0]
            state = parts[1]

            if state in US_STATES:
                result['hometown_city'] = city
                result['hometown_state'] = state
            elif state in STATE_ABBREVS:
                result['hometown_city'] = city
                result['hometown_state'] = STATE_ABBREVS[state]

    # Parse college
    college_match = re.search(r'\|\s*college\s*=\s*(.+?)(?=\n\||\n\}\})', wikitext, re.DOTALL)

    if college_match:
        college_text = college_match.group(1).strip()

        college_link = re.search(r'\[\[([^\]|]+)\|([^\]]+)\]\]', college_text)
        if college_link:
            result['college'] = college_link.group(2).strip()
        else:
            college_link = re.search(r'\[\[([^\]]+)\]\]', college_text)
            if college_link:
                result['college'] = college_link.group(1).strip()
            else:
                college_text = re.sub(r'\{\{[^}]+\}\}', '', college_text).strip()
                if college_text and len(college_text) > 2:
                    result['college'] = college_text

    # Parse high_school
    hs_match = re.search(r'\|\s*high_school\s*=\s*(.+?)(?=\n\||\n\}\})', wikitext, re.DOTALL)

    if hs_match:
        hs_text = hs_match.group(1).strip()

        hs_link = re.search(r'\[\[([^\]|]+)\|([^\]]+)\]\]', hs_text)
        if hs_link:
            result['high_school'] = hs_link.group(2).strip()
        else:
            hs_link = re.search(r'\[\[([^\]]+)\]\]', hs_text)
            if hs_link:
                result['high_school'] = hs_link.group(1).strip()
            else:
                hs_text = re.sub(r'\{\{[^}]+\}\}', '', hs_text).strip()
                if hs_text and len(hs_text) > 2:
                    result['high_school'] = hs_text

    # Successful if we found hometown or college
    if result['hometown_state'] or result['college']:
        result['lookup_successful'] = True

    return result


def lookup_player(name):
    """Look up a player's hometown and college on Wikipedia."""
    clean = clean_name(name)

    title = search_wikipedia(clean)
    if not title:
        return None

    wikitext = get_wiki_wikitext(title)
    if not wikitext:
        return None

    result = parse_infobox(wikitext)
    result['wiki_title'] = title

    return result if result['lookup_successful'] else None


def load_bbl_players():
    """Load BBL American players from JSON."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    filepath = os.path.join(output_dir, 'bbl_american_stats_latest.json')

    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('players', [])


def save_json(data, filename):
    """Save data to JSON file."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    logger.info(f"Saved: {filepath}")


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("GERMAN BBL - HOMETOWN LOOKUP")
    logger.info("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Load players
    players = load_bbl_players()
    if not players:
        logger.error("No players found")
        return

    logger.info(f"Processing {len(players)} players")

    # Look up each player
    results = []
    success = 0
    failed = 0

    for i, player in enumerate(players):
        name = player.get('name', '')
        team = player.get('team', 'Unknown')
        clean = clean_name(name)

        logger.info(f"[{i+1}/{len(players)}] {clean} ({team})")

        player_result = {
            'name': name,
            'team': team,
            'position': player.get('position'),
            'ppg': player.get('ppg'),
            'rpg': player.get('rpg'),
            'apg': player.get('apg'),
            'games_played': player.get('games_played'),
        }

        # Check manual overrides first
        if name.upper() in MANUAL_OVERRIDES:
            override = MANUAL_OVERRIDES[name.upper()]
            player_result['hometown_city'] = override.get('hometown_city')
            player_result['hometown_state'] = override.get('hometown_state')
            player_result['college'] = override.get('college')
            player_result['high_school'] = override.get('high_school')
            player_result['lookup_successful'] = True
            player_result['source'] = 'manual_override'
            success += 1
            logger.info(f"  OVERRIDE: {override.get('hometown_city')}, {override.get('hometown_state')}")
        else:
            # Look up on Wikipedia
            info = lookup_player(name)

            if info and info.get('lookup_successful'):
                player_result.update(info)
                success += 1
                city = info.get('hometown_city', '')
                state = info.get('hometown_state', '')
                college = info.get('college', '')
                logger.info(f"  FOUND: {city}, {state} | College: {college}")
            else:
                player_result['lookup_successful'] = False
                failed += 1
                logger.info(f"  Not found")

            # Rate limiting
            time.sleep(0.3)

        results.append(player_result)

    # Save all results
    save_json({
        'export_date': datetime.now().isoformat(),
        'total': len(players),
        'found': success,
        'not_found': failed,
        'players': results
    }, f'bbl_hometowns_{timestamp}.json')

    # Save just successful lookups
    found = [p for p in results if p.get('lookup_successful')]
    save_json({
        'export_date': datetime.now().isoformat(),
        'count': len(found),
        'players': found
    }, 'bbl_hometowns_latest.json')

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total: {len(players)}")
    logger.info(f"Found: {success} ({success/len(players)*100:.1f}%)")
    logger.info(f"Not found: {failed}")

    if found:
        logger.info("\nPlayers with hometown:")
        for p in found[:15]:
            city = p.get('hometown_city', '')
            state = p.get('hometown_state', '')
            college = p.get('college', 'N/A')
            logger.info(f"  {p['name']}: {city}, {state} | {college}")


if __name__ == '__main__':
    main()

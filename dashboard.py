"""
=============================================================================
INTERNATIONAL BASKETBALL - UNIFIED AMERICAN PLAYERS DASHBOARD
=============================================================================
A single dashboard for tracking American players across multiple international
basketball leagues with easy league switching.
"""

import json
import os
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# League configuration
LEAGUES = {
    'euroleague': {
        'name': 'EuroLeague',
        'country': 'Europe',
        'color': '#E31837',
        'data_file': 'euroleague_american_players_latest.json',
    },
    'acb': {
        'name': 'Liga ACB',
        'country': 'Spain',
        'color': '#FF6B00',
        'data_file': 'acb_american_players_latest.json',
    },
    'bsl': {
        'name': 'Turkish BSL',
        'country': 'Turkey',
        'color': '#E30A17',
        'data_file': 'bsl_american_players_latest.json',
    },
    'cba': {
        'name': 'Chinese Basketball Association',
        'country': 'China',
        'color': '#DE2910',
        'data_file': 'cba_american_players_latest.json',
    },
    'nbl': {
        'name': 'NBL Australia',
        'country': 'Australia',
        'color': '#00843D',
        'data_file': 'nbl_american_players_latest.json',
    },
    'lnb': {
        'name': 'LNB Pro A',
        'country': 'France',
        'color': '#0055A4',
        'data_file': 'lnb_american_players_latest.json',
    },
    'lba': {
        'name': 'Lega Basket Serie A',
        'country': 'Italy',
        'color': '#009246',
        'data_file': 'lba_american_players_latest.json',
    },
    'bbl': {
        'name': 'Basketball Bundesliga',
        'country': 'Germany',
        'color': '#FFCC00',
        'data_file': 'bbl_american_players_latest.json',
    },
    'esake': {
        'name': 'Greek Basket League',
        'country': 'Greece',
        'color': '#0D5EAF',
        'data_file': 'esake_american_players_latest.json',
    },
}


def load_league_data(league_code):
    """Load player data for a specific league."""
    if league_code not in LEAGUES:
        return None

    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    filepath = os.path.join(output_dir, LEAGUES[league_code]['data_file'])

    if not os.path.exists(filepath):
        return {'players': [], 'export_date': 'No data available'}

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_player_detail(league_code, player_code):
    """Load detailed player data including game logs."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')

    # Try unified file first
    unified_file = os.path.join(output_dir, f'{league_code}_unified_players_latest.json')
    if os.path.exists(unified_file):
        with open(unified_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        # Fall back to summary file
        data = load_league_data(league_code)

    if not data:
        return None

    for player in data.get('players', []):
        if str(player.get('code')) == str(player_code):
            return player

    return None


def get_available_leagues():
    """Get list of leagues that have data available."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')
    available = []

    for code, config in LEAGUES.items():
        filepath = os.path.join(output_dir, config['data_file'])
        if os.path.exists(filepath):
            available.append({
                'code': code,
                **config
            })

    return available


def get_styles(league_color='#333'):
    """Return CSS styles with the given league color."""
    return f"""
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }}
        h1 {{
            color: {league_color};
            margin: 0;
        }}
        .league-selector {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .league-btn {{
            padding: 8px 16px;
            border: 2px solid #ddd;
            border-radius: 20px;
            background: white;
            cursor: pointer;
            text-decoration: none;
            color: #333;
            font-size: 0.9em;
            transition: all 0.2s;
        }}
        .league-btn:hover {{
            border-color: #999;
            background: #f9f9f9;
        }}
        .league-btn.active {{
            border-color: {league_color};
            background: {league_color};
            color: white;
        }}
        .filters {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .filters select, .filters input {{
            padding: 8px;
            margin-right: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        table {{
            width: 100%;
            background: white;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background: {league_color};
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-size: 0.85em;
        }}
        th a {{ color: white; text-decoration: none; }}
        td {{
            padding: 10px 8px;
            border-bottom: 1px solid #eee;
            font-size: 0.9em;
        }}
        tr:hover {{ background: #f9f9f9; }}
        a {{ color: {league_color}; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .stats {{ font-weight: bold; }}
        .hometown {{ color: #666; font-size: 0.85em; }}
        .last-updated {{
            color: #666;
            font-size: 0.85em;
            margin-bottom: 10px;
        }}
        .player-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .game-log {{ font-size: 0.9em; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            color: white;
        }}
        .badge.win {{ background: #28a745; }}
        .badge.loss {{ background: #dc3545; }}
        .player-header {{
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }}
        .player-headshot {{
            width: 150px;
            height: auto;
            border-radius: 8px;
            object-fit: cover;
        }}
        .player-info {{ flex: 1; }}
        .player-info h2 {{
            margin-top: 0;
            color: {league_color};
        }}
        .home-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        .league-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
            color: inherit;
        }}
        .league-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }}
        .league-card h3 {{
            margin: 0 0 8px 0;
        }}
        .league-card .country {{
            color: #666;
            font-size: 0.9em;
        }}
        .league-card .player-count {{
            margin-top: 15px;
            font-size: 1.5em;
            font-weight: bold;
        }}
        @media (max-width: 768px) {{
            th, td {{ padding: 8px 4px; font-size: 0.8em; }}
            .player-header {{ flex-direction: column; }}
        }}
    """


HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>International Basketball - American Players Dashboard</title>
    <style>{{ styles }}</style>
</head>
<body>
<header>
    <h1>International Basketball</h1>
    <p style="color: #666; margin: 0;">American Players Dashboard</p>
</header>

<p>Track American basketball players competing in leagues around the world. Select a league below to view players.</p>

<div class="home-grid">
    {% for league in leagues %}
    <a href="/league/{{ league.code }}" class="league-card" style="border-left: 4px solid {{ league.color }};">
        <h3 style="color: {{ league.color }};">{{ league.name }}</h3>
        <div class="country">{{ league.country }}</div>
        <div class="player-count">{{ league.player_count if league.player_count else '—' }} players</div>
    </a>
    {% endfor %}
</div>

<div style="margin-top: 40px; padding: 20px; background: white; border-radius: 8px;">
    <h3>About</h3>
    <p>This dashboard tracks American basketball players in international leagues. Data is updated daily via automated scrapers.</p>
    <p><strong>Leagues:</strong> EuroLeague, Liga ACB (Spain), Turkish BSL, CBA (China), NBL (Australia), LNB Pro A (France), Lega Basket Serie A (Italy), Basketball Bundesliga (Germany), Greek Basket League</p>
</div>
</body>
</html>
"""

LEAGUE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ league_name }} - American Players</title>
    <style>{{ styles }}</style>
</head>
<body>
<header>
    <div>
        <a href="/" style="color: #666; font-size: 0.9em;">&larr; All Leagues</a>
        <h1>{{ league_name }}</h1>
    </div>
    <div class="league-selector">
        {% for lg in all_leagues %}
        <a href="/league/{{ lg.code }}" class="league-btn {% if lg.code == current_league %}active{% endif %}"
           style="{% if lg.code == current_league %}border-color: {{ lg.color }}; background: {{ lg.color }};{% endif %}">
            {{ lg.name }}
        </a>
        {% endfor %}
    </div>
</header>

<p class="last-updated">Last updated: {{ export_date }} | {{ league_country }}</p>

<div class="filters">
    <form method="GET">
        <input type="text" name="search" placeholder="Search by name..." value="{{ search }}">
        <select name="team">
            <option value="">All Teams</option>
            {% for team in teams %}
            <option value="{{ team }}" {% if team == selected_team %}selected{% endif %}>{{ team }}</option>
            {% endfor %}
        </select>
        <select name="state">
            <option value="">All States</option>
            {% for state in states %}
            <option value="{{ state }}" {% if state == selected_state %}selected{% endif %}>{{ state }}</option>
            {% endfor %}
        </select>
        <button type="submit">Filter</button>
        <a href="/league/{{ current_league }}">Reset</a>
    </form>
</div>

<table>
    <thead>
        <tr>
            <th>Player</th>
            <th>Team</th>
            <th>Pos</th>
            <th>GP</th>
            <th>PPG</th>
            <th>RPG</th>
            <th>APG</th>
            <th>Hometown</th>
            <th>High School</th>
            <th>College</th>
        </tr>
    </thead>
    <tbody>
        {% for player in players %}
        <tr>
            <td><a href="/player/{{ current_league }}/{{ player.code }}">{{ player.name }}</a></td>
            <td>{{ player.team or 'N/A' }}</td>
            <td>{{ player.position or 'N/A' }}</td>
            <td>{{ player.games_played or '-' }}</td>
            <td class="stats">{{ '%.1f'|format(player.ppg) if player.ppg else '-' }}</td>
            <td>{{ '%.1f'|format(player.rpg) if player.rpg else '-' }}</td>
            <td>{{ '%.1f'|format(player.apg) if player.apg else '-' }}</td>
            <td class="hometown">{{ player.hometown or 'Unknown' }}</td>
            <td>{{ player.high_school or 'N/A' }}</td>
            <td>{{ player.college or 'N/A' }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<p>Showing {{ players|length }} American players</p>
</body>
</html>
"""

PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ player.name }} - {{ league_name }}</title>
    <style>{{ styles }}</style>
</head>
<body>
<header>
    <div>
        <a href="/league/{{ current_league }}" style="color: #666; font-size: 0.9em;">&larr; Back to {{ league_name }}</a>
        <h1>{{ player.name }}</h1>
    </div>
</header>

<div class="player-card player-header">
    {% if player.headshot_url %}
    <img src="{{ player.headshot_url }}" alt="{{ player.name }}" class="player-headshot">
    {% endif %}
    <div class="player-info">
        <h2>{{ player.name }}</h2>
        <p>
            <strong>League:</strong> {{ league_name }}<br>
            <strong>Team:</strong> {{ player.team or 'N/A' }}<br>
            <strong>Position:</strong> {{ player.position or 'N/A' }}<br>
            <strong>Jersey:</strong> #{{ player.jersey or 'N/A' }}<br>
            <strong>Height:</strong> {% if player.height_feet %}{{ player.height_feet }}'{{ player.height_inches }}"{% else %}{{ player.height_cm or 'N/A' }} cm{% endif %}<br>
            <strong>Birth Date:</strong> {{ player.birth_date or 'N/A' }}
        </p>
        <p>
            <strong>Hometown:</strong> {{ player.hometown or 'Unknown' }}<br>
            <strong>High School:</strong> {{ player.high_school or 'N/A' }}<br>
            <strong>College:</strong> {{ player.college or 'N/A' }}
        </p>
        {% if player.games_played %}
        <p>
            <strong>Season Stats:</strong><br>
            {{ player.games_played }} GP |
            {{ '%.1f'|format(player.ppg) if player.ppg else '0.0' }} PPG |
            {{ '%.1f'|format(player.rpg) if player.rpg else '0.0' }} RPG |
            {{ '%.1f'|format(player.apg) if player.apg else '0.0' }} APG
        </p>
        {% endif %}
    </div>
</div>

{% if player.upcoming_games %}
<div class="player-card">
    <h3>Upcoming Games</h3>
    <table class="game-log">
        <thead>
            <tr><th>Date</th><th>Opponent</th><th>H/A</th><th>Round</th></tr>
        </thead>
        <tbody>
            {% for game in player.upcoming_games %}
            <tr>
                <td>{{ game.date }}</td>
                <td>{{ game.opponent }}</td>
                <td>{{ game.home_away }}</td>
                <td>{{ game.round or 'N/A' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}

{% if player.game_log %}
<div class="player-card">
    <h3>Game Log</h3>
    <table class="game-log">
        <thead>
            <tr><th>Date</th><th>Opponent</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th></tr>
        </thead>
        <tbody>
            {% for game in player.game_log %}
            <tr>
                <td>{{ game.date or 'N/A' }}</td>
                <td>{{ game.opponent or 'N/A' }}</td>
                <td>{{ game.minutes or '-' }}</td>
                <td class="stats">{{ game.points or '-' }}</td>
                <td>{{ game.rebounds or '-' }}</td>
                <td>{{ game.assists or '-' }}</td>
                <td>{{ game.steals or '-' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}

{% if player.past_games %}
<div class="player-card">
    <h3>Team Results</h3>
    <table class="game-log">
        <thead>
            <tr><th>Date</th><th>Opponent</th><th>H/A</th><th>Result</th><th>Score</th></tr>
        </thead>
        <tbody>
            {% for game in player.past_games[:10] %}
            <tr>
                <td>{{ game.date }}</td>
                <td>{{ game.opponent }}</td>
                <td>{{ game.home_away }}</td>
                <td><span class="badge {% if game.result == 'W' %}win{% else %}loss{% endif %}">{{ game.result }}</span></td>
                <td>{{ game.team_score }} - {{ game.opponent_score }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}
</body>
</html>
"""


@app.route('/')
def home():
    """Home page with league selection."""
    leagues = []
    output_dir = os.path.join(os.path.dirname(__file__), 'output', 'json')

    for code, config in LEAGUES.items():
        filepath = os.path.join(output_dir, config['data_file'])
        player_count = None
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    player_count = len(data.get('players', []))
            except:
                pass

        leagues.append({
            'code': code,
            'player_count': player_count,
            **config
        })

    # Sort: leagues with data first, then alphabetically
    leagues.sort(key=lambda x: (x['player_count'] is None, x['name']))

    return render_template_string(
        HOME_TEMPLATE,
        leagues=leagues,
        styles=get_styles('#333')
    )


@app.route('/league/<league_code>')
def league_view(league_code):
    """View players for a specific league."""
    if league_code not in LEAGUES:
        return redirect(url_for('home'))

    league = LEAGUES[league_code]
    data = load_league_data(league_code)

    if not data:
        return f"No data available for {league['name']}", 404

    players = data.get('players', [])
    export_date = data.get('export_date', 'Unknown')

    # Filters
    search = request.args.get('search', '').lower()
    selected_team = request.args.get('team', '')
    selected_state = request.args.get('state', '')

    if search:
        players = [p for p in players if search in p.get('name', '').lower()]
    if selected_team:
        players = [p for p in players if p.get('team') == selected_team]
    if selected_state:
        players = [p for p in players if p.get('hometown_state') == selected_state]

    # Sort by name
    players = sorted(players, key=lambda p: p.get('name', ''))

    # Get filter options
    all_players = data.get('players', [])
    teams = sorted(set(p.get('team') for p in all_players if p.get('team')))
    states = sorted(set(p.get('hometown_state') for p in all_players if p.get('hometown_state')))

    # Get all available leagues for selector
    all_leagues = get_available_leagues()

    return render_template_string(
        LEAGUE_TEMPLATE,
        players=players,
        export_date=export_date,
        league_name=league['name'],
        league_country=league['country'],
        current_league=league_code,
        all_leagues=all_leagues,
        teams=teams,
        states=states,
        search=search,
        selected_team=selected_team,
        selected_state=selected_state,
        styles=get_styles(league['color'])
    )


@app.route('/player/<league_code>/<player_code>')
def player_detail(league_code, player_code):
    """View detailed player information."""
    if league_code not in LEAGUES:
        return redirect(url_for('home'))

    league = LEAGUES[league_code]
    player = load_player_detail(league_code, player_code)

    if not player:
        return "Player not found", 404

    return render_template_string(
        PLAYER_TEMPLATE,
        player=player,
        league_name=league['name'],
        current_league=league_code,
        styles=get_styles(league['color'])
    )


if __name__ == '__main__':
    print("=" * 60)
    print("INTERNATIONAL BASKETBALL - AMERICAN PLAYERS DASHBOARD")
    print("=" * 60)
    print("\nStarting web server...")
    print("Open your browser to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server\n")

    app.run(debug=True, host='0.0.0.0', port=5000)

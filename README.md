# International Basketball - American Players Dashboard

A unified dashboard tracking American basketball players across multiple international leagues.

## Leagues Tracked

| League | Country | Status |
|--------|---------|--------|
| EuroLeague | Europe | Active |
| Liga ACB | Spain | Active |
| Turkish BSL | Turkey | Active |
| CBA | China | Coming Soon |
| NBL | Australia | Coming Soon |
| LNB Pro A | France | Coming Soon |
| Lega Basket Serie A | Italy | Coming Soon |
| Basketball Bundesliga | Germany | Coming Soon |
| Greek Basket League | Greece | Coming Soon |

## Features

- **League Toggle**: Switch between leagues with a single click
- **Player Search**: Filter by name, team, or home state
- **Player Profiles**: View detailed stats, game logs, and upcoming games
- **Daily Updates**: Automated scraping via GitHub Actions
- **Hometown Data**: Wikipedia integration for hometown/college info

## Project Structure

```
unified/
├── dashboard.py          # Flask web application
├── requirements.txt      # Python dependencies
├── Dockerfile            # Container configuration for Render
├── output/json/          # Data files for each league
├── scrapers/
│   ├── euroleague/       # EuroLeague scraper
│   ├── acb/              # Liga ACB scraper
│   └── bsl/              # Turkish BSL scraper
└── .github/workflows/    # GitHub Actions for daily scraping
```

## Running Locally

```bash
pip install -r requirements.txt
python dashboard.py
# Open http://localhost:5000
```

## Data Sources

- **EuroLeague**: Official EuroLeague API
- **Liga ACB**: ACB.com box scores
- **Turkish BSL**: TBLStat.net + TheSportsDB
- **Hometown Data**: Wikipedia

## Deployment

Deployed to Render with automatic deploys on push to main branch.

## License

MIT

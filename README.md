# 🌍 Global Epidemic Tracker

> **CDC is dead, we protect the people.**
>
> **El pueblo unido jamás será vencido.**

[![Live Dashboard](https://img.shields.io/badge/Live-Dashboard-00d4aa?style=for-the-badge&logo=googlechrome&logoColor=white)](https://mrlmrml.github.io/global-epidemic-tracker/)
[![Auto Update](https://github.com/MRLMRML/global-epidemic-tracker/actions/workflows/update-data.yml/badge.svg)](https://github.com/MRLMRML/global-epidemic-tracker/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Real-time global disease outbreak monitoring with news cross-validation. Data sourced from WHO Disease Outbreak News API, validated against independent news outlets, and presented through an interactive Chinese-language dashboard.

---

## What It Does

```
WHO DON API  →  Data Collector  →  News Cross-Validation  →  Dashboard
(all diseases)    (53 diseases)     (Bing/Google/Reddit)       (中文)
```

- **581 active outbreaks** across **151 countries**
- **53 diseases** tracked including Cholera, Ebola, Dengue, Measles, Hantavirus, Mpox, and more
- **2.97M cases** and **13,677 deaths** monitored globally
- **News cross-validation**: every outbreak verified against Bing, Google News, and Reddit
- **Data source & credibility labels**: each disease card shows data source and verification status
- **Auto-updates every 6 hours** via GitHub Actions

## Dashboard

**[→ Open Dashboard](https://mrlmrml.github.io/global-epidemic-tracker/)**

| Feature | Description |
|---------|------------|
| Interactive map | Dark theme, cluster markers, severity colors |
| Hierarchical filters | Continent → Country, Pathogen Type → Disease |
| Data source labels | WHO, OWID, news cross-validation badges per disease |
| Credibility indicators | Verified / Partial / Pending status for each outbreak |
| Disease tooltips | Hover to see disease description |
| Risk alerts | H2H transmission warnings, severity ranking |
| News ticker | Scrolling latest outbreak news |
| Disease detail | Click for 7-day/30-day/6-month trend charts |
| Language | 中文（简体） |

## Quick Start

```bash
git clone https://github.com/MRLMRML/global-epidemic-tracker.git
cd global-epidemic-tracker
pip install requests

# Fetch latest data + news validation
python3 scripts/fetch_data.py --fetch --validate --summary

# Export for dashboard
python3 scripts/fetch_data.py --fetch --export-json --export-geojson

# Open dashboard locally
open site/index.html          # macOS
xdg-open site/index.html      # Linux
start site/index.html          # Windows
```

## Python API

```python
from src.collectors.aggregator import EpidemicAggregator

agg = EpidemicAggregator()
agg.fetch_all(validate=True)

# Global summary
summary = agg.get_global_summary()
# → 581 outbreaks, 2,970,802 cases, 13,677 deaths

# Filter by disease, country, severity
cholera = agg.get_outbreaks(disease="Cholera")
japan = agg.get_outbreaks(country="JPN")
critical = agg.get_outbreaks(severity="very_high")

# Filter by continent and pathogen type
asia_outbreaks = agg.get_outbreaks(continent="Asia")
virus_outbreaks = agg.get_outbreaks(pathogen_type="Virus")

# Risk assessment
risk = agg.get_risk_assessment("JPN")
# → {"level": "low", "total_cases": 0, ...}
```

## Agent Integration

The `SKILL.md` file makes this project usable as an AI agent skill. Compatible with:

- **OpenCode** — `load_skills=["global-epidemic-tracker"]`
- **Claude Code** — Reference `SKILL.md` in context
- **OpenClaw** / **Hermes** — Include `SKILL.md` in agent context

Example agent queries:
- "What cholera outbreaks are active right now?"
- "What's the most dangerous outbreak in Asia?"
- "What diseases have H2H transmission?"

## Architecture

```
global-epidemic-tracker/
├── SKILL.md                          # Agent skill definition
├── scripts/fetch_data.py             # CLI data pipeline
├── src/
│   ├── collectors/
│   │   ├── who_don.py                # WHO Disease Outbreak News API
│   │   ├── who_gho.py                # WHO Global Health Observatory
│   │   ├── owid.py                   # Our World in Data (Mpox)
│   │   └── aggregator.py             # Multi-source aggregation
│   ├── validation/
│   │   └── news_validator.py         # Bing/Google/Reddit cross-validation
│   └── models/
│       └── __init__.py               # Data models (Outbreak, Country, etc.)
├── site/
│   ├── index.html                    # Dashboard (single-file, no server needed)
│   └── data/                         # Live data (JSON/GeoJSON)
├── data/
│   └── processed/                    # Exported data
├── .github/workflows/
│   └── update-data.yml               # Auto-update every 6 hours
└── SKILL.md                          # Agent skill
```

## Data Sources

| Source | What | Method | Frequency |
|--------|------|--------|-----------|
| **WHO DON API** | Global outbreak alerts | REST API | Event-driven |
| **WHO GHO** | Annual disease statistics | REST API | Annual |
| **OWID** | Mpox daily data | CSV | Daily |
| **Bing News** | Cross-validation | RSS | Per-run |
| **Google News** | Cross-validation | RSS | Per-run |
| **Reddit** | Community reports | API | Per-run |

## Diseases Tracked

Cholera · Ebola · Marburg · Mpox · Dengue · Measles · Influenza · Hantavirus · Yellow Fever · Meningitis · Polio · MERS · Nipah · Rift Valley Fever · West Nile · Oropouche · Lassa Fever · CCHF · Plague · Anthrax · Chikungunya · Diphtheria · Hepatitis E · Rabies · Zika · COVID-19 · and more (53 total)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Areas to contribute:
- New data source collectors
- Disease name translations
- Dashboard improvements
- Data accuracy fixes

## License

MIT — Use it, fork it, deploy it. The people's data belongs to the people.

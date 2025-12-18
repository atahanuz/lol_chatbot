# League of Legends Chatbot

A semantic web-powered chatbot that answers questions about League of Legends using RDF/Turtle ontologies and Language Models.

Developed by [Atahan Uz](https://www.linkedin.com/in/atahan-uz/) & [Gizem Yılmaz](https://www.linkedin.com/in/gizem7/)

Presentation: [Presentation.pdf](Presentation.pdf)

Paper: Coming Soon

![App Screenshot](assets/app.png)


## Features

- **Natural Language Queries**: Ask questions about champions, items, abilities, monsters, and turrets in plain English
- **Snapshot Analsyis**: Upload snapshot of a game state in JSON format and see suggestions
- **Semantic Web Data**: Uses RDF/Turtle ontologies for structured game data representation
- **Intent Classification**: AI-powered understanding of user questions to extract relevant entities
- **Comprehensive Game Data**: Includes 169 champions, 314 items, 17 monsters, and 4 turret types
- **Multiple Interfaces**: CLI and Streamlit web interface

## Project Structure

```
ssw_chatbot/
├── src/                          # Source code
│   ├── __init__.py               # Package initializer
│   ├── config.py                 # Configuration and file paths
│   ├── ttl_parser.py             # RDF/Turtle data parsing
│   ├── prompts.py                # OpenAI prompt templates
│   ├── intent_classifier.py      # NLU intent classification
│   ├── data_retriever.py         # Data lookup and retrieval
│   ├── sparql_queries.py         # SPARQL query engine
│   ├── snapshot_analyzer.py      # Game snapshot analysis
│   ├── main.py                   # CLI chatbot interface
│   └── streamlit_app.py          # Web UI interface
├── data/
│   ├── ontology/                 # RDF ontology schema
│   │   └── MobaGameOntology.rdf
│   ├── graphs/                   # RDF/Turtle graph files
│   │   ├── lol_champions.ttl
│   │   ├── lol_champions_functional.ttl
│   │   ├── lol_enrichment.ttl
│   │   ├── lol_items.ttl
│   │   ├── lol_monsters.ttl
│   │   └── lol_turrets.ttl
│   └── game_data/                # JSON game data files
│       ├── build_data/           # Champion build data (169 files)
│       ├── counter_data/         # Champion counter data (169 files)
│       ├── synergy_data/         # Champion synergy data (169 files)
│       ├── champions.json
│       ├── items.json
│       ├── monsters.json
│       ├── turrets.json
│       ├── enrichment_data.json
│       └── game_snapshots.json
├── scripts/
│   ├── mapping/                  # Ontology mapping scripts
│   │   ├── map_all_champion_data.py
│   │   ├── map_champions_to_ontology.py
│   │   ├── map_items_to_ontology.py
│   │   ├── map_monsters_to_ontology.py
│   │   └── map_turrets_to_ontology.py
│   └── scraping/                 # Data scraping scripts
│       ├── ontology_enricher.py
│       ├── scrape_builds.py
│       ├── scrape_counters.py
│       ├── scrape_monsters.py
│       └── scrape_synergy.py
├── assets/                       # Images and media
│   ├── app.png
│   ├── artwork_1.jpg
│   ├── artwork_2.jpg
│   └── lol_symbol.png
├── docs/                         # Documentation
│   └── WORKFLOW.md
├── requirements.txt
└── README.md
```

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ssw_chatbot.git
   cd ssw_chatbot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your LLM API key
   ```

## Usage

### CLI Interface

Run the command-line chatbot:

```bash
cd src
python main.py
```

### Web Interface (Streamlit)

Run the Streamlit web application:

```bash
cd src
streamlit run streamlit_app.py
```

## Example Questions
- "Who should I pick to counter enemy team: Yasuo mid, Zed jungle, Jinx ADC?"
- "Which assassins have stealth in their kit?"
- "On Jinx Should I buy IE or The Bloodthirster"
- "How much damage does Evelynn's Q do at level 3?"
- "What items should I build on Aatrox?"
- "How much does Infinity Edge cost?"

## Snapshot Analysis
Open the sidebar, select one of the games click "Analyse Game Snapshot"
By default, it analyses games in data/game_data/game_snapshots.json
You can use Riot Games API to fetch the state of a game and update the file to analyse that specific game.

## Data Sources

The chatbot uses semantic web ontologies in RDF/Turtle format:

- **Champions**: 169 champions with stats, skills, counters, synergies, and builds
- **Items**: 314 items with costs, stats, and build paths
- **Monsters**: 17 jungle monsters with health and stats
- **Turrets**: 4 turret types with health, damage, and range

## Architecture

```
User Question
      │
      ▼
┌──────────────────┐
│  Intent          │  (LLM API)
│  Classifier      │  - Extracts intent type
│                  │  - Extracts entities
└──────────────────┘
      │
      ▼
┌──────────────────┐
│  Data            │  (Local Python dictionaries)
│  Retriever       │  - Looks up structured data
│                  │  - Returns relevant information
└──────────────────┘
      │
      ▼
┌──────────────────┐
│  Response        │  (LLM API)
│  Generator       │  - Formats data into natural language
│                  │  - Maintains conversation context
└──────────────────┘
      │
      ▼
   Bot Response
```

## Requirements

- Python 3.8+
- OpenAI API Key (you can configure the app use other providers or a locally running LLM)
- Dependencies listed in `requirements.txt`

## Planned Features

- Support Dota2 and other MOBA games
- Allow be


## Acknowledgments

- League of Legends game by Riot Games
- Game data by [Mobalytics](https://mobalytics.gg/lol), [LoL Wiki](https://wiki.leagueoflegends.com/en-us/), [DataDragon](https://github.com/meraki-analytics/lolstaticdata), [Leaguepedia](https://lol.fandom.com/wiki/Help:Leaguepedia_API) and [LoLAlytics](https://lolalytics.com)
- Prof. Suzan Üsküdarlı for her guidance during the project 

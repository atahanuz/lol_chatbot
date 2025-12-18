# LoL Chatbot Workflow Documentation

## Overview

This chatbot answers questions about League of Legends by combining:
1. **Structured game data** from RDF/Turtle files (champions, items, monsters, turrets)
2. **OpenAI GPT** for natural language understanding and response generation

## Architecture Diagram

```
User Question
      |
      v
+------------------+
|  Intent          |  (OpenAI API)
|  Classifier      |  - Extracts intent type
|                  |  - Extracts entities (champion, skill, item, etc.)
+------------------+
      |
      v
+------------------+
|  Data            |  (Local Python dictionaries)
|  Retriever       |  - Looks up structured data
|                  |  - Returns relevant information
+------------------+
      |
      v
+------------------+
|  Response        |  (OpenAI API)
|  Generator       |  - Formats data into natural language
|                  |  - Maintains conversation context
+------------------+
      |
      v
   Bot Response
```

## Data Sources

### 1. Champions Data (`lol_champions_with_counters_synergy_builds.ttl`)
- **Format**: RDF Turtle
- **Contents**: 171 champions with:
  - Base stats (health, mana, armor, attack damage, etc.)
  - Stat growth per level
  - Skills (P, Q, W, E, R) with damage/cooldown at each level
  - Roles and lanes
  - Counter relationships (who beats who)
  - Synergy relationships (who works well together)
  - Item build recommendations

### 2. Items Data (`lol_items.ttl`)
- **Format**: RDF Turtle
- **Contents**: 314 items with:
  - Gold cost
  - Stats provided (AD, AP, health, etc.)
  - Build paths (components)
  - Item type (Advanced, Component, Consumable)

### 3. Monsters Data (`lol_monsters.ttl`)
- **Format**: RDF Turtle
- **Contents**: 17 jungle monsters with:
  - Health
  - Stats (armor, damage, etc.)
  - Spawn information

### 4. Turrets Data (`lol_turrets.ttl`)
- **Format**: RDF Turtle
- **Contents**: 4 turret types with:
  - Health
  - Damage
  - Attack range

## File Structure

```
ssw_chatbot/
├── src/                   # Source code
│   ├── config.py          # Configuration and file paths
│   ├── ttl_parser.py      # RDF/Turtle data parsing
│   ├── prompts.py         # OpenAI prompt templates
│   ├── intent_classifier.py   # NLU intent classification
│   ├── data_retriever.py  # Data lookup and retrieval
│   ├── sparql_queries.py  # SPARQL query engine
│   ├── snapshot_analyzer.py   # Game snapshot analysis
│   ├── ontology_enricher.py   # Ontology data enrichment
│   ├── main.py            # CLI chatbot interface
│   └── streamlit_app.py   # Web UI interface
├── data/
│   ├── ontology/          # RDF/Turtle ontology files
│   │   ├── lol_champions_with_counters_synergy_builds.ttl
│   │   ├── lol_items.ttl
│   │   ├── lol_monsters.ttl
│   │   ├── lol_turrets.ttl
│   │   └── MobaGameOntology.rdf
│   ├── enrichment_data.json
│   └── game_snapshots.json
├── assets/                # Images and media
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── requirements.txt
└── README.md
```

## Component Details

### 1. TTL Parser (`ttl_parser.py`)

**Purpose**: Parses RDF/Turtle files into Python dictionaries for fast lookup.

**Key Functions**:
- `parse_ttl_to_dict()` - Parses champion data
- `parse_items_ttl()` - Parses item data
- `parse_monsters_ttl()` - Parses monster data
- `parse_turrets_ttl()` - Parses turret data
- `parse_all_data()` - Loads all data sources into a combined dictionary

**Data Structure** (simplified):
```python
{
    "champions": {
        "evelynn": {
            "name": "Evelynn",
            "base_stats": {"health": 642, "mana": 315, ...},
            "skills": {
                "Q": {
                    "name": "Hate Spike",
                    "levels": {
                        1: {"damage": 25, "cooldown": 4},
                        2: {"damage": 30, "cooldown": 4},
                        ...
                    }
                },
                ...
            },
            "counters": [...],
            "synergy": [...],
            "core_items": [...],
        },
        ...
    },
    "items": {"infinity_edge": {...}, ...},
    "monsters": {"baron_nashor": {...}, ...},
    "turrets": {"outer_turret": {...}, ...},
}
```

### 2. Intent Classifier (`intent_classifier.py`)

**Purpose**: Uses OpenAI to understand user questions and extract structured information.

**How It Works**:
1. Receives user question + conversation history
2. Sends to OpenAI with a classification prompt
3. Returns JSON with intent type and entities

**Supported Intents**:
| Intent | Example Question |
|--------|------------------|
| `SKILL_DAMAGE_AT_LEVEL` | "How much damage does Evelynn's Q do at level 3?" |
| `SKILL_INFO` | "What does Jinx's W do?" |
| `CHAMPION_BASE_STATS` | "What is Ashe's base health?" |
| `CHAMPION_INFO` | "Tell me about Aatrox" |
| `COUNTER_QUERY` | "Who counters Yasuo?" |
| `SYNERGY_QUERY` | "Who synergizes with Jinx?" |
| `BUILD_QUERY` | "What items should I build on Aatrox?" |
| `ITEM_INFO` | "How much does Infinity Edge cost?" |
| `MONSTER_INFO` | "How much health does Baron have?" |
| `TURRET_INFO` | "What is the outer turret's damage?" |

**Extracted Entities**:
- `champion_name` - The champion mentioned
- `skill_key` - Q, W, E, R, or P (passive)
- `skill_level` - 1-5 for abilities
- `character_level` - 1-18 for stats
- `item_name` - Item being queried
- `monster_name` - Monster being queried
- `turret_name` - Turret type being queried
- `counter_direction` - "counters" or "countered_by"

**Context Resolution**:
The classifier receives conversation history to resolve pronouns:
- "What about her W?" -> resolves "her" to previously discussed champion
- "What does it cost?" -> resolves "it" to previously discussed item

### 3. Data Retriever (`data_retriever.py`)

**Purpose**: Looks up data based on classified intent and entities.

**Key Methods**:
| Method | Returns |
|--------|---------|
| `get_skill_damage_at_level()` | Damage, cooldown at specific skill level |
| `get_skill_info()` | All info about a skill |
| `get_champion_base_stats()` | Champion's level 1 stats |
| `get_champion_stats_at_level()` | Stats calculated at any level 1-18 |
| `get_counters()` | Who counters/is countered by champion |
| `get_synergies()` | Champions with good synergy |
| `get_build()` | Core/recommended/situational items |
| `get_item_info()` | Item stats, cost, build path |
| `get_monster_info()` | Monster health and stats |
| `get_turret_info()` | Turret health and damage |

**Name Normalization**:
- "Rabadon's Deathcap" -> "rabadons_deathcap"
- "Dr. Mundo" -> "dr_mundo"
- Aliases: "TF" -> "twisted_fate", "MF" -> "miss_fortune"

**Query Dispatch**:
The `dispatch_query()` function routes intents to the appropriate method:
```python
if intent_type == "SKILL_DAMAGE_AT_LEVEL":
    return retriever.get_skill_damage_at_level(...)
elif intent_type == "ITEM_INFO":
    return retriever.get_item_info(...)
# ... etc
```

### 4. Response Generator (`main.py` / `streamlit_app.py`)

**Purpose**: Converts retrieved data into natural language responses.

**How It Works**:
1. Receives user question + retrieved data
2. Formats data as JSON string
3. Sends to OpenAI with response generation prompt
4. Returns natural language answer

**System Prompt Context**:
- Knows about all data types available
- Instructed to be concise but informative
- Formats numbers nicely (35 not 35.0)
- Handles errors gracefully

## Request Flow Example

**User asks**: "How much damage does Evelynn's Q do at level 3?"

```
1. INTENT CLASSIFICATION
   Input: "How much damage does Evelynn's Q do at level 3?"
   Output: {
       "intent": "SKILL_DAMAGE_AT_LEVEL",
       "champion_name": "evelynn",
       "skill_key": "Q",
       "skill_level": 3
   }

2. DATA RETRIEVAL
   Method: get_skill_damage_at_level("evelynn", "Q", 3)
   Output: {
       "champion": "Evelynn",
       "skill_name": "Hate Spike",
       "skill_key": "Q",
       "level": 3,
       "damage": 35,
       "damage_type": "MagicDamage"
   }

3. RESPONSE GENERATION
   Input: Question + Retrieved Data
   Output: "Evelynn's Q (Hate Spike) deals 35 magic damage at level 3."
```

## Interfaces

### CLI (`main.py`)
- Run: `python main.py`
- Features:
  - Simple text-based chat
  - Context panel showing retrieved data
  - Conversation history for context

### Web UI (`streamlit_app.py`)
- Run: `streamlit run streamlit_app.py`
- Features:
  - Chat interface with message history
  - Side panel showing intent classification and retrieved data
  - Background image and styled UI

## Configuration

**Environment Variables** (`.env`):
```
OPENAI_API_KEY=your-api-key-here
```

**Model Settings** (`config.py`):
```python
MODEL_NAME = "gpt-4o-mini"  # Fast and cost-effective
```

## Error Handling

1. **Champion/Item Not Found**: Returns available options
2. **Invalid Skill Level**: Returns available levels
3. **Unknown Intent**: Suggests what can be asked
4. **API Errors**: Graceful error messages

## Performance Considerations

1. **Data Pre-loading**: All TTL files parsed once at startup
2. **Dictionary Lookups**: O(1) access to champions/items by normalized name
3. **Caching**: Streamlit uses `@st.cache_resource` to avoid re-parsing
4. **Context Limits**: Only last 6 exchanges sent to OpenAI for context

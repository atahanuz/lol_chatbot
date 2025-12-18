#!/usr/bin/env python3
"""
Unified Champion Data Mapping Script

This script combines counter, synergy, and build data mapping into a single
comprehensive pipeline. It loads the base lol_champions.ttl and outputs a
complete lol_champions_complete.ttl with all relationships.

Data Mappings:
1. Counter Data:
   - counters: Hero counters another Hero (subject is strong against object)
   - hardCounters: Hero severely counters another Hero (score <= 4.0)
   - counteredBy: Hero is countered by another Hero (subject is weak against object)
   - hardCounteredBy: Hero is severely countered (score >= 5.5)

2. Synergy Data:
   - strongSynergyWith: Win rate >= 52%
   - synergyWith: Win rate >= 50%
   - weakSynergyWith: Win rate 48-50%

3. Build Data:
   - coreItem: Core items for a champion
   - situationalItem: Optional items (4th, 5th, 6th slots)
   - recommendedItem: Full build items
"""

import json
import os
import re
import glob
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD
from urllib.parse import quote

# Define paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # ssw_chatbot/

# Data directories
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
GRAPHS_DIR = os.path.join(DATA_DIR, 'graphs')
GAME_DATA_DIR = os.path.join(DATA_DIR, 'game_data')

# Input files (TTL files in data/graphs)
BASE_CHAMPIONS_FILE = os.path.join(GRAPHS_DIR, 'lol_champions.ttl')
ITEMS_FILE = os.path.join(GRAPHS_DIR, 'lol_items.ttl')

# Data directories (JSON data inside data/game_data folder)
COUNTER_DATA_DIR = os.path.join(GAME_DATA_DIR, 'counter_data')
SYNERGY_DATA_DIR = os.path.join(GAME_DATA_DIR, 'synergy_data')
BUILD_DATA_DIR = os.path.join(GAME_DATA_DIR, 'build_data')

# Output file (in data/graphs)
OUTPUT_FILE = os.path.join(GRAPHS_DIR, 'lol_champions_functional.ttl')

# Define namespace
MOBA = Namespace("http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def sanitize_uri(name: str) -> str:
    """Create a valid URI component from a name."""
    sanitized = re.sub(r"['\-\.\(\)\:\,\&\!\/]", '', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = sanitized.replace('%', '_Percent')
    return quote(sanitized, safe='_')


def normalize_champion_name(name: str) -> str:
    """Normalize champion name for URI matching."""
    # Comprehensive special cases mapping
    special_cases = {
        # Space-separated names
        "Jarvan IV": "Jarvan_IV",
        "Lee Sin": "Lee_Sin",
        "Master Yi": "Master_Yi",
        "Xin Zhao": "Xin_Zhao",
        "Twisted Fate": "Twisted_Fate",
        "Miss Fortune": "Miss_Fortune",
        "Dr. Mundo": "Dr_Mundo",
        "Tahm Kench": "Tahm_Kench",
        "Aurelion Sol": "Aurelion_Sol",
        "Renata Glasc": "Renata_Glasc",
        
        # Apostrophe names
        "Kog'Maw": "KogMaw",
        "Kha'Zix": "KhaZix",
        "Bel'Veth": "BelVeth",
        "Cho'Gath": "ChoGath",
        "Rek'Sai": "RekSai",
        "Vel'Koz": "VelKoz",
        "Kai'Sa": "KaiSa",
        "K'Sante": "KSante",
        
        # Special characters
        "Nunu & Willump": "Nunu",
        "Wukong": "Wukong",
        "LeBlanc": "LeBlanc",
    }
    
    # Lowercase mapping for filename-based lookups
    lowercase_map = {
        'aurelionsol': 'Aurelion_Sol',
        'belveth': 'BelVeth',
        'chogath': 'ChoGath',
        'drmundo': 'Dr_Mundo',
        'jarvaniv': 'Jarvan_IV',
        'kaisa': 'KaiSa',
        'khazix': 'KhaZix',
        'kogmaw': 'KogMaw',
        'ksante': 'KSante',
        'leesin': 'Lee_Sin',
        'masteryi': 'Master_Yi',
        'missfortune': 'Miss_Fortune',
        'monkeyking': 'Wukong',
        'nunu': 'Nunu',
        'reksai': 'RekSai',
        'renata': 'Renata_Glasc',
        'tahmkench': 'Tahm_Kench',
        'twistedfate': 'Twisted_Fate',
        'velkoz': 'VelKoz',
        'xinzhao': 'Xin_Zhao',
        'leblanc': 'LeBlanc',
    }
    
    # Try exact match first
    if name in special_cases:
        return special_cases[name]
    
    # Try lowercase match
    lower_name = name.lower().replace('_', '').replace(' ', '').replace("'", "")
    if lower_name in lowercase_map:
        return lowercase_map[lower_name]
    
    # Default: capitalize first letter
    return sanitize_uri(name.capitalize())


def get_existing_champions(g: Graph) -> set:
    """Get the set of champion URIs in the graph."""
    champions = set()
    
    query = """
    PREFIX moba: <http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#>
    
    SELECT ?champion WHERE {
        ?champion moba:heroName ?name .
    }
    """
    
    for row in g.query(query):
        uri = str(row.champion)
        name = uri.split("#")[-1]
        champions.add(name)
    
    return champions


def find_champion_uri(champion_name: str, existing_champions: set, g: Graph) -> URIRef:
    """Find the URI for a champion, or None if not found."""
    normalized = normalize_champion_name(champion_name)
    
    # Direct match
    if normalized in existing_champions:
        return MOBA[normalized]
    
    # Case-insensitive match
    normalized_lower = normalized.lower().replace("_", "")
    for existing in existing_champions:
        if existing.lower().replace("_", "") == normalized_lower:
            return MOBA[existing]
    
    # Fallback: check if URI exists in graph
    potential_uri = MOBA[normalized]
    if (potential_uri, None, None) in g:
        return potential_uri
    
    return None


def parse_win_rate(win_rate_str: str) -> float:
    """Parse win rate string to float."""
    try:
        return float(win_rate_str.replace("%", ""))
    except (ValueError, AttributeError):
        return 0.0


# =============================================================================
# COUNTER DATA MAPPING
# =============================================================================

def load_counter_data(counter_data_dir: str) -> dict:
    """Load all counter data files from the directory."""
    counter_data = {}
    
    for filepath in glob.glob(os.path.join(counter_data_dir, "*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                champion = data.get("champion", "")
                if champion:
                    counter_data[champion] = {
                        "weakAgainst": data.get("weakAgainst", []),
                        "strongAgainst": data.get("strongAgainst", [])
                    }
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not load {filepath}: {e}")
    
    return counter_data


def add_counter_relationships(g: Graph, counter_data: dict, existing_champions: set) -> dict:
    """Add counter relationships to the graph."""
    stats = {
        "counters": 0,
        "hardCounters": 0,
        "counteredBy": 0,
        "hardCounteredBy": 0
    }
    
    for champion, data in counter_data.items():
        champion_uri = find_champion_uri(champion, existing_champions, g)
        if not champion_uri:
            continue
        
        # Process weakAgainst (champion is countered by these)
        for weak in data.get("weakAgainst", []):
            counter_champ = weak.get("champion", "")
            score = weak.get("score", 5.0)
            
            if not counter_champ:
                continue
            
            counter_uri_name = normalize_champion_name(counter_champ)
            counter_uri = MOBA[counter_uri_name]
            
            # Use hardCounteredBy for score >= 5.5, otherwise counteredBy
            if score >= 5.5:
                g.add((champion_uri, MOBA.hardCounteredBy, counter_uri))
                stats["hardCounteredBy"] += 1
            else:
                g.add((champion_uri, MOBA.counteredBy, counter_uri))
                stats["counteredBy"] += 1
        
        # Process strongAgainst (champion counters these)
        for strong in data.get("strongAgainst", []):
            victim_champ = strong.get("champion", "")
            score = strong.get("score", 5.0)
            
            if not victim_champ:
                continue
            
            victim_uri_name = normalize_champion_name(victim_champ)
            victim_uri = MOBA[victim_uri_name]
            
            # Use hardCounters for score <= 4.0, otherwise counters
            if score <= 4.0:
                g.add((champion_uri, MOBA.hardCounters, victim_uri))
                stats["hardCounters"] += 1
            else:
                g.add((champion_uri, MOBA.counters, victim_uri))
                stats["counters"] += 1
    
    return stats


# =============================================================================
# SYNERGY DATA MAPPING
# =============================================================================

def get_champion_from_filename(filename: str) -> str:
    """Extract champion name from synergy data filename."""
    basename = os.path.basename(filename).replace("_duos.json", "")
    
    # Handle special cases in filenames
    name_mapping = {
        "aurelionsol": "Aurelion_Sol",
        "belveth": "BelVeth",
        "chogath": "ChoGath",
        "drmundo": "Dr_Mundo",
        "jarvaniv": "Jarvan_IV",
        "kogmaw": "KogMaw",
        "khazix": "KhaZix",
        "leesin": "Lee_Sin",
        "masteryi": "Master_Yi",
        "missfortune": "Miss_Fortune",
        "reksai": "RekSai",
        "tahmkench": "Tahm_Kench",
        "twistedfate": "Twisted_Fate",
        "velkoz": "VelKoz",
        "xinzhao": "Xin_Zhao",
        "monkeyking": "Wukong",
        "nunu": "Nunu",
        "kaisa": "KaiSa",
        "ksante": "KSante",
        "renata": "Renata_Glasc",
        "leblanc": "LeBlanc",
    }
    
    if basename.lower() in name_mapping:
        return name_mapping[basename.lower()]
    
    return basename.capitalize()


def load_synergy_data(synergy_data_dir: str) -> dict:
    """Load all synergy data files from the directory."""
    synergy_data = {}
    
    for filepath in glob.glob(os.path.join(synergy_data_dir, "*.json")):
        try:
            champion = get_champion_from_filename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    synergy_data[champion] = data
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not load {filepath}: {e}")
    
    return synergy_data


def add_synergy_relationships(g: Graph, synergy_data: dict, existing_champions: set) -> dict:
    """Add synergy relationships to the graph."""
    stats = {
        "strongSynergyWith": 0,
        "synergyWith": 0,
        "weakSynergyWith": 0
    }
    
    for champion, duos in synergy_data.items():
        champion_uri = find_champion_uri(champion, existing_champions, g)
        if not champion_uri:
            continue
        
        for duo in duos:
            partner_name = duo.get("champion", "")
            win_rate = parse_win_rate(duo.get("duo_win_rate", "0%"))
            
            if not partner_name:
                continue
            
            partner_uri_name = normalize_champion_name(partner_name)
            partner_uri = MOBA[partner_uri_name]
            
            # Determine synergy type based on win rate
            if win_rate >= 52.0:
                g.add((champion_uri, MOBA.strongSynergyWith, partner_uri))
                stats["strongSynergyWith"] += 1
            elif win_rate >= 50.0:
                g.add((champion_uri, MOBA.synergyWith, partner_uri))
                stats["synergyWith"] += 1
            elif win_rate >= 48.0:
                g.add((champion_uri, MOBA.weakSynergyWith, partner_uri))
                stats["weakSynergyWith"] += 1
    
    return stats


# =============================================================================
# BUILD DATA MAPPING
# =============================================================================

def load_item_uris(items_file: str) -> dict:
    """Load item URIs from lol_items.ttl to match item names."""
    item_map = {}
    
    if os.path.exists(items_file):
        g = Graph()
        g.parse(items_file, format='turtle')
        
        # Get all items with their names
        for item_uri, _, item_name in g.triples((None, MOBA.itemName, None)):
            name_str = str(item_name)
            item_map[name_str.lower()] = item_uri
            item_map[sanitize_uri(name_str).lower()] = item_uri
        
        print(f"  Loaded {len(g)} triples from items file")
    else:
        print(f"  Warning: Items file not found at {items_file}")
    
    return item_map


def find_item_uri(item_name: str, item_map: dict) -> URIRef:
    """Find item URI from item map, or create one if not found."""
    name_lower = item_name.lower()
    
    # Try exact match
    if name_lower in item_map:
        return item_map[name_lower]
    
    # Try sanitized match
    sanitized = sanitize_uri(item_name).lower()
    if sanitized in item_map:
        return item_map[sanitized]
    
    # Create URI if not found
    return MOBA[sanitize_uri(item_name)]


def load_build_data(build_data_dir: str) -> dict:
    """Load all build data from build_data folder."""
    builds = {}
    
    for filename in os.listdir(build_data_dir):
        if filename.endswith('_build.json'):
            filepath = os.path.join(build_data_dir, filename)
            champion_name = filename.replace('_build.json', '')
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    builds[champion_name] = data
            except Exception as e:
                print(f"  Warning: Error loading {filename}: {e}")
    
    return builds


def add_build_relationships(g: Graph, builds: dict, existing_champions: set, item_map: dict) -> dict:
    """Add build relationships to the graph."""
    stats = {
        "coreItem": 0,
        "situationalItem": 0,
        "recommendedItem": 0
    }
    
    for champ_name, build_data in builds.items():
        champion_uri = find_champion_uri(champ_name, existing_champions, g)
        if not champion_uri:
            continue
        
        # Map core items
        for item_name in build_data.get('core_items', []):
            item_uri = find_item_uri(item_name, item_map)
            g.add((champion_uri, MOBA.coreItem, item_uri))
            stats["coreItem"] += 1
        
        # Map situational items (fourth, fifth, sixth options)
        situational_items = set()
        for key in ['fourth_item_options', 'fifth_item_options', 'sixth_item_options']:
            for item_name in build_data.get(key, []):
                if item_name not in situational_items:
                    item_uri = find_item_uri(item_name, item_map)
                    g.add((champion_uri, MOBA.situationalItem, item_uri))
                    situational_items.add(item_name)
                    stats["situationalItem"] += 1
        
        # Map full build as recommended items
        for item_name in build_data.get('full_build', []):
            item_uri = find_item_uri(item_name, item_map)
            g.add((champion_uri, MOBA.recommendedItem, item_uri))
            stats["recommendedItem"] += 1
    
    return stats


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def main():
    print("=" * 70)
    print("UNIFIED CHAMPION DATA MAPPING")
    print("=" * 70)
    
    # Verify input files exist
    if not os.path.exists(BASE_CHAMPIONS_FILE):
        print(f"Error: Base champions file not found at {BASE_CHAMPIONS_FILE}")
        return
    
    # Load base champions graph
    print("\n[1/4] Loading base champions graph...")
    g = Graph()
    g.parse(BASE_CHAMPIONS_FILE, format='turtle')
    initial_triples = len(g)
    print(f"  Loaded {initial_triples} triples")
    
    # Bind namespaces
    g.bind("moba", MOBA)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    
    # Get existing champion URIs
    existing_champions = get_existing_champions(g)
    print(f"  Found {len(existing_champions)} champions in the graph")
    
    # Load item URIs for build mapping
    print("\n  Loading item URIs...")
    item_map = load_item_uris(ITEMS_FILE)
    
    # ==========================================================================
    # PHASE 1: Counter Data
    # ==========================================================================
    print("\n[2/4] Mapping counter relationships...")
    if os.path.exists(COUNTER_DATA_DIR):
        counter_data = load_counter_data(COUNTER_DATA_DIR)
        print(f"  Loaded counter data for {len(counter_data)} champions")
        
        counter_stats = add_counter_relationships(g, counter_data, existing_champions)
        total_counter = sum(counter_stats.values())
        print(f"  Added {total_counter} counter relationships:")
        print(f"    - counters: {counter_stats['counters']}")
        print(f"    - hardCounters: {counter_stats['hardCounters']}")
        print(f"    - counteredBy: {counter_stats['counteredBy']}")
        print(f"    - hardCounteredBy: {counter_stats['hardCounteredBy']}")
    else:
        print(f"  Warning: Counter data directory not found at {COUNTER_DATA_DIR}")
        counter_stats = {"counters": 0, "hardCounters": 0, "counteredBy": 0, "hardCounteredBy": 0}
    
    # ==========================================================================
    # PHASE 2: Synergy Data
    # ==========================================================================
    print("\n[3/4] Mapping synergy relationships...")
    if os.path.exists(SYNERGY_DATA_DIR):
        synergy_data = load_synergy_data(SYNERGY_DATA_DIR)
        print(f"  Loaded synergy data for {len(synergy_data)} champions")
        
        synergy_stats = add_synergy_relationships(g, synergy_data, existing_champions)
        total_synergy = sum(synergy_stats.values())
        print(f"  Added {total_synergy} synergy relationships:")
        print(f"    - strongSynergyWith: {synergy_stats['strongSynergyWith']}")
        print(f"    - synergyWith: {synergy_stats['synergyWith']}")
        print(f"    - weakSynergyWith: {synergy_stats['weakSynergyWith']}")
    else:
        print(f"  Warning: Synergy data directory not found at {SYNERGY_DATA_DIR}")
        synergy_stats = {"strongSynergyWith": 0, "synergyWith": 0, "weakSynergyWith": 0}
    
    # ==========================================================================
    # PHASE 3: Build Data
    # ==========================================================================
    print("\n[4/4] Mapping build relationships...")
    if os.path.exists(BUILD_DATA_DIR):
        builds = load_build_data(BUILD_DATA_DIR)
        print(f"  Loaded build data for {len(builds)} champions")
        
        build_stats = add_build_relationships(g, builds, existing_champions, item_map)
        total_build = sum(build_stats.values())
        print(f"  Added {total_build} build relationships:")
        print(f"    - coreItem: {build_stats['coreItem']}")
        print(f"    - situationalItem: {build_stats['situationalItem']}")
        print(f"    - recommendedItem: {build_stats['recommendedItem']}")
    else:
        print(f"  Warning: Build data directory not found at {BUILD_DATA_DIR}")
        build_stats = {"coreItem": 0, "situationalItem": 0, "recommendedItem": 0}
    
    # ==========================================================================
    # Serialize output
    # ==========================================================================
    print("\n" + "=" * 70)
    print("SERIALIZING OUTPUT")
    print("=" * 70)
    
    g.serialize(destination=OUTPUT_FILE, format='turtle')
    final_triples = len(g)
    
    print(f"\nSuccessfully created: {OUTPUT_FILE}")
    print(f"\nSUMMARY:")
    print(f"  Initial triples: {initial_triples}")
    print(f"  Final triples:   {final_triples}")
    print(f"  Triples added:   {final_triples - initial_triples}")
    print(f"\n  Total relationships added:")
    print(f"    Counter:  {sum(counter_stats.values())}")
    print(f"    Synergy:  {sum(synergy_stats.values())}")
    print(f"    Build:    {sum(build_stats.values())}")
    
    # Print sample relationships
    print("\n" + "=" * 70)
    print("SAMPLE RELATIONSHIPS")
    print("=" * 70)
    
    sample_queries = [
        ("Counter", "counters"),
        ("Synergy", "strongSynergyWith"),
        ("Build", "coreItem")
    ]
    
    for label, predicate in sample_queries:
        print(f"\n{label} samples:")
        count = 0
        for s, p, o in g.triples((None, MOBA[predicate], None)):
            if count < 3:
                subj = str(s).split('#')[-1]
                obj = str(o).split('#')[-1]
                print(f"  {subj} {predicate} {obj}")
                count += 1


if __name__ == '__main__':
    main()

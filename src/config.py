import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4.1"

# Project root directory (one level up from src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data directories
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ONTOLOGY_DIR = os.path.join(DATA_DIR, "ontology")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# File paths - Ontology files
TTL_FILE_PATH = os.path.join(ONTOLOGY_DIR, "lol_champions_with_counters_synergy_builds.ttl")
ITEMS_TTL_FILE_PATH = os.path.join(ONTOLOGY_DIR, "lol_items.ttl")
MONSTERS_TTL_FILE_PATH = os.path.join(ONTOLOGY_DIR, "lol_monsters.ttl")
TURRETS_TTL_FILE_PATH = os.path.join(ONTOLOGY_DIR, "lol_turrets.ttl")
RDF_FILE_PATH = os.path.join(ONTOLOGY_DIR, "MobaGameOntology.rdf")
ENRICHMENT_TTL_PATH = os.path.join(ONTOLOGY_DIR, "lol_enrichment.ttl")

# File paths - JSON data
ENRICHMENT_DATA_PATH = os.path.join(DATA_DIR, "enrichment_data.json")
GAME_SNAPSHOTS_PATH = os.path.join(DATA_DIR, "game_snapshots.json")

# Namespace
MOBA_NAMESPACE = "http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#"

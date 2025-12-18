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
GRAPHS_DIR = os.path.join(DATA_DIR, "graphs")
GAME_DATA_DIR = os.path.join(DATA_DIR, "game_data")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# File paths - Graph files (TTL)
TTL_FILE_PATH = os.path.join(GRAPHS_DIR, "lol_champions_functional.ttl")
ITEMS_TTL_FILE_PATH = os.path.join(GRAPHS_DIR, "lol_items.ttl")
MONSTERS_TTL_FILE_PATH = os.path.join(GRAPHS_DIR, "lol_monsters.ttl")
TURRETS_TTL_FILE_PATH = os.path.join(GRAPHS_DIR, "lol_turrets.ttl")
ENRICHMENT_TTL_PATH = os.path.join(GRAPHS_DIR, "lol_enrichment.ttl")

# File paths - Ontology
RDF_FILE_PATH = os.path.join(ONTOLOGY_DIR, "MobaGameOntology.rdf")

# File paths - JSON data
ENRICHMENT_DATA_PATH = os.path.join(GAME_DATA_DIR, "enrichment_data.json")
GAME_SNAPSHOTS_PATH = os.path.join(GAME_DATA_DIR, "game_snapshots.json")

# Namespace
MOBA_NAMESPACE = "http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#"

#!/usr/bin/env python3
"""
Map League of Legends item data to MobaGameOntology instances.
This script reads items.json and creates RDF instances using rdflib.

Item Classification:
- ConsumableItem: One-time use items
- ComponentItem: No buildsFrom (base items)
- AdvancedItem: Has buildsFrom (built from components)
- Both ComponentItem + AdvancedItem: Has both buildsFrom AND buildsInto
"""

import json
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD
from urllib.parse import quote

# Define the ontology namespace
MOBA = Namespace("http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#")

# Mapping from JSON stat keys to ontology Stats properties
# Only maps properties that exist in the ontology (domain: Stats)
STAT_MAPPING = {
    # Direct mappings
    "abilityPower": ("flat", "hasAbilityPower"),
    "armor": ("flat", "hasArmor"),
    "armorPenetration": ("flat", "hasArmorPenetration"),
    "attackDamage": ("flat", "hasAttackDamage"),
    "attackSpeed": ("percent", "hasAttackSpeed"),
    "cooldownReduction": ("flat", "hasCooldownReduction"),
    "criticalStrikeChance": ("flat", "hasCriticalChance"),
    "criticalStrikeDamage": ("flat", "baseCriticalDamage"),
    "health": ("flat", "hasHealth"),
    "healthRegen": ("percent", "hasHealthRegen"),
    "lifesteal": ("flat", "hasLifeSteal"),
    "magicPenetration": ("flat", "hasMagicPenetration"),
    "magicResistance": ("flat", "hasMagicResist"),
    "mana": ("flat", "hasMana"),
    "manaRegen": ("percent", "hasManaRegen"),
    "movespeed": ("flat", "hasMovementSpeed"),
    "tenacity": ("percent", "hasTenacity"),
    # User-defined mappings
    "lethality": ("flat", "hasArmorPenetration"),  # Lethality is armor pen
    "abilityHaste": ("flat", "hasCooldownReduction"),  # Map to CDR
    "omnivamp": ("flat", "hasSpellVamp"),  # Map to spell vamp
    # Not mapped: goldPer10 (user said skip)
}

# Additional percent-based stats that need special handling
PERCENT_STATS = {
    "armorPenetration": "hasArmorPenetration",
    "magicPenetration": "hasMagicPenetration",
    "movespeed": "hasMovementSpeed",
    "healthRegen": "hasHealthRegen",
    "manaRegen": "hasManaRegen",
}


def sanitize_uri(name: str) -> str:
    """Create a valid URI component from a name."""
    sanitized = name.replace(" ", "_").replace("'", "").replace(".", "").replace(":", "").replace("/", "_")
    sanitized = sanitized.replace("(", "").replace(")", "").replace("-", "_")
    return quote(sanitized, safe="_")


def is_consumable(item_data: dict) -> bool:
    """Determine if item is a consumable based on rank or other indicators."""
    ranks = item_data.get("rank", [])
    name = item_data.get("name", "").lower()
    
    # Check rank for consumable indicator
    if "CONSUMABLE" in ranks:
        return True
    
    # Check common consumable items by name patterns
    consumable_keywords = ["potion", "elixir", "ward", "control ward", "stealth ward"]
    for keyword in consumable_keywords:
        if keyword in name:
            return True
    
    return False


def determine_item_types(item_data: dict) -> list:
    """
    Determine item type(s) based on buildsFrom/buildsInto.
    
    Rules:
    - ConsumableItem: One-time use items
    - ComponentItem: No buildsFrom (base items)
    - AdvancedItem: Has buildsFrom (built from components)
    - Both: Has both buildsFrom AND buildsInto
    """
    builds_from = item_data.get("buildsFrom", [])
    builds_into = item_data.get("buildsInto", [])
    
    # Check for consumable first
    if is_consumable(item_data):
        return ["ConsumableItem"]
    
    types = []
    
    # Has buildsFrom means it's built from components → AdvancedItem
    if builds_from:
        types.append("AdvancedItem")
    
    # No buildsFrom means it's a base item → ComponentItem
    # OR has buildsInto (can upgrade) → also ComponentItem
    if not builds_from or builds_into:
        if not builds_from:
            types.append("ComponentItem")
        elif builds_into:
            # Has both buildsFrom AND buildsInto → add ComponentItem too
            types.append("ComponentItem")
    
    # Default to Item if no specific type
    if not types:
        types.append("Item")
    
    return types


def create_item_instances(items_file: str, output_file: str):
    """
    Read items.json and create RDF instances mapped to the ontology.
    """
    g = Graph()
    
    # Bind namespaces
    g.bind("moba", MOBA)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    
    # Load item data
    with open(items_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    print(f"Loaded {len(items)} items from {items_file}")
    
    # Build item ID to name mapping for relationship creation
    item_id_to_uri = {}
    
    # First pass: create all item URIs
    for item_id, item_data in items.items():
        # Skip removed items
        if item_data.get("removed", False):
            continue
            
        item_name = item_data.get("name", f"Item_{item_id}")
        item_uri_name = sanitize_uri(item_name)
        item_uri = MOBA[item_uri_name]
        item_id_to_uri[int(item_id)] = item_uri
    
    # Second pass: create item instances with all properties
    stats_count = 0
    relationship_count = 0
    
    for item_id, item_data in items.items():
        # Skip removed items
        if item_data.get("removed", False):
            continue
        
        item_name = item_data.get("name", f"Item_{item_id}")
        item_uri_name = sanitize_uri(item_name)
        item_uri = MOBA[item_uri_name]
        
        # Determine item types
        item_types = determine_item_types(item_data)
        
        # Add item type(s)
        for item_type in item_types:
            g.add((item_uri, RDF.type, MOBA[item_type]))
        
        # Add itemName property (use item name from JSON)
        g.add((item_uri, MOBA.itemName, Literal(item_name, datatype=XSD.string)))
        
        # Add rdfs:label for readability
        g.add((item_uri, RDFS.label, Literal(item_name, lang="en")))
        
        # Add simple description as comment if available
        simple_desc = item_data.get("simpleDescription", "")
        if simple_desc:
            g.add((item_uri, RDFS.comment, Literal(simple_desc, lang="en")))
        
        # Add gold cost
        shop = item_data.get("shop", {})
        prices = shop.get("prices", {})
        total_cost = prices.get("total", 0)
        if total_cost > 0:
            g.add((item_uri, MOBA.goldCost, Literal(int(total_cost), datatype=XSD.integer)))
        
        # Create Stats instance and link via providesStats
        stats = item_data.get("stats", {})
        if stats:
            has_stats = False
            stats_uri = MOBA[f"{item_uri_name}_Stats"]
            
            for stat_key, stat_values in stats.items():
                if not isinstance(stat_values, dict):
                    continue
                
                # Check direct mapping
                if stat_key in STAT_MAPPING:
                    value_type, prop_name = STAT_MAPPING[stat_key]
                    value = stat_values.get(value_type, 0)
                    if value and value != 0:
                        if not has_stats:
                            g.add((stats_uri, RDF.type, MOBA.Stats))
                            g.add((item_uri, MOBA.providesStats, stats_uri))
                            has_stats = True
                        g.add((stats_uri, MOBA[prop_name], Literal(float(value), datatype=XSD.float)))
                        stats_count += 1
                
                # Check percent stats as fallback
                if stat_key in PERCENT_STATS:
                    percent_value = stat_values.get("percent", 0)
                    if percent_value and percent_value != 0:
                        prop_name = PERCENT_STATS[stat_key]
                        if not has_stats:
                            g.add((stats_uri, RDF.type, MOBA.Stats))
                            g.add((item_uri, MOBA.providesStats, stats_uri))
                            has_stats = True
                        # Only add if not already added via flat
                        existing = list(g.triples((stats_uri, MOBA[prop_name], None)))
                        if not existing:
                            g.add((stats_uri, MOBA[prop_name], Literal(float(percent_value), datatype=XSD.float)))
                            stats_count += 1
            
            # Handle healAndShieldPower specially (map to both effects if present)
            heal_shield = stats.get("healAndShieldPower", {})
            flat_hs = heal_shield.get("flat", 0)
            if flat_hs and flat_hs != 0:
                # Add as both health regen boost indicator
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((item_uri, MOBA.providesStats, stats_uri))
                    has_stats = True
                # Note: No direct property, but we can add as hasHealthRegen boost
                # The ontology doesn't have healAndShieldPower, so we skip per user request
        
        # Add buildsInto relationships (upgradesInto in ontology)
        builds_into = item_data.get("buildsInto", [])
        for target_id in builds_into:
            target_uri = item_id_to_uri.get(target_id)
            if target_uri:
                g.add((item_uri, MOBA.upgradesInto, target_uri))
                relationship_count += 1
        
        # Add buildsFrom relationships (buildPath in ontology)
        builds_from = item_data.get("buildsFrom", [])
        for source_id in builds_from:
            source_uri = item_id_to_uri.get(source_id)
            if source_uri:
                g.add((item_uri, MOBA.buildPath, source_uri))
                relationship_count += 1
        
        # Add effect mappings from passives and actives
        passives = item_data.get("passives", [])
        actives = item_data.get("active", [])
        
        # Track if item has unique passive
        has_unique_passive = False
        
        for passive in passives:
            effects_text = passive.get("effects", "").lower()
            
            # Check if unique passive
            if passive.get("unique", False):
                has_unique_passive = True
            
            # Map effect types based on keywords in effect description
            if "damage" in effects_text:
                g.add((item_uri, MOBA.hasEffectType, MOBA.DamageEffect))
            if "heal" in effects_text:
                g.add((item_uri, MOBA.hasEffectType, MOBA.HealingEffect))
            if "mana" in effects_text and "restore" in effects_text:
                g.add((item_uri, MOBA.hasEffectType, MOBA.ManaRestore))
            if "speed" in effects_text or "dash" in effects_text:
                g.add((item_uri, MOBA.hasEffectType, MOBA.MobilityEffect))
            if "shield" in effects_text:
                g.add((item_uri, MOBA.hasEffectType, MOBA.Shield))
            if "slow" in effects_text:
                g.add((item_uri, MOBA.hasEffectType, MOBA.Slow))
            if "buff" in effects_text or "bonus" in effects_text:
                g.add((item_uri, MOBA.grantsStatusEffect, MOBA.Buff))
        
        # Add unique passive property
        if has_unique_passive:
            g.add((item_uri, MOBA.uniquePassive, Literal(True, datatype=XSD.boolean)))
        
        # Add active effect activation marker
        if actives:
            g.add((item_uri, MOBA.hasEffectActivation, MOBA.ActiveEffect))
    
    # Serialize to Turtle format
    g.serialize(destination=output_file, format="turtle")
    print(f"Successfully created {output_file}")
    print(f"Total triples: {len(g)}")
    print(f"Stats mapped: {stats_count}")
    print(f"Build relationships: {relationship_count}")
    
    return g


def main():
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))  # ssw_chatbot/
    
    # Input: items.json is in data/game_data
    items_file = os.path.join(project_root, "data", "game_data", "items.json")
    # Output: TTL file goes to data/graphs
    output_file = os.path.join(project_root, "data", "graphs", "lol_items.ttl")
    
    if not os.path.exists(items_file):
        print(f"Error: Items file not found at {items_file}")
        return
    
    graph = create_item_instances(items_file, output_file)
    
    # Print sample output
    print("\nSample output (first 5 items with stats):")
    print("-" * 60)
    
    query = """
    PREFIX moba: <http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?item ?name ?cost ?type WHERE {
        ?item moba:itemName ?name .
        ?item rdf:type ?type .
        OPTIONAL { ?item moba:goldCost ?cost }
    }
    LIMIT 5
    """
    
    for row in graph.query(query):
        type_name = str(row.type).split("#")[-1]
        cost = row.cost if row.cost else "N/A"
        print(f"  {row.name}: {type_name} (Cost: {cost})")


if __name__ == "__main__":
    main()

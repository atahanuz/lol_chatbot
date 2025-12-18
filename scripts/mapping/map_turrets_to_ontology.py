#!/usr/bin/env python3
"""
Map League of Legends turret data to MobaGameOntology instances.
This script reads lol_turrets.json and creates RDF instances using rdflib.

Turret Classification:
- Tower: All turrets (subclass of Objective)

Ontology Properties Used:
- objectiveHealth (Objective -> float) - Turret health
- attackRange (domain unspecified -> integer) - Attack range
- Stats instance with hasArmor, hasMagicResist, hasAttackDamage, hasAttackSpeed
"""

import json
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD
from urllib.parse import quote

# Define the ontology namespace
MOBA = Namespace("http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#")


def sanitize_uri(name: str) -> str:
    """Create a valid URI component from a name."""
    sanitized = name.replace(" ", "_").replace("'", "").replace(".", "").replace(":", "").replace("/", "_")
    sanitized = sanitized.replace("(", "").replace(")", "").replace("-", "_")
    return quote(sanitized, safe="_")


def get_base_value(value):
    """
    Extract base value from various formats:
    - Simple number: 5000 -> 5000
    - Dict with base: {"base": 182, "max": 350} -> 182
    - Dict with min: {"min": 425, "max": 675} -> 425
    """
    if isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, dict):
        if "base" in value:
            return float(value["base"])
        elif "min" in value:
            return float(value["min"])
        elif "global" in value:
            return float(value["global"])
    return 0.0


def create_turret_instances(turrets_file: str, output_file: str):
    """
    Read lol_turrets.json and create RDF instances mapped to the ontology.
    """
    g = Graph()
    
    # Bind namespaces
    g.bind("moba", MOBA)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    
    # Load turret data
    with open(turrets_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    turrets = data.get("turrets", {}).get("summoners_rift", {})
    
    print(f"Loaded {len(turrets)} turret types from {turrets_file}")
    
    stats_count = 0
    
    # Map turret type names to readable labels
    turret_labels = {
        "outer_turret": "Outer Turret",
        "inner_turret": "Inner Turret",
        "inhibitor_turret": "Inhibitor Turret",
        "nexus_turret": "Nexus Turret"
    }
    
    for turret_type, turret_data in turrets.items():
        turret_name = turret_labels.get(turret_type, turret_type.replace("_", " ").title())
        turret_uri_name = sanitize_uri(turret_name)
        turret_uri = MOBA[turret_uri_name]
        
        # All turrets are Tower type (subclass of Objective)
        g.add((turret_uri, RDF.type, MOBA.Tower))
        
        # Add rdfs:label for readability
        g.add((turret_uri, RDFS.label, Literal(turret_name, lang="en")))
        
        # Health - use objectiveHealth (Objective domain property)
        health = turret_data.get("health", 0)
        if health:
            health_value = get_base_value(health)
            if health_value > 0:
                g.add((turret_uri, MOBA.objectiveHealth, Literal(float(health_value), datatype=XSD.float)))
                stats_count += 1
        
        # Attack range - exists in ontology (attackRange)
        attack_range = turret_data.get("range", 0)
        if attack_range:
            g.add((turret_uri, MOBA.attackRange, Literal(int(attack_range), datatype=XSD.integer)))
            stats_count += 1
        
        # Create Stats instance for detailed stats
        stats_uri = MOBA[f"{turret_uri_name}_Stats"]
        has_stats = False
        
        # Attack damage -> Stats.hasAttackDamage
        attack_damage = turret_data.get("attack_damage", {})
        if attack_damage:
            ad_value = get_base_value(attack_damage)
            if ad_value > 0:
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((turret_uri, MOBA.hasBaseStats, stats_uri))
                    has_stats = True
                g.add((stats_uri, MOBA.hasAttackDamage, Literal(float(ad_value), datatype=XSD.float)))
                stats_count += 1
        
        # Attack speed -> Stats.hasAttackSpeed
        attack_speed = turret_data.get("attack_speed", 0)
        if attack_speed:
            as_value = get_base_value(attack_speed)
            if as_value > 0:
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((turret_uri, MOBA.hasBaseStats, stats_uri))
                    has_stats = True
                g.add((stats_uri, MOBA.hasAttackSpeed, Literal(float(as_value), datatype=XSD.float)))
                stats_count += 1
        
        # Armor -> Stats.hasArmor
        armor = turret_data.get("armor", 0)
        if armor:
            armor_value = get_base_value(armor)
            if armor_value > 0:
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((turret_uri, MOBA.hasBaseStats, stats_uri))
                    has_stats = True
                g.add((stats_uri, MOBA.hasArmor, Literal(float(armor_value), datatype=XSD.float)))
                stats_count += 1
        
        # Magic resistance -> Stats.hasMagicResist
        magic_resist = turret_data.get("magic_resistance", 0)
        if magic_resist:
            mr_value = get_base_value(magic_resist)
            if mr_value > 0:
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((turret_uri, MOBA.hasBaseStats, stats_uri))
                    has_stats = True
                g.add((stats_uri, MOBA.hasMagicResist, Literal(float(mr_value), datatype=XSD.float)))
                stats_count += 1
        
        # Add comments for additional data not in ontology
        comments = []
        
        # Gold bounty info
        gold_bounty = turret_data.get("gold_bounty", {})
        if gold_bounty:
            bounty_parts = []
            if "global" in gold_bounty:
                bounty_parts.append(f"Global: {gold_bounty['global']}")
            if "local" in gold_bounty:
                local = gold_bounty["local"]
                if isinstance(local, dict):
                    bounty_parts.append(f"Local: {local.get('min', 0)}-{local.get('max', 0)}")
                else:
                    bounty_parts.append(f"Local: {local}")
            if bounty_parts:
                comments.append(f"Gold bounty - {', '.join(bounty_parts)}")
        
        # Plates info (for outer turret)
        plates = turret_data.get("plates", {})
        if plates:
            plate_info = f"Plates: {plates.get('count', 0)} plates, {plates.get('health_per_plate', 0)} HP each, {plates.get('gold_per_plate', 0)} gold each"
            comments.append(plate_info)
        
        # Regeneration info
        regen = turret_data.get("regeneration", {})
        if regen:
            regen_info = f"Regeneration: {regen.get('hp_per_second', 0)} HP/s"
            if regen.get("condition"):
                regen_info += f" ({regen['condition']})"
            comments.append(regen_info)
        
        # Respawn time
        respawn = turret_data.get("respawn_time_seconds", 0)
        if respawn:
            comments.append(f"Respawn time: {respawn} seconds")
        
        # Add all comments
        for comment in comments:
            g.add((turret_uri, RDFS.comment, Literal(comment, lang="en")))
    
    # Serialize to Turtle format
    g.serialize(destination=output_file, format="turtle")
    print(f"Successfully created {output_file}")
    print(f"Total triples: {len(g)}")
    print(f"Stats mapped: {stats_count}")
    
    return g


def main():
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))  # ssw_chatbot/
    
    # Input: turrets.json is in data/game_data
    turrets_file = os.path.join(project_root, "data", "game_data", "turrets.json")
    # Output: TTL file goes to data/graphs
    output_file = os.path.join(project_root, "data", "graphs", "lol_turrets.ttl")
    
    if not os.path.exists(turrets_file):
        print(f"Error: Turrets file not found at {turrets_file}")
        return
    
    graph = create_turret_instances(turrets_file, output_file)
    
    # Print sample output
    print("\nSample output (turrets):")
    print("-" * 60)
    
    query = """
    PREFIX moba: <http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?turret ?name ?health ?range WHERE {
        ?turret rdfs:label ?name .
        ?turret rdf:type moba:Tower .
        OPTIONAL { ?turret moba:objectiveHealth ?health }
        OPTIONAL { ?turret moba:attackRange ?range }
    }
    ORDER BY DESC(?health)
    """
    
    for row in graph.query(query):
        health = int(float(str(row.health))) if row.health else "N/A"
        attack_range = int(row.range) if row.range else "N/A"
        print(f"  {row.name}: Health {health}, Range {attack_range}")


if __name__ == "__main__":
    main()

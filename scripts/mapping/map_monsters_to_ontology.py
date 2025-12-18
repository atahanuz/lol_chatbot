#!/usr/bin/env python3
"""
Map League of Legends monster data to MobaGameOntology instances.
This script reads monster_stats.json and creates RDF instances using rdflib.

Monster Classification:
- Boss: Epic monsters (Baron, Dragon, Herald)
- NeutralMonster: All jungle monsters

Ontology Properties Used:
- objectiveHealth (Objective -> float) - Monster health
- attackRange (domain unspecified -> integer) - Attack range
- Stats instance with hasArmor, hasMagicResist, hasAttackDamage, etc.
"""

import json
import re
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD
from urllib.parse import quote

# Define the ontology namespace
MOBA = Namespace("http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#")


def sanitize_uri(name: str) -> str:
    """Create a valid URI component from a name."""
    sanitized = name.replace(" ", "_").replace("'", "").replace(".", "").replace(":", "").replace("/", "_")
    sanitized = sanitized.replace("(", "").replace(")", "").replace("-", "_")
    return quote(sanitized, safe="_")


def parse_base_value(value_str: str) -> float:
    """
    Extract the base numeric value from a stat string.
    Handles formats like:
    - "11800 (+ 190 per minute from match start)"
    - "5730 – 10290 (based on level)"
    - "0.625"
    - "300"
    """
    if not value_str:
        return 0.0
    
    cleaned = value_str.strip()
    match = re.search(r'^[\d,]+\.?\d*', cleaned.replace(',', ''))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return 0.0
    return 0.0


def is_epic_monster(monster_data: dict) -> bool:
    """Determine if monster is an Epic monster (Boss)."""
    monster_type = monster_data.get("statistics", {}).get("monster type", "").lower()
    name = monster_data.get("name", "").lower()
    
    if "epic" in monster_type:
        return True
    
    epic_keywords = ["baron", "dragon", "drake", "herald", "elder"]
    for keyword in epic_keywords:
        if keyword in name:
            return True
    
    return False


def create_monster_instances(monsters_file: str, output_file: str):
    """
    Read monster_stats.json and create RDF instances mapped to the ontology.
    """
    g = Graph()
    
    # Bind namespaces
    g.bind("moba", MOBA)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    
    # Load monster data
    with open(monsters_file, "r", encoding="utf-8") as f:
        monsters = json.load(f)
    
    print(f"Loaded {len(monsters)} monsters from {monsters_file}")
    
    stats_count = 0
    
    for monster_data in monsters:
        monster_name = monster_data.get("name", "Unknown Monster")
        monster_uri_name = sanitize_uri(monster_name)
        monster_uri = MOBA[monster_uri_name]
        
        # Determine monster type (Boss or NeutralMonster)
        if is_epic_monster(monster_data):
            g.add((monster_uri, RDF.type, MOBA.Boss))
        else:
            g.add((monster_uri, RDF.type, MOBA.NeutralMonster))
        
        # Add rdfs:label for readability
        g.add((monster_uri, RDFS.label, Literal(monster_name, lang="en")))
        
        # Map statistics 
        statistics = monster_data.get("statistics", {})
        
        # Health - use objectiveHealth (Objective domain property)
        health = statistics.get("health", "")
        if health:
            health_value = parse_base_value(health)
            if health_value > 0:
                g.add((monster_uri, MOBA.objectiveHealth, Literal(float(health_value), datatype=XSD.float)))
                stats_count += 1
        
        # Attack range - exists in ontology (attackRange)
        attack_range = statistics.get("attack range", "")
        if attack_range:
            ar_value = parse_base_value(attack_range)
            if ar_value > 0:
                g.add((monster_uri, MOBA.attackRange, Literal(int(ar_value), datatype=XSD.integer)))
                stats_count += 1
        
        # Create Stats instance for detailed stats (following item pattern)
        # These properties have domain: Stats
        stats_uri = MOBA[f"{monster_uri_name}_Stats"]
        has_stats = False
        
        # Attack damage -> Stats.hasAttackDamage
        attack_damage = statistics.get("attack damage", "")
        if attack_damage:
            ad_value = parse_base_value(attack_damage)
            if ad_value > 0:
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((monster_uri, MOBA.hasBaseStats, stats_uri))
                    has_stats = True
                g.add((stats_uri, MOBA.hasAttackDamage, Literal(float(ad_value), datatype=XSD.float)))
                stats_count += 1
        
        # Attack speed -> Stats.hasAttackSpeed
        attack_speed = statistics.get("attack speed", "")
        if attack_speed:
            as_value = parse_base_value(attack_speed)
            if as_value > 0:
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((monster_uri, MOBA.hasBaseStats, stats_uri))
                    has_stats = True
                g.add((stats_uri, MOBA.hasAttackSpeed, Literal(float(as_value), datatype=XSD.float)))
                stats_count += 1
        
        # Armor -> Stats.hasArmor
        armor = statistics.get("armor", "")
        if armor:
            armor_value = parse_base_value(armor)
            if armor_value > 0:
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((monster_uri, MOBA.hasBaseStats, stats_uri))
                    has_stats = True
                g.add((stats_uri, MOBA.hasArmor, Literal(float(armor_value), datatype=XSD.float)))
                stats_count += 1
        
        # Magic resist -> Stats.hasMagicResist
        magic_resist = statistics.get("magic resist", "")
        if magic_resist:
            mr_value = parse_base_value(magic_resist)
            if mr_value > 0:
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((monster_uri, MOBA.hasBaseStats, stats_uri))
                    has_stats = True
                g.add((stats_uri, MOBA.hasMagicResist, Literal(float(mr_value), datatype=XSD.float)))
                stats_count += 1
        
        # Movement speed -> Stats.hasMovementSpeed
        move_speed = statistics.get("move speed", "")
        if move_speed:
            ms_value = parse_base_value(move_speed)
            if ms_value > 0:
                if not has_stats:
                    g.add((stats_uri, RDF.type, MOBA.Stats))
                    g.add((monster_uri, MOBA.hasBaseStats, stats_uri))
                    has_stats = True
                g.add((stats_uri, MOBA.hasMovementSpeed, Literal(float(ms_value), datatype=XSD.float)))
                stats_count += 1
        
        # Monster type description as comment
        monster_type = statistics.get("monster type", "")
        if monster_type:
            g.add((monster_uri, RDFS.comment, Literal(f"Monster type: {monster_type}", lang="en")))
        
        # Map bounty data as comments (no ontology properties exist for these)
        bounty = monster_data.get("bounty", {})
        bounty_parts = []
        if bounty.get("gold"):
            bounty_parts.append(f"Gold: {bounty['gold']}")
        if bounty.get("exp"):
            bounty_parts.append(f"Exp: {bounty['exp']}")
        if bounty.get("cs"):
            bounty_parts.append(f"CS: {bounty['cs']}")
        if bounty_parts:
            g.add((monster_uri, RDFS.comment, Literal(f"Bounty - {', '.join(bounty_parts)}", lang="en")))
        
        # Map location data as comments (no ontology properties exist)
        location = monster_data.get("location", {})
        loc_parts = []
        if location.get("camp"):
            loc_parts.append(f"Camp: {location['camp']}")
        if location.get("initial"):
            loc_parts.append(f"Initial spawn: {location['initial']}")
        if location.get("respawn"):
            loc_parts.append(f"Respawn: {location['respawn']}")
        if loc_parts:
            g.add((monster_uri, RDFS.comment, Literal(f"Location - {', '.join(loc_parts)}", lang="en")))
    
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
    
    # Input: monsters.json is in data/game_data
    monsters_file = os.path.join(project_root, "data", "game_data", "monsters.json")
    # Output: TTL file goes to data/graphs
    output_file = os.path.join(project_root, "data", "graphs", "lol_monsters.ttl")
    
    if not os.path.exists(monsters_file):
        print(f"Error: Monsters file not found at {monsters_file}")
        return
    
    graph = create_monster_instances(monsters_file, output_file)
    
    # Print sample output
    print("\nSample output (monsters by type):")
    print("-" * 60)
    
    query = """
    PREFIX moba: <http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?monster ?name ?type ?health WHERE {
        ?monster rdfs:label ?name .
        ?monster rdf:type ?type .
        OPTIONAL { ?monster moba:objectiveHealth ?health }
    }
    ORDER BY DESC(?health)
    LIMIT 10
    """
    
    for row in graph.query(query):
        type_name = str(row.type).split("#")[-1]
        health = int(float(str(row.health))) if row.health else "N/A"
        print(f"  {row.name}: {type_name} (Health: {health})")


if __name__ == "__main__":
    main()

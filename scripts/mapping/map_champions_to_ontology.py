#!/usr/bin/env python3
"""
Map League of Legends champion data to MobaGameOntology instances.
This script reads champions.json and creates RDF instances using rdflib.

Updated to create individual SkillLevel instances per level (1-5) with float values
for cooldown, cost, and damage - enabling SPARQL calculations on the graph.
"""

import json
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD
from urllib.parse import quote

# Define the ontology namespace
MOBA = Namespace("http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#")

# Mapping from JSON roles to ontology Role classes
ROLE_MAPPING = {
    "FIGHTER": "WarriorRole",
    "TANK": "TankRole",
    "MAGE": "MageRole",
    "ASSASSIN": "AssassinRole",
    "MARKSMAN": "CarryRole",
    "SUPPORT": "SupportRole",
    "JUGGERNAUT": "WarriorRole",
    "SLAYER": "AssassinRole",
    "SPECIALIST": "MageRole",
    "CONTROLLER": "SupportRole",
    "SKIRMISHER": "WarriorRole",
    "DIVER": "WarriorRole",
    "BURST": "AssassinRole",
    "BATTLEMAGE": "MageRole",
    "ARTILLERY": "MageRole",
    "CATCHER": "SupportRole",
    "ENCHANTER": "SupportRole",
    "VANGUARD": "TankRole",
    "WARDEN": "TankRole",
}

# Mapping from JSON positions to ontology Lane instances
LANE_MAPPING = {
    "TOP": "TopLane",
    "JUNGLE": "Jungle",
    "MIDDLE": "MidLane",
    "MID": "MidLane",
    "BOTTOM": "BottomLane",
    "BOT": "BottomLane",
    "SUPPORT": "BottomLane",
    "UTILITY": "BottomLane",
}

# Mapping from JSON damage types to ontology DamageType classes
DAMAGE_TYPE_MAPPING = {
    "PHYSICAL_DAMAGE": "PhysicalDamage",
    "MAGIC_DAMAGE": "MagicalDamage",
    "MIXED_DAMAGE": "MixedDamage",
    "TRUE_DAMAGE": "TrueDamage",
}

# Mapping from JSON attack types to ontology AttackType instances
ATTACK_TYPE_MAPPING = {
    "MELEE": "Melee",
    "RANGED": "Ranged",
}

# Mapping from JSON resource types to cost type strings
RESOURCE_MAPPING = {
    "MANA": "Mana",
    "ENERGY": "Energy",
    "HEALTH": "Health",
    "BLOOD_WELL": "BloodWell",
    "FURY": "Fury",
    "RAGE": "Rage",
    "FLOW": "Flow",
    "FEROCITY": "Ferocity",
    "HEAT": "Heat",
    "GRIT": "Grit",
    "COURAGE": "Courage",
    "SHIELD": "Shield",
    "NONE": "None",
}

# Mapping from JSON stat keys to ontology BaseStats properties (flat values)
# Only includes properties that exist in the ontology (domain: Stats/BaseStats)
BASE_STAT_MAPPING = {
    "health": "baseHealth",
    "healthRegen": "hasHealthRegen",  # Ontology uses hasHealthRegen, not baseHealthRegen
    "mana": "baseMana",
    "manaRegen": "hasManaRegen",  # Ontology uses hasManaRegen, not baseManaRegen
    "armor": "baseArmor",
    "magicResistance": "baseMagicResist",
    "attackDamage": "baseAttackDamage",
    "movespeed": "baseMovementSpeed",
    "attackSpeed": "baseAttackSpeed",
    "attackRange": "attackRange",
    "criticalStrikeDamage": "baseCriticalDamage",
    # Note: These JSON keys are intentionally NOT mapped (no ontology properties exist):
    # acquisitionRadius, selectionRadius, pathingRadius, gameplayRadius,
    # criticalStrikeDamageModifier, attackSpeedRatio, attackCastTime, attackTotalTime, attackDelayOffset
}

# Mapping from JSON stat keys to ontology StatGrowth properties (perLevel values)
# Only includes properties that exist in the ontology (domain: StatGrowth)
STAT_GROWTH_MAPPING = {
    "health": "healthPerLevel",
    "mana": "manaPerLevel",
    "armor": "armorPerLevel",
    "attackDamage": "attackDamagePerLevel",
    # Note: These JSON perLevel keys are intentionally NOT mapped (no ontology properties exist):
    # healthRegen, manaRegen, magicResistance, attackSpeed
}


def sanitize_uri(name: str) -> str:
    """Create a valid URI component from a name."""
    sanitized = name.replace(" ", "_").replace("'", "").replace(".", "").replace(":", "").replace("/", "_")
    return quote(sanitized, safe="_")


def create_champion_instances(champions_file: str, output_file: str):
    """
    Read champions.json and create RDF instances mapped to the ontology.
    Creates SkillLevel instances per level with float values for calculations.
    """
    g = Graph()
    
    # Bind namespaces
    g.bind("moba", MOBA)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    
    # Load champion data
    with open(champions_file, "r", encoding="utf-8") as f:
        champions = json.load(f)
    
    print(f"Loaded {len(champions)} champions from {champions_file}")
    
    for champion_key, champion_data in champions.items():
        champion_name = champion_data.get("name", champion_key)
        champion_uri_name = sanitize_uri(champion_name)
        champion_uri = MOBA[champion_uri_name]
        
        # Determine the hero subclass based on roles
        roles = champion_data.get("roles", [])
        hero_class = determine_hero_class(roles)
        
        # Add champion as instance of Hero (or subclass)
        g.add((champion_uri, RDF.type, MOBA[hero_class]))
        
        # Add heroName property
        g.add((champion_uri, MOBA.heroName, Literal(champion_name, datatype=XSD.string)))
        
        # Add rdfs:label for readability
        g.add((champion_uri, RDFS.label, Literal(champion_name, lang="en")))
        
        # Add title as comment
        title = champion_data.get("title", "")
        if title:
            g.add((champion_uri, RDFS.comment, Literal(title, lang="en")))
        
        # Add attack type (hasAttackType)
        attack_type = champion_data.get("attackType", "")
        if attack_type and attack_type in ATTACK_TYPE_MAPPING:
            attack_type_uri = MOBA[ATTACK_TYPE_MAPPING[attack_type]]
            g.add((champion_uri, MOBA.hasAttackType, attack_type_uri))
        
        # Add isRanged property
        is_ranged = attack_type == "RANGED"
        g.add((champion_uri, MOBA.isRanged, Literal(is_ranged, datatype=XSD.boolean)))
        
        # Add damage type (dealsDamageType)
        adaptive_type = champion_data.get("adaptiveType", "")
        if adaptive_type and adaptive_type in DAMAGE_TYPE_MAPPING:
            damage_type_uri = MOBA[DAMAGE_TYPE_MAPPING[adaptive_type]]
            g.add((champion_uri, MOBA.dealsDamageType, damage_type_uri))
        
        # Add roles (playsRole)
        for role in roles:
            if role in ROLE_MAPPING:
                role_uri = MOBA[ROLE_MAPPING[role]]
                g.add((champion_uri, MOBA.playsRole, role_uri))
        
        # Add positions as typical lanes (typicalLane)
        positions = champion_data.get("positions", [])
        for position in positions:
            if position in LANE_MAPPING:
                lane_uri = MOBA[LANE_MAPPING[position]]
                g.add((champion_uri, MOBA.typicalLane, lane_uri))
        
        # Note: resource type (MANA, ENERGY, etc.) is not mapped as resourceType property
        # does not exist in the ontology

        # Create and link BaseStats - only map keys that exist in the ontology
        stats = champion_data.get("stats", {})
        if stats:
            stats_uri = MOBA[f"{champion_uri_name}_BaseStats"]
            g.add((stats_uri, RDF.type, MOBA.BaseStats))
            g.add((champion_uri, MOBA.hasBaseStats, stats_uri))

            # Map only stat keys that have corresponding ontology properties
            for stat_key, stat_values in stats.items():
                if isinstance(stat_values, dict) and "flat" in stat_values:
                    flat_value = stat_values["flat"]
                    # Only add if the key is mapped to an ontology property
                    if stat_key in BASE_STAT_MAPPING and flat_value is not None and flat_value != 0:
                        prop_name = BASE_STAT_MAPPING[stat_key]
                        g.add((stats_uri, MOBA[prop_name], Literal(float(flat_value), datatype=XSD.float)))
        
        # Create and link StatGrowth - only map keys that exist in the ontology
        if stats:
            growth_uri = MOBA[f"{champion_uri_name}_StatGrowth"]
            g.add((growth_uri, RDF.type, MOBA.StatGrowth))
            g.add((champion_uri, MOBA.hasStatGrowth, growth_uri))

            # Map only stat keys that have corresponding ontology properties
            for stat_key, stat_values in stats.items():
                if isinstance(stat_values, dict) and "perLevel" in stat_values:
                    per_level_value = stat_values["perLevel"]
                    # Only add if the key is mapped to an ontology property
                    if stat_key in STAT_GROWTH_MAPPING and per_level_value is not None and per_level_value != 0:
                        prop_name = STAT_GROWTH_MAPPING[stat_key]
                        g.add((growth_uri, MOBA[prop_name], Literal(float(per_level_value), datatype=XSD.float)))
        
        # Add attribute ratings
        attr_ratings = champion_data.get("attributeRatings", {})
        if attr_ratings:
            difficulty = attr_ratings.get("difficulty", 0)
            if difficulty:
                complexity_levels = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}
                complexity_uri = MOBA[complexity_levels.get(difficulty, "Intermediate")]
                g.add((champion_uri, MOBA.hasComplexity, complexity_uri))
        
        # Add skills (abilities) with SkillLevel instances
        abilities = champion_data.get("abilities", {})
        for slot, ability_list in abilities.items():
            skill_uri = MOBA[f"{champion_uri_name}_{slot}"]
            
            if ability_list:
                ability = ability_list[0]
                ability_name = ability.get("name", f"{slot} Ability")
                
                # Determine skill type
                targeting = ability.get("targeting", "")
                if slot == "P" or targeting == "Passive":
                    g.add((skill_uri, RDF.type, MOBA.PassiveSkill))
                elif slot == "R":
                    g.add((skill_uri, RDF.type, MOBA.UltimateSkill))
                else:
                    g.add((skill_uri, RDF.type, MOBA.ActiveSkill))
                
                # Add skill name
                g.add((skill_uri, MOBA.skillName, Literal(ability_name, datatype=XSD.string)))
                g.add((skill_uri, RDFS.label, Literal(ability_name, lang="en")))
                
                # Link skill to champion
                g.add((champion_uri, MOBA.hasSkill, skill_uri))
                
                # Add damage type if specified
                damage_type = ability.get("damageType", "")
                if damage_type and damage_type in DAMAGE_TYPE_MAPPING:
                    g.add((skill_uri, MOBA.hasDamageType, MOBA[DAMAGE_TYPE_MAPPING[damage_type]]))
                
                # Add cost type (resource type for this skill)
                skill_resource = ability.get("resource")
                if skill_resource:
                    g.add((skill_uri, MOBA.costType, Literal(skill_resource, datatype=XSD.string)))
                
                # Add skill target (who the skill affects)
                affects = ability.get("affects")
                if affects:
                    g.add((skill_uri, MOBA.skillTarget, Literal(affects, datatype=XSD.string)))
                
                # Extract cooldown values and create SkillLevel instances
                cooldown = ability.get("cooldown")
                cooldown_values = []
                if cooldown and isinstance(cooldown, dict):
                    modifiers = cooldown.get("modifiers", [])
                    if modifiers and len(modifiers) > 0:
                        cooldown_values = modifiers[0].get("values", [])
                
                # Extract cost values
                cost = ability.get("cost")
                cost_values = []
                if cost and isinstance(cost, dict):
                    modifiers = cost.get("modifiers", [])
                    if modifiers and len(modifiers) > 0:
                        cost_values = modifiers[0].get("values", [])
                
                # Extract damage values from effects
                damage_values = []
                effects = ability.get("effects", [])
                for effect in effects:
                    leveling = effect.get("leveling", [])
                    for level_data in leveling:
                        attribute = level_data.get("attribute", "")
                        modifiers = level_data.get("modifiers", [])
                        if "Damage" in attribute and modifiers and not damage_values:
                            damage_values = modifiers[0].get("values", [])
                            break
                
                # Determine max level (usually 5 for regular skills, 3 for ultimates)
                max_level = 3 if slot == "R" else 5
                if cooldown_values:
                    max_level = min(len(cooldown_values), max_level)
                elif cost_values:
                    max_level = min(len(cost_values), max_level)
                elif damage_values:
                    max_level = min(len(damage_values), max_level)
                
                # Add maximum level to skill
                if max_level > 0 and slot != "P":  # Passives don't have levels
                    g.add((skill_uri, MOBA.maximumLevel, Literal(max_level, datatype=XSD.integer)))
                
                    # Create SkillLevel instances for each level
                    for level in range(1, max_level + 1):
                        skill_level_uri = MOBA[f"{champion_uri_name}_{slot}_Level{level}"]
                        g.add((skill_level_uri, RDF.type, MOBA.SkillLevel))
                        g.add((skill_level_uri, MOBA.skillLevelNumber, Literal(level, datatype=XSD.integer)))
                        g.add((skill_uri, MOBA.hasSkillLevel, skill_level_uri))
                        
                        # Add cooldown at this level
                        if cooldown_values and level <= len(cooldown_values):
                            cd_value = cooldown_values[level - 1]
                            if cd_value is not None:
                                g.add((skill_level_uri, MOBA.cooldownAtSkillLevel, 
                                      Literal(float(cd_value), datatype=XSD.float)))
                        
                        # Add cost at this level
                        if cost_values and level <= len(cost_values):
                            cost_value = cost_values[level - 1]
                            if cost_value is not None:
                                g.add((skill_level_uri, MOBA.manaCostAtSkillLevel, 
                                      Literal(float(cost_value), datatype=XSD.float)))
                        
                        # Add damage at this level
                        if damage_values and level <= len(damage_values):
                            dmg_value = damage_values[level - 1]
                            if dmg_value is not None:
                                g.add((skill_level_uri, MOBA.damageAtSkillLevel, 
                                      Literal(float(dmg_value), datatype=XSD.float)))
                
                # Add base cost (level 1 cost) directly to skill for quick access
                if cost_values and len(cost_values) > 0:
                    g.add((skill_uri, MOBA.baseCost, Literal(float(cost_values[0]), datatype=XSD.float)))
                
                # Add base cooldown (level 1 cooldown) directly to skill
                if cooldown_values and len(cooldown_values) > 0:
                    g.add((skill_uri, MOBA.cooldown, Literal(float(cooldown_values[0]), datatype=XSD.float)))
    
    # Serialize to Turtle format
    g.serialize(destination=output_file, format="turtle")
    print(f"Successfully created {output_file}")
    print(f"Total triples: {len(g)}")
    
    return g


def determine_hero_class(roles: list) -> str:
    """Determine the most appropriate Hero subclass based on roles."""
    if not roles:
        return "Hero"
    
    role_to_hero_class = {
        "ASSASSIN": "AssassinHero",
        "SLAYER": "AssassinHero",
        "MAGE": "MageHero",
        "MARKSMAN": "CarryHero",
        "FIGHTER": "WarriorHero",
        "JUGGERNAUT": "WarriorHero",
        "TANK": "TankHero",
        "SUPPORT": "SupportHero",
    }
    
    for role in roles:
        if role in role_to_hero_class:
            return role_to_hero_class[role]
    
    return "Hero"


def main():
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))  # ssw_chatbot/
    
    # Input: champions.json is in data/game_data
    champions_file = os.path.join(project_root, "data", "game_data", "champions.json")
    # Output: TTL file goes to data/graphs
    output_file = os.path.join(project_root, "data", "graphs", "lol_champions.ttl")
    
    if not os.path.exists(champions_file):
        print(f"Error: Champions file not found at {champions_file}")
        return
    
    graph = create_champion_instances(champions_file, output_file)
    
    
    print("\nSample output (Aatrox_Q with SkillLevels):")
    print("-" * 60)
    


if __name__ == "__main__":
    main()

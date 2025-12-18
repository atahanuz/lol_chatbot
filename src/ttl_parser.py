from rdflib import Graph, Namespace, RDF, RDFS
from typing import Dict, Any, List, Optional
import re

MOBA = Namespace("http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#")

# Hero type classes in the ontology
HERO_TYPES = [
    "AssassinHero", "MageHero", "WarriorHero", "CarryHero",
    "SupportHero", "TankHero", "MeleeHero", "RangedHero"
]


def normalize_name(name: str) -> str:
    """Normalize a champion name to a consistent key format."""
    return name.lower().strip().replace(" ", "_").replace("'", "").replace(".", "")


def extract_local_name(uri: str) -> str:
    """Extract the local name from a URI."""
    if "#" in str(uri):
        return str(uri).split("#")[-1]
    return str(uri).split("/")[-1]


def get_float_value(graph: Graph, subject, predicate) -> Optional[float]:
    """Get a float value from the graph."""
    value = graph.value(subject, predicate)
    if value is not None:
        try:
            return float(str(value))
        except ValueError:
            return None
    return None


def get_string_value(graph: Graph, subject, predicate) -> Optional[str]:
    """Get a string value from the graph."""
    value = graph.value(subject, predicate)
    if value is not None:
        return str(value)
    return None


def get_bool_value(graph: Graph, subject, predicate) -> Optional[bool]:
    """Get a boolean value from the graph."""
    value = graph.value(subject, predicate)
    if value is not None:
        return str(value).lower() == "true"
    return None


def extract_skill_key(skill_uri: str, champion_name: str) -> str:
    """Extract skill key (Q, W, E, R, P) from skill URI."""
    local_name = extract_local_name(skill_uri)
    # Format: ChampionName_Q, ChampionName_W, etc.
    suffix = local_name.replace(f"{champion_name}_", "")
    if suffix in ["Q", "W", "E", "R", "P"]:
        return suffix
    return suffix


def parse_skill_level(graph: Graph, level_uri) -> Dict[str, Any]:
    """Parse a skill level instance."""
    return {
        "level": int(get_float_value(graph, level_uri, MOBA.skillLevelNumber) or 0),
        "damage": get_float_value(graph, level_uri, MOBA.damageAtSkillLevel),
        "cooldown": get_float_value(graph, level_uri, MOBA.cooldownAtSkillLevel),
        "mana_cost": get_float_value(graph, level_uri, MOBA.manaCostAtSkillLevel),
        "cast_range": get_float_value(graph, level_uri, MOBA.castRangeAtSkillLevel),
        "duration": get_float_value(graph, level_uri, MOBA.durationAtSkillLevel),
    }


def parse_skill(graph: Graph, skill_uri, champion_name: str) -> Dict[str, Any]:
    """Parse a skill instance."""
    skill_key = extract_skill_key(str(skill_uri), champion_name)

    # Get skill type
    skill_types = []
    for skill_type in ["ActiveSkill", "PassiveSkill", "UltimateSkill", "ToggleSkill"]:
        if (skill_uri, RDF.type, MOBA[skill_type]) in graph:
            skill_types.append(skill_type)

    # Get damage type
    damage_type_uri = graph.value(skill_uri, MOBA.hasDamageType)
    damage_type = extract_local_name(str(damage_type_uri)) if damage_type_uri else None

    # Parse skill levels
    levels = {}
    for level_uri in graph.objects(skill_uri, MOBA.hasSkillLevel):
        level_data = parse_skill_level(graph, level_uri)
        if level_data["level"] > 0:
            levels[level_data["level"]] = level_data

    return {
        "key": skill_key,
        "name": get_string_value(graph, skill_uri, MOBA.skillName) or str(graph.value(skill_uri, RDFS.label) or skill_key),
        "types": skill_types,
        "damage_type": damage_type,
        "cost_type": get_string_value(graph, skill_uri, MOBA.costType),
        "base_cost": get_float_value(graph, skill_uri, MOBA.baseCost),
        "base_cooldown": get_float_value(graph, skill_uri, MOBA.cooldown),
        "max_level": int(get_float_value(graph, skill_uri, MOBA.maximumLevel) or 5),
        "target": get_string_value(graph, skill_uri, MOBA.skillTarget),
        "levels": levels,
    }


def parse_base_stats(graph: Graph, stats_uri) -> Dict[str, float]:
    """Parse base stats instance."""
    return {
        "health": get_float_value(graph, stats_uri, MOBA.baseHealth),
        "mana": get_float_value(graph, stats_uri, MOBA.baseMana),
        "armor": get_float_value(graph, stats_uri, MOBA.baseArmor),
        "magic_resist": get_float_value(graph, stats_uri, MOBA.baseMagicResist),
        "attack_damage": get_float_value(graph, stats_uri, MOBA.baseAttackDamage),
        "attack_speed": get_float_value(graph, stats_uri, MOBA.baseAttackSpeed),
        "attack_range": get_float_value(graph, stats_uri, MOBA.attackRange),
        "movement_speed": get_float_value(graph, stats_uri, MOBA.baseMovementSpeed),
        "health_regen": get_float_value(graph, stats_uri, MOBA.hasHealthRegen),
        "mana_regen": get_float_value(graph, stats_uri, MOBA.hasManaRegen),
        "critical_damage": get_float_value(graph, stats_uri, MOBA.baseCriticalDamage),
    }


def parse_stat_growth(graph: Graph, growth_uri) -> Dict[str, float]:
    """Parse stat growth instance."""
    return {
        "health_per_level": get_float_value(graph, growth_uri, MOBA.healthPerLevel),
        "mana_per_level": get_float_value(graph, growth_uri, MOBA.manaPerLevel),
        "armor_per_level": get_float_value(graph, growth_uri, MOBA.armorPerLevel),
        "attack_damage_per_level": get_float_value(graph, growth_uri, MOBA.attackDamagePerLevel),
    }


def get_uri_list(graph: Graph, subject, predicate) -> List[str]:
    """Get a list of local names from URI objects."""
    results = []
    for obj in graph.objects(subject, predicate):
        results.append(extract_local_name(str(obj)))
    return results


def parse_champion(graph: Graph, hero_uri) -> Dict[str, Any]:
    """Parse a champion/hero instance."""
    # Get champion name
    hero_name = get_string_value(graph, hero_uri, MOBA.heroName)
    if not hero_name:
        hero_name = str(graph.value(hero_uri, RDFS.label) or extract_local_name(str(hero_uri)))

    local_name = extract_local_name(str(hero_uri))

    # Get hero type
    hero_type = None
    for ht in HERO_TYPES:
        if (hero_uri, RDF.type, MOBA[ht]) in graph:
            hero_type = ht
            break

    # Get damage type
    damage_type_uri = graph.value(hero_uri, MOBA.dealsDamageType)
    damage_type = extract_local_name(str(damage_type_uri)) if damage_type_uri else None

    # Get attack type
    attack_type_uri = graph.value(hero_uri, MOBA.hasAttackType)
    attack_type = extract_local_name(str(attack_type_uri)) if attack_type_uri else None

    # Get complexity
    complexity_uri = graph.value(hero_uri, MOBA.hasComplexity)
    complexity = extract_local_name(str(complexity_uri)) if complexity_uri else None

    # Get roles
    roles = []
    for role_uri in graph.objects(hero_uri, MOBA.playsRole):
        roles.append(extract_local_name(str(role_uri)))

    # Get lanes
    lanes = []
    for lane_uri in graph.objects(hero_uri, MOBA.typicalLane):
        lanes.append(extract_local_name(str(lane_uri)))

    # Get title/comment
    title = str(graph.value(hero_uri, RDFS.comment) or "")

    # Parse base stats
    base_stats_uri = graph.value(hero_uri, MOBA.hasBaseStats)
    base_stats = parse_base_stats(graph, base_stats_uri) if base_stats_uri else {}

    # Parse stat growth
    stat_growth_uri = graph.value(hero_uri, MOBA.hasStatGrowth)
    stat_growth = parse_stat_growth(graph, stat_growth_uri) if stat_growth_uri else {}

    # Parse skills
    skills = {}
    for skill_uri in graph.objects(hero_uri, MOBA.hasSkill):
        skill_data = parse_skill(graph, skill_uri, local_name)
        skills[skill_data["key"]] = skill_data

    # Parse counter relationships
    counters = get_uri_list(graph, hero_uri, MOBA.counters)
    countered_by = get_uri_list(graph, hero_uri, MOBA.counteredBy)
    hard_counters = get_uri_list(graph, hero_uri, MOBA.hardCounters)
    hard_countered_by = get_uri_list(graph, hero_uri, MOBA.hardCounteredBy)

    # Parse synergy relationships
    strong_synergy = get_uri_list(graph, hero_uri, MOBA.strongSynergyWith)
    synergy = get_uri_list(graph, hero_uri, MOBA.synergyWith)
    weak_synergy = get_uri_list(graph, hero_uri, MOBA.weakSynergyWith)

    # Parse item recommendations
    core_items = get_uri_list(graph, hero_uri, MOBA.coreItem)
    recommended_items = get_uri_list(graph, hero_uri, MOBA.recommendedItem)
    situational_items = get_uri_list(graph, hero_uri, MOBA.situationalItem)

    return {
        "name": hero_name,
        "title": title,
        "hero_type": hero_type,
        "damage_type": damage_type,
        "attack_type": attack_type,
        "complexity": complexity,
        "is_ranged": get_bool_value(graph, hero_uri, MOBA.isRanged),
        "roles": roles,
        "lanes": lanes,
        "base_stats": base_stats,
        "stat_growth": stat_growth,
        "skills": skills,
        # Counter relationships
        "counters": counters,
        "countered_by": countered_by,
        "hard_counters": hard_counters,
        "hard_countered_by": hard_countered_by,
        # Synergy relationships
        "strong_synergy": strong_synergy,
        "synergy": synergy,
        "weak_synergy": weak_synergy,
        # Item builds
        "core_items": core_items,
        "recommended_items": recommended_items,
        "situational_items": situational_items,
    }


def build_indices(champions: Dict[str, Any]) -> Dict[str, Any]:
    """Build indices for quick lookups."""
    by_role = {}
    by_lane = {}
    by_damage_type = {}
    by_hero_type = {}

    for key, champ in champions.items():
        # Index by role
        for role in champ.get("roles", []):
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(key)

        # Index by lane
        for lane in champ.get("lanes", []):
            if lane not in by_lane:
                by_lane[lane] = []
            by_lane[lane].append(key)

        # Index by damage type
        dt = champ.get("damage_type")
        if dt:
            if dt not in by_damage_type:
                by_damage_type[dt] = []
            by_damage_type[dt].append(key)

        # Index by hero type
        ht = champ.get("hero_type")
        if ht:
            if ht not in by_hero_type:
                by_hero_type[ht] = []
            by_hero_type[ht].append(key)

    return {
        "by_role": by_role,
        "by_lane": by_lane,
        "by_damage_type": by_damage_type,
        "by_hero_type": by_hero_type,
    }


def parse_item_stats(graph: Graph, stats_uri) -> Dict[str, float]:
    """Parse item stats instance."""
    return {
        "attack_damage": get_float_value(graph, stats_uri, MOBA.hasAttackDamage),
        "ability_power": get_float_value(graph, stats_uri, MOBA.hasAbilityPower),
        "health": get_float_value(graph, stats_uri, MOBA.hasHealth),
        "mana": get_float_value(graph, stats_uri, MOBA.hasMana),
        "armor": get_float_value(graph, stats_uri, MOBA.hasArmor),
        "magic_resist": get_float_value(graph, stats_uri, MOBA.hasMagicResist),
        "attack_speed": get_float_value(graph, stats_uri, MOBA.hasAttackSpeed),
        "critical_chance": get_float_value(graph, stats_uri, MOBA.hasCriticalChance),
        "movement_speed": get_float_value(graph, stats_uri, MOBA.hasMovementSpeed),
        "cooldown_reduction": get_float_value(graph, stats_uri, MOBA.hasCooldownReduction),
        "life_steal": get_float_value(graph, stats_uri, MOBA.hasLifeSteal),
        "lethality": get_float_value(graph, stats_uri, MOBA.hasLethality),
        "armor_penetration": get_float_value(graph, stats_uri, MOBA.hasArmorPenetration),
        "magic_penetration": get_float_value(graph, stats_uri, MOBA.hasMagicPenetration),
    }


def parse_item(graph: Graph, item_uri) -> Dict[str, Any]:
    """Parse an item instance."""
    item_name = get_string_value(graph, item_uri, MOBA.itemName)
    if not item_name:
        item_name = str(graph.value(item_uri, RDFS.label) or extract_local_name(str(item_uri)))

    # Get item type
    item_type = None
    for it in ["AdvancedItem", "ComponentItem", "ConsumableItem"]:
        if (item_uri, RDF.type, MOBA[it]) in graph:
            item_type = it
            break

    # Get gold cost
    gold_cost = get_float_value(graph, item_uri, MOBA.goldCost)

    # Get build path
    build_path = get_uri_list(graph, item_uri, MOBA.buildPath)

    # Get stats
    stats_uri = graph.value(item_uri, MOBA.providesStats)
    stats = parse_item_stats(graph, stats_uri) if stats_uri else {}

    # Get effect types
    effect_types = get_uri_list(graph, item_uri, MOBA.hasEffectType)

    # Get description
    description = str(graph.value(item_uri, RDFS.comment) or "")

    # Get unique passive
    unique_passive = get_bool_value(graph, item_uri, MOBA.uniquePassive)

    return {
        "name": item_name,
        "item_type": item_type,
        "gold_cost": int(gold_cost) if gold_cost else None,
        "build_path": [b.replace("_", " ") for b in build_path],
        "stats": {k: v for k, v in stats.items() if v is not None},
        "effect_types": effect_types,
        "description": description,
        "unique_passive": unique_passive,
    }


def parse_monster_stats(graph: Graph, stats_uri) -> Dict[str, float]:
    """Parse monster stats instance."""
    return {
        "armor": get_float_value(graph, stats_uri, MOBA.hasArmor),
        "attack_damage": get_float_value(graph, stats_uri, MOBA.hasAttackDamage),
        "attack_speed": get_float_value(graph, stats_uri, MOBA.hasAttackSpeed),
        "magic_resist": get_float_value(graph, stats_uri, MOBA.hasMagicResist),
        "movement_speed": get_float_value(graph, stats_uri, MOBA.hasMovementSpeed),
    }


def parse_monster(graph: Graph, monster_uri) -> Dict[str, Any]:
    """Parse a monster instance."""
    monster_name = str(graph.value(monster_uri, RDFS.label) or extract_local_name(str(monster_uri)))

    # Get monster type
    monster_type = None
    if (monster_uri, RDF.type, MOBA.Boss) in graph:
        monster_type = "Boss"
    elif (monster_uri, RDF.type, MOBA.NeutralMonster) in graph:
        monster_type = "NeutralMonster"

    # Get health
    health = get_float_value(graph, monster_uri, MOBA.objectiveHealth)

    # Get attack range
    attack_range = get_float_value(graph, monster_uri, MOBA.attackRange)

    # Get stats
    stats_uri = graph.value(monster_uri, MOBA.hasBaseStats)
    stats = parse_monster_stats(graph, stats_uri) if stats_uri else {}

    # Get comments (contain bounty, spawn info)
    comments = []
    for comment in graph.objects(monster_uri, RDFS.comment):
        comments.append(str(comment))

    return {
        "name": monster_name,
        "monster_type": monster_type,
        "health": health,
        "attack_range": attack_range,
        "stats": {k: v for k, v in stats.items() if v is not None},
        "info": comments,
    }


def parse_turret(graph: Graph, turret_uri) -> Dict[str, Any]:
    """Parse a turret instance."""
    turret_name = str(graph.value(turret_uri, RDFS.label) or extract_local_name(str(turret_uri)))

    # Get health
    health = get_float_value(graph, turret_uri, MOBA.objectiveHealth)

    # Get attack range
    attack_range = get_float_value(graph, turret_uri, MOBA.attackRange)

    # Get stats
    stats_uri = graph.value(turret_uri, MOBA.hasBaseStats)
    stats = parse_monster_stats(graph, stats_uri) if stats_uri else {}

    # Get comments (contain bounty info)
    comments = []
    for comment in graph.objects(turret_uri, RDFS.comment):
        comments.append(str(comment))

    return {
        "name": turret_name,
        "health": health,
        "attack_range": attack_range,
        "stats": {k: v for k, v in stats.items() if v is not None},
        "info": comments,
    }


def parse_items_ttl(ttl_path: str) -> Dict[str, Any]:
    """Parse the items TTL file into a dictionary."""
    print(f"Loading items from {ttl_path}...")
    graph = Graph()
    graph.parse(ttl_path, format="turtle")

    items = {}

    # Find all items
    for item_type in ["AdvancedItem", "ComponentItem", "ConsumableItem"]:
        for item_uri in graph.subjects(RDF.type, MOBA[item_type]):
            item_data = parse_item(graph, item_uri)
            key = normalize_name(item_data["name"])
            if key not in items:
                items[key] = item_data

    print(f"Parsed {len(items)} items")
    return items


def parse_monsters_ttl(ttl_path: str) -> Dict[str, Any]:
    """Parse the monsters TTL file into a dictionary."""
    print(f"Loading monsters from {ttl_path}...")
    graph = Graph()
    graph.parse(ttl_path, format="turtle")

    monsters = {}

    # Find all monsters (Boss and NeutralMonster)
    for monster_type in ["Boss", "NeutralMonster"]:
        for monster_uri in graph.subjects(RDF.type, MOBA[monster_type]):
            monster_data = parse_monster(graph, monster_uri)
            key = normalize_name(monster_data["name"])
            if key not in monsters:
                monsters[key] = monster_data

    print(f"Parsed {len(monsters)} monsters")
    return monsters


def parse_turrets_ttl(ttl_path: str) -> Dict[str, Any]:
    """Parse the turrets TTL file into a dictionary."""
    print(f"Loading turrets from {ttl_path}...")
    graph = Graph()
    graph.parse(ttl_path, format="turtle")

    turrets = {}

    # Find all turrets (Tower type)
    for turret_uri in graph.subjects(RDF.type, MOBA.Tower):
        turret_data = parse_turret(graph, turret_uri)
        key = normalize_name(turret_data["name"])
        turrets[key] = turret_data

    print(f"Parsed {len(turrets)} turrets")
    return turrets


def parse_ttl_to_dict(ttl_path: str) -> Dict[str, Any]:
    """Parse the TTL file into a structured dictionary."""
    print(f"Loading RDF data from {ttl_path}...")
    graph = Graph()
    graph.parse(ttl_path, format="turtle")
    print(f"Loaded {len(graph)} triples")

    champions = {}

    # Find all heroes by checking hero types
    for hero_type in HERO_TYPES:
        for hero_uri in graph.subjects(RDF.type, MOBA[hero_type]):
            champion_data = parse_champion(graph, hero_uri)
            key = normalize_name(champion_data["name"])
            if key not in champions:  # Avoid duplicates
                champions[key] = champion_data

    print(f"Parsed {len(champions)} champions")

    return {
        "champions": champions,
        "indices": build_indices(champions),
    }


def parse_all_data(champions_path: str, items_path: str, monsters_path: str, turrets_path: str) -> Dict[str, Any]:
    """Parse all data files and return a combined dictionary."""
    champions_data = parse_ttl_to_dict(champions_path)
    items = parse_items_ttl(items_path)
    monsters = parse_monsters_ttl(monsters_path)
    turrets = parse_turrets_ttl(turrets_path)

    return {
        "champions": champions_data["champions"],
        "indices": champions_data["indices"],
        "items": items,
        "monsters": monsters,
        "turrets": turrets,
    }


if __name__ == "__main__":
    # Test the parser
    from config import TTL_FILE_PATH
    data = parse_ttl_to_dict(TTL_FILE_PATH)

    # Print Aatrox data as a test (has counter/synergy data)
    aatrox = data["champions"].get("aatrox")
    if aatrox:
        print(f"\n{aatrox['name']} - {aatrox['title']}")
        print(f"Roles: {aatrox['roles']}")
        print(f"Lanes: {aatrox['lanes']}")
        print(f"\nCore Items: {aatrox['core_items']}")
        print(f"Recommended Items: {aatrox['recommended_items']}")
        print(f"Situational Items: {aatrox['situational_items']}")
        print(f"\nHard Counters (Aatrox beats): {aatrox['hard_counters'][:5]}...")
        print(f"Hard Countered By: {aatrox['hard_countered_by'][:5]}...")
        print(f"\nStrong Synergy: {aatrox['strong_synergy'][:5]}...")
        print(f"Synergy: {aatrox['synergy'][:5]}...")

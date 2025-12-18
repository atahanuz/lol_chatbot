"""
Ontology Enricher for LoL Chatbot

Scrapes data from LoL Wiki and Data Dragon to enrich the RDF ontology with:
- Crowd control types (stun, slow, knockup, silence, root, etc.)
- Ability effects (dash, shield, heal, stealth, etc.)
- Playstyle archetypes (burst, poke, sustained, utility, engage)
- Power curves (early/mid/late game)
- Win conditions (teamfight, splitpush, pick, siege)
"""

import requests
import json
import re
import time
from typing import Dict, List, Set, Any, Optional
from pathlib import Path

# Data Dragon base URL
DDRAGON_BASE = "https://ddragon.leagueoflegends.com"

# Keywords for detecting CC types in ability descriptions
CC_KEYWORDS = {
    "Stun": ["stun", "stunned", "stunning"],
    "Slow": ["slow", "slowed", "slowing"],
    "Root": ["root", "rooted", "rooting", "immobilize", "snare", "snared"],
    "Knockup": ["knock up", "knocked up", "knocking up", "airborne", "knock back", "knockback"],
    "Silence": ["silence", "silenced", "silencing"],
    "Blind": ["blind", "blinded", "blinding", "nearsight", "nearsighted"],
    "Charm": ["charm", "charmed", "charming"],
    "Fear": ["fear", "feared", "fearing", "flee", "fleeing", "terrify"],
    "Taunt": ["taunt", "taunted", "taunting"],
    "Suppress": ["suppress", "suppressed", "suppressing", "suppression"],
    "Knockdown": ["knock down", "knocked down", "ground", "grounded", "grounding"],
    "Sleep": ["sleep", "drowsy", "asleep"],
    "Polymorph": ["polymorph", "polymorphed"],
    "Stasis": ["stasis"],
}

# Keywords for detecting ability effects
EFFECT_KEYWORDS = {
    "Dash": ["dash", "dashes", "dashing", "leap", "leaps", "leaping", "jump", "jumps", "lunge", "lunges"],
    "Blink": ["blink", "blinks", "teleport", "teleports", "flash"],
    "Shield": ["shield", "shields", "shielding", "barrier"],
    "Heal": ["heal", "heals", "healing", "restore", "restores", "restoring health", "regenerate"],
    "Stealth": ["stealth", "invisible", "invisibility", "camouflage", "camouflaged", "untargetable"],
    "Invulnerability": ["invulnerable", "invulnerability", "untargetable", "immune"],
    "SpellBlock": ["spell shield", "spellshield", "block", "blocks ability"],
    "Revive": ["revive", "revived", "resurrection", "resurrect"],
    "Clone": ["clone", "clones", "decoy"],
    "Pull": ["pull", "pulls", "pulling", "hook", "hooks", "grab", "grabs"],
    "Terrain": ["terrain", "wall", "create terrain", "impassable"],
    "Execute": ["execute", "executes", "execution", "bonus damage.*low health"],
    "Reset": ["reset", "resets cooldown", "refund"],
    "AOE": ["area", "enemies in", "all enemies", "nearby enemies", "around"],
    "GlobalRange": ["global", "anywhere on the map", "unlimited range"],
    "Unstoppable": ["unstoppable"],
}

# Champion playstyle classifications (based on community consensus)
# This is manually curated data that would be hard to scrape accurately
CHAMPION_PLAYSTYLES = {
    # Assassins - Burst focused
    "Akali": ["Burst", "Mobility", "Assassin"],
    "Akshan": ["Burst", "Mobility", "Marksman"],
    "Diana": ["Burst", "Dive", "Assassin"],
    "Ekko": ["Burst", "Mobility", "Assassin"],
    "Evelynn": ["Burst", "Assassin", "Stealth"],
    "Fizz": ["Burst", "Mobility", "Assassin"],
    "Kassadin": ["Burst", "Scaling", "Assassin"],
    "Katarina": ["Burst", "Reset", "Assassin"],
    "Kayn": ["Burst", "Mobility", "Assassin"],
    "Khazix": ["Burst", "Assassin", "Stealth"],
    "Leblanc": ["Burst", "Mobility", "Assassin"],
    "Naafiri": ["Burst", "Assassin"],
    "Nocturne": ["Burst", "Dive", "Assassin"],
    "Pyke": ["Burst", "Assassin", "Support"],
    "Qiyana": ["Burst", "Assassin"],
    "Rengar": ["Burst", "Assassin", "Stealth"],
    "Shaco": ["Burst", "Assassin", "Stealth"],
    "Talon": ["Burst", "Mobility", "Assassin"],
    "Zed": ["Burst", "Assassin"],

    # Mages - Burst/Poke/Control
    "Ahri": ["Burst", "Mobility", "Mage"],
    "Anivia": ["Control", "Zone", "Mage"],
    "Annie": ["Burst", "Engage", "Mage"],
    "Aurelion Sol": ["Sustained", "Scaling", "Mage"],
    "Azir": ["Sustained", "Scaling", "Zone", "Mage"],
    "Brand": ["Burst", "AOE", "Mage"],
    "Cassiopeia": ["Sustained", "DPS", "Mage"],
    "Hwei": ["Poke", "Control", "Mage"],
    "Karma": ["Poke", "Utility", "Mage"],
    "Karthus": ["Sustained", "Scaling", "Mage"],
    "Lissandra": ["Burst", "Engage", "Control", "Mage"],
    "Lux": ["Burst", "Poke", "Mage"],
    "Malzahar": ["Sustained", "Control", "Mage"],
    "Neeko": ["Burst", "Engage", "Mage"],
    "Orianna": ["Control", "Utility", "Mage"],
    "Ryze": ["Sustained", "Scaling", "Mage"],
    "Syndra": ["Burst", "Mage"],
    "Taliyah": ["Burst", "Zone", "Mage"],
    "Twisted Fate": ["Utility", "Roam", "Mage"],
    "Veigar": ["Burst", "Scaling", "Mage"],
    "Vel'Koz": ["Poke", "Burst", "Mage"],
    "Vex": ["Burst", "Engage", "Mage"],
    "Viktor": ["Burst", "Zone", "Mage"],
    "Vladimir": ["Sustained", "Scaling", "Mage"],
    "Xerath": ["Poke", "Artillery", "Mage"],
    "Ziggs": ["Poke", "Siege", "Mage"],
    "Zoe": ["Burst", "Poke", "Mage"],
    "Zyra": ["Zone", "Control", "Mage"],

    # Fighters/Bruisers
    "Aatrox": ["Sustained", "Drain", "Fighter"],
    "Camille": ["Burst", "Dive", "Fighter"],
    "Darius": ["Sustained", "Juggernaut", "Fighter"],
    "Fiora": ["Splitpush", "Duelist", "Fighter"],
    "Garen": ["Sustained", "Juggernaut", "Fighter"],
    "Gwen": ["Sustained", "Scaling", "Fighter"],
    "Illaoi": ["Sustained", "Juggernaut", "Fighter"],
    "Irelia": ["Sustained", "Dive", "Fighter"],
    "Jax": ["Sustained", "Scaling", "Splitpush", "Fighter"],
    "Jayce": ["Poke", "Burst", "Fighter"],
    "Kled": ["Dive", "Engage", "Fighter"],
    "Lee Sin": ["Burst", "Mobility", "Fighter"],
    "Mordekaiser": ["Sustained", "Juggernaut", "Fighter"],
    "Nasus": ["Sustained", "Scaling", "Splitpush", "Fighter"],
    "Olaf": ["Sustained", "Dive", "Fighter"],
    "Pantheon": ["Burst", "Dive", "Fighter"],
    "Rek'Sai": ["Burst", "Dive", "Fighter"],
    "Renekton": ["Burst", "Dive", "Fighter"],
    "Riven": ["Burst", "Mobility", "Fighter"],
    "Sett": ["Sustained", "Engage", "Fighter"],
    "Trundle": ["Sustained", "Juggernaut", "Fighter"],
    "Tryndamere": ["Sustained", "Splitpush", "Fighter"],
    "Urgot": ["Sustained", "Juggernaut", "Fighter"],
    "Vi": ["Burst", "Dive", "Fighter"],
    "Volibear": ["Sustained", "Dive", "Fighter"],
    "Warwick": ["Sustained", "Dive", "Fighter"],
    "Wukong": ["Burst", "Engage", "Fighter"],
    "Xin Zhao": ["Sustained", "Dive", "Fighter"],
    "Yasuo": ["Sustained", "Scaling", "Fighter"],
    "Yone": ["Sustained", "Scaling", "Fighter"],
    "Yorick": ["Sustained", "Splitpush", "Fighter"],

    # Tanks
    "Alistar": ["Engage", "Peel", "Tank"],
    "Amumu": ["Engage", "AOE", "Tank"],
    "Braum": ["Peel", "Utility", "Tank"],
    "Cho'Gath": ["Sustained", "Scaling", "Tank"],
    "Dr. Mundo": ["Sustained", "Juggernaut", "Tank"],
    "Galio": ["Engage", "Utility", "Tank"],
    "Gragas": ["Burst", "Engage", "Tank"],
    "Jarvan IV": ["Engage", "Dive", "Tank"],
    "K'Sante": ["Engage", "Peel", "Tank"],
    "Leona": ["Engage", "Lockdown", "Tank"],
    "Malphite": ["Engage", "AOE", "Tank"],
    "Maokai": ["Engage", "Peel", "Tank"],
    "Nautilus": ["Engage", "Lockdown", "Tank"],
    "Nunu & Willump": ["Engage", "Objective", "Tank"],
    "Ornn": ["Engage", "Utility", "Tank"],
    "Poppy": ["Peel", "Engage", "Tank"],
    "Rammus": ["Engage", "Dive", "Tank"],
    "Rell": ["Engage", "Lockdown", "Tank"],
    "Sejuani": ["Engage", "AOE", "Tank"],
    "Shen": ["Utility", "Splitpush", "Tank"],
    "Singed": ["Sustained", "Proxy", "Tank"],
    "Sion": ["Engage", "Scaling", "Tank"],
    "Skarner": ["Engage", "Pick", "Tank"],
    "Tahm Kench": ["Peel", "Utility", "Tank"],
    "Taric": ["Peel", "Utility", "Tank"],
    "Thresh": ["Engage", "Peel", "Utility", "Tank"],
    "Zac": ["Engage", "Dive", "Tank"],

    # Marksmen/ADCs
    "Aphelios": ["Sustained", "Scaling", "Marksman"],
    "Ashe": ["Utility", "Engage", "Marksman"],
    "Caitlyn": ["Poke", "Siege", "Marksman"],
    "Corki": ["Burst", "Poke", "Marksman"],
    "Draven": ["Burst", "Snowball", "Marksman"],
    "Ezreal": ["Poke", "Burst", "Marksman"],
    "Jhin": ["Burst", "Utility", "Marksman"],
    "Jinx": ["Sustained", "Scaling", "Marksman"],
    "Kai'Sa": ["Burst", "Scaling", "Marksman"],
    "Kalista": ["Sustained", "Utility", "Marksman"],
    "Kindred": ["Sustained", "Scaling", "Marksman"],
    "Kog'Maw": ["Sustained", "Scaling", "Marksman"],
    "Lucian": ["Burst", "Lane", "Marksman"],
    "Miss Fortune": ["Burst", "AOE", "Marksman"],
    "Nilah": ["Sustained", "Scaling", "Marksman"],
    "Samira": ["Burst", "Reset", "Marksman"],
    "Senna": ["Poke", "Utility", "Scaling", "Marksman"],
    "Sivir": ["Sustained", "Utility", "Marksman"],
    "Smolder": ["Poke", "Scaling", "Marksman"],
    "Tristana": ["Burst", "Scaling", "Marksman"],
    "Twitch": ["Burst", "Stealth", "Marksman"],
    "Varus": ["Poke", "Burst", "Marksman"],
    "Vayne": ["Sustained", "Scaling", "Duelist", "Marksman"],
    "Xayah": ["Burst", "Utility", "Marksman"],
    "Zeri": ["Sustained", "Mobility", "Marksman"],

    # Supports
    "Bard": ["Utility", "Roam", "Support"],
    "Blitzcrank": ["Pick", "Engage", "Support"],
    "Janna": ["Peel", "Disengage", "Support"],
    "Karma": ["Poke", "Utility", "Support"],
    "Lulu": ["Peel", "Utility", "Support"],
    "Milio": ["Peel", "Utility", "Support"],
    "Morgana": ["Peel", "Pick", "Support"],
    "Nami": ["Poke", "Utility", "Support"],
    "Rakan": ["Engage", "Mobility", "Support"],
    "Renata Glasc": ["Utility", "Peel", "Support"],
    "Seraphine": ["Utility", "Poke", "Support"],
    "Sona": ["Utility", "Sustained", "Support"],
    "Soraka": ["Sustained", "Heal", "Support"],
    "Yuumi": ["Sustained", "Utility", "Support"],
    "Zilean": ["Utility", "Poke", "Support"],

    # Others
    "Elise": ["Burst", "Dive", "Mage"],
    "Fiddlesticks": ["Burst", "Engage", "Mage"],
    "Heimerdinger": ["Zone", "Siege", "Mage"],
    "Ivern": ["Utility", "Support", "Mage"],
    "Kayle": ["Sustained", "Scaling", "Mage"],
    "Kennen": ["Burst", "Engage", "Mage"],
    "Lillia": ["Sustained", "Kite", "Mage"],
    "Master Yi": ["Sustained", "Reset", "Assassin"],
    "Nidalee": ["Poke", "Burst", "Mage"],
    "Rumble": ["Sustained", "Zone", "Mage"],
    "Shyvana": ["Sustained", "Dive", "Fighter"],
    "Swain": ["Sustained", "Drain", "Mage"],
    "Sylas": ["Burst", "Sustained", "Mage"],
    "Teemo": ["Poke", "Zone", "Mage"],
    "Viego": ["Sustained", "Reset", "Assassin"],
}

# Power curve classifications
POWER_CURVES = {
    # Early game champions (strong levels 1-6)
    "EarlyGame": [
        "Draven", "Renekton", "Pantheon", "Lee Sin", "Elise", "Olaf",
        "Darius", "Lucian", "Caitlyn", "Jayce", "Karma", "Rakan",
        "Rek'Sai", "Xin Zhao", "Blitzcrank", "Thresh", "Leona",
        "Nautilus", "Alistar", "Volibear", "Warwick", "Nidalee"
    ],
    # Mid game champions (strong levels 6-13)
    "MidGame": [
        "Ahri", "Fizz", "Katarina", "Talon", "Zed", "Qiyana",
        "Syndra", "Orianna", "Viktor", "Corki", "Ezreal", "Miss Fortune",
        "Jhin", "Kai'Sa", "Hecarim", "Kha'Zix", "Rengar", "Graves",
        "Kindred", "Irelia", "Camille", "Fiora", "Riven", "Aatrox",
        "Mordekaiser", "Sett", "Gnar", "Rumble", "Gragas"
    ],
    # Late game champions (strong levels 14-18)
    "LateGame": [
        "Kassadin", "Kayle", "Veigar", "Vladimir", "Ryze", "Azir",
        "Cassiopeia", "Karthus", "Aurelion Sol", "Jinx", "Vayne",
        "Kog'Maw", "Twitch", "Aphelios", "Tristana", "Sivir",
        "Jax", "Nasus", "Gangplank", "Ornn", "Cho'Gath", "Sion",
        "Senna", "Smolder", "Nilah", "Zeri", "Yasuo", "Yone", "Gwen"
    ],
}

# Win conditions
WIN_CONDITIONS = {
    "Teamfight": [
        "Amumu", "Malphite", "Orianna", "Seraphine", "Miss Fortune",
        "Wukong", "Kennen", "Diana", "Zyra", "Brand", "Fiddlesticks",
        "Jarvan IV", "Sejuani", "Galio", "Neeko", "Rell", "Leona",
        "Karthus", "Vex", "Annie", "Lissandra", "Qiyana", "Rakan"
    ],
    "Splitpush": [
        "Fiora", "Jax", "Tryndamere", "Yorick", "Nasus", "Camille",
        "Shen", "Gwen", "Trundle", "Udyr", "Illaoi", "Sion"
    ],
    "Pick": [
        "Blitzcrank", "Thresh", "Pyke", "Zoe", "Ahri", "Evelyn",
        "Rengar", "Kha'Zix", "Nocturne", "Ashe", "Morgana", "Lux"
    ],
    "Siege": [
        "Ziggs", "Xerath", "Vel'Koz", "Caitlyn", "Jayce", "Heimerdinger",
        "Varus", "Ezreal", "Corki", "Zeri"
    ],
    "Objective": [
        "Nunu & Willump", "Shyvana", "Master Yi", "Kindred", "Karthus",
        "Cho'Gath", "Kalista"
    ],
}


def get_latest_version() -> str:
    """Get the latest Data Dragon version."""
    try:
        response = requests.get(f"{DDRAGON_BASE}/api/versions.json", timeout=10)
        versions = response.json()
        return versions[0]
    except Exception as e:
        print(f"Error fetching versions: {e}")
        return "14.23.1"  # Fallback version


def get_champion_data(version: str) -> Dict[str, Any]:
    """Fetch all champion data from Data Dragon."""
    url = f"{DDRAGON_BASE}/cdn/{version}/data/en_US/champion.json"
    response = requests.get(url, timeout=30)
    return response.json()["data"]


def get_champion_details(version: str, champion_id: str) -> Dict[str, Any]:
    """Fetch detailed champion data including abilities."""
    url = f"{DDRAGON_BASE}/cdn/{version}/data/en_US/champion/{champion_id}.json"
    response = requests.get(url, timeout=30)
    return response.json()["data"][champion_id]


def extract_cc_from_description(description: str) -> Set[str]:
    """Extract CC types from ability description."""
    description_lower = description.lower()
    # Remove HTML tags
    description_lower = re.sub(r'<[^>]+>', '', description_lower)

    found_cc = set()
    for cc_type, keywords in CC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in description_lower:
                found_cc.add(cc_type)
                break
    return found_cc


def extract_effects_from_description(description: str) -> Set[str]:
    """Extract ability effects from description."""
    description_lower = description.lower()
    # Remove HTML tags
    description_lower = re.sub(r'<[^>]+>', '', description_lower)

    found_effects = set()
    for effect_type, keywords in EFFECT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in description_lower:
                found_effects.add(effect_type)
                break
    return found_effects


def analyze_champion_abilities(champion_details: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a champion's abilities to extract CC and effects."""
    all_cc = set()
    all_effects = set()

    # Analyze passive
    if "passive" in champion_details:
        passive_desc = champion_details["passive"].get("description", "")
        all_cc.update(extract_cc_from_description(passive_desc))
        all_effects.update(extract_effects_from_description(passive_desc))

    # Analyze spells (Q, W, E, R)
    for spell in champion_details.get("spells", []):
        spell_desc = spell.get("description", "")
        tooltip = spell.get("tooltip", "")
        full_desc = spell_desc + " " + tooltip

        all_cc.update(extract_cc_from_description(full_desc))
        all_effects.update(extract_effects_from_description(full_desc))

    return {
        "cc_types": list(all_cc),
        "effects": list(all_effects),
    }


def normalize_champion_name(name: str) -> str:
    """Normalize champion name for TTL format."""
    # Handle special cases - must match the format in main TTL file
    name = name.replace("'", "").replace(".", "").replace(" ", "_")
    name = name.replace("&", "and")  # Handle Nunu & Willump
    name = name.replace("__", "_")  # Clean up double underscores
    return name


def generate_ttl_triples(enrichment_data: Dict[str, Dict]) -> str:
    """Generate TTL format triples for the enrichment data."""
    lines = [
        "# Ontology Enrichment - Auto-generated semantic properties",
        "# Generated by ontology_enricher.py",
        "",
        "@prefix moba: <http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        "# === CC Type Classes ===",
    ]

    # Define CC type classes
    for cc_type in CC_KEYWORDS.keys():
        lines.append(f"moba:{cc_type}CC a rdfs:Class ;")
        lines.append(f'    rdfs:label "{cc_type}"@en .')

    lines.append("")
    lines.append("# === Effect Type Classes ===")

    # Define effect type classes
    for effect in EFFECT_KEYWORDS.keys():
        lines.append(f"moba:{effect}Effect a rdfs:Class ;")
        lines.append(f'    rdfs:label "{effect}"@en .')

    lines.append("")
    lines.append("# === Playstyle Classes ===")

    # Get all unique playstyles
    all_playstyles = set()
    for styles in CHAMPION_PLAYSTYLES.values():
        all_playstyles.update(styles)

    for playstyle in sorted(all_playstyles):
        lines.append(f"moba:{playstyle}Playstyle a rdfs:Class ;")
        lines.append(f'    rdfs:label "{playstyle}"@en .')

    lines.append("")
    lines.append("# === Power Curve Classes ===")

    for curve in ["EarlyGame", "MidGame", "LateGame"]:
        lines.append(f"moba:{curve}PowerSpike a rdfs:Class ;")
        lines.append(f'    rdfs:label "{curve}"@en .')

    lines.append("")
    lines.append("# === Win Condition Classes ===")

    for condition in WIN_CONDITIONS.keys():
        lines.append(f"moba:{condition}WinCondition a rdfs:Class ;")
        lines.append(f'    rdfs:label "{condition}"@en .')

    lines.append("")
    lines.append("# === Champion Enrichment Data ===")
    lines.append("")

    # Generate champion enrichment triples
    for champ_name, data in enrichment_data.items():
        ttl_name = normalize_champion_name(champ_name)

        # CC types
        if data.get("cc_types"):
            cc_values = ", ".join([f"moba:{cc}CC" for cc in data["cc_types"]])
            lines.append(f"moba:{ttl_name} moba:hasCrowdControl {cc_values} .")

        # Effects
        if data.get("effects"):
            effect_values = ", ".join([f"moba:{e}Effect" for e in data["effects"]])
            lines.append(f"moba:{ttl_name} moba:hasAbilityEffect {effect_values} .")

        # Playstyles
        if data.get("playstyles"):
            style_values = ", ".join([f"moba:{s}Playstyle" for s in data["playstyles"]])
            lines.append(f"moba:{ttl_name} moba:hasPlaystyle {style_values} .")

        # Power curve
        if data.get("power_curve"):
            curve_values = ", ".join([f"moba:{c}PowerSpike" for c in data["power_curve"]])
            lines.append(f"moba:{ttl_name} moba:hasPowerSpike {curve_values} .")

        # Win condition
        if data.get("win_conditions"):
            cond_values = ", ".join([f"moba:{c}WinCondition" for c in data["win_conditions"]])
            lines.append(f"moba:{ttl_name} moba:hasWinCondition {cond_values} .")

        lines.append("")

    return "\n".join(lines)


def enrich_from_data_dragon() -> Dict[str, Dict]:
    """Fetch and analyze all champions from Data Dragon."""
    print("Fetching latest Data Dragon version...")
    version = get_latest_version()
    print(f"Using version: {version}")

    print("Fetching champion list...")
    champions = get_champion_data(version)

    enrichment_data = {}
    total = len(champions)

    for i, (champ_id, champ_info) in enumerate(champions.items(), 1):
        champ_name = champ_info["name"]
        print(f"[{i}/{total}] Analyzing {champ_name}...")

        try:
            details = get_champion_details(version, champ_id)
            analysis = analyze_champion_abilities(details)

            # Add playstyle data if available
            playstyles = CHAMPION_PLAYSTYLES.get(champ_name, [])

            # Determine power curve
            power_curve = []
            for curve, champs in POWER_CURVES.items():
                if champ_name in champs:
                    power_curve.append(curve)

            # Determine win conditions
            win_conditions = []
            for condition, champs in WIN_CONDITIONS.items():
                if champ_name in champs:
                    win_conditions.append(condition)

            enrichment_data[champ_name] = {
                "cc_types": analysis["cc_types"],
                "effects": analysis["effects"],
                "playstyles": playstyles,
                "power_curve": power_curve,
                "win_conditions": win_conditions,
            }

            # Rate limiting
            time.sleep(0.1)

        except Exception as e:
            print(f"  Error analyzing {champ_name}: {e}")
            enrichment_data[champ_name] = {
                "cc_types": [],
                "effects": [],
                "playstyles": CHAMPION_PLAYSTYLES.get(champ_name, []),
                "power_curve": [],
                "win_conditions": [],
            }

    return enrichment_data


def save_enrichment_data(enrichment_data: Dict[str, Dict], output_path: str):
    """Save enrichment data as JSON for inspection."""
    with open(output_path, 'w') as f:
        json.dump(enrichment_data, f, indent=2, sort_keys=True)
    print(f"Saved enrichment data to {output_path}")


def main():
    """Main function to run the ontology enricher."""
    print("=" * 60)
    print("LoL Ontology Enricher")
    print("=" * 60)

    # Fetch and analyze champion data
    enrichment_data = enrich_from_data_dragon()

    # Save raw data for inspection
    import sys
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    sys.path.insert(0, os.path.join(project_root, 'src'))
    from config import ENRICHMENT_DATA_PATH, ENRICHMENT_TTL_PATH
    save_enrichment_data(enrichment_data, ENRICHMENT_DATA_PATH)

    # Generate TTL triples
    print("\nGenerating TTL triples...")
    ttl_content = generate_ttl_triples(enrichment_data)

    # Save TTL file
    ttl_path = ENRICHMENT_TTL_PATH
    with open(ttl_path, 'w') as f:
        f.write(ttl_content)
    print(f"Saved TTL enrichment to {ttl_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    total_cc = sum(len(d.get("cc_types", [])) for d in enrichment_data.values())
    total_effects = sum(len(d.get("effects", [])) for d in enrichment_data.values())
    total_playstyles = sum(len(d.get("playstyles", [])) for d in enrichment_data.values())

    print(f"Champions analyzed: {len(enrichment_data)}")
    print(f"Total CC annotations: {total_cc}")
    print(f"Total effect annotations: {total_effects}")
    print(f"Total playstyle annotations: {total_playstyles}")

    # Sample output
    print("\nSample enrichment (Leona):")
    if "Leona" in enrichment_data:
        leona = enrichment_data["Leona"]
        print(f"  CC Types: {leona.get('cc_types', [])}")
        print(f"  Effects: {leona.get('effects', [])}")
        print(f"  Playstyles: {leona.get('playstyles', [])}")
        print(f"  Power Curve: {leona.get('power_curve', [])}")
        print(f"  Win Conditions: {leona.get('win_conditions', [])}")


if __name__ == "__main__":
    main()

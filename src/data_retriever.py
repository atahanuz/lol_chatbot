from typing import Dict, Any, List, Optional
from intent_classifier import normalize_champion_name

# Import semantic query engine (lazy loaded)
_semantic_engine = None

def get_semantic_engine():
    """Lazy load the semantic query engine."""
    global _semantic_engine
    if _semantic_engine is None:
        from sparql_queries import get_query_engine
        _semantic_engine = get_query_engine()
    return _semantic_engine


# Import snapshot analyzer (lazy loaded)
_snapshot_analyzer = None

def get_snapshot_analyzer(retriever: 'DataRetriever'):
    """Lazy load the snapshot analyzer."""
    global _snapshot_analyzer
    if _snapshot_analyzer is None:
        from snapshot_analyzer import SnapshotAnalyzer
        _snapshot_analyzer = SnapshotAnalyzer(retriever)
    return _snapshot_analyzer


class DataRetriever:
    """Retrieves data from the parsed champion dictionary based on user queries."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.champions = data.get("champions", {})
        self.indices = data.get("indices", {})
        self.items = data.get("items", {})
        self.monsters = data.get("monsters", {})
        self.turrets = data.get("turrets", {})

    def find_champion(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a champion by name, handling aliases and variations."""
        normalized = normalize_champion_name(name)

        # Direct lookup
        if normalized in self.champions:
            return self.champions[normalized]

        # Try fuzzy matching
        for key, champ in self.champions.items():
            if normalized in key or key in normalized:
                return champ
            if champ.get("name", "").lower() == name.lower():
                return champ

        return None

    def get_skill_damage_at_level(
        self, champion_name: str, skill_key: str, level: int
    ) -> Dict[str, Any]:
        """Get damage for a specific skill at a specific level."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        skill = champ.get("skills", {}).get(skill_key.upper())
        if not skill:
            return {
                "error": f"Skill '{skill_key}' not found for {champ['name']}",
                "available_skills": list(champ.get("skills", {}).keys()),
            }

        level_data = skill.get("levels", {}).get(level)
        if not level_data:
            available_levels = list(skill.get("levels", {}).keys())
            return {
                "error": f"Level {level} not found for {skill['name']}",
                "available_levels": available_levels,
            }

        return {
            "champion": champ["name"],
            "skill_name": skill["name"],
            "skill_key": skill_key.upper(),
            "level": level,
            "damage": level_data.get("damage"),
            "damage_type": skill.get("damage_type"),
            "cooldown": level_data.get("cooldown"),
            "mana_cost": level_data.get("mana_cost"),
        }

    def get_skill_info(self, champion_name: str, skill_key: str) -> Dict[str, Any]:
        """Get general information about a skill."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        skill = champ.get("skills", {}).get(skill_key.upper())
        if not skill:
            return {
                "error": f"Skill '{skill_key}' not found for {champ['name']}",
                "available_skills": list(champ.get("skills", {}).keys()),
            }

        # Compile all level data
        levels_summary = []
        for lvl, data in sorted(skill.get("levels", {}).items()):
            levels_summary.append({
                "level": lvl,
                "damage": data.get("damage"),
                "cooldown": data.get("cooldown"),
                "mana_cost": data.get("mana_cost"),
            })

        return {
            "champion": champ["name"],
            "skill_name": skill["name"],
            "skill_key": skill_key.upper(),
            "skill_types": skill.get("types", []),
            "damage_type": skill.get("damage_type"),
            "cost_type": skill.get("cost_type"),
            "base_cost": skill.get("base_cost"),
            "base_cooldown": skill.get("base_cooldown"),
            "max_level": skill.get("max_level"),
            "target": skill.get("target"),
            "levels": levels_summary,
        }

    def get_skill_cooldown(
        self, champion_name: str, skill_key: str, level: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get cooldown for a skill, optionally at a specific level."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        skill = champ.get("skills", {}).get(skill_key.upper())
        if not skill:
            return {"error": f"Skill '{skill_key}' not found for {champ['name']}"}

        if level is not None:
            level_data = skill.get("levels", {}).get(level)
            if level_data:
                return {
                    "champion": champ["name"],
                    "skill_name": skill["name"],
                    "skill_key": skill_key.upper(),
                    "level": level,
                    "cooldown": level_data.get("cooldown"),
                }

        # Return all cooldowns
        cooldowns = {}
        for lvl, data in sorted(skill.get("levels", {}).items()):
            cooldowns[lvl] = data.get("cooldown")

        return {
            "champion": champ["name"],
            "skill_name": skill["name"],
            "skill_key": skill_key.upper(),
            "base_cooldown": skill.get("base_cooldown"),
            "cooldowns_by_level": cooldowns,
        }

    def get_champion_base_stats(self, champion_name: str) -> Dict[str, Any]:
        """Get base stats for a champion."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        return {
            "champion": champ["name"],
            "title": champ.get("title", ""),
            "base_stats": champ.get("base_stats", {}),
        }

    def get_specific_stat(
        self, champion_name: str, stat_name: str
    ) -> Dict[str, Any]:
        """Get a specific base stat for a champion."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        base_stats = champ.get("base_stats", {})

        # Normalize stat name
        stat_mapping = {
            "health": "health",
            "hp": "health",
            "mana": "mana",
            "mp": "mana",
            "armor": "armor",
            "ar": "armor",
            "magic_resist": "magic_resist",
            "mr": "magic_resist",
            "magic resist": "magic_resist",
            "attack_damage": "attack_damage",
            "ad": "attack_damage",
            "attack damage": "attack_damage",
            "attack_speed": "attack_speed",
            "as": "attack_speed",
            "attack speed": "attack_speed",
            "movement_speed": "movement_speed",
            "ms": "movement_speed",
            "move speed": "movement_speed",
            "movement speed": "movement_speed",
            "attack_range": "attack_range",
            "range": "attack_range",
            "attack range": "attack_range",
        }

        normalized_stat = stat_mapping.get(stat_name.lower(), stat_name.lower())
        value = base_stats.get(normalized_stat)

        if value is None:
            return {
                "error": f"Stat '{stat_name}' not found for {champ['name']}",
                "available_stats": list(base_stats.keys()),
            }

        return {
            "champion": champ["name"],
            "stat": normalized_stat,
            "value": value,
        }

    def get_champion_info(self, champion_name: str) -> Dict[str, Any]:
        """Get general information about a champion."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        # Get skill names
        skills_summary = {}
        for key, skill in champ.get("skills", {}).items():
            skills_summary[key] = skill.get("name", key)

        return {
            "champion": champ["name"],
            "title": champ.get("title", ""),
            "hero_type": champ.get("hero_type"),
            "damage_type": champ.get("damage_type"),
            "attack_type": champ.get("attack_type"),
            "is_ranged": champ.get("is_ranged"),
            "complexity": champ.get("complexity"),
            "roles": champ.get("roles", []),
            "lanes": champ.get("lanes", []),
            "skills": skills_summary,
            "base_stats": champ.get("base_stats", {}),
        }

    def get_champion_stats_at_level(
        self, champion_name: str, char_level: int
    ) -> Dict[str, Any]:
        """Calculate champion stats at a specific character level."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        if char_level < 1 or char_level > 18:
            return {"error": "Character level must be between 1 and 18"}

        base = champ.get("base_stats", {})
        growth = champ.get("stat_growth", {})

        # LoL stat formula: base + growth * (level - 1) * (0.7025 + 0.0175 * (level - 1))
        def calc_stat(base_val: Optional[float], growth_val: Optional[float], level: int) -> Optional[float]:
            if base_val is None:
                return None
            if growth_val is None:
                return base_val
            return base_val + growth_val * (level - 1) * (0.7025 + 0.0175 * (level - 1))

        calculated = {}
        stat_growth_mapping = {
            "health": "health_per_level",
            "mana": "mana_per_level",
            "armor": "armor_per_level",
            "attack_damage": "attack_damage_per_level",
        }

        for stat, growth_key in stat_growth_mapping.items():
            base_val = base.get(stat)
            growth_val = growth.get(growth_key)
            calc_val = calc_stat(base_val, growth_val, char_level)
            if calc_val is not None:
                calculated[stat] = round(calc_val, 1)

        # Add non-scaling stats
        for stat in ["attack_speed", "movement_speed", "attack_range"]:
            if base.get(stat):
                calculated[stat] = base[stat]

        return {
            "champion": champ["name"],
            "level": char_level,
            "stats": calculated,
        }

    def compare_champions(
        self, champion_names: List[str], stat_name: str
    ) -> Dict[str, Any]:
        """Compare a stat between multiple champions."""
        results = []

        # Normalize stat name
        stat_mapping = {
            "health": "health",
            "hp": "health",
            "mana": "mana",
            "armor": "armor",
            "magic_resist": "magic_resist",
            "mr": "magic_resist",
            "attack_damage": "attack_damage",
            "ad": "attack_damage",
            "attack_speed": "attack_speed",
            "as": "attack_speed",
            "movement_speed": "movement_speed",
            "ms": "movement_speed",
            "attack_range": "attack_range",
            "range": "attack_range",
        }

        normalized_stat = stat_mapping.get(stat_name.lower() if stat_name else "", stat_name.lower() if stat_name else "attack_damage")

        for name in champion_names:
            champ = self.find_champion(name)
            if champ:
                value = champ.get("base_stats", {}).get(normalized_stat)
                results.append({
                    "champion": champ["name"],
                    "stat": normalized_stat,
                    "value": value,
                })
            else:
                results.append({
                    "champion": name,
                    "stat": normalized_stat,
                    "value": None,
                    "error": "Champion not found",
                })

        # Sort by value (highest first)
        results.sort(key=lambda x: x.get("value") or 0, reverse=True)

        return {
            "comparison": results,
            "stat": normalized_stat,
            "winner": results[0]["champion"] if results and results[0].get("value") else None,
        }

    def get_champions_by_role(self, role: str) -> Dict[str, Any]:
        """Get all champions that play a specific role."""
        # Normalize role
        role_mapping = {
            "assassin": "AssassinRole",
            "mage": "MageRole",
            "tank": "TankRole",
            "support": "SupportRole",
            "carry": "CarryRole",
            "adc": "CarryRole",
            "warrior": "WarriorRole",
            "fighter": "WarriorRole",
            "bruiser": "WarriorRole",
        }

        normalized_role = role_mapping.get(role.lower() if role else "", role)
        champions = self.indices.get("by_role", {}).get(normalized_role, [])

        # Get actual names
        champion_names = []
        for key in champions:
            champ = self.champions.get(key)
            if champ:
                champion_names.append(champ["name"])

        return {
            "role": normalized_role,
            "count": len(champion_names),
            "champions": sorted(champion_names),
        }

    def get_champions_by_lane(self, lane: str) -> Dict[str, Any]:
        """Get all champions that typically play in a specific lane."""
        # Normalize lane
        lane_mapping = {
            "top": "TopLane",
            "mid": "MidLane",
            "middle": "MidLane",
            "bot": "BottomLane",
            "bottom": "BottomLane",
            "adc": "BottomLane",
            "jungle": "Jungle",
            "jg": "Jungle",
        }

        normalized_lane = lane_mapping.get(lane.lower() if lane else "", lane)
        champions = self.indices.get("by_lane", {}).get(normalized_lane, [])

        # Get actual names
        champion_names = []
        for key in champions:
            champ = self.champions.get(key)
            if champ:
                champion_names.append(champ["name"])

        return {
            "lane": normalized_lane,
            "count": len(champion_names),
            "champions": sorted(champion_names),
        }

    def list_champion_skills(self, champion_name: str) -> Dict[str, Any]:
        """List all skills for a champion."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        skills = []
        for key in ["P", "Q", "W", "E", "R"]:
            skill = champ.get("skills", {}).get(key)
            if skill:
                skills.append({
                    "key": key,
                    "name": skill.get("name", key),
                    "types": skill.get("types", []),
                    "damage_type": skill.get("damage_type"),
                })

        return {
            "champion": champ["name"],
            "skills": skills,
        }

    def _format_champion_names(self, name_list: List[str]) -> List[str]:
        """Convert internal names (like 'Nunu_and_Willump') to display names."""
        formatted = []
        for name in name_list:
            # Try to find the champion and get their display name
            champ = self.find_champion(name)
            if champ:
                formatted.append(champ["name"])
            else:
                # Fallback: convert underscore names to spaces
                formatted.append(name.replace("_", " "))
        return formatted

    def get_counters(self, champion_name: str, direction: str = "countered_by") -> Dict[str, Any]:
        """Get counter information for a champion.

        Args:
            champion_name: The champion to query
            direction: 'countered_by' for who counters this champion,
                      'counters' for who this champion counters
        """
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        if direction == "counters":
            # Who does this champion counter?
            hard_counters = self._format_champion_names(champ.get("hard_counters", []))
            counters = self._format_champion_names(champ.get("counters", []))
            return {
                "champion": champ["name"],
                "query_type": "who_this_champion_counters",
                "hard_counters": hard_counters,
                "counters": counters,
                "total": len(hard_counters) + len(counters),
            }
        else:
            # Who counters this champion?
            hard_countered_by = self._format_champion_names(champ.get("hard_countered_by", []))
            countered_by = self._format_champion_names(champ.get("countered_by", []))
            return {
                "champion": champ["name"],
                "query_type": "who_counters_this_champion",
                "hard_countered_by": hard_countered_by,
                "countered_by": countered_by,
                "total": len(hard_countered_by) + len(countered_by),
            }

    def get_synergies(self, champion_name: str) -> Dict[str, Any]:
        """Get synergy information for a champion."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        strong_synergy = self._format_champion_names(champ.get("strong_synergy", []))
        synergy = self._format_champion_names(champ.get("synergy", []))
        weak_synergy = self._format_champion_names(champ.get("weak_synergy", []))

        return {
            "champion": champ["name"],
            "strong_synergy": strong_synergy,
            "synergy": synergy,
            "weak_synergy": weak_synergy,
            "total": len(strong_synergy) + len(synergy) + len(weak_synergy),
        }

    def get_build(self, champion_name: str) -> Dict[str, Any]:
        """Get item build information for a champion."""
        champ = self.find_champion(champion_name)
        if not champ:
            return {"error": f"Champion '{champion_name}' not found"}

        # Format item names (replace underscores with spaces)
        def format_items(items: List[str]) -> List[str]:
            return [item.replace("_", " ").replace("s ", "'s ") for item in items]

        core_items = format_items(champ.get("core_items", []))
        recommended_items = format_items(champ.get("recommended_items", []))
        situational_items = format_items(champ.get("situational_items", []))

        return {
            "champion": champ["name"],
            "core_items": core_items,
            "recommended_items": recommended_items,
            "situational_items": situational_items,
        }

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for lookup."""
        if not name:
            return ""
        return name.lower().strip().replace(" ", "_").replace("'", "").replace("-", "_")

    def find_item(self, name: str) -> Optional[Dict[str, Any]]:
        """Find an item by name."""
        if not name:
            return None

        normalized = self._normalize_name(name)

        # Direct lookup
        if normalized in self.items:
            return self.items[normalized]

        # Try fuzzy matching
        for key, item in self.items.items():
            if normalized in key or key in normalized:
                return item
            if item.get("name", "").lower() == name.lower():
                return item

        return None

    def find_monster(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a monster by name."""
        if not name:
            return None

        normalized = self._normalize_name(name)

        # Direct lookup
        if normalized in self.monsters:
            return self.monsters[normalized]

        # Try fuzzy matching
        for key, monster in self.monsters.items():
            if normalized in key or key in normalized:
                return monster
            if monster.get("name", "").lower() == name.lower():
                return monster

        return None

    def find_turret(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a turret by name."""
        if not name:
            return None

        normalized = self._normalize_name(name)

        # Direct lookup
        if normalized in self.turrets:
            return self.turrets[normalized]

        # Try fuzzy matching
        for key, turret in self.turrets.items():
            if normalized in key or key in normalized:
                return turret
            if turret.get("name", "").lower() == name.lower():
                return turret

        return None

    def get_item_info(self, item_name: str) -> Dict[str, Any]:
        """Get information about an item."""
        item = self.find_item(item_name)
        if not item:
            # List some available items
            available = list(self.items.keys())[:10]
            return {
                "error": f"Item '{item_name}' not found",
                "available_items_sample": [self.items[k]["name"] for k in available],
            }

        return {
            "name": item["name"],
            "item_type": item.get("item_type"),
            "gold_cost": item.get("gold_cost"),
            "stats": item.get("stats", {}),
            "build_path": item.get("build_path", []),
            "description": item.get("description"),
            "effect_types": item.get("effect_types", []),
            "unique_passive": item.get("unique_passive"),
        }

    def get_monster_info(self, monster_name: str) -> Dict[str, Any]:
        """Get information about a jungle monster."""
        monster = self.find_monster(monster_name)
        if not monster:
            # List available monsters
            available = list(self.monsters.keys())
            return {
                "error": f"Monster '{monster_name}' not found",
                "available_monsters": [self.monsters[k]["name"] for k in available],
            }

        return {
            "name": monster["name"],
            "monster_type": monster.get("monster_type"),
            "health": monster.get("health"),
            "attack_range": monster.get("attack_range"),
            "stats": monster.get("stats", {}),
            "info": monster.get("info", []),
        }

    def get_turret_info(self, turret_name: str) -> Dict[str, Any]:
        """Get information about a turret type."""
        turret = self.find_turret(turret_name)
        if not turret:
            # List available turrets
            available = list(self.turrets.keys())
            return {
                "error": f"Turret '{turret_name}' not found",
                "available_turrets": [self.turrets[k]["name"] for k in available],
            }

        return {
            "name": turret["name"],
            "health": turret.get("health"),
            "attack_range": turret.get("attack_range"),
            "stats": turret.get("stats", {}),
            "info": turret.get("info", []),
        }

    def list_all_monsters(self) -> Dict[str, Any]:
        """List all jungle monsters."""
        bosses = []
        neutral_monsters = []

        for monster in self.monsters.values():
            if monster.get("monster_type") == "Boss":
                bosses.append(monster["name"])
            else:
                neutral_monsters.append(monster["name"])

        return {
            "bosses": sorted(bosses),
            "neutral_monsters": sorted(neutral_monsters),
            "total": len(self.monsters),
        }

    def list_all_turrets(self) -> Dict[str, Any]:
        """List all turret types."""
        turret_names = [t["name"] for t in self.turrets.values()]
        return {
            "turrets": sorted(turret_names),
            "total": len(self.turrets),
        }


def dispatch_query(retriever: DataRetriever, intent: Dict[str, Any]) -> Dict[str, Any]:
    """Route to appropriate retriever method based on classified intent."""
    intent_type = intent.get("intent", "UNKNOWN")

    if intent_type == "SKILL_DAMAGE_AT_LEVEL":
        return retriever.get_skill_damage_at_level(
            intent.get("champion_name", ""),
            intent.get("skill_key", "Q"),
            intent.get("skill_level", 1),
        )

    elif intent_type == "SKILL_INFO":
        return retriever.get_skill_info(
            intent.get("champion_name", ""),
            intent.get("skill_key", "Q"),
        )

    elif intent_type == "SKILL_COOLDOWN":
        return retriever.get_skill_cooldown(
            intent.get("champion_name", ""),
            intent.get("skill_key", "R"),
            intent.get("skill_level"),
        )

    elif intent_type == "SKILL_MANA_COST":
        skill_info = retriever.get_skill_info(
            intent.get("champion_name", ""),
            intent.get("skill_key", "Q"),
        )
        # Extract just mana cost info
        if "error" not in skill_info:
            return {
                "champion": skill_info["champion"],
                "skill_name": skill_info["skill_name"],
                "skill_key": skill_info["skill_key"],
                "cost_type": skill_info.get("cost_type"),
                "base_cost": skill_info.get("base_cost"),
                "costs_by_level": [l.get("mana_cost") for l in skill_info.get("levels", [])],
            }
        return skill_info

    elif intent_type == "CHAMPION_BASE_STATS":
        stat_name = intent.get("stat_name")
        if stat_name:
            return retriever.get_specific_stat(
                intent.get("champion_name", ""),
                stat_name,
            )
        return retriever.get_champion_base_stats(intent.get("champion_name", ""))

    elif intent_type == "CHAMPION_INFO":
        return retriever.get_champion_info(intent.get("champion_name", ""))

    elif intent_type == "CHAMPION_STATS_AT_LEVEL":
        return retriever.get_champion_stats_at_level(
            intent.get("champion_name", ""),
            intent.get("character_level", 1),
        )

    elif intent_type == "CHAMPION_COMPARISON":
        return retriever.compare_champions(
            intent.get("comparison_champions", []),
            intent.get("stat_name", "attack_damage"),
        )

    elif intent_type == "ROLE_QUERY":
        return retriever.get_champions_by_role(intent.get("role", ""))

    elif intent_type == "LANE_QUERY":
        return retriever.get_champions_by_lane(intent.get("lane", ""))

    elif intent_type == "LIST_SKILLS":
        return retriever.list_champion_skills(intent.get("champion_name", ""))

    elif intent_type == "COUNTER_QUERY":
        direction = intent.get("counter_direction", "countered_by")
        return retriever.get_counters(
            intent.get("champion_name", ""),
            direction,
        )

    elif intent_type == "SYNERGY_QUERY":
        return retriever.get_synergies(intent.get("champion_name", ""))

    elif intent_type == "BUILD_QUERY":
        return retriever.get_build(intent.get("champion_name", ""))

    elif intent_type == "ITEM_INFO":
        item_name = intent.get("item_name", "")
        if item_name:
            return retriever.get_item_info(item_name)
        return {"error": "No item name provided"}

    elif intent_type == "MONSTER_INFO":
        monster_name = intent.get("monster_name", "")
        if monster_name:
            return retriever.get_monster_info(monster_name)
        # If no specific monster, list all
        return retriever.list_all_monsters()

    elif intent_type == "TURRET_INFO":
        turret_name = intent.get("turret_name", "")
        if turret_name:
            return retriever.get_turret_info(turret_name)
        # If no specific turret, list all
        return retriever.list_all_turrets()

    # ========== SEMANTIC QUERIES ==========

    elif intent_type == "MULTI_PROPERTY_FILTER":
        engine = get_semantic_engine()
        engine.clear_query_log()  # Clear previous queries
        results = engine.multi_criteria_champion_search(
            roles=[intent.get("role")] if intent.get("role") else None,
            lanes=[intent.get("lane")] if intent.get("lane") else None,
            cc_types=intent.get("cc_types"),
            effects=intent.get("ability_effects"),
            playstyles=intent.get("playstyles"),
            power_curves=[intent.get("power_curve")] if intent.get("power_curve") else None,
            win_conditions=[intent.get("win_condition")] if intent.get("win_condition") else None,
        )
        return {
            "query_type": "multi_property_filter",
            "criteria": {
                "roles": intent.get("role"),
                "lanes": intent.get("lane"),
                "cc_types": intent.get("cc_types"),
                "ability_effects": intent.get("ability_effects"),
                "playstyles": intent.get("playstyles"),
                "power_curve": intent.get("power_curve"),
                "win_condition": intent.get("win_condition"),
            },
            "champions": results,
            "count": len(results),
            "sparql_queries": engine.get_last_queries(),
        }

    elif intent_type == "CHAMPION_BY_CC":
        engine = get_semantic_engine()
        engine.clear_query_log()
        cc_types = intent.get("cc_types", [])
        if not cc_types:
            return {"error": "No CC type specified"}
        results = engine.get_champions_by_cc_type(cc_types)
        return {
            "query_type": "champions_by_cc",
            "cc_types": cc_types,
            "champions": results,
            "count": len(results),
            "sparql_queries": engine.get_last_queries(),
        }

    elif intent_type == "CHAMPION_BY_EFFECT":
        engine = get_semantic_engine()
        engine.clear_query_log()
        effects = intent.get("ability_effects", [])
        if not effects:
            return {"error": "No ability effect specified"}
        results = engine.get_champions_by_effects(effects)
        return {
            "query_type": "champions_by_effect",
            "ability_effects": effects,
            "champions": results,
            "count": len(results),
            "sparql_queries": engine.get_last_queries(),
        }

    elif intent_type == "CHAMPION_BY_PLAYSTYLE":
        engine = get_semantic_engine()
        engine.clear_query_log()
        playstyles = intent.get("playstyles", [])
        if not playstyles:
            return {"error": "No playstyle specified"}
        results = engine.get_champions_by_playstyle(playstyles)
        return {
            "query_type": "champions_by_playstyle",
            "playstyles": playstyles,
            "champions": results,
            "count": len(results),
            "sparql_queries": engine.get_last_queries(),
        }

    elif intent_type == "CHAMPION_BY_POWER_CURVE":
        engine = get_semantic_engine()
        engine.clear_query_log()
        power_curve = intent.get("power_curve")
        if not power_curve:
            return {"error": "No power curve specified (EarlyGame, MidGame, or LateGame)"}
        results = engine.get_champions_by_power_curve(power_curve)
        return {
            "query_type": "champions_by_power_curve",
            "power_curve": power_curve,
            "champions": results,
            "count": len(results),
            "sparql_queries": engine.get_last_queries(),
        }

    elif intent_type == "CHAMPION_BY_WIN_CONDITION":
        engine = get_semantic_engine()
        engine.clear_query_log()
        win_condition = intent.get("win_condition")
        if not win_condition:
            return {"error": "No win condition specified (Teamfight, Splitpush, Pick, Siege, Objective)"}
        results = engine.get_champions_by_win_condition(win_condition)
        return {
            "query_type": "champions_by_win_condition",
            "win_condition": win_condition,
            "champions": results,
            "count": len(results),
            "sparql_queries": engine.get_last_queries(),
        }

    elif intent_type == "CHAMPION_SEMANTIC_PROFILE":
        engine = get_semantic_engine()
        engine.clear_query_log()
        champion_name = intent.get("champion_name", "")
        if not champion_name:
            return {"error": "No champion specified"}
        # Try to find proper champion name
        champ = retriever.find_champion(champion_name)
        if champ:
            champion_name = champ["name"]
        profile = engine.get_champion_semantic_profile(champion_name)
        return {
            "query_type": "semantic_profile",
            "profile": profile,
            "sparql_queries": engine.get_last_queries(),
        }

    elif intent_type == "TEAM_COUNTER_ANALYSIS":
        engine = get_semantic_engine()
        engine.clear_query_log()
        enemy_champions = intent.get("enemy_champions", [])
        if not enemy_champions:
            return {"error": "No enemy champions specified"}
        # Normalize champion names
        normalized_enemies = []
        for name in enemy_champions:
            champ = retriever.find_champion(name)
            if champ:
                normalized_enemies.append(champ["name"])
            else:
                normalized_enemies.append(name)
        counter_coverage = engine.get_team_counter_coverage(normalized_enemies)
        # Get top recommendations
        top_picks = []
        for champ, countered in list(counter_coverage.items())[:10]:
            top_picks.append({
                "champion": champ,
                "counters": countered,
                "counter_count": len(countered),
            })
        return {
            "query_type": "team_counter_analysis",
            "enemy_team": normalized_enemies,
            "recommended_picks": top_picks,
            "total_options": len(counter_coverage),
            "sparql_queries": engine.get_last_queries(),
        }

    elif intent_type == "TEAM_SYNERGY_ANALYSIS":
        engine = get_semantic_engine()
        engine.clear_query_log()
        team_champions = intent.get("team_champions", [])
        if not team_champions:
            return {"error": "No team champions specified"}
        # Normalize champion names
        normalized_team = []
        for name in team_champions:
            champ = retriever.find_champion(name)
            if champ:
                normalized_team.append(champ["name"])
            else:
                normalized_team.append(name)
        synergy_data = engine.get_team_synergy_score(normalized_team)
        return {
            "query_type": "team_synergy_analysis",
            "team": normalized_team,
            "synergy_pairs": synergy_data["synergy_pairs"],
            "total_score": synergy_data["total_score"],
            "max_possible": synergy_data["max_possible"],
            "synergy_rating": "Strong" if synergy_data["total_score"] > synergy_data["max_possible"] * 0.5 else "Moderate" if synergy_data["total_score"] > synergy_data["max_possible"] * 0.25 else "Weak",
            "sparql_queries": engine.get_last_queries(),
        }

    elif intent_type == "SNAPSHOT_ANALYSIS":
        analyzer = get_snapshot_analyzer(retriever)
        analysis_type = intent.get("snapshot_analysis_type", "full")
        game_index = intent.get("game_index", 0)  # Default to first game

        snapshot = analyzer.get_snapshot(game_index)
        if not snapshot:
            return {"error": "No game snapshot available. Please ensure game_snapshots.json exists."}

        if analysis_type == "items":
            return {
                "query_type": "snapshot_item_analysis",
                "game_index": game_index,
                "analysis": analyzer.analyze_item_recommendations(snapshot),
            }
        elif analysis_type == "counters":
            return {
                "query_type": "snapshot_counter_analysis",
                "game_index": game_index,
                "analysis": analyzer.analyze_counter_strategies(snapshot),
            }
        elif analysis_type == "game_state":
            return {
                "query_type": "snapshot_game_state_analysis",
                "game_index": game_index,
                "analysis": analyzer.analyze_game_state(snapshot),
            }
        else:  # full analysis
            return {
                "query_type": "snapshot_full_analysis",
                "game_index": game_index,
                "analysis": analyzer.full_analysis(snapshot),
            }

    elif intent_type == "GET_AVAILABLE_GAMES":
        # Special intent to get list of available games for UI
        analyzer = get_snapshot_analyzer(retriever)
        return {
            "query_type": "available_games",
            "games": analyzer.get_available_games(),
            "total_count": analyzer.get_snapshot_count(),
        }

    else:
        return {
            "error": "Could not understand the query. Try asking about champion stats, skill damage, counters, synergies, builds, items, monsters, or turrets. You can also ask semantic questions like 'tanks with stuns', 'late game champions', or 'who counters this enemy team?'",
            "intent_detected": intent_type,
        }

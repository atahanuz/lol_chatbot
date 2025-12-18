"""
Snapshot Analysis Module for LoL Chatbot

Analyzes game snapshots at minute 10 and provides:
- Item build recommendations based on current items, gold, and enemy composition
- Counter strategies against enemy champions
- Game state analysis (gold diff, level advantages)
- Lane matchup analysis
- Team synergy and win condition assessment
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from config import GAME_SNAPSHOTS_PATH

SNAPSHOT_FILE = GAME_SNAPSHOTS_PATH

# Role position mapping based on participant_id
ROLE_POSITIONS = {
    1: "Top", 2: "Jungle", 3: "Mid", 4: "ADC", 5: "Support",
    6: "Top", 7: "Jungle", 8: "Mid", 9: "ADC", 10: "Support"
}


class SnapshotAnalyzer:
    """Analyzes game snapshots and provides detailed recommendations for the user (participant_id: 1)."""

    def __init__(self, data_retriever):
        """
        Initialize with a DataRetriever instance for accessing game data.

        Args:
            data_retriever: DataRetriever instance with champions, items, counters, builds
        """
        self.retriever = data_retriever
        self.snapshots = self._load_snapshots()

    def _load_snapshots(self) -> List[Dict[str, Any]]:
        """Load game snapshots from JSON file."""
        snapshot_path = Path(__file__).parent / SNAPSHOT_FILE
        if snapshot_path.exists():
            with open(snapshot_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Handle both list of snapshots and single snapshot
                if isinstance(data, list):
                    return data
                return [data]
        return []

    def get_snapshot(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """Get a game snapshot by index (defaults to first)."""
        if self.snapshots and 0 <= index < len(self.snapshots):
            return self.snapshots[index]
        return self.snapshots[0] if self.snapshots else None

    def get_available_games(self) -> List[Dict[str, Any]]:
        """Get list of available games with identifying info for UI selection."""
        games = []
        for i, snapshot in enumerate(self.snapshots):
            user = None
            for player in snapshot.get("players", []):
                if player.get("participant_id") == 1:
                    user = player
                    break

            games.append({
                "index": i,
                "match_id": snapshot.get("match_id", f"Game {i+1}"),
                "champion": user.get("champion", "Unknown") if user else "Unknown",
                "team": user.get("team", "Unknown") if user else "Unknown",
                "display_name": f"{user.get('champion', 'Unknown')} - {snapshot.get('match_id', f'Game {i+1}')}" if user else f"Game {i+1}",
            })
        return games

    def get_snapshot_count(self) -> int:
        """Get the number of available snapshots."""
        return len(self.snapshots)

    def get_user_player(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the user's player data (participant_id: 1)."""
        for player in snapshot.get("players", []):
            if player.get("participant_id") == 1:
                return player
        return None

    def get_allies(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get allied players (same team as user, excluding user)."""
        user = self.get_user_player(snapshot)
        if not user:
            return []
        user_team = user.get("team")
        return [
            p
            for p in snapshot.get("players", [])
            if p.get("team") == user_team and p.get("participant_id") != 1
        ]

    def get_enemies(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get enemy players (opposite team from user)."""
        user = self.get_user_player(snapshot)
        if not user:
            return []
        user_team = user.get("team")
        return [p for p in snapshot.get("players", []) if p.get("team") != user_team]

    def _get_lane_opponent(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the user's lane opponent based on position."""
        user = self.get_user_player(snapshot)
        if not user:
            return None

        user_position = ROLE_POSITIONS.get(user.get("participant_id", 1), "Top")
        enemies = self.get_enemies(snapshot)

        for enemy in enemies:
            enemy_position = ROLE_POSITIONS.get(enemy.get("participant_id"), "")
            if enemy_position == user_position:
                return enemy
        return enemies[0] if enemies else None

    def _get_champion_details(self, champion_name: str) -> Dict[str, Any]:
        """Get detailed champion information."""
        info = self.retriever.get_champion_info(champion_name)
        if "error" in info:
            return {"name": champion_name, "roles": [], "damage_type": "Unknown"}
        return info

    def _analyze_player_performance(self, player: Dict[str, Any], minute: int) -> Dict[str, Any]:
        """Analyze a player's performance metrics."""
        cs = player.get("cs", 0)
        gold = player.get("total_gold", 0)
        level = player.get("level", 1)

        cs_per_min = cs / minute if minute > 0 else 0
        gold_per_min = gold / minute if minute > 0 else 0

        # Performance ratings
        if cs_per_min >= 8:
            cs_rating = "Excellent"
        elif cs_per_min >= 6:
            cs_rating = "Good"
        elif cs_per_min >= 4:
            cs_rating = "Average"
        else:
            cs_rating = "Below Average"

        return {
            "cs": cs,
            "cs_per_minute": round(cs_per_min, 1),
            "cs_rating": cs_rating,
            "gold": gold,
            "gold_per_minute": round(gold_per_min, 0),
            "level": level,
        }

    def analyze_item_recommendations(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate detailed item build recommendations.

        Considers:
        - User's current items and components
        - User's available gold
        - User's champion build path
        - Enemy team composition (AP/AD heavy, tanks, threats)
        - Lane opponent's items
        - Game state (ahead/behind)
        """
        user = self.get_user_player(snapshot)
        if not user:
            return {"error": "User player not found in snapshot"}

        champion_name = user.get("champion")
        current_items = user.get("items", [])
        total_gold = user.get("total_gold", 0)
        minute = snapshot.get("minute", 10)

        # Get champion's recommended build
        champion_build = self.retriever.get_build(champion_name)
        if "error" in champion_build:
            champion_build = {
                "core_items": [],
                "recommended_items": [],
                "situational_items": [],
            }

        # Get champion info for damage type context
        champ_info = self._get_champion_details(champion_name)

        # Analyze enemy composition
        enemies = self.get_enemies(snapshot)
        enemy_analysis = self._analyze_enemy_composition(enemies)

        # Get lane opponent info
        lane_opponent = self._get_lane_opponent(snapshot)
        lane_opponent_analysis = None
        if lane_opponent:
            lane_opponent_analysis = {
                "champion": lane_opponent.get("champion"),
                "level": lane_opponent.get("level"),
                "gold": lane_opponent.get("total_gold"),
                "items": lane_opponent.get("items", []),
                "gold_diff": total_gold - lane_opponent.get("total_gold", 0),
            }

        # Estimate available gold
        spent_gold = self._estimate_spent_gold(current_items)
        available_gold = max(0, total_gold - spent_gold)

        # Analyze current build progress
        build_progress = self._analyze_build_progress(current_items, champion_build)

        # Generate detailed item recommendations
        recommendations = self._generate_detailed_item_recommendations(
            champion_build=champion_build,
            current_items=current_items,
            available_gold=available_gold,
            enemy_analysis=enemy_analysis,
            lane_opponent=lane_opponent_analysis,
            champ_info=champ_info,
        )

        # Generate immediate purchase suggestions based on gold
        immediate_buys = self._get_immediate_purchases(available_gold, recommendations, current_items)

        return {
            "champion": champion_name,
            "role": champ_info.get("roles", ["Unknown"])[0] if champ_info.get("roles") else "Unknown",
            "damage_type": champ_info.get("damage_type", "Unknown"),
            "current_items": current_items,
            "total_gold": total_gold,
            "estimated_available_gold": available_gold,
            "build_progress": build_progress,
            "core_items": champion_build.get("core_items", []),
            "recommended_items": champion_build.get("recommended_items", []),
            "situational_items": champion_build.get("situational_items", []),
            "next_item_suggestions": recommendations,
            "immediate_purchases": immediate_buys,
            "lane_opponent": lane_opponent_analysis,
            "enemy_composition": enemy_analysis,
        }

    def _analyze_build_progress(self, current_items: List[str], champion_build: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how far along the user is in their build."""
        core_items = champion_build.get("core_items", [])
        current_lower = [i.lower() for i in current_items]

        completed_core = []
        missing_core = []

        for item in core_items:
            item_lower = item.lower()
            if any(item_lower in ci or ci in item_lower for ci in current_lower):
                completed_core.append(item)
            else:
                missing_core.append(item)

        # Check for boots
        has_boots = any("boots" in i.lower() or "greaves" in i.lower() or "steelcaps" in i.lower()
                       or "treads" in i.lower() or "shoes" in i.lower() for i in current_items)

        # Count completed items (non-component items)
        starter_items = ["doran", "cull", "tear", "dark seal", "long sword", "amplifying tome",
                        "cloth armor", "ruby crystal", "sapphire crystal"]
        completed_items = [i for i in current_items
                         if not any(s in i.lower() for s in starter_items)]

        return {
            "completed_core_items": completed_core,
            "missing_core_items": missing_core,
            "core_completion_percentage": round(len(completed_core) / len(core_items) * 100, 0) if core_items else 0,
            "has_boots": has_boots,
            "total_items": len(current_items),
            "completed_items_count": len(completed_items),
        }

    def _analyze_enemy_composition(
        self, enemies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze enemy team composition in detail."""
        ap_champions = []
        ad_champions = []
        tanks = []
        assassins = []
        healers = []
        threats = []
        cc_champions = []

        for enemy in enemies:
            champ_name = enemy.get("champion")
            champ_info = self.retriever.get_champion_info(champ_name)

            if "error" not in champ_info:
                damage_type = str(champ_info.get("damage_type", ""))
                hero_type = str(champ_info.get("hero_type", ""))
                roles = champ_info.get("roles", [])

                # Categorize by damage type
                if "Magic" in damage_type or "Mage" in hero_type:
                    ap_champions.append(champ_name)
                elif "Physical" in damage_type or "Attack" in damage_type:
                    ad_champions.append(champ_name)

                # Identify tanks
                if "Tank" in hero_type or "TankRole" in str(roles):
                    tanks.append(champ_name)

                # Identify assassins
                if "Assassin" in hero_type or "AssassinRole" in str(roles):
                    assassins.append(champ_name)

            # Identify fed enemies (threats) based on gold/level
            threat_level = None
            if enemy.get("level", 0) >= 10 or enemy.get("total_gold", 0) > 4500:
                threat_level = "High"
            elif enemy.get("level", 0) >= 8 or enemy.get("total_gold", 0) > 3500:
                threat_level = "Medium"

            if threat_level:
                threats.append({
                    "champion": champ_name,
                    "level": enemy.get("level"),
                    "gold": enemy.get("total_gold"),
                    "items": enemy.get("items", []),
                    "threat_level": threat_level,
                    "position": ROLE_POSITIONS.get(enemy.get("participant_id"), "Unknown"),
                })

        # Determine team damage profile
        total_champs = len(enemies)
        ap_ratio = len(ap_champions) / total_champs if total_champs > 0 else 0
        ad_ratio = len(ad_champions) / total_champs if total_champs > 0 else 0

        if ap_ratio >= 0.6:
            damage_profile = "AP Heavy - Consider Magic Resist"
        elif ad_ratio >= 0.6:
            damage_profile = "AD Heavy - Consider Armor"
        else:
            damage_profile = "Mixed Damage - Build balanced resistances"

        return {
            "damage_profile": damage_profile,
            "ap_heavy": len(ap_champions) >= 3,
            "ad_heavy": len(ad_champions) >= 3,
            "ap_champions": ap_champions,
            "ad_champions": ad_champions,
            "tanks": tanks,
            "assassins": assassins,
            "has_assassins": len(assassins) > 0,
            "has_tanks": len(tanks) > 0,
            "threats": sorted(threats, key=lambda x: x.get("gold", 0), reverse=True),
            "primary_threat": threats[0] if threats else None,
        }

    def _estimate_spent_gold(self, items: List[str]) -> int:
        """Estimate total gold spent on current items."""
        total = 0
        for item_name in items:
            item_info = self.retriever.get_item_info(item_name)
            if "error" not in item_info:
                gold_cost = item_info.get("gold_cost") or item_info.get("total_cost", 0)
                if gold_cost:
                    total += gold_cost
        return total

    def _generate_detailed_item_recommendations(
        self,
        champion_build: Dict[str, Any],
        current_items: List[str],
        available_gold: int,
        enemy_analysis: Dict[str, Any],
        lane_opponent: Optional[Dict[str, Any]],
        champ_info: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate detailed prioritized item recommendations."""
        recommendations = []
        current_items_lower = [i.lower() for i in current_items]

        # Check if we need boots
        has_boots = any("boots" in i.lower() or "greaves" in i.lower() or "steelcaps" in i.lower()
                       or "treads" in i.lower() or "shoes" in i.lower() for i in current_items)

        # Priority 0: Boots (if not owned)
        if not has_boots:
            # Recommend boots based on enemy comp
            if enemy_analysis.get("ap_heavy"):
                boot_choice = "Mercury's Treads"
                boot_reason = "Magic resist and tenacity against AP-heavy team"
            elif enemy_analysis.get("ad_heavy") or enemy_analysis.get("has_assassins"):
                boot_choice = "Plated Steelcaps"
                boot_reason = "Armor against AD-heavy/assassin team"
            else:
                boot_choice = "Ionian Boots of Lucidity"
                boot_reason = "Ability haste for faster cooldowns"

            recommendations.append({
                "item": boot_choice,
                "priority": "essential",
                "gold_cost": 1100,
                "reason": boot_reason,
                "timing": "Buy on next back",
            })

        # Priority 1: Core items not yet purchased
        for item in champion_build.get("core_items", []):
            item_lower = item.lower()
            if not any(item_lower in ci or ci in item_lower for ci in current_items_lower):
                item_info = self.retriever.get_item_info(item)
                gold_cost = 0
                stats = {}
                if "error" not in item_info:
                    gold_cost = item_info.get("gold_cost") or item_info.get("total_cost", 0)
                    stats = item_info.get("stats", {})

                recommendations.append({
                    "item": item,
                    "priority": "core",
                    "gold_cost": gold_cost,
                    "stats": stats,
                    "reason": f"Core build item - essential for {champ_info.get('name', 'your champion')}'s kit",
                    "timing": "Rush this item",
                })

        # Priority 2: Counter items based on threats
        primary_threat = enemy_analysis.get("primary_threat")
        if primary_threat:
            threat_name = primary_threat.get("champion")
            threat_info = self._get_champion_details(threat_name)
            threat_damage = str(threat_info.get("damage_type", ""))

            if "Magic" in threat_damage and not any("spirit" in i.lower() or "force of nature" in i.lower()
                                                     or "maw" in i.lower() for i in current_items_lower):
                recommendations.append({
                    "item": "Spirit Visage" if "heal" in str(champ_info).lower() else "Force of Nature",
                    "priority": "situational",
                    "gold_cost": 2900,
                    "reason": f"Magic resist to survive {threat_name} (fed with {primary_threat.get('gold')} gold)",
                    "timing": "Build after core if they're a problem",
                })
            elif "Physical" in threat_damage and not any("thornmail" in i.lower() or "randuin" in i.lower()
                                                          or "dead man" in i.lower() for i in current_items_lower):
                recommendations.append({
                    "item": "Randuin's Omen" if threat_info.get("is_ranged") else "Thornmail",
                    "priority": "situational",
                    "gold_cost": 2700,
                    "reason": f"Armor to survive {threat_name} (fed with {primary_threat.get('gold')} gold)",
                    "timing": "Build after core if they're a problem",
                })

        # Priority 3: Anti-heal if needed
        healing_champs = ["Aatrox", "Vladimir", "Sylas", "Swain", "Soraka", "Yuumi", "Sona",
                         "Nami", "Dr. Mundo", "Warwick", "Fiddlesticks", "Illaoi"]
        enemy_names = [e.get("champion", "") for e in enemy_analysis.get("threats", [])]
        needs_antiheal = any(h.lower() in str(enemy_names).lower() for h in healing_champs)

        if needs_antiheal and not any("thornmail" in i.lower() or "mortal" in i.lower() or
                                       "oblivion" in i.lower() or "putrifier" in i.lower()
                                       for i in current_items_lower):
            antiheal_item = "Thornmail" if "Tank" in str(champ_info.get("roles", [])) else "Mortal Reminder"
            recommendations.append({
                "item": antiheal_item,
                "priority": "situational",
                "gold_cost": 2700,
                "reason": "Anti-heal to reduce enemy healing",
                "timing": "Important against healing champions",
            })

        # Priority 4: Defensive items based on enemy comp
        if enemy_analysis.get("ap_heavy") and not any("spirit" in i.lower() or "force" in i.lower()
                                                       or "maw" in i.lower() for i in current_items_lower):
            mr_items = [
                {"item": "Spirit Visage", "gold_cost": 2900, "reason": "Increased healing + MR"},
                {"item": "Force of Nature", "gold_cost": 2900, "reason": "Movement speed + high MR"},
                {"item": "Maw of Malmortius", "gold_cost": 2800, "reason": "AD + MR shield"},
            ]
            for mr_item in mr_items:
                mr_item["priority"] = "defensive"
                mr_item["timing"] = f"Needed against {', '.join(enemy_analysis.get('ap_champions', [])[:2])}"
            recommendations.extend(mr_items[:2])

        if enemy_analysis.get("ad_heavy") and not any("thornmail" in i.lower() or "randuin" in i.lower()
                                                       or "dead man" in i.lower() for i in current_items_lower):
            armor_items = [
                {"item": "Thornmail", "gold_cost": 2700, "reason": "Armor + anti-heal + damage reflection"},
                {"item": "Randuin's Omen", "gold_cost": 2700, "reason": "Armor + anti-crit + slow"},
                {"item": "Dead Man's Plate", "gold_cost": 2900, "reason": "Armor + movement speed"},
            ]
            for armor_item in armor_items:
                armor_item["priority"] = "defensive"
                armor_item["timing"] = f"Needed against {', '.join(enemy_analysis.get('ad_champions', [])[:2])}"
            recommendations.extend(armor_items[:2])

        # Remove duplicates and sort by priority
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec["item"] not in seen:
                seen.add(rec["item"])
                unique_recommendations.append(rec)

        priority_order = {"essential": 0, "core": 1, "situational": 2, "defensive": 3}
        unique_recommendations.sort(
            key=lambda x: (priority_order.get(x["priority"], 4), x.get("gold_cost", 9999))
        )

        return unique_recommendations[:8]

    def _get_immediate_purchases(self, available_gold: int, recommendations: List[Dict[str, Any]],
                                  current_items: List[str]) -> List[Dict[str, Any]]:
        """Get items that can be purchased immediately with available gold."""
        immediate = []

        # Component items that are always useful
        components = [
            {"item": "Long Sword", "gold_cost": 350, "builds_into": "AD items"},
            {"item": "Amplifying Tome", "gold_cost": 435, "builds_into": "AP items"},
            {"item": "Ruby Crystal", "gold_cost": 400, "builds_into": "Health items"},
            {"item": "Cloth Armor", "gold_cost": 300, "builds_into": "Armor items"},
            {"item": "Null-Magic Mantle", "gold_cost": 450, "builds_into": "MR items"},
            {"item": "Boots", "gold_cost": 300, "builds_into": "Upgraded boots"},
            {"item": "Control Ward", "gold_cost": 75, "builds_into": "Vision"},
        ]

        # Check which full items we can afford
        for rec in recommendations:
            if rec.get("gold_cost", 9999) <= available_gold:
                immediate.append({
                    "item": rec["item"],
                    "gold_cost": rec["gold_cost"],
                    "type": "complete",
                    "reason": rec.get("reason", ""),
                })

        # If we can't afford full items, suggest components
        if not immediate or available_gold < 1000:
            current_lower = [i.lower() for i in current_items]
            for comp in components:
                if comp["gold_cost"] <= available_gold and comp["item"].lower() not in current_lower:
                    immediate.append({
                        "item": comp["item"],
                        "gold_cost": comp["gold_cost"],
                        "type": "component",
                        "reason": f"Builds into {comp['builds_into']}",
                    })

        return immediate[:5]

    def analyze_counter_strategies(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze enemy champions and provide detailed counter strategies.

        Provides:
        - Lane matchup analysis
        - Which enemies counter the user
        - Detailed tips for each enemy
        - Team fight positioning advice
        """
        user = self.get_user_player(snapshot)
        if not user:
            return {"error": "User player not found in snapshot"}

        enemies = self.get_enemies(snapshot)
        allies = self.get_allies(snapshot)
        user_champion = user.get("champion")
        user_position = ROLE_POSITIONS.get(user.get("participant_id", 1), "Top")

        # Get user champion details
        user_info = self._get_champion_details(user_champion)

        # Get counter data for user's champion
        user_counters = self.retriever.get_counters(user_champion, "countered_by")

        # Find lane opponent
        lane_opponent = self._get_lane_opponent(snapshot)
        lane_matchup = None
        if lane_opponent:
            lane_matchup = self._analyze_lane_matchup(user, lane_opponent, user_counters)

        # Check which enemies counter the user
        enemies_that_counter_user = []
        hard_countered_by = user_counters.get("hard_countered_by", [])
        countered_by = user_counters.get("countered_by", [])

        for enemy in enemies:
            enemy_name = enemy.get("champion")
            enemy_normalized = enemy_name.lower().replace(" ", "")

            # Check hard counters
            is_hard_counter = False
            is_soft_counter = False
            for counter in hard_countered_by:
                if enemy_normalized in counter.lower().replace(" ", ""):
                    enemies_that_counter_user.append({
                        "champion": enemy_name,
                        "counter_type": "HARD COUNTER",
                        "advice": f"Play very carefully against {enemy_name}. Consider roaming or asking for jungle help."
                    })
                    is_hard_counter = True
                    break

            if not is_hard_counter:
                for counter in countered_by:
                    if enemy_normalized in counter.lower().replace(" ", ""):
                        enemies_that_counter_user.append({
                            "champion": enemy_name,
                            "counter_type": "Soft Counter",
                            "advice": f"{enemy_name} has an advantage. Play around their cooldowns."
                        })
                        is_soft_counter = True
                        break

        # Get detailed strategies for each enemy
        enemy_strategies = []
        for enemy in enemies:
            enemy_name = enemy.get("champion")
            enemy_position = ROLE_POSITIONS.get(enemy.get("participant_id"), "Unknown")
            counter_info = self.retriever.get_counters(enemy_name, "countered_by")
            enemy_info = self._get_champion_details(enemy_name)

            # Check if user counters this enemy
            user_counters_enemy = False
            enemy_hard_countered_by = counter_info.get("hard_countered_by", [])
            enemy_countered_by = counter_info.get("countered_by", [])

            user_normalized = user_champion.lower().replace(" ", "")
            for counter in enemy_hard_countered_by + enemy_countered_by:
                if user_normalized in counter.lower().replace(" ", ""):
                    user_counters_enemy = True
                    break

            # Generate specific tips
            tips = self._generate_enemy_tips(enemy_name, enemy_info, enemy, user_info)

            # Determine threat level
            threat_level = "Low"
            if enemy.get("level", 0) >= 10 or enemy.get("total_gold", 0) > 4500:
                threat_level = "High"
            elif enemy.get("level", 0) >= 8 or enemy.get("total_gold", 0) > 3500:
                threat_level = "Medium"

            enemy_strategies.append({
                "champion": enemy_name,
                "position": enemy_position,
                "level": enemy.get("level"),
                "gold": enemy.get("total_gold"),
                "items": enemy.get("items", []),
                "skills": enemy.get("skills", {}),
                "damage_type": enemy_info.get("damage_type", "Unknown"),
                "threat_level": threat_level,
                "user_counters_them": user_counters_enemy,
                "hard_countered_by": enemy_hard_countered_by[:5],
                "countered_by": enemy_countered_by[:5],
                "tips": tips,
            })

        # Analyze team synergies
        ally_synergies = self._analyze_ally_synergies(user_champion, allies)

        # Generate teamfight advice
        teamfight_advice = self._generate_teamfight_advice(user_info, enemies, allies)

        return {
            "user_champion": user_champion,
            "user_position": user_position,
            "user_damage_type": user_info.get("damage_type", "Unknown"),
            "lane_matchup": lane_matchup,
            "enemies_that_counter_user": enemies_that_counter_user,
            "enemy_strategies": sorted(enemy_strategies, key=lambda x: x.get("gold", 0), reverse=True),
            "ally_synergies": ally_synergies,
            "teamfight_advice": teamfight_advice,
        }

    def _analyze_lane_matchup(self, user: Dict[str, Any], opponent: Dict[str, Any],
                               user_counters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the lane matchup in detail."""
        user_champ = user.get("champion")
        opp_champ = opponent.get("champion")

        gold_diff = user.get("total_gold", 0) - opponent.get("total_gold", 0)
        level_diff = user.get("level", 1) - opponent.get("level", 1)
        cs_diff = user.get("cs", 0) - opponent.get("cs", 0)

        # Check if opponent counters user
        is_countered = False
        counter_severity = None
        for counter in user_counters.get("hard_countered_by", []):
            if opp_champ.lower().replace(" ", "") in counter.lower().replace(" ", ""):
                is_countered = True
                counter_severity = "Hard"
                break
        if not is_countered:
            for counter in user_counters.get("countered_by", []):
                if opp_champ.lower().replace(" ", "") in counter.lower().replace(" ", ""):
                    is_countered = True
                    counter_severity = "Soft"
                    break

        # Determine lane state
        if gold_diff > 1000:
            lane_state = "Winning Hard"
            advice = "You have a significant lead. Zone them from CS and look for kills or roams."
        elif gold_diff > 300:
            lane_state = "Winning"
            advice = "You're ahead. Maintain your lead and deny farm when safe."
        elif gold_diff < -1000:
            lane_state = "Losing Hard"
            advice = "You're significantly behind. Play safe under tower and wait for ganks."
        elif gold_diff < -300:
            lane_state = "Losing"
            advice = "You're behind. Focus on farming safely and avoid trading."
        else:
            lane_state = "Even"
            advice = "Lane is even. Look for favorable trades and jungle assistance."

        if is_countered:
            advice += f" Note: {opp_champ} is a {counter_severity.lower()} counter to you - play extra careful."

        return {
            "opponent": opp_champ,
            "opponent_level": opponent.get("level"),
            "opponent_gold": opponent.get("total_gold"),
            "opponent_items": opponent.get("items", []),
            "gold_difference": gold_diff,
            "level_difference": level_diff,
            "cs_difference": cs_diff,
            "lane_state": lane_state,
            "is_countered": is_countered,
            "counter_severity": counter_severity,
            "advice": advice,
        }

    def _generate_enemy_tips(self, enemy_name: str, enemy_info: Dict[str, Any],
                             enemy_player: Dict[str, Any], user_info: Dict[str, Any]) -> List[str]:
        """Generate specific tips for playing against an enemy champion."""
        tips = []

        damage_type = str(enemy_info.get("damage_type", ""))
        hero_type = str(enemy_info.get("hero_type", ""))

        # Damage type tips
        if "Magic" in damage_type:
            tips.append(f"{enemy_name} deals magic damage - consider Mercury's Treads or MR items")
        elif "Physical" in damage_type:
            tips.append(f"{enemy_name} deals physical damage - consider Plated Steelcaps or armor items")

        # Role-based tips
        if "Assassin" in hero_type:
            tips.append(f"Watch out for {enemy_name}'s burst damage - don't get caught alone")
            tips.append("Stay grouped with your team and ward flanks")
        elif "Tank" in hero_type:
            tips.append(f"{enemy_name} is tanky - focus on kiting and don't waste all cooldowns on them")
            tips.append("Consider armor penetration or magic penetration items")
        elif "Mage" in hero_type:
            tips.append(f"Dodge {enemy_name}'s skillshots - their damage comes from abilities")

        # Fed enemy tips
        if enemy_player.get("total_gold", 0) > 4000:
            tips.append(f"DANGER: {enemy_name} is fed ({enemy_player.get('total_gold')} gold) - don't fight them alone")

        # Level advantage tips
        if enemy_player.get("level", 0) >= 6:
            tips.append(f"{enemy_name} has their ultimate - respect their all-in potential")

        return tips[:4]  # Limit to 4 tips per enemy

    def _analyze_ally_synergies(self, user_champion: str, allies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze synergies with allied champions."""
        synergy_info = self.retriever.get_synergies(user_champion)
        strong_synergies = synergy_info.get("strong_synergy", [])
        synergies = synergy_info.get("synergy", [])

        ally_names = [a.get("champion", "") for a in allies]

        good_synergies = []
        for ally in ally_names:
            ally_normalized = ally.lower().replace(" ", "")
            for strong in strong_synergies:
                if ally_normalized in strong.lower().replace(" ", ""):
                    good_synergies.append({
                        "champion": ally,
                        "synergy_level": "Strong",
                        "advice": f"Great synergy with {ally}! Look for combo opportunities.",
                    })
                    break
            else:
                for syn in synergies:
                    if ally_normalized in syn.lower().replace(" ", ""):
                        good_synergies.append({
                            "champion": ally,
                            "synergy_level": "Good",
                            "advice": f"Good synergy with {ally}. Coordinate your abilities.",
                        })
                        break

        return {
            "allies": [{"champion": a.get("champion"), "level": a.get("level")} for a in allies],
            "synergies": good_synergies,
        }

    def _generate_teamfight_advice(self, user_info: Dict[str, Any], enemies: List[Dict[str, Any]],
                                    allies: List[Dict[str, Any]]) -> List[str]:
        """Generate teamfight positioning and focus advice."""
        advice = []
        hero_type = str(user_info.get("hero_type", ""))
        roles = user_info.get("roles", [])

        # Role-based positioning
        if "Tank" in hero_type or "TankRole" in str(roles):
            advice.append("Position in front of your team to absorb damage and initiate")
            advice.append("Use your CC on enemy carries when they step forward")
        elif "Assassin" in hero_type or "AssassinRole" in str(roles):
            advice.append("Wait for key abilities to be used before going in")
            advice.append("Flank to reach enemy backline - focus the ADC or mid laner")
        elif "Carry" in str(roles) or "Marksman" in str(roles):
            advice.append("Stay behind your frontline and attack the closest safe target")
            advice.append("Don't overextend - your survival is crucial for DPS")
        elif "Mage" in hero_type or "MageRole" in str(roles):
            advice.append("Position safely and land your abilities on grouped enemies")
            advice.append("Save your CC for enemy divers")
        elif "Support" in str(roles):
            advice.append("Protect your carries and peel for them")
            advice.append("Save your key abilities to counter enemy engages")

        # Identify priority targets
        enemy_carries = []
        for enemy in enemies:
            enemy_info = self._get_champion_details(enemy.get("champion", ""))
            if "Carry" in str(enemy_info.get("roles", [])) or "Assassin" in str(enemy_info.get("hero_type", "")):
                enemy_carries.append(enemy.get("champion"))

        if enemy_carries:
            advice.append(f"Priority targets in teamfights: {', '.join(enemy_carries)}")

        return advice[:5]

    def analyze_game_state(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze overall game state in detail.

        Provides:
        - Gold difference analysis
        - Level advantages/disadvantages
        - CS per minute comparison
        - Team composition analysis
        - Objective recommendations
        - Win condition assessment
        """
        user = self.get_user_player(snapshot)
        if not user:
            return {"error": "User player not found in snapshot"}

        enemies = self.get_enemies(snapshot)
        allies = self.get_allies(snapshot)
        minute = snapshot.get("minute", 10)

        # Gold analysis
        gold_diff = snapshot.get("gold_diff", 0)
        user_team = user.get("team")

        # Determine which gold diff applies to user
        if user_team == "Blue":
            team_gold = snapshot.get("blue_team_gold", 0)
            enemy_team_gold = snapshot.get("red_team_gold", 0)
        else:
            team_gold = snapshot.get("red_team_gold", 0)
            enemy_team_gold = snapshot.get("blue_team_gold", 0)
            gold_diff = -gold_diff  # Flip for red team perspective

        # Analyze user performance
        user_performance = self._analyze_player_performance(user, minute)

        # Analyze all players
        ally_performance = [self._analyze_player_performance(a, minute) for a in allies]
        enemy_performance = [self._analyze_player_performance(e, minute) for e in enemies]

        # Level analysis
        user_level = user.get("level", 1)
        avg_enemy_level = (
            sum(e.get("level", 1) for e in enemies) / len(enemies) if enemies else 1
        )
        avg_ally_level = (
            sum(a.get("level", 1) for a in allies) / len(allies) if allies else user_level
        )
        team_avg_level = (user_level + sum(a.get("level", 1) for a in allies)) / (1 + len(allies))

        # CS comparison with lane opponent
        lane_opponent = self._get_lane_opponent(snapshot)
        lane_cs_diff = user.get("cs", 0) - lane_opponent.get("cs", 0) if lane_opponent else 0

        # Game state assessment
        if gold_diff > 3000:
            gold_assessment = "Significant lead - Look to force objectives and end"
            game_state = "Winning"
        elif gold_diff > 1500:
            gold_assessment = "Good lead - Press your advantage on objectives"
            game_state = "Ahead"
        elif gold_diff > 500:
            gold_assessment = "Slight lead - Continue to build your advantage"
            game_state = "Slightly Ahead"
        elif gold_diff < -3000:
            gold_assessment = "Significantly behind - Stall for late game, avoid fights"
            game_state = "Losing"
        elif gold_diff < -1500:
            gold_assessment = "Behind - Play safe, look for picks, defend objectives"
            game_state = "Behind"
        elif gold_diff < -500:
            gold_assessment = "Slightly behind - Focus on farming and scaling"
            game_state = "Slightly Behind"
        else:
            gold_assessment = "Even game - Focus on objectives and team coordination"
            game_state = "Even"

        # Objective recommendations
        objectives = self._get_objective_recommendations(minute, game_state, user_team)

        # Win condition analysis
        win_conditions = self._analyze_win_conditions(user, allies, enemies, game_state)

        # Power spike analysis
        power_spikes = self._analyze_power_spikes(user, enemies)

        return {
            "minute": minute,
            "game_state": game_state,
            "user": {
                "champion": user.get("champion"),
                "position": ROLE_POSITIONS.get(user.get("participant_id", 1), "Top"),
                "level": user_level,
                "gold": user.get("total_gold"),
                "cs": user.get("cs"),
                "cs_per_minute": user_performance["cs_per_minute"],
                "cs_rating": user_performance["cs_rating"],
                "gold_per_minute": user_performance["gold_per_minute"],
                "items": user.get("items", []),
                "skills": user.get("skills", {}),
                "lane_cs_diff": lane_cs_diff,
            },
            "team_gold": team_gold,
            "enemy_team_gold": enemy_team_gold,
            "team_gold_diff": gold_diff,
            "gold_per_player_diff": round(gold_diff / 5, 0),
            "gold_assessment": gold_assessment,
            "level_comparison": {
                "user_level": user_level,
                "team_avg_level": round(team_avg_level, 1),
                "avg_enemy_level": round(avg_enemy_level, 1),
                "level_advantage": round(team_avg_level - avg_enemy_level, 1),
            },
            "team_composition": {
                "allies": [
                    {
                        "champion": a.get("champion"),
                        "position": ROLE_POSITIONS.get(a.get("participant_id"), "Unknown"),
                        "level": a.get("level"),
                        "gold": a.get("total_gold"),
                        "cs_per_minute": ally_performance[i]["cs_per_minute"],
                    }
                    for i, a in enumerate(allies)
                ],
                "enemies": [
                    {
                        "champion": e.get("champion"),
                        "position": ROLE_POSITIONS.get(e.get("participant_id"), "Unknown"),
                        "level": e.get("level"),
                        "gold": e.get("total_gold"),
                        "cs_per_minute": enemy_performance[i]["cs_per_minute"],
                    }
                    for i, e in enumerate(enemies)
                ],
            },
            "objectives": objectives,
            "win_conditions": win_conditions,
            "power_spikes": power_spikes,
        }

    def _get_objective_recommendations(self, minute: int, game_state: str, team: str) -> Dict[str, Any]:
        """Get objective recommendations based on game state."""
        recommendations = []

        # Dragon timing (spawns at 5:00, respawns every 5 minutes)
        if minute >= 5:
            dragon_timing = "Dragon should be available - contest if your bot lane has priority"
            recommendations.append({"objective": "Dragon", "priority": "High", "tip": dragon_timing})

        # Rift Herald timing (spawns at 8:00)
        if minute >= 8 and minute < 20:
            herald_tip = "Rift Herald is available - great for taking first tower"
            recommendations.append({"objective": "Rift Herald", "priority": "High", "tip": herald_tip})

        # Tower recommendations based on game state
        if game_state in ["Winning", "Ahead", "Slightly Ahead"]:
            recommendations.append({
                "objective": "First Tower",
                "priority": "High",
                "tip": "Use your lead to take the first tower and open up the map"
            })
            recommendations.append({
                "objective": "Vision Control",
                "priority": "Medium",
                "tip": "Place deep wards in enemy jungle to track their jungler"
            })
        else:
            recommendations.append({
                "objective": "Defensive Wards",
                "priority": "High",
                "tip": "Ward your own jungle entrances to avoid ganks"
            })
            recommendations.append({
                "objective": "Farm",
                "priority": "High",
                "tip": "Focus on catching waves and scaling - avoid risky plays"
            })

        return {
            "recommendations": recommendations,
            "next_dragon_spawn": f"~{((minute // 5) + 1) * 5}:00" if minute >= 5 else "5:00",
        }

    def _analyze_win_conditions(self, user: Dict[str, Any], allies: List[Dict[str, Any]],
                                 enemies: List[Dict[str, Any]], game_state: str) -> Dict[str, Any]:
        """Analyze team win conditions."""
        win_conditions = []

        # Check team composition for win conditions
        all_allies = [user] + allies

        # Splitpush check
        splitpush_champs = ["Fiora", "Tryndamere", "Jax", "Camille", "Shen", "Yorick", "Nasus"]
        team_champs = [a.get("champion", "") for a in all_allies]
        has_splitpusher = any(c in team_champs for c in splitpush_champs)

        if has_splitpusher:
            win_conditions.append({
                "condition": "Splitpush",
                "description": "Your team has strong splitpushers. Apply side lane pressure while team groups.",
            })

        # Teamfight check
        teamfight_champs = ["Malphite", "Amumu", "Orianna", "Miss Fortune", "Leona", "Sejuani"]
        has_teamfight = any(c in team_champs for c in teamfight_champs)

        if has_teamfight:
            win_conditions.append({
                "condition": "Teamfighting",
                "description": "Your team has good teamfight presence. Group for objectives and force 5v5s.",
            })

        # Pick comp check
        pick_champs = ["Blitzcrank", "Thresh", "Morgana", "Ahri", "Leblanc", "Zed"]
        has_pick = any(c in team_champs for c in pick_champs)

        if has_pick:
            win_conditions.append({
                "condition": "Pick Composition",
                "description": "Your team can catch enemies out. Set up vision and look for isolated targets.",
            })

        # Late game scaling
        scaling_champs = ["Kayle", "Kassadin", "Vayne", "Jinx", "Kog'Maw", "Viktor"]
        has_scaling = any(c in team_champs for c in scaling_champs)

        if has_scaling:
            win_conditions.append({
                "condition": "Late Game Scaling",
                "description": "Your team scales well. Don't force early - play for 25+ minutes.",
            })

        # Default based on game state
        if not win_conditions:
            if game_state in ["Winning", "Ahead"]:
                win_conditions.append({
                    "condition": "Snowball Lead",
                    "description": "You're ahead - keep pressuring and don't give free shutdowns.",
                })
            else:
                win_conditions.append({
                    "condition": "Outplay",
                    "description": "Look for mechanical outplays and capitalize on enemy mistakes.",
                })

        return {
            "primary": win_conditions[0] if win_conditions else None,
            "secondary": win_conditions[1] if len(win_conditions) > 1 else None,
            "all_conditions": win_conditions,
        }

    def _analyze_power_spikes(self, user: Dict[str, Any], enemies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze power spikes for user and enemies."""
        user_level = user.get("level", 1)
        user_champ = user.get("champion", "")

        # General power spike levels
        user_spikes = []
        if user_level < 6:
            user_spikes.append(f"Level 6 - {user_champ}'s ultimate unlocks major power spike")
        if user_level < 11:
            user_spikes.append("Level 11 - Second ultimate rank")

        # Item power spikes (check current items)
        user_items = user.get("items", [])
        completed_items = [i for i in user_items if not any(s in i.lower() for s in
                         ["doran", "cull", "tear", "dark seal", "long sword", "amplifying tome"])]

        if len(completed_items) == 0:
            user_spikes.append("First completed item - significant power boost incoming")
        elif len(completed_items) == 1:
            user_spikes.append("Second item completion will be a major spike")

        # Enemy power spikes to watch
        enemy_spikes = []
        for enemy in enemies:
            enemy_level = enemy.get("level", 1)
            enemy_champ = enemy.get("champion", "")

            if enemy_level >= 6:
                enemy_spikes.append(f"{enemy_champ} has ultimate - be careful of all-ins")

            # Check for completed mythics
            enemy_items = enemy.get("items", [])
            if any("eclipse" in i.lower() or "kraken" in i.lower() or "liandry" in i.lower()
                   or "everfrost" in i.lower() or "sunderer" in i.lower() or "riftmaker" in i.lower()
                   for i in enemy_items):
                enemy_spikes.append(f"{enemy_champ} has completed a major item - they're stronger now")

        return {
            "your_upcoming_spikes": user_spikes[:3],
            "enemy_current_spikes": enemy_spikes[:3],
            "advice": "Respect enemy power spikes and look to fight around your own.",
        }

    def full_analysis(self, snapshot: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform complete detailed snapshot analysis.

        Combines game state, item recommendations, counter strategies, and strategic advice.
        """
        if snapshot is None:
            snapshot = self.get_snapshot()

        if not snapshot:
            return {"error": "No game snapshot available"}

        user = self.get_user_player(snapshot)
        game_state = self.analyze_game_state(snapshot)
        item_recommendations = self.analyze_item_recommendations(snapshot)
        counter_strategies = self.analyze_counter_strategies(snapshot)

        # Generate executive summary
        summary = self._generate_summary(user, game_state, item_recommendations, counter_strategies)

        return {
            "match_id": snapshot.get("match_id"),
            "summary": summary,
            "game_state": game_state,
            "item_recommendations": item_recommendations,
            "counter_strategies": counter_strategies,
        }

    def _generate_summary(self, user: Dict[str, Any], game_state: Dict[str, Any],
                          items: Dict[str, Any], counters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an executive summary of the analysis."""
        champion = user.get("champion", "Unknown")
        state = game_state.get("game_state", "Unknown")
        gold_diff = game_state.get("team_gold_diff", 0)

        # Key points
        key_points = []

        # Game state summary
        if state in ["Winning", "Ahead"]:
            key_points.append(f"You're ahead by {abs(gold_diff)} gold - press your advantage")
        elif state in ["Losing", "Behind"]:
            key_points.append(f"You're behind by {abs(gold_diff)} gold - play safe and scale")
        else:
            key_points.append("Game is even - focus on objectives and smart trades")

        # CS assessment
        cs_rating = game_state.get("user", {}).get("cs_rating", "")
        if cs_rating in ["Below Average"]:
            key_points.append("Focus on improving CS - you're falling behind in farm")

        # Counter warning
        counters_user = counters.get("enemies_that_counter_user", [])
        if counters_user:
            hard_counters = [c for c in counters_user if isinstance(c, dict) and "HARD" in c.get("counter_type", "")]
            if hard_counters:
                key_points.append(f"Warning: {hard_counters[0].get('champion')} hard counters you")

        # Lane matchup
        lane_matchup = counters.get("lane_matchup", {})
        if lane_matchup:
            lane_state = lane_matchup.get("lane_state", "")
            if "Losing" in lane_state:
                key_points.append(f"You're losing lane to {lane_matchup.get('opponent')} - play safe")
            elif "Winning" in lane_state:
                key_points.append(f"You're winning lane - look to roam or dive")

        # Item priority
        next_items = items.get("next_item_suggestions", [])
        if next_items:
            priority_item = next_items[0]
            key_points.append(f"Priority purchase: {priority_item.get('item')}")

        # Immediate action
        immediate = items.get("immediate_purchases", [])
        available_gold = items.get("estimated_available_gold", 0)
        if immediate and available_gold > 0:
            key_points.append(f"You have {available_gold} gold - buy {immediate[0].get('item')}")

        return {
            "champion": champion,
            "position": ROLE_POSITIONS.get(user.get("participant_id", 1), "Top"),
            "game_state": state,
            "gold_diff": gold_diff,
            "key_points": key_points[:6],
            "primary_focus": key_points[0] if key_points else "Play your game",
        }


def get_snapshot_analyzer(data_retriever) -> SnapshotAnalyzer:
    """Factory function to create a SnapshotAnalyzer instance."""
    return SnapshotAnalyzer(data_retriever)

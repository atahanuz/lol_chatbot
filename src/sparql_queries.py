"""
SPARQL Query Engine for LoL Chatbot

Provides semantic querying capabilities using SPARQL over the RDF graph.
Enables complex multi-criteria queries like:
- "Champions with CC AND burst damage"
- "Tanky champions that scale late"
- "Items with armor AND ability power"
"""

from rdflib import Graph, Namespace, RDF, RDFS
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

MOBA = Namespace("http://www.semanticweb.org/gizemyilmaz/ontologies/moba/ontology#")


class SemanticQueryEngine:
    """
    Semantic query engine for the LoL ontology.
    Keeps RDF graphs loaded and provides SPARQL query capabilities.
    """

    def __init__(self, champions_ttl: str, items_ttl: str, enrichment_ttl: str = None):
        """Initialize the query engine with TTL files."""
        self.graph = Graph()
        self.graph.bind("moba", MOBA)

        # Track last executed queries for debugging/display
        self.last_queries: List[str] = []

        # Load main ontology files
        print("Loading champion ontology...")
        self.graph.parse(champions_ttl, format="turtle")

        print("Loading items ontology...")
        self.graph.parse(items_ttl, format="turtle")

        # Load enrichment data if available
        if enrichment_ttl and Path(enrichment_ttl).exists():
            print("Loading enrichment data...")
            self.graph.parse(enrichment_ttl, format="turtle")

        print(f"Total triples loaded: {len(self.graph)}")

        # Build quick lookup indices
        self._build_indices()

    def clear_query_log(self):
        """Clear the query log before a new operation."""
        self.last_queries = []

    def get_last_queries(self) -> List[str]:
        """Get the list of last executed SPARQL queries."""
        return self.last_queries

    def _build_indices(self):
        """Build indices for common lookups."""
        # Index champion URIs by name
        self.champion_uris = {}
        for hero_type in ["AssassinHero", "MageHero", "WarriorHero", "CarryHero",
                         "SupportHero", "TankHero", "MeleeHero", "RangedHero"]:
            for uri in self.graph.subjects(RDF.type, MOBA[hero_type]):
                name = self.graph.value(uri, MOBA.heroName)
                if name:
                    key = str(name).lower().replace(" ", "_").replace("'", "").replace(".", "")
                    self.champion_uris[key] = uri

    def query(self, sparql_query: str, log_query: bool = True) -> List[Dict[str, Any]]:
        """Execute a SPARQL query and return results as a list of dicts."""
        try:
            # Log the query for debugging/display
            if log_query:
                # Clean up the query for display (remove extra whitespace)
                clean_query = "\n".join(line for line in sparql_query.strip().split("\n") if line.strip())
                self.last_queries.append(clean_query)

            results = self.graph.query(sparql_query)
            return [
                {str(var): str(row[var]) for var in results.vars}
                for row in results
            ]
        except Exception as e:
            print(f"SPARQL query error: {e}")
            return []

    def get_champions_by_cc_type(self, cc_types: List[str]) -> List[str]:
        """
        Get champions that have specific CC types.

        Args:
            cc_types: List of CC types like ["Stun", "Knockup"]

        Returns:
            List of champion names that have ALL specified CC types
        """
        if not cc_types:
            return []

        # Build SPARQL query with AND logic
        cc_patterns = "\n".join([
            f"    ?champion moba:hasCrowdControl moba:{cc}CC ."
            for cc in cc_types
        ])

        query = f"""
        PREFIX moba: <{MOBA}>
        SELECT DISTINCT ?name WHERE {{
            ?champion moba:heroName ?name .
            {cc_patterns}
        }}
        ORDER BY ?name
        """

        results = self.query(query)
        return [r["name"] for r in results]

    def get_champions_by_effects(self, effects: List[str]) -> List[str]:
        """
        Get champions that have specific ability effects.

        Args:
            effects: List of effects like ["Dash", "Shield"]

        Returns:
            List of champion names that have ALL specified effects
        """
        if not effects:
            return []

        effect_patterns = "\n".join([
            f"    ?champion moba:hasAbilityEffect moba:{effect}Effect ."
            for effect in effects
        ])

        query = f"""
        PREFIX moba: <{MOBA}>
        SELECT DISTINCT ?name WHERE {{
            ?champion moba:heroName ?name .
            {effect_patterns}
        }}
        ORDER BY ?name
        """

        results = self.query(query)
        return [r["name"] for r in results]

    def get_champions_by_playstyle(self, playstyles: List[str]) -> List[str]:
        """
        Get champions that have specific playstyles.

        Args:
            playstyles: List of playstyles like ["Burst", "Assassin"]

        Returns:
            List of champion names that have ALL specified playstyles
        """
        if not playstyles:
            return []

        style_patterns = "\n".join([
            f"    ?champion moba:hasPlaystyle moba:{style}Playstyle ."
            for style in playstyles
        ])

        query = f"""
        PREFIX moba: <{MOBA}>
        SELECT DISTINCT ?name WHERE {{
            ?champion moba:heroName ?name .
            {style_patterns}
        }}
        ORDER BY ?name
        """

        results = self.query(query)
        return [r["name"] for r in results]

    def get_champions_by_power_curve(self, power_curve: str) -> List[str]:
        """
        Get champions that spike at a specific game phase.

        Args:
            power_curve: One of "EarlyGame", "MidGame", "LateGame"

        Returns:
            List of champion names
        """
        query = f"""
        PREFIX moba: <{MOBA}>
        SELECT DISTINCT ?name WHERE {{
            ?champion moba:heroName ?name .
            ?champion moba:hasPowerSpike moba:{power_curve}PowerSpike .
        }}
        ORDER BY ?name
        """

        results = self.query(query)
        return [r["name"] for r in results]

    def get_champions_by_win_condition(self, win_condition: str) -> List[str]:
        """
        Get champions that excel at a specific win condition.

        Args:
            win_condition: One of "Teamfight", "Splitpush", "Pick", "Siege", "Objective"

        Returns:
            List of champion names
        """
        query = f"""
        PREFIX moba: <{MOBA}>
        SELECT DISTINCT ?name WHERE {{
            ?champion moba:heroName ?name .
            ?champion moba:hasWinCondition moba:{win_condition}WinCondition .
        }}
        ORDER BY ?name
        """

        results = self.query(query)
        return [r["name"] for r in results]

    def get_champions_by_role_and_cc(self, role: str, cc_types: List[str]) -> List[str]:
        """
        Get champions that have a specific role AND specific CC types.

        Args:
            role: Role like "TankRole", "MageRole"
            cc_types: List of CC types

        Returns:
            List of champion names
        """
        cc_patterns = "\n".join([
            f"    ?champion moba:hasCrowdControl moba:{cc}CC ."
            for cc in cc_types
        ]) if cc_types else ""

        query = f"""
        PREFIX moba: <{MOBA}>
        SELECT DISTINCT ?name WHERE {{
            ?champion moba:heroName ?name .
            ?champion moba:playsRole moba:{role} .
            {cc_patterns}
        }}
        ORDER BY ?name
        """

        results = self.query(query)
        return [r["name"] for r in results]

    def multi_criteria_champion_search(
        self,
        roles: List[str] = None,
        lanes: List[str] = None,
        cc_types: List[str] = None,
        effects: List[str] = None,
        playstyles: List[str] = None,
        power_curves: List[str] = None,
        win_conditions: List[str] = None,
        damage_type: str = None
    ) -> List[str]:
        """
        Search for champions matching multiple criteria (AND logic).

        All specified criteria must match.
        """
        patterns = []

        # Role patterns
        if roles:
            for role in roles:
                patterns.append(f"?champion moba:playsRole moba:{role} .")

        # Lane patterns
        if lanes:
            for lane in lanes:
                patterns.append(f"?champion moba:typicalLane moba:{lane} .")

        # CC patterns
        if cc_types:
            for cc in cc_types:
                patterns.append(f"?champion moba:hasCrowdControl moba:{cc}CC .")

        # Effect patterns
        if effects:
            for effect in effects:
                patterns.append(f"?champion moba:hasAbilityEffect moba:{effect}Effect .")

        # Playstyle patterns
        if playstyles:
            for style in playstyles:
                patterns.append(f"?champion moba:hasPlaystyle moba:{style}Playstyle .")

        # Power curve patterns
        if power_curves:
            for curve in power_curves:
                patterns.append(f"?champion moba:hasPowerSpike moba:{curve}PowerSpike .")

        # Win condition patterns
        if win_conditions:
            for cond in win_conditions:
                patterns.append(f"?champion moba:hasWinCondition moba:{cond}WinCondition .")

        # Damage type pattern
        if damage_type:
            patterns.append(f"?champion moba:dealsDamageType moba:{damage_type} .")

        if not patterns:
            return []

        pattern_str = "\n            ".join(patterns)

        query = f"""
        PREFIX moba: <{MOBA}>
        SELECT DISTINCT ?name WHERE {{
            ?champion moba:heroName ?name .
            {pattern_str}
        }}
        ORDER BY ?name
        """

        results = self.query(query)
        return [r["name"] for r in results]

    def get_team_counter_coverage(self, enemy_champions: List[str]) -> Dict[str, List[str]]:
        """
        Find champions that counter multiple enemies on the team.

        Args:
            enemy_champions: List of enemy champion names

        Returns:
            Dict mapping champion names to the enemies they counter
        """
        counter_coverage = {}

        for enemy in enemy_champions:
            enemy_key = enemy.lower().replace(" ", "_").replace("'", "").replace(".", "")

            # Query for champions that counter this enemy
            query = f"""
            PREFIX moba: <{MOBA}>
            SELECT DISTINCT ?counter_name WHERE {{
                ?enemy moba:heroName ?enemy_name .
                FILTER(LCASE(?enemy_name) = "{enemy.lower()}")
                ?enemy moba:counteredBy ?counter .
                ?counter moba:heroName ?counter_name .
            }}
            """

            results = self.query(query)

            for r in results:
                counter_name = r["counter_name"]
                if counter_name not in counter_coverage:
                    counter_coverage[counter_name] = []
                counter_coverage[counter_name].append(enemy)

        # Sort by number of enemies countered
        return dict(sorted(
            counter_coverage.items(),
            key=lambda x: len(x[1]),
            reverse=True
        ))

    def get_team_synergy_score(self, team_champions: List[str]) -> Dict[str, Any]:
        """
        Calculate synergy score for a team composition.

        Returns synergy pairs and overall score.
        """
        synergy_pairs = []
        total_score = 0

        for i, champ1 in enumerate(team_champions):
            for champ2 in team_champions[i+1:]:
                # Check strong synergy
                query = f"""
                PREFIX moba: <{MOBA}>
                ASK WHERE {{
                    ?c1 moba:heroName "{champ1}" .
                    ?c2 moba:heroName "{champ2}" .
                    {{ ?c1 moba:strongSynergyWith ?c2 }}
                    UNION
                    {{ ?c2 moba:strongSynergyWith ?c1 }}
                }}
                """
                if self.graph.query(query).askAnswer:
                    synergy_pairs.append((champ1, champ2, "strong"))
                    total_score += 3
                    continue

                # Check normal synergy
                query = f"""
                PREFIX moba: <{MOBA}>
                ASK WHERE {{
                    ?c1 moba:heroName "{champ1}" .
                    ?c2 moba:heroName "{champ2}" .
                    {{ ?c1 moba:synergyWith ?c2 }}
                    UNION
                    {{ ?c2 moba:synergyWith ?c1 }}
                }}
                """
                if self.graph.query(query).askAnswer:
                    synergy_pairs.append((champ1, champ2, "normal"))
                    total_score += 1

        return {
            "synergy_pairs": synergy_pairs,
            "total_score": total_score,
            "max_possible": len(team_champions) * (len(team_champions) - 1) // 2 * 3
        }

    def recommend_pick(
        self,
        lane: str,
        enemy_champion: str = None,
        ally_champions: List[str] = None,
        preferred_playstyles: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recommend a champion pick based on multiple criteria.

        Args:
            lane: The lane to pick for (e.g., "TopLane", "MidLane")
            enemy_champion: Enemy laner to counter (optional)
            ally_champions: Allies to synergize with (optional)
            preferred_playstyles: Preferred playstyles (optional)

        Returns:
            List of recommendations with scores
        """
        candidates = []

        # Get champions for this lane
        lane_query = f"""
        PREFIX moba: <{MOBA}>
        SELECT ?name WHERE {{
            ?champion moba:heroName ?name .
            ?champion moba:typicalLane moba:{lane} .
        }}
        """
        lane_champs = [r["name"] for r in self.query(lane_query)]

        for champ in lane_champs:
            score = 0
            reasons = []

            # Check if counters enemy
            if enemy_champion:
                counter_query = f"""
                PREFIX moba: <{MOBA}>
                ASK WHERE {{
                    ?c moba:heroName "{champ}" .
                    ?enemy moba:heroName "{enemy_champion}" .
                    {{ ?c moba:counters ?enemy }}
                    UNION
                    {{ ?c moba:hardCounters ?enemy }}
                }}
                """
                if self.graph.query(counter_query).askAnswer:
                    score += 5
                    reasons.append(f"Counters {enemy_champion}")

            # Check synergy with allies
            if ally_champions:
                for ally in ally_champions:
                    synergy_query = f"""
                    PREFIX moba: <{MOBA}>
                    ASK WHERE {{
                        ?c moba:heroName "{champ}" .
                        ?ally moba:heroName "{ally}" .
                        {{ ?c moba:strongSynergyWith ?ally }}
                        UNION
                        {{ ?ally moba:strongSynergyWith ?c }}
                        UNION
                        {{ ?c moba:synergyWith ?ally }}
                        UNION
                        {{ ?ally moba:synergyWith ?c }}
                    }}
                    """
                    if self.graph.query(synergy_query).askAnswer:
                        score += 2
                        reasons.append(f"Synergizes with {ally}")

            # Check playstyle match
            if preferred_playstyles:
                for style in preferred_playstyles:
                    style_query = f"""
                    PREFIX moba: <{MOBA}>
                    ASK WHERE {{
                        ?c moba:heroName "{champ}" .
                        ?c moba:hasPlaystyle moba:{style}Playstyle .
                    }}
                    """
                    if self.graph.query(style_query).askAnswer:
                        score += 1
                        reasons.append(f"Has {style} playstyle")

            if score > 0:
                candidates.append({
                    "champion": champ,
                    "score": score,
                    "reasons": reasons
                })

        # Sort by score
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:10]  # Return top 10

    def get_champion_semantic_profile(self, champion_name: str) -> Dict[str, Any]:
        """
        Get the full semantic profile of a champion.

        Returns all semantic properties: CC types, effects, playstyles, etc.
        """
        profile = {
            "champion": champion_name,
            "cc_types": [],
            "effects": [],
            "playstyles": [],
            "power_spikes": [],
            "win_conditions": [],
            "roles": [],
            "lanes": []
        }

        # Find the champion URI first - use STR() to handle typed literals
        uri_query = f"""
        PREFIX moba: <{MOBA}>
        SELECT ?champion WHERE {{
            ?champion moba:heroName ?name .
            FILTER(STR(?name) = "{champion_name}")
        }} LIMIT 1
        """
        uri_results = self.query(uri_query)
        if not uri_results:
            return profile

        champ_uri = uri_results[0]["champion"]

        # Get CC types
        cc_query = f"""
        PREFIX moba: <{MOBA}>
        SELECT ?cc WHERE {{
            <{champ_uri}> moba:hasCrowdControl ?cc .
        }}
        """
        for r in self.query(cc_query):
            value = r["cc"].split("#")[-1].replace("CC", "")
            profile["cc_types"].append(value)

        # Get effects
        effect_query = f"""
        PREFIX moba: <{MOBA}>
        SELECT ?effect WHERE {{
            <{champ_uri}> moba:hasAbilityEffect ?effect .
        }}
        """
        for r in self.query(effect_query):
            value = r["effect"].split("#")[-1].replace("Effect", "")
            profile["effects"].append(value)

        # Get playstyles
        style_query = f"""
        PREFIX moba: <{MOBA}>
        SELECT ?style WHERE {{
            <{champ_uri}> moba:hasPlaystyle ?style .
        }}
        """
        for r in self.query(style_query):
            value = r["style"].split("#")[-1].replace("Playstyle", "")
            profile["playstyles"].append(value)

        # Get power spikes
        spike_query = f"""
        PREFIX moba: <{MOBA}>
        SELECT ?spike WHERE {{
            <{champ_uri}> moba:hasPowerSpike ?spike .
        }}
        """
        for r in self.query(spike_query):
            value = r["spike"].split("#")[-1].replace("PowerSpike", "")
            profile["power_spikes"].append(value)

        # Get win conditions
        win_query = f"""
        PREFIX moba: <{MOBA}>
        SELECT ?win WHERE {{
            <{champ_uri}> moba:hasWinCondition ?win .
        }}
        """
        for r in self.query(win_query):
            value = r["win"].split("#")[-1].replace("WinCondition", "")
            profile["win_conditions"].append(value)

        # Get roles
        role_query = f"""
        PREFIX moba: <{MOBA}>
        SELECT ?role WHERE {{
            <{champ_uri}> moba:playsRole ?role .
        }}
        """
        for r in self.query(role_query):
            value = r["role"].split("#")[-1].replace("Role", "")
            profile["roles"].append(value)

        # Get lanes
        lane_query = f"""
        PREFIX moba: <{MOBA}>
        SELECT ?lane WHERE {{
            <{champ_uri}> moba:typicalLane ?lane .
        }}
        """
        for r in self.query(lane_query):
            value = r["lane"].split("#")[-1]
            profile["lanes"].append(value)

        return profile


# Global instance for reuse
_engine: Optional[SemanticQueryEngine] = None


def get_query_engine(
    champions_ttl: str = None,
    items_ttl: str = None,
    enrichment_ttl: str = None
) -> SemanticQueryEngine:
    """Get or create the global query engine instance."""
    global _engine
    if _engine is None:
        if champions_ttl is None:
            from config import TTL_FILE_PATH, ITEMS_TTL_FILE_PATH, ENRICHMENT_TTL_PATH
            champions_ttl = TTL_FILE_PATH
            items_ttl = ITEMS_TTL_FILE_PATH
            enrichment_ttl = ENRICHMENT_TTL_PATH

        _engine = SemanticQueryEngine(champions_ttl, items_ttl, enrichment_ttl)
    return _engine


if __name__ == "__main__":
    # Test the query engine
    from config import TTL_FILE_PATH, ITEMS_TTL_FILE_PATH, ENRICHMENT_TTL_PATH

    engine = SemanticQueryEngine(TTL_FILE_PATH, ITEMS_TTL_FILE_PATH, ENRICHMENT_TTL_PATH)

    print("\n" + "=" * 60)
    print("Testing Semantic Query Engine")
    print("=" * 60)

    # Test 1: Champions with Stun CC
    print("\n1. Champions with Stun CC:")
    stun_champs = engine.get_champions_by_cc_type(["Stun"])
    print(f"   Found {len(stun_champs)} champions: {stun_champs[:10]}...")

    # Test 2: Champions with Dash AND Shield
    print("\n2. Champions with Dash AND Shield effects:")
    dash_shield = engine.get_champions_by_effects(["Dash", "Shield"])
    print(f"   Found {len(dash_shield)} champions: {dash_shield[:10]}...")

    # Test 3: Late game scaling champions
    print("\n3. Late game scaling champions:")
    late_game = engine.get_champions_by_power_curve("LateGame")
    print(f"   Found {len(late_game)} champions: {late_game[:10]}...")

    # Test 4: Multi-criteria search - Tank with Stun for Top lane
    print("\n4. Tanks with Stun for Top lane:")
    tanks = engine.multi_criteria_champion_search(
        roles=["TankRole"],
        lanes=["TopLane"],
        cc_types=["Stun"]
    )
    print(f"   Found {len(tanks)} champions: {tanks}")

    # Test 5: Teamfight champions
    print("\n5. Teamfight-focused champions:")
    teamfight = engine.get_champions_by_win_condition("Teamfight")
    print(f"   Found {len(teamfight)} champions: {teamfight[:10]}...")

    # Test 6: Champion semantic profile
    print("\n6. Leona's semantic profile:")
    profile = engine.get_champion_semantic_profile("Leona")
    for key, value in profile.items():
        if value and key != "champion":
            print(f"   {key}: {value}")

    # Test 7: Team counter coverage
    print("\n7. Counter coverage for enemy team [Yasuo, Zed, Jinx]:")
    counters = engine.get_team_counter_coverage(["Yasuo", "Zed", "Jinx"])
    top_counters = list(counters.items())[:5]
    for champ, enemies in top_counters:
        print(f"   {champ} counters: {enemies}")

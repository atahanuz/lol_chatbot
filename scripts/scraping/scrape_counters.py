#!/usr/bin/env python3
"""
League of Legends Champion Counter Data API
Fetches real matchup data from counterstats.net for any champion.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import sys
import os
from typing import Optional

# Get project root directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # ssw_chatbot/
GAME_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'game_data')
COUNTER_DATA_DIR = os.path.join(GAME_DATA_DIR, 'counter_data')


def get_champion_list() -> dict:
    """Get list of all champions from Riot's Data Dragon."""
    url = "https://ddragon.leagueoflegends.com/cdn/14.24.1/data/en_US/champion.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {name.lower().replace("'", "").replace(" ", ""): name
                    for name in data['data'].keys()}
    except Exception:
        pass
    return {}


def normalize_champion_name(name: str, champion_map: dict) -> str:
    """Normalize champion name to URL format."""
    name_clean = name.lower().replace("'", "").replace(" ", "").replace(".", "")

    # Check direct match
    if name_clean in champion_map:
        return champion_map[name_clean]

    # Special URL mappings
    special = {
        "wukong": "MonkeyKing",
        "reksai": "RekSai",
        "khazix": "Khazix",
        "chogath": "Chogath",
        "velkoz": "Velkoz",
        "kaisa": "Kaisa",
        "kogmaw": "KogMaw",
        "leesin": "LeeSin",
        "jarvaniv": "JarvanIV",
        "drmundo": "DrMundo",
        "masteryi": "MasterYi",
        "missfortune": "MissFortune",
        "twistedfate": "TwistedFate",
        "xinzhao": "XinZhao",
        "aurelionsol": "AurelionSol",
        "tahmkench": "TahmKench",
        "renata": "Renata",
        "belveth": "Belveth",
        "ksante": "KSante",
    }

    return special.get(name_clean, name)


def get_counters(champion_name: str) -> Optional[dict]:
    """
    Fetch counter data for a champion from counterstats.net.

    Returns dict with:
        - champion: name
        - weakAgainst: list of champions that counter this one (with winRate)
        - strongAgainst: list of champions this one counters (with winRate)
        - source: data source
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
    }

    # Format name for URL - add hyphens between words in camelCase
    url_name = re.sub(r'([a-z])([A-Z])', r'\1-\2', champion_name)
    url_name = url_name.lower().replace(" ", "-").replace("'", "").replace(".", "")
    url = f"https://www.counterstats.net/league-of-legends/{url_name}"

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "champion": champion_name}

        soup = BeautifulSoup(r.text, 'html.parser')

        # Find all matchup links
        links = soup.find_all('a', href=re.compile(r'/league-of-legends/'))

        seen = set()
        weak_against = []
        strong_against = []

        for link in links:
            text = link.get_text(strip=True)
            # Pattern: score + name + "Win" + percentage
            match = re.match(r'(\d+\.?\d*)([\w\s\']+)Win(\d+)%', text)
            if match:
                score = float(match.group(1))
                name = match.group(2).strip()
                win_rate = int(match.group(3))

                # Skip duplicates
                if name in seen:
                    continue
                seen.add(name)

                entry = {
                    'champion': name,
                    'score': score,
                    'winRate': win_rate
                }

                # Score >= 5.0 = they counter you, < 5.0 = you counter them
                if score >= 5.0:
                    weak_against.append(entry)
                else:
                    strong_against.append(entry)

        # Sort by effectiveness
        weak_against.sort(key=lambda x: x['score'], reverse=True)
        strong_against.sort(key=lambda x: x['score'])

        return {
            'champion': champion_name,
            'weakAgainst': weak_against,
            'strongAgainst': strong_against,
            'source': 'counterstats.net',
            'url': url
        }

    except requests.exceptions.Timeout:
        return {"error": "Request timeout", "champion": champion_name}
    except Exception as e:
        return {"error": str(e), "champion": champion_name}


def get_all_counters(champions: list) -> dict:
    """Fetch counter data for multiple champions."""
    results = {}
    for champ in champions:
        print(f"Fetching {champ}...", file=sys.stderr)
        results[champ] = get_counters(champ)
    return results


def main():
    """CLI interface."""
    if len(sys.argv) < 2:
        print("Usage: python get_counters.py <champion_name> [--json]")
        print("       python get_counters.py --all [--json]")
        print("\nExamples:")
        print("  python get_counters.py Ahri")
        print("  python get_counters.py 'Lee Sin' --json")
        print("  python get_counters.py --all --json")
        sys.exit(1)

    json_output = '--json' in sys.argv

    if sys.argv[1] == '--all':
        # Fetch all champions
        champ_map = get_champion_list()
        if not champ_map:
            print("Error: Could not fetch champion list", file=sys.stderr)
            sys.exit(1)

        champions = sorted(set(champ_map.values()))
        print(f"Fetching data for {len(champions)} champions...", file=sys.stderr)

        if json_output:
            # Create directory for output
            os.makedirs(COUNTER_DATA_DIR, exist_ok=True)

            for i, champ in enumerate(champions, 1):
                print(f"[{i}/{len(champions)}] Fetching {champ}...", file=sys.stderr)
                data = get_counters(champ)
                filename = os.path.join(COUNTER_DATA_DIR, f"{champ.lower()}_counters.json")
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)

            print(f"\nSaved {len(champions)} files to {COUNTER_DATA_DIR}/")
        else:
            results = get_all_counters(champions)
            for champ, data in results.items():
                if 'error' not in data:
                    print(f"\n{champ}: countered by {[c['champion'] for c in data['weakAgainst'][:3]]}")
    else:
        champion_name = sys.argv[1]

        # Normalize name
        champ_map = get_champion_list()
        normalized = normalize_champion_name(champion_name, champ_map)

        data = get_counters(normalized)

        if json_output:
            filename = f"{normalized.lower()}_counters.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved to {filename}")
        else:
            if 'error' in data:
                print(f"Error: {data['error']}")
                sys.exit(1)

            print(f"\n{'='*60}")
            print(f"  Counter Data for {data['champion']}")
            print(f"{'='*60}")

            print(f"\n🔴 COUNTERED BY (hard matchups):")
            for i, c in enumerate(data['weakAgainst'][:8], 1):
                print(f"   {i}. {c['champion']:15} - {c['winRate']}% win rate (score: {c['score']})")

            print(f"\n🟢 STRONG AGAINST (easy matchups):")
            for i, c in enumerate(data['strongAgainst'][:8], 1):
                print(f"   {i}. {c['champion']:15} - {c['winRate']}% win rate (score: {c['score']})")

            print(f"\n📊 Source: {data['url']}")
            print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

import json
from typing import Dict, Any, Optional
from openai import OpenAI
from prompts import INTENT_CLASSIFICATION_PROMPT
from config import MODEL_NAME


def classify_intent(
    client: OpenAI, question: str, conversation_history: list = None
) -> Dict[str, Any]:
    """
    Use OpenAI to classify the user's question and extract entities.

    Returns a dictionary with:
    - intent: The classified intent type
    - champion_name: Extracted champion name (or None)
    - skill_key: Q/W/E/R/P (or None)
    - skill_level: Skill level number (or None)
    - character_level: Champion level (or None)
    - stat_name: Stat being queried (or None)
    - comparison_champions: List of champions for comparison (or None)
    - role: Role being queried (or None)
    - lane: Lane being queried (or None)
    """
    # Build context from conversation history for resolving references
    context_str = ""
    if conversation_history:
        recent_history = conversation_history[-6:]  # Last 3 exchanges
        context_lines = []
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            context_lines.append(f"{role}: {msg['content']}")
        context_str = "\n".join(context_lines)

    prompt = INTENT_CLASSIFICATION_PROMPT.format(question=question)

    # Add context instruction if there's history
    if context_str:
        prompt = f"""Previous conversation:
{context_str}

IMPORTANT: If the current question uses pronouns (he, she, it, they, that, this) or references like "the same champion", "that ability", etc., resolve them using the conversation context above.

{prompt}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a precise JSON extractor. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )

        content = response.choices[0].message.content.strip()

        # Try to extract JSON from the response
        # Sometimes the model wraps JSON in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)

        # Normalize champion name if present
        if result.get("champion_name"):
            result["champion_name"] = result["champion_name"].lower().strip()

        # Normalize skill key
        if result.get("skill_key"):
            result["skill_key"] = result["skill_key"].upper().strip()

        # Normalize comparison champions
        if result.get("comparison_champions"):
            result["comparison_champions"] = [
                c.lower().strip() for c in result["comparison_champions"]
            ]

        return result

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Raw response: {content}")
        return {"intent": "UNKNOWN", "error": "Failed to parse intent"}
    except Exception as e:
        print(f"Error classifying intent: {e}")
        return {"intent": "UNKNOWN", "error": str(e)}


def normalize_champion_name(name: str) -> str:
    """
    Normalize champion name to match dictionary keys.
    Handles common variations and aliases.
    """
    if not name:
        return name

    name = name.lower().strip()

    # Common aliases and variations
    aliases = {
        "mundo": "dr_mundo",
        "dr mundo": "dr_mundo",
        "doctor mundo": "dr_mundo",
        "lee sin": "lee_sin",
        "lee": "lee_sin",
        "jarvan": "jarvan_iv",
        "jarvan iv": "jarvan_iv",
        "j4": "jarvan_iv",
        "tf": "twisted_fate",
        "twisted fate": "twisted_fate",
        "mf": "miss_fortune",
        "miss fortune": "miss_fortune",
        "asol": "aurelion_sol",
        "aurelion": "aurelion_sol",
        "aurelion sol": "aurelion_sol",
        "cho": "chogath",
        "cho'gath": "chogath",
        "kog'maw": "kogmaw",
        "kog": "kogmaw",
        "kha'zix": "khazix",
        "kha": "khazix",
        "bel'veth": "belveth",
        "bel veth": "belveth",
        "kai'sa": "kaisa",
        "k'sante": "ksante",
        "rek'sai": "reksai",
        "vel'koz": "velkoz",
        "xin zhao": "xin_zhao",
        "xin": "xin_zhao",
        "master yi": "master_yi",
        "yi": "master_yi",
        "tahm kench": "tahm_kench",
        "tahm": "tahm_kench",
        "renata glasc": "renata_glasc",
        "renata": "renata_glasc",
        "nunu": "nunu_willump",
        "nunu & willump": "nunu_willump",
        "wukong": "wukong",
        "monkey king": "wukong",
    }

    if name in aliases:
        return aliases[name]

    # Replace spaces and apostrophes
    return name.replace(" ", "_").replace("'", "").replace(".", "")


if __name__ == "__main__":
    # Test the classifier
    from config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)

    test_questions = [
        "How much damage does Evelynn's Q do at level 3?",
        "What is Ashe's base health?",
        "Tell me about Jinx",
        "Which champions are assassins?",
        "Who has higher base attack damage, Darius or Garen?",
        "What is the cooldown on Annie's ultimate?",
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        result = classify_intent(client, q)
        print(f"Result: {json.dumps(result, indent=2)}")

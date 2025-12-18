import json
from openai import OpenAI

from config import (
    OPENAI_API_KEY, TTL_FILE_PATH, MODEL_NAME,
    ITEMS_TTL_FILE_PATH, MONSTERS_TTL_FILE_PATH, TURRETS_TTL_FILE_PATH
)
from ttl_parser import parse_all_data
from intent_classifier import classify_intent
from data_retriever import DataRetriever, dispatch_query
from prompts import RESPONSE_GENERATION_PROMPT, CONVERSATION_SYSTEM_PROMPT


def format_context_panel(intent: dict, data: dict) -> str:
    """Format the retrieved context data for display in a side panel."""
    lines = []
    panel_width = 60

    # Header
    lines.append("+" + "-" * (panel_width - 2) + "+")
    lines.append("|" + " CONTEXT ".center(panel_width - 2) + "|")
    lines.append("+" + "-" * (panel_width - 2) + "+")

    # Intent info
    intent_type = intent.get("intent", "UNKNOWN")
    lines.append("|" + f" Intent: {intent_type}".ljust(panel_width - 2) + "|")

    # Add relevant entity info based on intent
    if intent.get("champion_name"):
        lines.append("|" + f" Champion: {intent['champion_name']}".ljust(panel_width - 2) + "|")
    if intent.get("skill_key"):
        lines.append("|" + f" Skill: {intent['skill_key']}".ljust(panel_width - 2) + "|")
    if intent.get("skill_level"):
        lines.append("|" + f" Skill Level: {intent['skill_level']}".ljust(panel_width - 2) + "|")
    if intent.get("item_name"):
        lines.append("|" + f" Item: {intent['item_name']}".ljust(panel_width - 2) + "|")
    if intent.get("monster_name"):
        lines.append("|" + f" Monster: {intent['monster_name']}".ljust(panel_width - 2) + "|")
    if intent.get("turret_name"):
        lines.append("|" + f" Turret: {intent['turret_name']}".ljust(panel_width - 2) + "|")

    lines.append("|" + "-" * (panel_width - 2) + "|")
    lines.append("|" + " Retrieved Data:".ljust(panel_width - 2) + "|")

    # Format the data based on its structure
    if "error" in data:
        lines.append("|" + f"   Error: {data['error'][:45]}...".ljust(panel_width - 2) + "|")
    else:
        for key, value in data.items():
            if value is None:
                continue

            # Format key nicely
            display_key = key.replace("_", " ").title()

            if isinstance(value, dict):
                lines.append("|" + f"   {display_key}:".ljust(panel_width - 2) + "|")
                for k, v in value.items():
                    if v is not None:
                        k_display = k.replace("_", " ").title()
                        val_str = str(v)
                        if len(val_str) > 35:
                            val_str = val_str[:32] + "..."
                        lines.append("|" + f"     {k_display}: {val_str}".ljust(panel_width - 2) + "|")
            elif isinstance(value, list):
                if len(value) == 0:
                    continue
                lines.append("|" + f"   {display_key}:".ljust(panel_width - 2) + "|")
                # Show first few items
                for item in value[:5]:
                    item_str = str(item)
                    if len(item_str) > 45:
                        item_str = item_str[:42] + "..."
                    lines.append("|" + f"     - {item_str}".ljust(panel_width - 2) + "|")
                if len(value) > 5:
                    lines.append("|" + f"     ... and {len(value) - 5} more".ljust(panel_width - 2) + "|")
            else:
                val_str = str(value)
                if len(val_str) > 40:
                    val_str = val_str[:37] + "..."
                lines.append("|" + f"   {display_key}: {val_str}".ljust(panel_width - 2) + "|")

    # Footer
    lines.append("+" + "-" * (panel_width - 2) + "+")

    return "\n".join(lines)


def generate_response(
    client: OpenAI,
    question: str,
    data: dict,
    conversation_history: list,
) -> str:
    """Generate a natural language response using OpenAI."""
    # Format the data for the prompt
    data_str = json.dumps(data, indent=2, default=str)

    prompt = RESPONSE_GENERATION_PROMPT.format(
        question=question,
        data=data_str,
    )

    messages = [
        {"role": "system", "content": CONVERSATION_SYSTEM_PROMPT},
    ]

    # Add recent conversation history (last 6 exchanges)
    for msg in conversation_history[-12:]:
        messages.append(msg)

    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating response: {e}"


def main():
    """Main chat loop."""
    print("=" * 60)
    print("League of Legends Champion Chatbot")
    print("=" * 60)
    print("\nLoading champion data...")

    # Initialize OpenAI client
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set. Please set it in .env file.")
        return

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Load and parse all game data
    try:
        game_data = parse_all_data(
            TTL_FILE_PATH,
            ITEMS_TTL_FILE_PATH,
            MONSTERS_TTL_FILE_PATH,
            TURRETS_TTL_FILE_PATH
        )
    except Exception as e:
        print(f"Error loading game data: {e}")
        return

    retriever = DataRetriever(game_data)

    print(f"\nReady! Ask me anything about League of Legends.")
    print("Examples:")
    print("  - How much damage does Evelynn's Q do at level 3?")
    print("  - What is Ashe's base health?")
    print("  - Who counters Aatrox?")
    print("  - What items should I build on Aatrox?")
    print("  - How much does Infinity Edge cost?")
    print("  - How much health does Baron have?")
    print("  - What is the outer turret's damage?")
    print("\nType 'quit' or 'exit' to stop.\n")

    conversation_history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        # Classify the intent (with conversation history for context resolution)
        intent = classify_intent(client, user_input, conversation_history)

        # Debug: show intent (optional)
        # print(f"[Debug] Intent: {json.dumps(intent, indent=2)}")

        # Retrieve relevant data
        retrieved_data = dispatch_query(retriever, intent)

        # Display context panel showing retrieved data
        context_panel = format_context_panel(intent, retrieved_data)
        print(f"\n{context_panel}")

        # Generate response
        response = generate_response(
            client,
            user_input,
            retrieved_data,
            conversation_history,
        )

        print(f"\nBot: {response}\n")

        # Update conversation history
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()

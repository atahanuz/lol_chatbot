import json
import base64
import streamlit as st
from openai import OpenAI

import os
from config import (
    OPENAI_API_KEY, TTL_FILE_PATH, MODEL_NAME,
    ITEMS_TTL_FILE_PATH, MONSTERS_TTL_FILE_PATH, TURRETS_TTL_FILE_PATH,
    ASSETS_DIR, GAME_SNAPSHOTS_PATH
)
from ttl_parser import parse_all_data
from intent_classifier import classify_intent
from data_retriever import DataRetriever, dispatch_query
from prompts import RESPONSE_GENERATION_PROMPT, CONVERSATION_SYSTEM_PROMPT

# LoL Theme Colors
LOL_GOLD = "#C89B3C"
LOL_GOLD_LIGHT = "#F0E6D2"
LOL_BLUE_DARK = "#0A1428"
LOL_BLUE_ACCENT = "#0AC8B9"
LOL_BLUE_SECONDARY = "#005A82"


def get_base64_image(image_path: str) -> str:
    """Encode image to base64 for CSS background."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def set_custom_css(image_path: str, debug_mode: bool):
    """Set custom CSS styling with LoL theme."""
    b64_image = get_base64_image(image_path)

    # Base styles
    base_css = f"""
    <style>
    /* Import LoL-style font */
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');

    /* Main app background */
    .stApp {{
        background-image: linear-gradient(rgba(10, 20, 40, 0.85), rgba(10, 20, 40, 0.9)),
                          url("data:image/jpeg;base64,{b64_image}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}

    .stApp > header {{
        background-color: transparent;
    }}

    /* Hide default Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Title styling */
    .lol-title {{
        font-family: 'Cinzel', serif;
        font-size: 2.5rem;
        font-weight: 700;
        color: {LOL_GOLD} !important;
        text-shadow: 0 0 20px rgba(200, 155, 60, 0.5);
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 15px;
    }}

    .lol-subtitle {{
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: {LOL_GOLD_LIGHT} !important;
        opacity: 0.8;
        margin-bottom: 1.5rem;
    }}

    /* Chat container */
    .chat-container {{
        background: linear-gradient(135deg, rgba(10, 20, 40, 0.95), rgba(0, 30, 50, 0.9));
        border: 1px solid rgba(200, 155, 60, 0.3);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5),
                    inset 0 1px 0 rgba(200, 155, 60, 0.1);
    }}

    /* Chat messages */
    .stChatMessage {{
        background: linear-gradient(135deg, rgba(10, 20, 40, 0.8), rgba(0, 40, 60, 0.7)) !important;
        border: 1px solid rgba(200, 155, 60, 0.2);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
    }}

    .stChatMessage [data-testid="chatAvatarIcon-user"] {{
        background: linear-gradient(135deg, {LOL_GOLD}, #d4a84b) !important;
    }}

    .stChatMessage [data-testid="chatAvatarIcon-assistant"] {{
        background: linear-gradient(135deg, {LOL_BLUE_ACCENT}, {LOL_BLUE_SECONDARY}) !important;
    }}

    /* Chat input */
    .stChatInputContainer {{
        background: rgba(10, 20, 40, 0.9) !important;
        border: 1px solid rgba(200, 155, 60, 0.4) !important;
        border-radius: 10px;
    }}

    .stChatInputContainer > div {{
        background: transparent !important;
    }}

    .stChatInputContainer textarea {{
        background: rgba(10, 20, 40, 0.5) !important;
        border: 1px solid rgba(200, 155, 60, 0.3) !important;
        color: {LOL_GOLD_LIGHT} !important;
        font-family: 'Inter', sans-serif;
    }}

    .stChatInputContainer textarea::placeholder {{
        color: rgba(240, 230, 210, 0.5) !important;
    }}

    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, rgba(10, 20, 40, 0.98), rgba(0, 20, 35, 0.98));
        border-right: 1px solid rgba(200, 155, 60, 0.3);
    }}

    [data-testid="stSidebar"] .stRadio > label {{
        color: {LOL_GOLD_LIGHT} !important;
        font-family: 'Cinzel', serif;
        font-weight: 600;
    }}

    [data-testid="stSidebar"] .stRadio > div {{
        background: rgba(10, 20, 40, 0.5);
        border-radius: 8px;
        padding: 10px;
        border: 1px solid rgba(200, 155, 60, 0.2);
    }}

    /* Mode toggle styling */
    .mode-indicator {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    .mode-live {{
        background: linear-gradient(135deg, #1a5a3a, #0d3d26);
        color: #4ade80;
        border: 1px solid #22c55e;
    }}

    .mode-debug {{
        background: linear-gradient(135deg, #5a3a1a, #3d260d);
        color: #fbbf24;
        border: 1px solid #f59e0b;
    }}

    /* General text colors */
    h1, h2, h3 {{
        color: {LOL_GOLD} !important;
        font-family: 'Cinzel', serif;
    }}

    p, span, li, label {{
        color: {LOL_GOLD_LIGHT} !important;
        font-family: 'Inter', sans-serif;
    }}

    /* Debug panel styling */
    .debug-panel {{
        background: linear-gradient(135deg, rgba(20, 30, 50, 0.95), rgba(10, 25, 40, 0.95));
        border: 1px solid rgba(200, 155, 60, 0.4);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }}

    .debug-header {{
        color: {LOL_GOLD} !important;
        font-family: 'Cinzel', serif;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid rgba(200, 155, 60, 0.3);
    }}

    /* Debug column container - only apply to 2-column layouts (chat + debug) */
    [data-testid="stHorizontalBlock"]:has([data-testid="stColumn"]:nth-child(2):last-child) > [data-testid="stColumn"]:last-child {{
        background: linear-gradient(135deg, rgba(10, 20, 40, 0.95), rgba(5, 15, 35, 0.95));
        border: 1px solid rgba(200, 155, 60, 0.3);
        border-radius: 12px;
        padding: 1rem;
    }}

    /* JSON display in debug mode */
    [data-testid="stJson"] {{
        background: rgba(5, 15, 30, 0.95) !important;
        border: 1px solid rgba(200, 155, 60, 0.4);
        border-radius: 8px;
        padding: 12px !important;
    }}

    /* JSON text styling */
    [data-testid="stJson"] * {{
        color: {LOL_GOLD_LIGHT} !important;
        font-family: 'Monaco', 'Consolas', monospace !important;
        font-size: 0.85rem !important;
    }}

    /* JSON keys */
    [data-testid="stJson"] .json-key {{
        color: {LOL_GOLD} !important;
    }}

    /* JSON string values */
    [data-testid="stJson"] .json-string {{
        color: {LOL_BLUE_ACCENT} !important;
    }}

    /* JSON number values */
    [data-testid="stJson"] .json-number {{
        color: #4ade80 !important;
    }}

    /* JSON null values */
    [data-testid="stJson"] .json-null {{
        color: #f87171 !important;
        opacity: 0.7;
    }}

    /* Override any white backgrounds in JSON viewer */
    [data-testid="stJson"] div {{
        background: transparent !important;
    }}

    /* Style the expand/collapse icons */
    [data-testid="stJson"] svg {{
        fill: {LOL_GOLD} !important;
    }}

    /* Expander styling */
    .streamlit-expanderHeader {{
        background: linear-gradient(135deg, rgba(15, 25, 45, 0.95), rgba(10, 30, 50, 0.9)) !important;
        border: 1px solid rgba(200, 155, 60, 0.4) !important;
        border-radius: 8px;
        color: {LOL_GOLD_LIGHT} !important;
    }}

    .streamlit-expanderHeader:hover {{
        border-color: {LOL_GOLD} !important;
        box-shadow: 0 0 10px rgba(200, 155, 60, 0.2);
    }}

    .streamlit-expanderContent {{
        background: rgba(5, 15, 30, 0.95) !important;
        border: 1px solid rgba(200, 155, 60, 0.3) !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px;
    }}

    /* Expander text */
    [data-testid="stExpander"] summary span {{
        color: {LOL_GOLD_LIGHT} !important;
        font-weight: 500;
    }}

    [data-testid="stExpander"] svg {{
        fill: {LOL_GOLD} !important;
    }}

    /* Code blocks - aggressive override */
    .stCode,
    .stCodeBlock,
    [data-testid="stCode"],
    [data-testid="stCodeBlock"],
    pre[class*="language-"],
    code[class*="language-"] {{
        background: rgba(5, 15, 30, 0.98) !important;
        background-color: rgba(5, 15, 30, 0.98) !important;
        border: 1px solid rgba(200, 155, 60, 0.4) !important;
        border-radius: 8px !important;
    }}

    .stCode *,
    .stCodeBlock *,
    [data-testid="stCode"] *,
    [data-testid="stCodeBlock"] * {{
        background: transparent !important;
        background-color: transparent !important;
    }}

    .stCode pre,
    .stCodeBlock pre,
    [data-testid="stCode"] pre,
    [data-testid="stCodeBlock"] pre {{
        background: rgba(5, 15, 30, 0.98) !important;
        background-color: rgba(5, 15, 30, 0.98) !important;
        padding: 1rem !important;
        margin: 0 !important;
    }}

    .stCode code,
    .stCodeBlock code,
    [data-testid="stCode"] code,
    [data-testid="stCodeBlock"] code,
    pre code,
    code {{
        color: {LOL_GOLD_LIGHT} !important;
        font-family: 'Monaco', 'Consolas', 'Courier New', monospace !important;
        font-size: 0.85rem !important;
        line-height: 1.6 !important;
        background: transparent !important;
    }}

    /* Code block wrapper divs */
    .stCode > div,
    .stCodeBlock > div,
    [data-testid="stCode"] > div,
    [data-testid="stCodeBlock"] > div,
    [data-testid="stCodeBlock"] > div > div {{
        background: rgba(5, 15, 30, 0.98) !important;
        background-color: rgba(5, 15, 30, 0.98) !important;
    }}

    /* Copy button */
    .stCode button,
    .stCodeBlock button,
    [data-testid="stCode"] button,
    [data-testid="stCodeBlock"] button {{
        background: rgba(200, 155, 60, 0.3) !important;
        border: 1px solid rgba(200, 155, 60, 0.5) !important;
        color: {LOL_GOLD_LIGHT} !important;
        border-radius: 4px !important;
    }}

    .stCode button:hover,
    .stCodeBlock button:hover {{
        background: rgba(200, 155, 60, 0.5) !important;
        border-color: {LOL_GOLD} !important;
    }}

    .stCode button svg,
    .stCodeBlock button svg {{
        fill: {LOL_GOLD_LIGHT} !important;
        stroke: {LOL_GOLD_LIGHT} !important;
    }}

    /* Language label header */
    [data-testid="stCodeBlock"] [data-testid="stMarkdownContainer"],
    .stCodeBlock [class*="header"],
    .stCodeBlock [class*="Header"] {{
        background: rgba(15, 25, 45, 0.98) !important;
        color: {LOL_GOLD} !important;
        border-bottom: 1px solid rgba(200, 155, 60, 0.3) !important;
        padding: 0.5rem 1rem !important;
    }}

    /* Hljs syntax highlighting overrides */
    .hljs {{
        background: rgba(5, 15, 30, 0.98) !important;
        color: {LOL_GOLD_LIGHT} !important;
    }}

    .hljs-keyword,
    .hljs-selector-tag,
    .hljs-built_in {{
        color: {LOL_BLUE_ACCENT} !important;
    }}

    .hljs-string,
    .hljs-attr {{
        color: #4ade80 !important;
    }}

    .hljs-comment {{
        color: rgba(240, 230, 210, 0.5) !important;
    }}

    .hljs-variable,
    .hljs-template-variable {{
        color: #f472b6 !important;
    }}

    .hljs-number {{
        color: #fbbf24 !important;
    }}

    .hljs-literal {{
        color: {LOL_BLUE_ACCENT} !important;
    }}

    .hljs-title {{
        color: {LOL_GOLD} !important;
    }}

    /* Fix hover visibility issue on code blocks */
    .stCode:hover,
    .stCode:hover *,
    .stCodeBlock:hover,
    .stCodeBlock:hover *,
    [data-testid="stCode"]:hover,
    [data-testid="stCode"]:hover *,
    [data-testid="stCodeBlock"]:hover,
    [data-testid="stCodeBlock"]:hover *,
    pre:hover,
    pre:hover *,
    code:hover {{
        color: {LOL_GOLD_LIGHT} !important;
        opacity: 1 !important;
        visibility: visible !important;
    }}

    .stCode:hover code,
    .stCodeBlock:hover code,
    [data-testid="stCode"]:hover code,
    [data-testid="stCodeBlock"]:hover code,
    pre:hover code {{
        color: {LOL_GOLD_LIGHT} !important;
        opacity: 1 !important;
    }}

    /* Ensure syntax highlighting colors persist on hover */
    .stCodeBlock:hover .hljs-keyword,
    pre:hover .hljs-keyword {{
        color: {LOL_BLUE_ACCENT} !important;
    }}

    .stCodeBlock:hover .hljs-string,
    pre:hover .hljs-string {{
        color: #4ade80 !important;
    }}

    .stCodeBlock:hover .hljs-variable,
    pre:hover .hljs-variable {{
        color: #f472b6 !important;
    }}

    .stCodeBlock:hover .hljs-number,
    pre:hover .hljs-number {{
        color: #fbbf24 !important;
    }}

    .stCodeBlock:hover .hljs-title,
    pre:hover .hljs-title {{
        color: {LOL_GOLD} !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, {LOL_GOLD}, #a8832f) !important;
        color: {LOL_BLUE_DARK} !important;
        border: none;
        font-family: 'Cinzel', serif;
        font-weight: 600;
        padding: 8px 20px;
        border-radius: 6px;
        transition: all 0.3s ease;
    }}

    .stButton > button:hover {{
        background: linear-gradient(135deg, #d4a84b, {LOL_GOLD}) !important;
        box-shadow: 0 0 15px rgba(200, 155, 60, 0.5);
    }}

    /* Divider */
    hr {{
        border-color: rgba(200, 155, 60, 0.3) !important;
    }}

    /* Footer styling */
    .footer {{
        text-align: center;
        padding: 1rem;
        margin-top: 2rem;
        border-top: 1px solid rgba(200, 155, 60, 0.2);
    }}

    .footer a {{
        color: {LOL_BLUE_ACCENT} !important;
        text-decoration: none;
        font-weight: 500;
        transition: color 0.3s ease;
    }}

    .footer a:hover {{
        color: {LOL_GOLD} !important;
    }}

    /* Spinner */
    .stSpinner > div {{
        border-top-color: {LOL_GOLD} !important;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: rgba(10, 20, 40, 0.5);
    }}

    ::-webkit-scrollbar-thumb {{
        background: rgba(200, 155, 60, 0.5);
        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: rgba(200, 155, 60, 0.7);
    }}

    /* Example question buttons */
    .example-questions {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 1rem;
        justify-content: center;
    }}

    .example-btn {{
        background: linear-gradient(135deg, rgba(10, 20, 40, 0.9), rgba(0, 30, 50, 0.8)) !important;
        border: 1px solid rgba(200, 155, 60, 0.4) !important;
        color: {LOL_GOLD_LIGHT} !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 400 !important;
        padding: 10px 16px !important;
        border-radius: 20px !important;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: left !important;
        white-space: normal !important;
        height: auto !important;
        line-height: 1.4 !important;
    }}

    .example-btn:hover {{
        background: linear-gradient(135deg, rgba(200, 155, 60, 0.2), rgba(200, 155, 60, 0.1)) !important;
        border-color: {LOL_GOLD} !important;
        box-shadow: 0 0 15px rgba(200, 155, 60, 0.3);
        transform: translateY(-2px);
    }}

    .example-label {{
        color: rgba(240, 230, 210, 0.6) !important;
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }}

    /* Override default button styles for example buttons */
    [data-testid="stHorizontalBlock"] .stButton > button {{
        background: linear-gradient(135deg, rgba(10, 20, 40, 0.9), rgba(0, 30, 50, 0.8)) !important;
        border: 1px solid rgba(200, 155, 60, 0.4) !important;
        color: {LOL_GOLD_LIGHT} !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 400 !important;
        padding: 10px 16px !important;
        border-radius: 20px !important;
        white-space: normal !important;
        height: auto !important;
        min-height: 50px !important;
        line-height: 1.4 !important;
    }}

    [data-testid="stHorizontalBlock"] .stButton > button:hover {{
        background: linear-gradient(135deg, rgba(200, 155, 60, 0.2), rgba(200, 155, 60, 0.1)) !important;
        border-color: {LOL_GOLD} !important;
        box-shadow: 0 0 15px rgba(200, 155, 60, 0.3);
    }}
    </style>
    """

    st.markdown(base_css, unsafe_allow_html=True)


@st.cache_resource
def load_game_data():
    """Load and cache all game data (champions, items, monsters, turrets)."""
    return parse_all_data(
        TTL_FILE_PATH,
        ITEMS_TTL_FILE_PATH,
        MONSTERS_TTL_FILE_PATH,
        TURRETS_TTL_FILE_PATH
    )


@st.cache_resource
def get_openai_client():
    """Get and cache the OpenAI client."""
    return OpenAI(api_key=OPENAI_API_KEY)


def generate_response(
    client: OpenAI,
    question: str,
    data: dict,
    conversation_history: list,
) -> str:
    """Generate a natural language response using OpenAI."""
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


def render_sidebar():
    """Render the sidebar with mode toggle and settings."""
    with st.sidebar:
        # Logo and title in sidebar
        lol_logo_b64 = get_base64_image(os.path.join(ASSETS_DIR, "LoL-Symbol.png"))
        st.markdown(
            f"""
            <div style="text-align: center; padding: 1rem 0;">
                <img src="data:image/png;base64,{lol_logo_b64}" style="width: 60px; margin-bottom: 10px;">
                <h3 style="margin: 0; font-size: 1.1rem;">Settings</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Mode toggle
        st.markdown("##### Mode")
        mode = st.radio(
            "Select Mode",
            ["Live", "Debug"],
            index=0,
            label_visibility="collapsed",
            help="Live mode shows only the chat. Debug mode reveals intent classification and retrieved context."
        )

        # Mode indicator
        if mode == "Live":
            st.markdown(
                '<span class="mode-indicator mode-live">Live Mode</span>',
                unsafe_allow_html=True,
            )
            st.caption("Clean chat interface")
        else:
            st.markdown(
                '<span class="mode-indicator mode-debug">Debug Mode</span>',
                unsafe_allow_html=True,
            )
            st.caption("Shows intent & context panel")

        st.markdown("---")

        # Clear chat button
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_history = []
            st.session_state.retrieved_context = None
            st.session_state.current_intent = None
            st.rerun()

        st.markdown("---")

        # Snapshot Analysis section
        st.markdown("##### Snapshot Analysis")
        st.markdown(
            """
            <div style="font-size: 0.85rem; opacity: 0.8; margin-bottom: 0.5rem;">
                Analyze your game state at minute 10
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Load available games for selection
        available_games = []
        if "available_games" not in st.session_state:
            try:
                from snapshot_analyzer import SnapshotAnalyzer
                from pathlib import Path
                import json
                snapshot_path = Path(GAME_SNAPSHOTS_PATH)
                if snapshot_path.exists():
                    with open(snapshot_path, "r", encoding="utf-8") as f:
                        snapshots = json.load(f)
                        if isinstance(snapshots, list):
                            for i, snap in enumerate(snapshots):
                                user = next((p for p in snap.get("players", []) if p.get("participant_id") == 1), None)
                                champ = user.get("champion", "Unknown") if user else "Unknown"
                                match_id = snap.get("match_id", f"Game {i+1}")
                                available_games.append(f"{champ} ({match_id})")
                st.session_state.available_games = available_games
            except Exception:
                st.session_state.available_games = ["Game 1"]
        else:
            available_games = st.session_state.available_games

        # Game selector (only show if multiple games)
        selected_game_index = 0
        if len(available_games) > 1:
            selected_game = st.selectbox(
                "Select Game",
                available_games,
                index=st.session_state.get("selected_game_index", 0),
                key="game_selector",
            )
            selected_game_index = available_games.index(selected_game)
            st.session_state.selected_game_index = selected_game_index

        # Analysis type selector
        analysis_type = st.selectbox(
            "Analysis Type",
            ["Full Analysis", "Item Recommendations", "Counter Strategies", "Game State"],
            label_visibility="collapsed",
        )

        # Map selection to query
        analysis_queries = {
            "Full Analysis": "Analyze my game snapshot",
            "Item Recommendations": "What items should I build based on my game snapshot?",
            "Counter Strategies": "How do I play against the enemy team in my game?",
            "Game State": "How am I doing in my current game?",
        }

        if st.button("Analyze Game Snapshot", use_container_width=True, type="primary"):
            st.session_state.pending_snapshot_analysis = analysis_queries[analysis_type]
            st.session_state.pending_game_index = selected_game_index
            st.rerun()

        st.markdown("---")

        # Info section
        st.markdown("##### About")
        st.markdown(
            """
            <div style="font-size: 0.85rem; opacity: 0.8;">
                Ask questions about League of Legends champions, items, abilities, and more.
            </div>
            """,
            unsafe_allow_html=True,
        )

        return mode == "Debug"


def render_debug_panel():
    """Render the debug context panel."""
    st.markdown('<div class="debug-header">Debug Context</div>', unsafe_allow_html=True)

    if st.session_state.current_intent:
        with st.expander("Classified Intent", expanded=True):
            st.json(st.session_state.current_intent)

    if st.session_state.retrieved_context:
        # SPARQL queries
        sparql_queries = st.session_state.retrieved_context.get("sparql_queries", [])
        if sparql_queries:
            with st.expander("SPARQL Queries", expanded=False):
                for i, query in enumerate(sparql_queries, 1):
                    st.markdown(f"**Query {i}**")
                    st.code(query, language="sparql")

        # Retrieved data
        with st.expander("Retrieved Data", expanded=True):
            display_data = {
                k: v for k, v in st.session_state.retrieved_context.items()
                if k != "sparql_queries"
            }
            st.json(display_data)
    else:
        st.markdown(
            """
            <div style="text-align: center; padding: 2rem; opacity: 0.6;">
                <p>No context yet</p>
                <p style="font-size: 0.85rem;">Ask a question to see debug info</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main():
    st.set_page_config(
        page_title="LoL Chatbot",
        page_icon="https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/leagueoflegends.svg",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Example questions
    EXAMPLE_QUESTIONS = [
        "Who should I pick to counter enemy team: Yasuo mid, Zed jungle, Jinx ADC?",
        "Which assassins have stealth in their kit?",
        "On Jinx Should I buy IE or The Bloodthirster",
    ]

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "retrieved_context" not in st.session_state:
        st.session_state.retrieved_context = None
    if "current_intent" not in st.session_state:
        st.session_state.current_intent = None
    if "pending_example" not in st.session_state:
        st.session_state.pending_example = None
    if "pending_snapshot_analysis" not in st.session_state:
        st.session_state.pending_snapshot_analysis = None
    if "pending_game_index" not in st.session_state:
        st.session_state.pending_game_index = None

    # Render sidebar and get debug mode state
    debug_mode = render_sidebar()

    # Set custom CSS (after knowing the mode)
    set_custom_css(os.path.join(ASSETS_DIR, "artwork_2.jpg"), debug_mode)

    # Check for API key
    if not OPENAI_API_KEY:
        st.error("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")
        st.stop()

    # Load resources
    try:
        game_data = load_game_data()
        client = get_openai_client()
        retriever = DataRetriever(game_data)
    except Exception as e:
        st.error(f"Error loading game data: {e}")
        st.stop()

    # Title with LoL logo
    lol_logo_b64 = get_base64_image(os.path.join(ASSETS_DIR, "lol_symbol.png"))
    st.markdown(
        f"""
        <div class="lol-title">
            <img src="data:image/png;base64,{lol_logo_b64}" style="height: 50px;">
            League of Legends Chatbot
        </div>
        <p class="lol-subtitle">Ask me anything about champions, items, abilities, and more!</p>
        """,
        unsafe_allow_html=True,
    )

    # Layout based on mode
    if debug_mode:
        chat_col, debug_col = st.columns([2, 1])
    else:
        chat_col = st.container()
        debug_col = None

    # Helper function to process a question
    def process_question(question: str, game_index: int = None):
        """Process a question and generate response."""
        # Add user message to display
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Consulting the Summoner's Rift..."):
                # Classify the intent
                intent = classify_intent(
                    client, question, st.session_state.conversation_history
                )

                # Inject game_index for snapshot analysis
                if game_index is not None and intent.get("intent") == "SNAPSHOT_ANALYSIS":
                    intent["game_index"] = game_index

                # Retrieve relevant data
                retrieved_data = dispatch_query(retriever, intent)

                # Store context for debug panel
                st.session_state.current_intent = intent
                st.session_state.retrieved_context = retrieved_data

                # Generate response
                response = generate_response(
                    client,
                    question,
                    retrieved_data,
                    st.session_state.conversation_history,
                )

                st.markdown(response)

        # Update session state
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.conversation_history.append({"role": "user", "content": question})
        st.session_state.conversation_history.append({"role": "assistant", "content": response})

    # Chat column
    with chat_col:
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Check for pending example question
        if st.session_state.pending_example:
            question = st.session_state.pending_example
            st.session_state.pending_example = None
            process_question(question)
            st.rerun()

        # Check for pending snapshot analysis
        if st.session_state.pending_snapshot_analysis:
            question = st.session_state.pending_snapshot_analysis
            game_index = st.session_state.get("pending_game_index", 0)
            st.session_state.pending_snapshot_analysis = None
            st.session_state.pending_game_index = None
            process_question(question, game_index=game_index)
            st.rerun()

        # Chat input
        if user_input := st.chat_input("Ask about champions, items, abilities..."):
            process_question(user_input)
            st.rerun()

        # Example questions (show only when chat is empty)
        if not st.session_state.messages:
            st.markdown(
                '<p class="example-label">Try one of these questions:</p>',
                unsafe_allow_html=True,
            )
            cols = st.columns(3)
            for i, question in enumerate(EXAMPLE_QUESTIONS):
                with cols[i]:
                    if st.button(question, key=f"example_{i}", use_container_width=True):
                        st.session_state.pending_example = question
                        st.rerun()

    # Debug column (only in debug mode)
    if debug_mode and debug_col:
        with debug_col:
            render_debug_panel()

    # Footer
    st.markdown(
        """
        <div class="footer">
            <span style="opacity: 0.7;">Developed by</span>
            <a href="https://www.linkedin.com/in/atahan-uz/" target="_blank">Atahan Uz</a>
            <span style="opacity: 0.5;">&</span>
            <a href="https://www.linkedin.com/in/gizem7/" target="_blank">Gizem Yılmaz</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

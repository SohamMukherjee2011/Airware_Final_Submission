import json
from google import genai
from config import get_settings

# ---------- GLOBAL GEMINI CLIENT (persistent)
settings = get_settings()
client = genai.Client(api_key=settings.GEMINI_API_KEY)

def build_initial_context(analysis_json):
    return f"""
You are an AQI exposure, pollution, and health advisor.

ANALYSIS:
{json.dumps(analysis_json, indent=2)}

Use this knowledge to answer all future user questions.
Give medically safe, precise, actionable guidance.
"""

def create_aqi_chat_agent(analysis_json):
    system_context = build_initial_context(analysis_json)

    # Create new chat session
    chat = client.chats.create(model="gemini-2.5-flash")

    # Add system context
    chat.send_message(system_context)

    return chat

def user_chat(chat, user_message: str):
    """Send message to the Gemini chat session."""
    response = chat.send_message(user_message)
    return response.text

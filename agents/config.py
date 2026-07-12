import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# We support dynamic configuration from environment or UI
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

def get_api_key():
    global API_KEY
    # Check if loaded in env, if not check global
    if not API_KEY:
        API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    return API_KEY

def set_api_key(key):
    global API_KEY
    API_KEY = key.strip()
    # Also write to env for current process session
    os.environ["GEMINI_API_KEY"] = API_KEY

def is_live_mode():
    key = get_api_key()
    return bool(key and len(key) > 5)

def get_llm(temperature=0.2):
    if is_live_mode():
        # Initialize LangChain Google GenAI client
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=get_api_key(),
            temperature=temperature
        )
    return None

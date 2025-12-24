import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", YOUTUBE_API_KEY)  # Use Gemini key if set, else YouTube key
RAF_TALKS_HANDLE = "@RafTalks"
RAF_TALKS_CHANNEL_ID = ""  # Will be populated at runtime

# Development mode - limit videos shown
DEV_MODE = True
DEV_VIDEO_LIMIT = 20

# Available AI models - simplified list with most useful options
AVAILABLE_MODELS = {
    # Gemini - primary model
    "gemini-2.5-flash-lite": {
        "name": "Gemini 2.5 Flash Lite",
        "description": "Fast, best quality (default)",
        "category": "gemini"
    },
    # Gemma - backup options (instruction-tuned)
    "gemma-3-27b-it": {
        "name": "Gemma 3 27B",
        "description": "Most powerful backup",
        "category": "gemma"
    },
    "gemma-3-4b-it": {
        "name": "Gemma 3 4B",
        "description": "Fast backup option",
        "category": "gemma"
    }
}

# Default model
DEFAULT_MODEL = "gemini-2.5-flash-lite"

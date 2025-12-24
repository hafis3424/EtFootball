import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", YOUTUBE_API_KEY)  # Use Gemini key if set, else YouTube key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Groq API key for GPT models
RAF_TALKS_HANDLE = "@RafTalks"
RAF_TALKS_CHANNEL_ID = ""  # Will be populated at runtime

# Development mode - limit videos shown
DEV_MODE = True
DEV_VIDEO_LIMIT = 20

# Available AI models - organized by provider
AVAILABLE_MODELS = {
    # Gemini - primary model (Google)
    "gemini-2.5-flash-lite": {
        "name": "Gemini 2.5 Flash Lite",
        "description": "Fast, best quality (default)",
        "category": "gemini",
        "provider": "google"
    },
    # Gemma - backup options (Google, instruction-tuned)
    "gemma-3-27b-it": {
        "name": "Gemma 3 27B",
        "description": "Powerful open-source backup",
        "category": "gemma",
        "provider": "google"
    },
    "gemma-3-4b-it": {
        "name": "Gemma 3 4B",
        "description": "Fast open-source backup",
        "category": "gemma",
        "provider": "google"
    },
    # Groq - GPT model (via Groq API)
    "openai/gpt-oss-120b": {
        "name": "GPT-OSS 120B (Groq)",
        "description": "ChatGPT-style via Groq",
        "category": "groq",
        "provider": "groq"
    }
}

# Default model
DEFAULT_MODEL = "gemini-2.5-flash-lite"

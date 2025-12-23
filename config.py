import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", YOUTUBE_API_KEY)  # Use Gemini key if set, else YouTube key
RAF_TALKS_HANDLE = "@RafTalks"
RAF_TALKS_CHANNEL_ID = ""  # Will be populated at runtime

# Development mode - limit videos shown
DEV_MODE = True
DEV_VIDEO_LIMIT = 5

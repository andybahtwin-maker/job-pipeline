
import os

# Keywords that make a job relevant to you. Case-insensitive containment.
KEYWORDS_ANY = [
    "industrial design",
    "design engineer",
    "fabrication",
    "automation",
    "osint",
    "investigator",
    "research",
    "remote",
    "ai",
    "python",
]

MIN_DESCRIPTION_LEN = 80  # ignore ultra-short spammy posts

# Optional Google Sheets settings (detected at runtime)
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
GOOGLE_SHEET_TAB = os.getenv("GOOGLE_SHEET_TAB", "Jobs").strip()
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

# Optional Groq for ranking/summarization (future step)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

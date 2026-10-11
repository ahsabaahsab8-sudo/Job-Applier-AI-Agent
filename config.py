import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# API Keys & Endpoints
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "").strip()
KILO_API_KEY = os.getenv("KILO_API_KEY", "").strip()
KILO_BASE_URL = os.getenv("KILO_BASE_URL", "https://api.kilo.ai/api/gateway/v1").strip()
KILO_MODEL = os.getenv("KILO_MODEL", "kilo-auto/free").strip()

# Candidate Profile
CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Ahsan Ali").strip()
CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL", "ahsantechnical003@gmail.com").strip()
CANDIDATE_PHONE = os.getenv("CANDIDATE_PHONE", "+92 300 8156021").strip()
CANDIDATE_PORTFOLIO = os.getenv("CANDIDATE_PORTFOLIO", "https://natureai.online").strip()
CANDIDATE_GITHUB = os.getenv("CANDIDATE_GITHUB", "https://github.com/ahsabaahsab8-sudo").strip()
RESUME_FILE = os.getenv("RESUME_FILE", "AhsanAli_Resume_v5.pdf").strip()
RESUME_PATH = BASE_DIR / RESUME_FILE

# Gmail Settings
GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", CANDIDATE_EMAIL).strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
GMAIL_TOKEN_JSON = BASE_DIR / os.getenv("GMAIL_TOKEN_JSON", "gmail_token.json")

# Operational Settings
TARGET_ROLES = [
    "Flutter Developer",
    "Mobile App Developer",
    "AI Engineer",
    "WebGL Developer",
    "React Developer"
]
TARGET_KEYWORDS = [
    "flutter", "dart", "mobile", "ios", "android",
    "ai", "artificial intelligence", "agent", "llm", "python",
    "webgl", "three.js", "threejs", "3d", "react"
]
DAILY_JOB_LIMIT = int(os.getenv("DAILY_JOB_LIMIT", "100"))
DRY_RUN = os.getenv("DRY_RUN", "True").lower() in ("true", "1", "yes")

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Database Path
DB_PATH = BASE_DIR / "applied_jobs.db"
CSV_PATH = BASE_DIR / "applied_jobs.csv"

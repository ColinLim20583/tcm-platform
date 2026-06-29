import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = "claude-sonnet-4-5"
DB_PATH = "tcm_knowledge.db"
APP_TITLE = "Chemigran TCM Formulation Intelligence Platform"
APP_SUBTITLE = "AI-Powered TCM Product Development | Singapore & Southeast Asia"
VERSION = "1.0.0"
COMPANY = "Chemigran Pte Ltd"

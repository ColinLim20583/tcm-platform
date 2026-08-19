"""
Configuration.

The Anthropic API key is deliberately NOT read from Streamlit Cloud secrets.
Each user enters their own key in the sidebar, so the deployed app never bills
a shared account.

A local .env is still honoured for development convenience — there is no .env
on Streamlit Cloud, so the deployed sidebar always starts empty.
"""

import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()

DEFAULT_MODEL = "claude-sonnet-4-5"
DB_PATH = "tcm_knowledge.db"
APP_TITLE = "ChemSync™"
APP_SUBTITLE = "AI-powered product discovery that scans, analyses and guides you to the right Chemigran health product"
VERSION = "2.0.0"
COMPANY = "Chemigran Pte Ltd"

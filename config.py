"""
Configuration.

Secrets are resolved in this order, first hit wins:

  1. Streamlit Cloud secrets  -> st.secrets["ANTHROPIC_API_KEY"]
  2. Environment variable     -> ANTHROPIC_API_KEY
  3. Local .env file          -> loaded by python-dotenv

Nothing secret belongs in this file, and .env must stay out of git.
On Streamlit Cloud set the key under: app -> Settings -> Secrets.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _read_secret(name: str, default: str = "") -> str:
    """Look up a secret from Streamlit Cloud, then the environment, then .env."""
    try:
        import streamlit as st

        # st.secrets raises rather than returning None when no secrets file exists,
        # which is the normal case when running locally.
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


ANTHROPIC_API_KEY = _read_secret("ANTHROPIC_API_KEY")

DEFAULT_MODEL = "claude-sonnet-4-5"
DB_PATH = "tcm_knowledge.db"
APP_TITLE = "Chemigran TCM Formulation Intelligence Platform"
APP_SUBTITLE = "AI-Powered TCM Product Development | Singapore & Southeast Asia"
VERSION = "2.0.0"
COMPANY = "Chemigran Pte Ltd"

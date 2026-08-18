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


def _read_secret(name: str, default: str = "") -> tuple[str, str]:
    """
    Look up a secret from Streamlit Cloud, then the environment, then .env.

    Returns (value, source) so the UI can show where the key came from — without
    that, a missing secret is indistinguishable from a misread one.
    """
    try:
        import streamlit as st

        # st.secrets raises rather than returning None when no secrets file
        # exists, which is the normal case when running locally.
        if name in st.secrets:
            value = str(st.secrets[name]).strip()
            if value:
                return value, "Streamlit secrets"
            return "", "secrets key present but empty"
    except Exception as e:
        _secret_error = f"{type(e).__name__}: {e}"
    else:
        _secret_error = "not in secrets"

    env_value = (os.getenv(name) or "").strip()
    if env_value:
        return env_value, "environment / .env"

    return default, _secret_error


ANTHROPIC_API_KEY, ANTHROPIC_KEY_SOURCE = _read_secret("ANTHROPIC_API_KEY")

DEFAULT_MODEL = "claude-sonnet-4-5"
DB_PATH = "tcm_knowledge.db"
APP_TITLE = "Chemigran TCM Formulation Intelligence Platform"
APP_SUBTITLE = "AI-Powered TCM Product Development | Singapore & Southeast Asia"
VERSION = "2.0.0"
COMPANY = "Chemigran Pte Ltd"

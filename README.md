====================================================
Chemigran TCM Formulation Intelligence Platform
====================================================

SETUP (first time):
1. Open this folder in PyCharm
2. Create virtual environment: python -m venv venv
3. Activate: venv\Scripts\activate (Windows) or source venv/bin/activate (Mac)
4. Install: pip install -r requirements.txt
5. (Optional) Copy .env.example to .env and add your API key

RUN:
  streamlit run app.py

Then open http://localhost:8501 in your browser.

USAGE:
1. Enter your Anthropic API key in the sidebar
2. Go to "Formulation Generator" tab
3. Describe the health condition and demographic
4. Click "Generate Formula"
5. Review the product card (formula table, rationale, safety, commercial scores)
6. Save to Knowledge Base
7. Click "Ask AI: full business case" for a deep commercial analysis

FILES:
  app.py               - Main Streamlit application (run this)
  config.py            - Settings and API key configuration
  inventory_data.py    - All 551 Chemigran granule SKUs with TCM properties
  database.py          - SQLite knowledge management
  formulation_engine.py- Claude API integration for AI formulation
  requirements.txt     - Python dependencies
  tcm_knowledge.db     - Auto-created SQLite database (all saved formulations)

KNOWLEDGE MANAGEMENT:
- Every formulation is auto-saved when you click "Save to Knowledge Base"
- Evidence entries from the Evidence Enricher tab are also saved
- Search, star, export, and delete from the Knowledge Base tab
- The SQLite database grows over time as your team generates formulations

SUPPORT: colinlim205@gmail.com

=============================================================
CHEMIGRAN TCM FORMULATION INTELLIGENCE PLATFORM v2.0
=============================================================
AI-Powered TCM Product Development | Chemigran Pte Ltd Singapore

NEW IN v2.0: Visual AI Diagnosis
---------------------------------
- Use your computer webcam or phone camera to scan tongue & face
- Claude Vision analyses TCM patterns from visual cues
- Auto-populates the formulation generator with diagnosis results
- Cross-references against published TCM tongue/face image datasets

SETUP
-----
1. Copy this folder to your computer (e.g. C:\Projects\tcm_platform\)
2. Open terminal / command prompt in that folder
3. Install dependencies:
      pip install -r requirements.txt
4. Copy .env.example to .env and add your Anthropic API key:
      ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxx
5. Launch the app:
      streamlit run app.py
6. Open browser at http://localhost:8501

PLATFORM TABS
-------------
1. Visual AI Diagnosis     — Camera scan (tongue + face) → TCM pattern → auto-fill formula
2. Formulation Generator   — AI generates formulas using 551-herb Chemigran inventory
3. Knowledge Base          — All saved formulations with search, star, export
4. Inventory Browser       — Browse all 100+ key herbs with evidence enrichment
5. Evidence Enricher       — Fetch clinical evidence for herb + condition pairs

CAMERA TIPS (Visual Diagnosis)
-------------------------------
TONGUE SCAN:
  - Good natural or white LED lighting (avoid yellow light)
  - Extend tongue fully, keep flat and relaxed
  - Hold camera 20-30cm away
  - Do NOT eat, drink coffee/coloured foods 30min before

FACE SCAN:
  - Neutral expression, face camera directly
  - Remove heavy makeup
  - Natural daylight or neutral white light
  - No filters or beauty modes

MOBILE USE
----------
Works on phone browser! Open http://YOUR_COMPUTER_IP:8501 on same WiFi.
Run with: streamlit run app.py --server.address 0.0.0.0

REQUIREMENTS
------------
Python 3.9+
Anthropic API key (https://console.anthropic.com)

SUPPORT
-------
Chemigran Pte Ltd, Singapore
colinlim205@gmail.com

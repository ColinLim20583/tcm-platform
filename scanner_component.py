"""
scanner_component.py — guided auto-capture camera.

Wraps components/scanner/index.html, which runs entirely in the browser:

  * live preview with a face or tongue guide outline
  * a scan line sweeping top to bottom over ~2.6 s
  * light / focus / steadiness / position measured on every frame of the sweep
  * capture only if at least 85% of the sweep was clean, otherwise it says what
    is wrong and sweeps again
  * the captured frame is taken from the video track at the camera's NATIVE
    resolution, not the size of the on-screen preview

Scan type drives the sequence: "face" captures one frame, "tongue" one frame,
"full" captures the face, then prompts for the tongue and captures again.

No new Python dependencies and no server-side video processing — everything
above happens client-side, so it costs the Streamlit container nothing.
"""

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_DIR = Path(__file__).parent / "components" / "scanner"

_scanner = components.declare_component("chemsync_scanner", path=str(_DIR))


def scan(scan_type: str = "full", key: str = "scanner") -> dict | None:
    """
    Render the scanner. Returns None until a scan completes, then:

        {"face": bytes|None, "tongue": bytes|None,
         "width": int, "height": int}
    """
    result = _scanner(scan_type=scan_type, key=key, default=None)
    if not result or not result.get("done"):
        return None

    def _decode(data_url):
        if not data_url:
            return None
        try:
            return base64.b64decode(data_url.split(",", 1)[1])
        except Exception:
            return None

    face = _decode(result.get("face"))
    tongue = _decode(result.get("tongue"))
    if not face and not tongue:
        return None

    return {
        "face": face,
        "tongue": tongue,
        "width": result.get("width"),
        "height": result.get("height"),
    }


def primary_image(shot: dict) -> bytes | None:
    """
    The single frame to send for analysis.

    The tongue frame is preferred when present: tongue signs carry more
    diagnostic weight than complexion, and the detector is trained on tongues.
    """
    if not shot:
        return None
    return shot.get("tongue") or shot.get("face")

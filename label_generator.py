"""
Chemigran Premium TCM Label Generator  v2.0
Adobe Illustrator-ready SVG labels.

Formats
-------
  inner   121mm x 42mm   two-panel bottle label (matches Chemigran standard)
  box     59mm x 103mm   retail box front panel
  sachet  40mm x 120mm   granule stick pack

Color themes auto-selected from TCM pattern / tags.
Botanical SVG art: lotus, bamboo, plum blossom, chrysanthemum.
HSA CPM GL-CHPB-4-001 (Jan 2025) compliant fields.
"""

from __future__ import annotations
import math

COMPANY    = "Chemigran Pte Ltd"
COMPANY_ZH = "化美健私人有限公司"

THEMES = {
    "kidney": {
        "bg": "#1B3264", "bg2": "#0F1F42",
        "accent": "#C9A84C", "accent2": "#E8C96A",
        "banner": "#2A4A8C", "text": "#F0ECE0",
        "label": "Kidney", "botanical": "lotus",
    },
    "heart": {
        "bg": "#6B1020", "bg2": "#4A0A14",
        "accent": "#C9A84C", "accent2": "#E8C96A",
        "banner": "#8B1A2A", "text": "#F5EDE8",
        "label": "Heart", "botanical": "plum",
    },
    "liver": {
        "bg": "#1A4028", "bg2": "#0F2818",
        "accent": "#8FBE6A", "accent2": "#B0D880",
        "banner": "#2A5A38", "text": "#EAF2E8",
        "label": "Liver", "botanical": "bamboo",
    },
    "spleen": {
        "bg": "#7B3210", "bg2": "#552208",
        "accent": "#C9A84C", "accent2": "#E8C96A",
        "banner": "#9B4218", "text": "#F5EDE0",
        "label": "Spleen", "botanical": "lotus",
    },
    "lung": {
        "bg": "#2A4A6B", "bg2": "#1A3050",
        "accent": "#A8C8D8", "accent2": "#C8E0EC",
        "banner": "#3A608A", "text": "#EAF0F5",
        "label": "Lung", "botanical": "chrysanthemum",
    },
    "women": {
        "bg": "#6B1A32", "bg2": "#4A1020",
        "accent": "#C9956A", "accent2": "#E8B888",
        "banner": "#8B2442", "text": "#F5EDE8",
        "label": "Women", "botanical": "plum",
    },
    "default": {
        "bg": "#7B2808", "bg2": "#521A04",
        "accent": "#C9A84C", "accent2": "#E8C96A",
        "banner": "#9B3810", "text": "#F5EDE0",
        "label": "TCM Formula", "botanical": "lotus",
    },
}


def _get_theme(fd: dict) -> dict:
    pat = (fd.get("tcm_pattern", "") + " " + " ".join(fd.get("tags", []))).lower()
    # Check organ-specific patterns first (liver/heart/spleen/lung/women) before
    # broad "yin deficiency" so that e.g. "Liver Fire with Yin Deficiency" → liver, not kidney
    if any(k in pat for k in ["liver", "liver fire", "qi stagnat", "eye", "detox", "gallbladder"]):
        return THEMES["liver"]
    if any(k in pat for k in ["heart", "shen", "sleep", "insomnia", "calm", "spirit", "palpitat"]):
        return THEMES["heart"]
    if any(k in pat for k in ["spleen", "stomach", "digest", "fatigue", "damp", "phlegm-damp"]):
        return THEMES["spleen"]
    if any(k in pat for k in ["lung", "cough", "respiratory", "breath", "phlegm-heat"]):
        return THEMES["lung"]
    if any(k in pat for k in ["women", "menstrual", "period", "female", "uterus", "breast"]):
        return THEMES["women"]
    if any(k in pat for k in ["kidney", "renal", "yin defic", "yang defic", "jing", "essence"]):
        return THEMES["kidney"]
    return THEMES["default"]


def _e(s: str, n: int = 9999) -> str:
    s = str(s)[:n]
    return (s.replace("&", "&amp;")
              .replace("<", "&lt;")
              .replace(">", "&gt;")
              .replace('"', "&quot;"))


def _ing_en(formula: list, n: int = 15) -> str:
    return ", ".join(
        f"{h.get('english', h.get('chinese', ''))} {h.get('percentage', 0)}%"
        for h in formula[:n]
    )


def _ing_zh(formula: list, n: int = 15) -> str:
    sep = "、"
    parts = [f"{h['chinese']}{h.get('percentage',0)}%" for h in formula[:n] if h.get("chinese")]
    return sep.join(parts)


# ── BOTANICAL SVG HELPERS ─────────────────────────────────────────────────────

def _lotus(cx, cy, r, color, op=0.18):
    p = []
    for i in range(8):
        a = i * 45
        p.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy-r*0.65:.1f}" rx="{r*0.28:.1f}" ry="{r*0.65:.1f}"'
            f' fill="{color}" opacity="{op:.2f}" transform="rotate({a},{cx:.1f},{cy:.1f})"/>'
        )
    for i in range(8):
        a = i * 45 + 22.5
        p.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy-r*0.38:.1f}" rx="{r*0.18:.1f}" ry="{r*0.38:.1f}"'
            f' fill="{color}" opacity="{op*1.25:.2f}" transform="rotate({a},{cx:.1f},{cy:.1f})"/>'
        )
    p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r*0.18:.1f}" fill="{color}" opacity="{op*2:.2f}"/>')
    p.append(
        f'<path d="M{cx:.1f},{cy:.1f} Q{cx-r*0.8:.1f},{cy+r*0.35:.1f} {cx-r*0.5:.1f},{cy+r*0.7:.1f}"'
        f' stroke="{color}" stroke-width="{r*0.06:.1f}" fill="none" opacity="{op*1.5:.2f}"/>'
    )
    p.append(
        f'<path d="M{cx:.1f},{cy:.1f} Q{cx+r*0.8:.1f},{cy+r*0.35:.1f} {cx+r*0.5:.1f},{cy+r*0.7:.1f}"'
        f' stroke="{color}" stroke-width="{r*0.06:.1f}" fill="none" opacity="{op*1.5:.2f}"/>'
    )
    p.append(
        f'<path d="M{cx:.1f},{cy:.1f} Q{cx:.1f},{cy+r*0.5:.1f} {cx:.1f},{cy+r:.1f}"'
        f' stroke="{color}" stroke-width="{r*0.07:.1f}" fill="none" opacity="{op*1.5:.2f}"/>'
    )
    return "\n".join(p)


def _bamboo(x, y, h, color, op=0.15):
    p = []
    for idx, (ox, w) in enumerate([(0, 2.5), (4.5, 2.0), (-4.0, 1.8)]):
        sh = h / 5
        for j in range(5):
            sy = y - j * sh
            p.append(
                f'<rect x="{x+ox-w/2:.1f}" y="{sy-sh:.1f}" width="{w:.1f}" height="{sh*0.92:.1f}"'
                f' rx="0.5" fill="{color}" opacity="{op:.2f}"/>'
            )
            p.append(
                f'<line x1="{x+ox-w/2:.1f}" y1="{sy:.1f}" x2="{x+ox+w/2:.1f}" y2="{sy:.1f}"'
                f' stroke="{color}" stroke-width="0.4" opacity="{op*2:.2f}"/>'
            )
        ld = 1 if idx % 2 == 0 else -1
        for lv in [1, 2, 3]:
            ly = y - lv * (h / 4)
            p.append(
                f'<path d="M{x+ox:.1f},{ly:.1f} Q{x+ox+ld*8:.1f},{ly-4:.1f} {x+ox+ld*13:.1f},{ly-8:.1f}"'
                f' stroke="{color}" stroke-width="0.8" fill="none" opacity="{op*1.8:.2f}"/>'
            )
    return "\n".join(p)


def _plum(cx, cy, r, color, op=0.16):
    p = []
    pts = [
        (cx, cy), (cx-r*0.45, cy-r*0.4), (cx+r*0.4, cy-r*0.5),
        (cx-r*0.25, cy-r*0.85), (cx+r*0.15, cy-r*0.95),
    ]
    prev = (cx, cy + r * 0.3)
    for bx, by in pts:
        mx, my = (prev[0]+bx)/2, (prev[1]+by)/2 - r*0.08
        p.append(
            f'<path d="M{prev[0]:.1f},{prev[1]:.1f} Q{mx:.1f},{my:.1f} {bx:.1f},{by:.1f}"'
            f' stroke="{color}" stroke-width="{r*0.06:.1f}" fill="none" opacity="{op*2:.2f}"/>'
        )
        for k in range(5):
            a = math.radians(k * 72)
            px2, py2 = bx + math.cos(a)*r*0.17, by + math.sin(a)*r*0.17
            p.append(f'<circle cx="{px2:.1f}" cy="{py2:.1f}" r="{r*0.10:.1f}" fill="{color}" opacity="{op:.2f}"/>')
        p.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{r*0.055:.1f}" fill="{color}" opacity="{op*2:.2f}"/>')
        prev = (bx, by)
    return "\n".join(p)


def _chrysanthemum(cx, cy, r, color, op=0.16):
    p = []
    for i in range(16):
        a = math.radians(i * 22.5)
        x1, y1 = cx + math.cos(a)*r*0.2, cy + math.sin(a)*r*0.2
        x2, y2 = cx + math.cos(a)*r, cy + math.sin(a)*r
        cpx = cx + math.cos(a+0.3)*r*0.7
        cpy = cy + math.sin(a+0.3)*r*0.7
        p.append(
            f'<path d="M{x1:.1f},{y1:.1f} Q{cpx:.1f},{cpy:.1f} {x2:.1f},{y2:.1f}"'
            f' stroke="{color}" stroke-width="{r*0.09:.1f}" fill="none" opacity="{op:.2f}"/>'
        )
    p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r*0.18:.1f}" fill="{color}" opacity="{op*2:.2f}"/>')
    return "\n".join(p)


def _botanical(style, cx, cy, r, color, op=0.16):
    if style == "lotus":          return _lotus(cx, cy, r, color, op)
    if style == "bamboo":         return _bamboo(cx, cy - r*0.3, r*1.8, color, op)
    if style == "plum":           return _plum(cx, cy, r, color, op)
    if style == "chrysanthemum":  return _chrysanthemum(cx, cy, r, color, op)
    return _lotus(cx, cy, r, color, op)


def _logo(x, y, size, bg, fg):
    r = size / 2
    cx, cy = x + r, y + r
    ff = "Helvetica Neue,Arial,sans-serif"
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{bg}"/>'
        f'<text x="{cx:.1f}" y="{cy+r*0.42:.1f}" text-anchor="middle"'
        f' font-size="{r*1.1:.1f}" font-weight="900" fill="{fg}" font-family="{ff}">C</text>'
    )


# ═════════════════════════════════════════════════════════════════════════════
# INNER LABEL  121mm x 42mm
# Two-panel: left = product identity, right = regulatory text
# ═════════════════════════════════════════════════════════════════════════════
def generate_inner_svg(fd: dict) -> str:
    t = _get_theme(fd)
    nzh = _e(fd.get("product_name_zh", "中药配方"), 12)
    nen = _e(fd.get("product_name_en", "TCM Formula"), 35)
    # Short TCM pattern for banner (e.g. "Liver Fire with Yin Deficiency")
    pat_full = fd.get("tcm_pattern", "")
    pat  = _e(pat_full, 45)
    rat  = fd.get("formula_rationale", "Traditionally used for TCM wellness support.")
    ind  = _e(rat, 130)
    dos  = _e(fd.get("dosage_recommendation", "5g twice daily dissolved in warm water"), 120)
    saf  = fd.get("safety", {})
    con  = saf.get("contraindications", [])
    cs   = _e("; ".join(con[:2]) if con else "Consult physician if pregnant or on medication.")
    herbs = fd.get("formula", [])
    ien  = _e(_ing_en(herbs, 12))
    izh  = _e(_ing_zh(herbs, 12))
    nh   = len(herbs)
    sp   = "  ".join(nen.upper()[:24])
    # Right-panel text — ~58 chars per line fits the 62mm panel at 1.8mm font
    d1, d2 = _e(dos[:58]), _e(dos[58:116])
    i1, i2 = _e(ind[:58]), _e(ind[58:116])
    # Banner line 1: first segment of TCM pattern (up to first comma or 30 chars)
    pat_short = pat_full.split(",")[0].split(" with ")[0][:30]
    banner1 = _e(pat_short) if pat_short else "Chinese Proprietary Medicine"
    bot = _botanical(t["botanical"], 28, 22, 16, "#FFFFFF", 0.13)

    ff  = "Helvetica Neue,Arial,sans-serif"
    zff = "Noto Sans SC,PingFang SC,Microsoft YaHei,sans-serif"

    p = []
    p.append('<?xml version="1.0" encoding="UTF-8"?>')
    p.append('<svg xmlns="http://www.w3.org/2000/svg" width="121mm" height="42mm" viewBox="0 0 121 42">')
    p.append('<defs>')
    p.append(
        f'<linearGradient id="lgL" x1="0" y1="0" x2="0.4" y2="1">'
        f'<stop offset="0%" stop-color="{t["bg"]}"/>'
        f'<stop offset="100%" stop-color="{t["bg2"]}"/></linearGradient>'
    )
    p.append(
        f'<linearGradient id="lgB" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{t["banner"]}"/>'
        f'<stop offset="100%" stop-color="{t["bg2"]}"/></linearGradient>'
    )
    p.append('</defs>')
    p.append('<rect width="121" height="42" fill="white"/>')
    p.append(f'<rect x="0.3" y="0.3" width="120.4" height="41.4" fill="none" stroke="{t["bg"]}" stroke-width="0.5"/>')
    p.append('<rect x="0" y="0" width="55" height="42" fill="url(#lgL)"/>')
    p.append(f'<rect x="1.5" y="1.5" width="52" height="39" fill="none" stroke="{t["accent"]}" stroke-width="0.3" opacity="0.55"/>')
    p.append(bot)
    p.append(_logo(3, 3, 5, t["accent"], t["bg"]))
    p.append(f'<text x="9.5" y="6.6" font-size="2.8" font-weight="800" fill="{t["accent"]}" font-family="{ff}" letter-spacing="0.4">CHEMIGRAN</text>')
    p.append(f'<text x="9.5" y="9.4" font-size="1.7" fill="{t["text"]}" opacity="0.75" font-family="{ff}">{COMPANY_ZH}</text>')
    p.append(f'<text x="27.5" y="22" text-anchor="middle" font-size="9.5" font-weight="700" fill="white" font-family="{zff}" opacity="0.96">{nzh}</text>')
    p.append(f'<text x="27.5" y="27" text-anchor="middle" font-size="2.0" fill="{t["accent"]}" font-family="{ff}" letter-spacing="1.1">{sp[:36]}</text>')
    p.append('<rect x="2" y="29" width="51" height="9" rx="1.5" fill="url(#lgB)" opacity="0.88"/>')
    p.append(f'<text x="27.5" y="32.8" text-anchor="middle" font-size="2.1" fill="{t["accent2"]}" font-weight="700" font-family="{zff}">{banner1}</text>')
    p.append(f'<text x="27.5" y="36.3" text-anchor="middle" font-size="1.85" fill="white" font-family="{ff}" font-style="italic" opacity="0.88">{pat[:42]}</text>')
    p.append(f'<text x="3" y="39.8" font-size="1.65" fill="{t["text"]}" opacity="0.65" font-family="{ff}">Reg. No.: [SINCPM XXXXXXXX]</text>')
    p.append(f'<text x="52" y="39.8" text-anchor="end" font-size="1.9" fill="{t["accent"]}" font-weight="700" font-family="{ff}">{nh} herbs</text>')
    p.append(f'<line x1="55" y1="0" x2="55" y2="42" stroke="{t["bg"]}" stroke-width="0.6"/>')
    p.append(f'<line x1="57" y1="2" x2="119.5" y2="2" stroke="{t["accent"]}" stroke-width="0.25" opacity="0.45"/>')
    p.append(f'<line x1="57" y1="40.5" x2="119.5" y2="40.5" stroke="{t["accent"]}" stroke-width="0.25" opacity="0.45"/>')
    hd = f'font-size="1.95" font-weight="700" fill="{t["bg"]}" font-family="{ff}"'
    tx = f'font-size="1.8" fill="#222" font-family="{ff}"'
    sm = f'font-size="1.7" fill="#333" font-family="{ff}"'
    p.append(f'<text x="57" y="5.8" {hd}>Indication:</text>')
    p.append(f'<text x="57" y="8.5" {tx}>{i1}</text>')
    p.append(f'<text x="57" y="10.9" {tx}>{i2}</text>')
    p.append(f'<text x="57" y="14" {hd}>Dosage and Administration:</text>')
    p.append(f'<text x="57" y="16.7" {tx}>{d1}</text>')
    p.append(f'<text x="57" y="19.1" {tx}>{d2}</text>')
    p.append(f'<text x="57" y="22.5" {hd}>Ingredients:</text>')
    p.append(f'<text x="57" y="25.0" font-size="1.72" fill="#222" font-family="{ff}">{_e(ien[:62])}</text>')
    p.append(f'<text x="57" y="27.1" font-size="1.72" fill="#222" font-family="{ff}">{_e(ien[62:124])}</text>')
    p.append(f'<text x="57" y="29.0" font-size="1.65" fill="#444" font-family="{zff}">{_e(izh[:45])}</text>')
    p.append(f'<text x="57" y="31.2" {hd}>Cautions:</text>')
    p.append(f'<text x="57" y="33.5" {sm}>{_e(cs[:62])}</text>')
    p.append(f'<text x="57" y="35.5" {sm}>Storage: Cool dry place below 30 C. Keep from children.</text>')
    p.append(f'<text x="57" y="37.5" font-size="1.6" fill="#555" font-family="{ff}">Allowed for sale as a CPM. {COMPANY}</text>')
    p.append(f'<text x="57" y="39.4" font-size="1.6" fill="#555" font-family="{ff}">[Batch No]  [Expiry date]  Made in Singapore</text>')
    p.append('</svg>')
    return "\n".join(p)


# ═════════════════════════════════════════════════════════════════════════════
# BOX FRONT  59mm x 103mm
# Rich colored panel with botanical art (matches Liu Wei box aesthetic)
# ═════════════════════════════════════════════════════════════════════════════
def generate_box_svg(fd: dict) -> str:
    t = _get_theme(fd)
    nzh  = _e(fd.get("product_name_zh", "中药配方"), 10)
    nen  = _e(fd.get("product_name_en", "TCM Formula"), 28)
    pat  = _e(fd.get("tcm_pattern", ""), 40)
    herbs = fd.get("formula", [])
    key_s = _e("  x  ".join(h.get("english", h.get("chinese", "")) for h in herbs[:3]))
    com  = fd.get("commercial", {})
    usp  = _e(com.get("usp", "Evidence-based TCM formulation")[:55])
    dos  = _e(fd.get("dosage_recommendation", "5g twice daily")[:55])
    nh   = len(herbs)
    sp   = "  ".join(nen.upper()[:22])
    bot  = _botanical(t["botanical"], 29.5, 58, 30, "#FFFFFF", 0.11)

    ff  = "Helvetica Neue,Arial,sans-serif"
    zff = "Noto Sans SC,PingFang SC,Microsoft YaHei,sans-serif"

    p = []
    p.append('<?xml version="1.0" encoding="UTF-8"?>')
    p.append('<svg xmlns="http://www.w3.org/2000/svg" width="59mm" height="103mm" viewBox="0 0 59 103">')
    p.append('<defs>')
    p.append(
        f'<linearGradient id="bg" x1="0" y1="0" x2="0.25" y2="1">'
        f'<stop offset="0%" stop-color="{t["bg"]}"/>'
        f'<stop offset="100%" stop-color="{t["bg2"]}"/></linearGradient>'
    )
    p.append('</defs>')
    p.append('<rect width="59" height="103" fill="url(#bg)"/>')
    p.append(f'<rect x="0" y="0" width="59" height="1.2" fill="{t["accent"]}"/>')
    p.append(f'<rect x="0" y="101.8" width="59" height="1.2" fill="{t["accent"]}"/>')
    p.append(f'<rect x="0" y="0" width="1.2" height="103" fill="{t["accent"]}"/>')
    p.append(f'<rect x="57.8" y="0" width="1.2" height="103" fill="{t["accent"]}"/>')
    p.append(f'<rect x="3" y="3" width="53" height="97" fill="none" stroke="{t["accent"]}" stroke-width="0.3" opacity="0.4"/>')
    p.append(bot)
    p.append(_logo(4, 5, 6.5, t["accent"], t["bg"]))
    p.append(f'<text x="12" y="9.8" font-size="3.2" font-weight="800" fill="{t["accent"]}" font-family="{ff}" letter-spacing="0.5">CHEMIGRAN</text>')
    p.append(f'<text x="12" y="13.2" font-size="1.9" fill="{t["text"]}" opacity="0.7" font-family="{ff}">{COMPANY_ZH}</text>')
    p.append(f'<line x1="4" y1="16" x2="55" y2="16" stroke="{t["accent"]}" stroke-width="0.5"/>')
    p.append(f'<text x="29.5" y="37" text-anchor="middle" font-size="13.5" font-weight="700" fill="white" font-family="{zff}" opacity="0.97">{nzh}</text>')
    p.append(f'<text x="29.5" y="42.5" text-anchor="middle" font-size="2.1" fill="{t["accent"]}" font-family="{ff}" letter-spacing="1.4">{sp[:36]}</text>')
    p.append(f'<text x="29.5" y="47" text-anchor="middle" font-size="1.95" fill="{t["text"]}" font-family="{ff}" font-style="italic" opacity="0.8">{pat[:38]}</text>')
    p.append(f'<line x1="8" y1="49.5" x2="51" y2="49.5" stroke="{t["accent"]}" stroke-width="0.5"/>')
    p.append(f'<text x="29.5" y="54" text-anchor="middle" font-size="1.9" fill="{t["text"]}" font-family="{ff}" opacity="0.8">Key herbs: {key_s}</text>')
    p.append(f'<text x="29.5" y="58.5" text-anchor="middle" font-size="2.0" fill="{t["text"]}" font-family="{ff}" opacity="0.88">{usp[:40]}</text>')
    p.append(f'<text x="29.5" y="62" text-anchor="middle" font-size="2.0" fill="{t["text"]}" font-family="{ff}" opacity="0.88">{usp[40:]}</text>')
    p.append(f'<rect x="6" y="64.5" width="47" height="8" rx="4" fill="none" stroke="{t["accent"]}" stroke-width="0.6"/>')
    p.append(f'<text x="29.5" y="70" text-anchor="middle" font-size="2.15" fill="{t["accent"]}" font-weight="700" font-family="{ff}" letter-spacing="0.3">CHINESE PROPRIETARY MEDICINE</text>')
    p.append(f'<line x1="4" y1="75" x2="55" y2="75" stroke="{t["accent"]}" stroke-width="0.4"/>')
    p.append(f'<text x="29.5" y="80" text-anchor="middle" font-size="2.2" fill="white" font-family="{ff}" font-weight="700">{nh} Herb Formula  30 servings x 5g</text>')
    p.append(f'<text x="29.5" y="84" text-anchor="middle" font-size="1.9" fill="{t["text"]}" font-family="{ff}" opacity="0.85">{dos[:50]}</text>')
    p.append(f'<text x="29.5" y="88.5" text-anchor="middle" font-size="2.0" fill="{t["accent2"]}" font-family="{zff}">Traditional Formula  {t["label"]}</text>')
    p.append(f'<rect x="6" y="91" width="13" height="13" rx="1" fill="none" stroke="{t["accent"]}" stroke-width="0.5"/>')
    p.append(f'<text x="12.5" y="100" text-anchor="middle" font-size="1.5" fill="{t["accent"]}" opacity="0.65" font-family="{ff}">QR CODE</text>')
    p.append(f'<text x="21.5" y="95" font-size="1.7" fill="{t["text"]}" opacity="0.7" font-family="{ff}">{COMPANY}</text>')
    p.append(f'<text x="21.5" y="97.8" font-size="1.6" fill="{t["text"]}" opacity="0.6" font-family="{ff}">Singapore 658077</text>')
    p.append(f'<text x="21.5" y="100.5" font-size="1.6" fill="{t["text"]}" opacity="0.6" font-family="{ff}">[Batch]  [Mfg]  [Exp]</text>')
    p.append(f'<text x="29.5" y="102.5" text-anchor="middle" font-size="1.6" fill="{t["accent"]}" font-family="{ff}" opacity="0.8">Reg. No.: [SINCPM XXXXXXXX]</text>')
    p.append('</svg>')
    return "\n".join(p)


# ═════════════════════════════════════════════════════════════════════════════
# SACHET  40mm x 120mm
# ═════════════════════════════════════════════════════════════════════════════
def generate_sachet_svg(fd: dict) -> str:
    t = _get_theme(fd)
    nzh  = _e(fd.get("product_name_zh", "中药配方"), 8)
    nen  = _e(fd.get("product_name_en", "TCM Formula"), 26)
    pat  = _e(fd.get("tcm_pattern", ""), 36)
    dos  = _e(fd.get("dosage_recommendation", "5g once or twice daily dissolved in warm water"), 130)
    saf  = fd.get("safety", {})
    con  = saf.get("contraindications", [])
    cs   = _e("; ".join(con[:2]) if con else "Consult physician if pregnant or on medication.")
    herbs = fd.get("formula", [])
    ien  = _e(_ing_en(herbs, 12))
    izh  = _e(_ing_zh(herbs, 12))
    sp   = "  ".join(nen.upper()[:18])
    d1, d2 = _e(dos[:60]), _e(dos[60:120])
    bot  = _botanical(t["botanical"], 20, 52, 21, "#FFFFFF", 0.12)

    ff  = "Helvetica Neue,Arial,sans-serif"
    zff = "Noto Sans SC,PingFang SC,Microsoft YaHei,sans-serif"

    p = []
    p.append('<?xml version="1.0" encoding="UTF-8"?>')
    p.append('<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="120mm" viewBox="0 0 40 120">')
    p.append('<defs>')
    p.append(
        f'<linearGradient id="sg" x1="0" y1="0" x2="0.2" y2="1">'
        f'<stop offset="0%" stop-color="{t["bg"]}"/>'
        f'<stop offset="100%" stop-color="{t["bg2"]}"/></linearGradient>'
    )
    p.append(
        f'<linearGradient id="sb" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{t["banner"]}"/>'
        f'<stop offset="100%" stop-color="{t["bg2"]}"/></linearGradient>'
    )
    p.append('</defs>')
    p.append('<rect width="40" height="120" fill="url(#sg)"/>')
    p.append(f'<rect x="0" y="0" width="40" height="1.0" fill="{t["accent"]}"/>')
    p.append(f'<rect x="0" y="119" width="40" height="1.0" fill="{t["accent"]}"/>')
    p.append(f'<rect x="0" y="0" width="0.8" height="120" fill="{t["accent"]}"/>')
    p.append(f'<rect x="39.2" y="0" width="0.8" height="120" fill="{t["accent"]}"/>')
    p.append(f'<rect x="2" y="2" width="36" height="116" fill="none" stroke="{t["accent"]}" stroke-width="0.25" opacity="0.4"/>')
    p.append(bot)
    p.append(_logo(3, 3.5, 5, t["accent"], t["bg"]))
    p.append(f'<text x="9.5" y="7.1" font-size="2.8" font-weight="800" fill="{t["accent"]}" font-family="{ff}" letter-spacing="0.3">CHEMIGRAN</text>')
    p.append(f'<text x="9.5" y="10" font-size="1.7" fill="{t["text"]}" opacity="0.7" font-family="{ff}">{COMPANY_ZH}</text>')
    p.append(f'<line x1="3" y1="12" x2="37" y2="12" stroke="{t["accent"]}" stroke-width="0.4"/>')
    p.append(f'<text x="20" y="30" text-anchor="middle" font-size="10.5" font-weight="700" fill="white" font-family="{zff}" opacity="0.96">{nzh}</text>')
    p.append(f'<text x="20" y="36.2" text-anchor="middle" font-size="1.95" fill="{t["accent"]}" font-family="{ff}" letter-spacing="1.1">{sp[:28]}</text>')
    p.append(f'<text x="20" y="40.2" text-anchor="middle" font-size="1.85" fill="{t["text"]}" font-family="{ff}" font-style="italic" opacity="0.8">{pat[:34]}</text>')
    p.append(f'<line x1="5" y1="42.5" x2="35" y2="42.5" stroke="{t["accent"]}" stroke-width="0.35"/>')
    p.append('<rect x="3" y="44" width="34" height="7.5" rx="1.5" fill="url(#sb)" opacity="0.9"/>')
    p.append(f'<text x="20" y="47.5" text-anchor="middle" font-size="2.1" fill="{t["accent2"]}" font-weight="700" font-family="{zff}">{t["label"]}</text>')
    p.append(f'<text x="20" y="50.7" text-anchor="middle" font-size="1.8" fill="white" font-family="{ff}" opacity="0.88">Chinese Proprietary Medicine</text>')
    p.append(f'<text x="3" y="56" font-size="1.7" fill="{t["text"]}" opacity="0.85" font-family="{ff}">Net Weight: 5g per sachet</text>')
    p.append(f'<line x1="3" y1="58" x2="37" y2="58" stroke="{t["accent"]}" stroke-width="0.25" opacity="0.45"/>')
    p.append(f'<text x="3" y="61.5" font-size="1.85" fill="{t["accent"]}" font-weight="700" font-family="{ff}">Dosage</text>')
    p.append(f'<text x="3" y="64.5" font-size="1.78" fill="{t["text"]}" font-family="{ff}">{d1}</text>')
    p.append(f'<text x="3" y="67.2" font-size="1.78" fill="{t["text"]}" font-family="{ff}">{d2}</text>')
    p.append(f'<line x1="3" y1="69.5" x2="37" y2="69.5" stroke="{t["accent"]}" stroke-width="0.25" opacity="0.45"/>')
    p.append(f'<text x="3" y="73" font-size="1.85" fill="{t["accent"]}" font-weight="700" font-family="{ff}">Ingredients</text>')
    p.append(f'<text x="3" y="76" font-size="1.72" fill="{t["text"]}" font-family="{ff}">{_e(ien[:73])}</text>')
    p.append(f'<text x="3" y="78.7" font-size="1.72" fill="{t["text"]}" font-family="{ff}">{_e(ien[73:146])}</text>')
    p.append(f'<text x="3" y="81.4" font-size="1.72" fill="{t["text"]}" opacity="0.8" font-family="{zff}">{_e(izh[:50])}</text>')
    p.append(f'<line x1="3" y1="83.5" x2="37" y2="83.5" stroke="{t["accent"]}" stroke-width="0.25" opacity="0.45"/>')
    p.append(f'<text x="3" y="87" font-size="1.85" fill="{t["accent"]}" font-weight="700" font-family="{ff}">Cautions</text>')
    p.append(f'<text x="3" y="89.7" font-size="1.72" fill="{t["text"]}" font-family="{ff}">{_e(cs[:73])}</text>')
    p.append(f'<text x="3" y="92.4" font-size="1.72" fill="{t["text"]}" font-family="{ff}">Store below 30 C. Keep out of reach of children.</text>')
    p.append(f'<text x="3" y="95.1" font-size="1.65" fill="{t["text"]}" opacity="0.8" font-family="{ff}">For traditional use only.</text>')
    p.append(f'<line x1="3" y1="97" x2="37" y2="97" stroke="{t["accent"]}" stroke-width="0.25" opacity="0.45"/>')
    p.append(f'<text x="3" y="100.2" font-size="1.55" fill="{t["text"]}" opacity="0.72" font-family="{ff}">Allowed for sale as a Chinese Proprietary</text>')
    p.append(f'<text x="3" y="102.6" font-size="1.55" fill="{t["text"]}" opacity="0.72" font-family="{ff}">Medicine. Consumer discretion is advised.</text>')
    p.append(f'<line x1="3" y1="104.5" x2="37" y2="104.5" stroke="{t["accent"]}" stroke-width="0.3"/>')
    p.append(f'<text x="20" y="108.2" text-anchor="middle" font-size="1.7" fill="{t["text"]}" opacity="0.8" font-family="{ff}">{COMPANY}  Singapore</text>')
    p.append(f'<text x="20" y="113.7" text-anchor="middle" font-size="1.72" fill="{t["accent"]}" font-family="{ff}">[Batch No]  Exp: [MM/YYYY]</text>')
    p.append(f'<text x="20" y="116.5" text-anchor="middle" font-size="1.6" fill="{t["text"]}" opacity="0.65" font-family="Helvetica Neue,Arial,sans-serif">Reg. No.: [SINCPM XXXXXXXX]</text>')
    p.append(f'<text x="20" y="119" text-anchor="middle" font-size="1.55" fill="{t["text"]}" opacity="0.55" font-family="{ff}">Made in Singapore</text>')
    p.append('</svg>')
    return "\n".join(p)


# ── PUBLIC API ────────────────────────────────────────────────────────────────
def generate_label(formula_data: dict, format_type: str = "inner") -> str:
    fmt = format_type.lower().strip()
    if fmt in ("inner", "bottle"):  return generate_inner_svg(formula_data)
    if fmt in ("box", "front"):     return generate_box_svg(formula_data)
    if fmt in ("sachet", "stick"):  return generate_sachet_svg(formula_data)
    raise ValueError(f"Unknown format '{format_type}'. Choose: inner | box | sachet")
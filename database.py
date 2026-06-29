import sqlite3
import json
from datetime import datetime
from config import DB_PATH


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS formulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            session_name TEXT,
            condition_input TEXT,
            tcm_pattern TEXT,
            demographic TEXT,
            product_name_en TEXT,
            product_name_zh TEXT,
            formula_json TEXT,
            rationale TEXT,
            safety_json TEXT,
            evidence TEXT,
            commercial_json TEXT,
            dosage TEXT,
            gross_margin_est TEXT,
            formula_complexity TEXT,
            tags TEXT,
            notes TEXT,
            starred INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS knowledge_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            herb_chinese TEXT,
            herb_english TEXT,
            evidence_text TEXT,
            source TEXT,
            category TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            label TEXT,
            query_count INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


def save_formulation(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO formulations (
            created_at, session_name, condition_input, tcm_pattern, demographic,
            product_name_en, product_name_zh, formula_json, rationale,
            safety_json, evidence, commercial_json, dosage,
            gross_margin_est, formula_complexity, tags, notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        datetime.now().isoformat(),
        data.get("session_name", ""),
        data.get("condition_input", ""),
        data.get("tcm_pattern", ""),
        data.get("demographic", ""),
        data.get("product_name_en", ""),
        data.get("product_name_zh", ""),
        json.dumps(data.get("formula", []), ensure_ascii=False),
        data.get("rationale", ""),
        json.dumps(data.get("safety", {}), ensure_ascii=False),
        data.get("evidence", ""),
        json.dumps(data.get("commercial", {}), ensure_ascii=False),
        data.get("dosage", ""),
        data.get("gross_margin_est", ""),
        data.get("formula_complexity", ""),
        json.dumps(data.get("tags", []), ensure_ascii=False),
        data.get("notes", ""),
    ))
    row_id = c.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_all_formulations():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM formulations ORDER BY created_at DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    for r in rows:
        for key in ("formula_json", "safety_json", "commercial_json", "tags"):
            try:
                r[key] = json.loads(r[key]) if r[key] else {}
            except Exception:
                pass
    return rows


def get_formulation_by_id(fid: int):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM formulations WHERE id=?", (fid,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    r = dict(row)
    for key in ("formula_json", "safety_json", "commercial_json", "tags"):
        try:
            r[key] = json.loads(r[key]) if r[key] else {}
        except Exception:
            pass
    return r


def toggle_star(fid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE formulations SET starred = 1 - starred WHERE id=?", (fid,))
    conn.commit()
    conn.close()


def delete_formulation(fid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM formulations WHERE id=?", (fid,))
    conn.commit()
    conn.close()


def search_formulations(query: str):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    like = f"%{query}%"
    c.execute("""
        SELECT * FROM formulations
        WHERE product_name_en LIKE ? OR product_name_zh LIKE ?
           OR condition_input LIKE ? OR tcm_pattern LIKE ? OR tags LIKE ?
        ORDER BY created_at DESC
    """, (like, like, like, like, like))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    for r in rows:
        for key in ("formula_json", "safety_json", "commercial_json", "tags"):
            try:
                r[key] = json.loads(r[key]) if r[key] else {}
            except Exception:
                pass
    return rows


def save_knowledge_entry(herb_chinese, herb_english, evidence_text, source="", category=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO knowledge_entries (created_at, herb_chinese, herb_english, evidence_text, source, category)
        VALUES (?,?,?,?,?,?)
    """, (datetime.now().isoformat(), herb_chinese, herb_english, evidence_text, source, category))
    conn.commit()
    conn.close()


def get_knowledge_entries(herb_chinese=""):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if herb_chinese:
        c.execute("SELECT * FROM knowledge_entries WHERE herb_chinese LIKE ? ORDER BY created_at DESC", (f"%{herb_chinese}%",))
    else:
        c.execute("SELECT * FROM knowledge_entries ORDER BY created_at DESC LIMIT 100")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM formulations")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM formulations WHERE starred=1")
    starred = c.fetchone()[0]
    c.execute("SELECT tcm_pattern, COUNT(*) as cnt FROM formulations GROUP BY tcm_pattern ORDER BY cnt DESC LIMIT 5")
    top_patterns = c.fetchall()
    conn.close()
    return {"total": total, "starred": starred, "top_patterns": top_patterns}

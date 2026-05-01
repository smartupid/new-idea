import sqlite3
from typing import Iterable, Dict

def init_db(db_path: str = "yahoo_52wk_gainers.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS gainers (
            id INTEGER PRIMARY KEY,
            scraped_at TEXT,
            symbol TEXT,
            name TEXT,
            last TEXT,
            change TEXT,
            percent_change TEXT,
            volume TEXT,
            avg_volume TEXT,
            market_cap TEXT,
            pe_ratio TEXT,
            _52wk_change TEXT,
            _52wk_range TEXT
        )
        """
    )
    conn.commit()
    return conn

def insert_rows(conn: sqlite3.Connection, rows: Iterable[Dict], scraped_at: str):
    c = conn.cursor()
    for r in rows:
        c.execute(
            "INSERT INTO gainers (scraped_at, symbol, name, last, change, percent_change, volume, avg_volume, market_cap, pe_ratio, _52wk_change, _52wk_range) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scraped_at,
                r.get("symbol"),
                r.get("name"),
                r.get("last"),
                r.get("change"),
                r.get("percent_change"),
                r.get("volume"),
                r.get("avg_volume"),
                r.get("market_cap"),
                r.get("pe_ratio"),
                r.get("_52wk_change"),
                r.get("_52wk_range"),
            ),
        )
    conn.commit()

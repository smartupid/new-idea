import requests
import pandas as pd
import time
from datetime import datetime
import sqlite3
import json

BASE_URL = "https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved"

HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
    "Connection": "keep-alive",
}

SHORT_COLS_MAP = {
    "symbol": "Symbol",
    "shortName": "Name",
    "regularMarketPrice": "Price (Intraday)",
    "regularMarketChange": "Change",
    "regularMarketChangePercent": "% Change",
    "regularMarketVolume": "Volume",
    "averageDailyVolume3Month": "Avg Vol (3 month)",
    "marketCap": "Market Cap",
    "trailingPE": "PE Ratio (TTM)",
}

def fetch_page(session, scr_id, start, count=100, timeout=15):
    params = {
        "count": count,
        "formatted": "false",
        "lang": "en-US",
        "region": "US",
        "scrIds": scr_id,
        "start": start,
    }
    for attempt in range(4):
        resp = session.get(BASE_URL, headers=HDRS, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        time.sleep(1.2 * (attempt + 1))
    resp.raise_for_status()

def fetch_all(scr_id, warmup_url, count_per_page=100, pause=0.8, max_pages=200):
    all_rows = []
    start = 0
    with requests.Session() as sess:
        sess.get(warmup_url, headers=HDRS, timeout=15)
        for _ in range(max_pages):
            data = fetch_page(sess, scr_id, start, count_per_page)
            try:
                quotes = data["finance"]["result"][0]["quotes"]
            except (KeyError, IndexError, TypeError):
                break
            if not quotes:
                break
            all_rows.extend(quotes)
            start += count_per_page
            time.sleep(pause)
    return pd.DataFrame(all_rows)

def clean_for_sqlite(df):
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: json.dumps(list(x) if isinstance(x, set) else x)
            if isinstance(x, (list, dict, set)) else x
        )
    return df

def _sqlite_type(series):
    if pd.api.types.is_integer_dtype(series):
        return "INTEGER"
    if pd.api.types.is_float_dtype(series):
        return "REAL"
    return "TEXT"

def save_to_sqlite(df, db_name, table_name):
    df = clean_for_sqlite(df)
    df["run_date"] = datetime.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if cur.fetchone():
        cur.execute(f"PRAGMA table_info({table_name})")
        existing = {row[1] for row in cur.fetchall()}
        for col in df.columns:
            if col not in existing:
                cur.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" {_sqlite_type(df[col])}')
        conn.commit()
    df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.close()
    print(f"Appended {len(df)} rows to {db_name} in table '{table_name}'.")

def run(label, scr_id, warmup_url, long_db, short_db, table_name):
    print(f"\n--- {label} ---")
    df_long = fetch_all(scr_id, warmup_url)
    print(f"Retrieved {len(df_long)} rows from API")
    save_to_sqlite(df_long, long_db, table_name)
    available = [c for c in SHORT_COLS_MAP if c in df_long.columns]
    df_short = df_long[available].rename(columns=SHORT_COLS_MAP)
    save_to_sqlite(df_short, short_db, table_name)

if __name__ == "__main__":
    run(
        label="Gainers",
        scr_id="day_gainers",
        warmup_url="https://finance.yahoo.com/markets/stocks/gainers/",
        long_db="yahoo_gainers_long.db",
        short_db="yahoo_gainers_short.db",
        table_name="gainers_history",
    )
    run(
        label="Losers",
        scr_id="day_losers",
        warmup_url="https://finance.yahoo.com/markets/stocks/losers/",
        long_db="yahoo_losers_long.db",
        short_db="yahoo_losers_short.db",
        table_name="losers_history",
    )

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

def fetch_page(session, start, count=100, timeout=15, scrIds="gainers"):
    params = {
        "count": count,
        "formatted": "false",
        "lang": "en-US",
        "region": "US",
        "scrIds": scrIds,
        "start": start,
    }
    for attempt in range(4):
        resp = session.get(BASE_URL, headers=HDRS, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        time.sleep(1.2 * (attempt + 1))
    resp.raise_for_status()


def fetch_all(scrIds, total=500, count_per_page=100, pause=0.8):
    """Generic fetcher for any Yahoo predefined screener."""
    all_rows = []
    start = 0
    with requests.Session() as sess:
        sess.get("https://finance.yahoo.com/markets/stocks/52-week-gainers/", headers=HDRS, timeout=15)
        while start < total:
            data = fetch_page(sess, start, count_per_page, scrIds=scrIds)
            try:
                quotes = data["finance"]["result"][0]["quotes"]
            except (KeyError, IndexError, TypeError):
                break
            if not quotes:
                break
            all_rows.extend(quotes)
            start += count_per_page
            time.sleep(pause)
    return pd.DataFrame(all_rows[:total])


def clean_for_sqlite(df):
    """Convert any list/dict/set values to JSON strings so SQLite can store them."""
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: json.dumps(x) if isinstance(x, (list, dict, set)) else x
        )
    return df

def save_to_sqlite(df, db_name, table_name):
    df = clean_for_sqlite(df)
    df["run_date"] = datetime.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(db_name)
    df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.close()
    print(f"Appended {len(df)} rows to {db_name} in table '{table_name}'.")


if __name__ == "__main__":
    # Existing daily gainers
    # df_long = fetch_all("day_gainers", total=2000)  # keep your original
    # print(f"Retrieved {len(df_long)} daily gainers")
    # save_to_sqlite(df_long, "yahoo_gainers_long.db", "gainers_history")

    # New: 52-week gainers (first 500)
    df_52wk = fetch_all("52_week_gainers", total=500)
    print(f"Retrieved {len(df_52wk)} 52-week gainers")
    save_to_sqlite(df_52wk, "yahoo_gainers_long.db", "gainers_52week")
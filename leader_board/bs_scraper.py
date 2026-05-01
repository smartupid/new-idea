import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

def _extract_first_number(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"[0-9]+[\,0-9]*(?:\.[0-9]+)?", text)
    return m.group(0) if m else text.strip()


def parse_table(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []
    tbody = table.find("tbody")
    if not tbody:
        return []
    rows = tbody.find_all("tr")
    data = []
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 12:
            continue
        def get_td(idx):
            if idx < 0 or idx >= len(tds):
                return ""
            return tds[idx].get_text(" ", strip=True)

        # Hardcoded positions (accounting for embedded sparkline at col 2):
        # 0: symbol, 1: name, 2: sparkline (skip), 3: last, 4: change, 5: percent,
        # 6: volume, 7: avg_volume, 8: market_cap, 9: pe_ratio, 10: _52wk_change, 11: _52wk_range
        symbol = get_td(0)
        name = get_td(1)
        last_raw = get_td(3)
        last = _extract_first_number(last_raw)
        change = get_td(4)
        percent = get_td(5)
        volume = get_td(6)
        avg_volume = get_td(7)
        market_cap = get_td(8)
        pe_ratio = get_td(9)
        wk52_change = get_td(10)
        wk52_range = get_td(11)

        data.append({
            "symbol": symbol,
            "name": name,
            "last": last,
            "change": change,
            "percent_change": percent,
            "volume": volume,
            "avg_volume": avg_volume,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "_52wk_change": wk52_change,
            "_52wk_range": wk52_range,
        })
    return data

def scrape_url(url: str) -> List[Dict]:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return parse_table(r.text)

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://finance.yahoo.com/markets/stocks/52-week-gainers/?start=0&count=100"
    rows = scrape_url(url)
    print(f"Found {len(rows)} rows")
    if rows:
        import json
        print(json.dumps(rows[0], ensure_ascii=False, indent=2))

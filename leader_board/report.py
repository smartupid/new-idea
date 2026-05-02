import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Value parsers — return float for data-val sorting; NaN when unparseable
# ---------------------------------------------------------------------------

def _parse_pct(s: str) -> float:
    """'+247.89%' → 247.89, '-5.12%' → -5.12"""
    if not s:
        return math.nan
    try:
        return float(s.strip().replace('%', '').replace(',', '').replace('+', ''))
    except ValueError:
        return math.nan


def _parse_abbrev(s: str) -> float:
    """'1.23B' → 1.23e9, '456.78M' → 4.5678e8, etc."""
    if not s:
        return math.nan
    s = s.strip().replace(',', '').replace('+', '')
    mult = {'T': 1e12, 'B': 1e9, 'M': 1e6, 'K': 1e3}
    if s and s[-1].upper() in mult:
        try:
            return float(s[:-1]) * mult[s[-1].upper()]
        except ValueError:
            return math.nan
    try:
        return float(s)
    except ValueError:
        return math.nan


def _parse_float(s) -> float:
    try:
        return float(str(s).strip().replace(',', '').replace('+', ''))
    except (ValueError, TypeError):
        return math.nan


# ---------------------------------------------------------------------------
# Column definitions: (key, label, parser)
# parser=None → sort as plain text; otherwise numeric sort via data-val
# ---------------------------------------------------------------------------

_DATA_COLS = [
    ("rank",           "Rank",        _parse_float),
    ("symbol",         "Symbol",      None),
    ("name",           "Name",        None),
    ("last",           "Price",       _parse_float),
    ("change",         "Change",      _parse_float),
    ("percent_change", "% Change",    _parse_pct),
    ("volume",         "Volume",      _parse_abbrev),
    ("avg_volume",     "Avg Vol",     _parse_abbrev),
    ("market_cap",     "Mkt Cap",     _parse_abbrev),
    ("pe_ratio",       "P/E",         _parse_float),
    ("_52wk_change",   "52Wk Chg",    _parse_pct),
    ("_52wk_range",    "52Wk Range",  None),
]

_IMPROVED_EXTRA = [
    ("prev_rank",   "Prev Rank", _parse_float),
    ("improvement", "Rank ↑",   _parse_float),
]

_PRICE_CHG_EXTRA = [
    ("prev_last",     "Prev Price",  _parse_float),
    ("price_chg_pct", "Price Chg %", _parse_pct),
]

_52WK_EXTRA = [
    ("prev_52wk_change", "Prev 52Wk Chg", _parse_pct),
    ("wk52_chg_delta",   "52Wk Chg ↑",   _parse_pct),
]


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_last_two_dates(conn: sqlite3.Connection) -> list[str]:
    c = conn.cursor()
    c.execute("SELECT DISTINCT scraped_at FROM gainers ORDER BY scraped_at DESC LIMIT 2")
    return [r[0] for r in c.fetchall()]


def _get_ranked_data(conn: sqlite3.Connection, date: str) -> list[dict]:
    c = conn.cursor()
    c.execute(
        """
        SELECT
            ROW_NUMBER() OVER (ORDER BY id) AS rank,
            symbol, name, last, change, percent_change, volume, avg_volume,
            market_cap, pe_ratio, _52wk_change, _52wk_range
        FROM gainers
        WHERE scraped_at = ?
        ORDER BY id
        """,
        (date,),
    )
    cols = [d[0] for d in c.description]
    return [dict(zip(cols, row)) for row in c.fetchall()]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        dates = _get_last_two_dates(conn)
        if len(dates) < 2:
            raise ValueError(f"Need at least 2 runs in the database, found {len(dates)}.")
        latest_date, prev_date = dates[0], dates[1]
        latest = _get_ranked_data(conn, latest_date)
        prev   = _get_ranked_data(conn, prev_date)
    finally:
        conn.close()

    prev_by_symbol = {r["symbol"]: r for r in prev}

    # 0. Biggest price change % between runs
    price_changed = []
    for r in latest:
        sym = r["symbol"]
        if sym in prev_by_symbol:
            curr_price = _parse_float(r["last"])
            prev_price = _parse_float(prev_by_symbol[sym]["last"])
            if not math.isnan(curr_price) and not math.isnan(prev_price) and prev_price != 0:
                pct = (curr_price - prev_price) / prev_price * 100
                price_changed.append({
                    **r,
                    "prev_last":     prev_by_symbol[sym]["last"],
                    "price_chg_pct": f"{pct:+.2f}%",
                    "_price_chg_num": pct,
                })
    price_changed.sort(key=lambda x: x["_price_chg_num"], reverse=True)
    top_price_chg = price_changed[:20]

    # 1. Most improved rank
    improved = []
    for r in latest:
        sym = r["symbol"]
        if sym in prev_by_symbol:
            prev_rank = prev_by_symbol[sym]["rank"]
            improved.append({**r, "prev_rank": prev_rank, "improvement": prev_rank - r["rank"]})
    improved.sort(key=lambda x: x["improvement"], reverse=True)
    top_improved = improved[:20]

    # 2. New entrants
    new_entrants = [r for r in latest if r["symbol"] not in prev_by_symbol]
    new_entrants.sort(key=lambda x: x["rank"])
    top_new = new_entrants[:20]

    # 3. Biggest increase in 52-week change percentage
    wk52_moved = []
    for r in latest:
        sym = r["symbol"]
        if sym in prev_by_symbol:
            curr_val = _parse_pct(r["_52wk_change"])
            prev_val = _parse_pct(prev_by_symbol[sym]["_52wk_change"])
            if not math.isnan(curr_val) and not math.isnan(prev_val):
                delta = curr_val - prev_val
                wk52_moved.append({
                    **r,
                    "prev_52wk_change": prev_by_symbol[sym]["_52wk_change"],
                    "wk52_chg_delta": f"{delta:+.2f}%",
                    "_wk52_delta_num": delta,
                })
    wk52_moved.sort(key=lambda x: x["_wk52_delta_num"], reverse=True)
    top_52wk = wk52_moved[:20]

    return {
        "latest_date":   latest_date,
        "prev_date":     prev_date,
        "top_price_chg": top_price_chg,
        "top_improved":  top_improved,
        "top_new":       top_new,
        "top_52wk":      top_52wk,
    }


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def _data_val(text: str, parser) -> str:
    if parser is None:
        return str(text).lower()
    v = parser(str(text))
    return "" if math.isnan(v) else repr(v)


def _html_table(table_id: str, rows: list[dict], col_defs: list[tuple]) -> str:
    header_cells = "".join(
        f'<th data-col="{i}">{label}</th>'
        for i, (_, label, *_rest) in enumerate(col_defs)
    )
    body_rows = []
    for row in rows:
        cells = []
        for key, _label, *rest in col_defs:
            parser = rest[0] if rest else None
            val = str(row.get(key, ""))
            dv  = _data_val(val, parser)
            cells.append(f'<td data-val="{dv}">{val}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    body = "\n".join(body_rows)
    return (
        f'<table id="{table_id}" class="sortable">\n'
        f'  <thead><tr>{header_cells}</tr></thead>\n'
        f'  <tbody>\n{body}\n  </tbody>\n'
        f'</table>'
    )


_SORT_JS = r"""
<script>
(function () {
  var _state = {};   // tableId -> { col, asc }

  function restripe(tbody) {
    Array.from(tbody.rows).forEach(function (r, i) {
      r.className = i % 2 === 0 ? 'even' : 'odd';
    });
  }

  function sortTable(tbl, col, asc) {
    var tbody = tbl.tBodies[0];
    var rows  = Array.from(tbody.rows);

    rows.sort(function (a, b) {
      var av = a.cells[col].dataset.val;
      var bv = b.cells[col].dataset.val;
      // Push blanks to bottom regardless of direction
      if (av === '' && bv !== '') return 1;
      if (bv === '' && av !== '') return -1;
      var an = parseFloat(av), bn = parseFloat(bv);
      if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    });

    rows.forEach(function (r) { tbody.appendChild(r); });
    restripe(tbody);

    // Update header arrows
    Array.from(tbl.tHead.rows[0].cells).forEach(function (th, i) {
      th.dataset.sort = i === col ? (asc ? 'asc' : 'desc') : '';
    });
  }

  document.querySelectorAll('table.sortable').forEach(function (tbl) {
    var id = tbl.id;
    _state[id] = { col: -1, asc: true };

    Array.from(tbl.tHead.rows[0].cells).forEach(function (th, col) {
      th.addEventListener('click', function () {
        var s   = _state[id];
        var asc = s.col === col ? !s.asc : true;
        _state[id] = { col: col, asc: asc };
        sortTable(tbl, col, asc);
      });
    });

    // Apply initial zebra striping
    restripe(tbl.tBodies[0]);
  });
}());
</script>
"""

_CSS = """
<style>
  body  { font-family: Arial, sans-serif; margin: 24px; color: #222; background: #f7f7f7; }
  h1    { color: #1a5276; }
  h2    { color: #1f618d; margin-top: 36px; border-bottom: 2px solid #aed6f1; padding-bottom: 6px; }
  .meta { color: #666; font-size: 0.9em; margin-bottom: 24px; }
  .wrap { overflow-x: auto; margin-bottom: 8px; }

  table { border-collapse: collapse; width: 100%; min-width: 900px; background: #fff; font-size: 0.85em; }
  th    { background: #1f618d; color: #fff; padding: 8px 10px; text-align: left;
          white-space: nowrap; cursor: pointer; user-select: none; }
  th:hover { background: #154360; }
  th::after { content: ' ⇅'; opacity: 0.4; font-size: 0.8em; }
  th[data-sort="asc"]::after  { content: ' ▲'; opacity: 1; }
  th[data-sort="desc"]::after { content: ' ▼'; opacity: 1; }

  td { padding: 6px 10px; white-space: nowrap; }
  tr.even { background: #eaf4fb; }
  tr.odd  { background: #fff; }
  tr:hover td { background: #d6eaf8; }
</style>
"""


def generate_html(result: dict, out_path: str = "52wk_gainers_report.html") -> str:
    latest_date = result["latest_date"]
    prev_date   = result["prev_date"]
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    price_chg_cols = _PRICE_CHG_EXTRA + _DATA_COLS
    wk52_cols      = _52WK_EXTRA + _DATA_COLS
    improved_cols  = _IMPROVED_EXTRA + _DATA_COLS
    new_cols       = _DATA_COLS

    t_price_chg = _html_table("tbl-price-chg", result["top_price_chg"], price_chg_cols)
    t_52wk      = _html_table("tbl-52wk",      result["top_52wk"],      wk52_cols)
    t_improved  = _html_table("tbl-improved",  result["top_improved"],  improved_cols)
    t_new       = _html_table("tbl-new",       result["top_new"],       new_cols)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>52-Week Gainers Report — {latest_date}</title>
{_CSS}
</head>
<body>
<h1>52-Week Gainers — Monthly Leaderboard</h1>
<p class="meta">
  Comparing <strong>{prev_date}</strong> → <strong>{latest_date}</strong> &nbsp;|&nbsp;
  Report generated: {generated_at}<br>
  <em>Click any column header to sort. Click again to reverse.</em>
</p>

<h2>Top 20 Biggest Price Change % (between last two runs)</h2>
<div class="wrap">{t_price_chg}</div>

<h2>Top 20 Biggest Increase in 52-Week Change %</h2>
<div class="wrap">{t_52wk}</div>

<h2>Top 20 Most Improved (biggest rank gain between last two runs)</h2>
<div class="wrap">{t_improved}</div>

<h2>Top 20 New Entrants (first appeared in {latest_date} run)</h2>
<div class="wrap">{t_new}</div>

{_SORT_JS}
</body>
</html>"""

    Path(out_path).write_text(html, encoding="utf-8")
    return out_path

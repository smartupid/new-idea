#!/usr/bin/env python3
"""Generate HTML gainer-loser trend report from Yahoo Finance SQLite databases."""

import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go

GAINERS_DB = "yahoo_gainers_long.db"
LOSERS_DB = "yahoo_losers_long.db"
OUTPUT_HTML = "report.html"
MARKET_CAP_FILTER = 1_000_000_000  # 1B

COLS = [
    "symbol", "shortName", "regularMarketPrice", "regularMarketChange",
    "regularMarketChangePercent", "regularMarketVolume",
    "averageDailyVolume3Month", "marketCap", "run_date",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(db_path: str, table: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        f"SELECT {', '.join(COLS)} FROM {table} WHERE marketCap > ?",
        conn,
        params=(MARKET_CAP_FILTER,),
    )
    conn.close()
    df["run_date"] = pd.to_datetime(df["run_date"])
    df["regVolWeightedChangePercent"] = (
        df["regularMarketVolume"] * df["regularMarketChangePercent"]
    )
    safe_avg = df["averageDailyVolume3Month"].replace(0, float("nan"))
    df["regIndexedVolWeightedChangePercent"] = (
        df["regularMarketVolume"] / safe_avg * df["regularMarketChangePercent"]
    )
    df["marketCapChange"] = df["marketCap"] * df["regularMarketChangePercent"]
    return df


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def sorted_dates(df_g: pd.DataFrame, df_l: pd.DataFrame) -> list:
    return sorted(set(df_g["run_date"].tolist()) | set(df_l["run_date"].tolist()))


def last_n_days(dates: list, n: int) -> list:
    return dates[-n:] if len(dates) >= n else dates[:]


def trading_days_cutoff(dates: list, n: int):
    """Return the date just before the last n trading days (use with run_date > cutoff)."""
    if len(dates) <= n:
        return dates[0] - timedelta(days=1)
    return dates[-(n + 1)]


# ---------------------------------------------------------------------------
# Plotly helpers
# ---------------------------------------------------------------------------

def fig_div(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"responsive": True})


def two_col_divs(left: str, right: str) -> str:
    return (
        '<div class="two-col">'
        f'<div class="col">{left}</div>'
        f'<div class="col">{right}</div>'
        "</div>"
    )


def three_col_divs(a: str, b: str, c: str) -> str:
    return (
        '<div class="three-col">'
        f'<div class="col3">{a}</div>'
        f'<div class="col3">{b}</div>'
        f'<div class="col3">{c}</div>'
        "</div>"
    )


def one_col_div(content: str) -> str:
    return f'<div class="full-col">{content}</div>'


# Columns kept from raw data before computing trend summaries
_TREND_KEEP = [
    "symbol", "regularMarketChangePercent", "regIndexedVolWeightedChangePercent",
    "marketCapChange", "run_date",
]


# ---------------------------------------------------------------------------
# Trend charts
# ---------------------------------------------------------------------------

def make_trend_charts(df_g: pd.DataFrame, df_l: pd.DataFrame, dates_all: list) -> list:
    # Step 1: truncate to last 60 trading days; market cap filter already applied in load_data.
    dates_60 = last_n_days(dates_all, 60)
    date_set = set(dates_60)

    g = df_g.loc[df_g["run_date"].isin(date_set), _TREND_KEEP].copy()
    l = df_l.loc[df_l["run_date"].isin(date_set), _TREND_KEEP].copy()

    # Step 2: per-day intermediate summaries.
    def day_summary(df, max_or_min):
        agg_fn = "max" if max_or_min == "max" else "min"
        return df.groupby("run_date").agg(
            count=("symbol", "count"),
            vw_sum=("regIndexedVolWeightedChangePercent", "sum"),
            mc_sum=("marketCapChange", "sum"),
            extreme_pct=("regularMarketChangePercent", agg_fn),
        ).reindex(dates_60, fill_value=0)

    g_day = day_summary(g, "max")
    l_day = day_summary(l, "min")

    # Step 3: merge by run_date and compute ratios.
    m = g_day.join(l_day, lsuffix="_g", rsuffix="_l")
    xs = [d.strftime("%Y-%m-%d") for d in dates_60]

    # Convert to plain Python lists so Plotly uses JSON encoding, not binary bdata.
    # bdata (numpy int64/float64 arrays) is misrendered by some Plotly.js CDN versions.
    count_g     = m["count_g"].tolist()
    count_l     = m["count_l"].tolist()
    extreme_g   = m["extreme_pct_g"].tolist()
    extreme_l   = m["extreme_pct_l"].tolist()
    import math

    def safe_log_ratio(series_num, series_den):
        """Compute log2(num / den), returning None where undefined."""
        ratio = series_num / series_den.abs().replace(0, float("nan"))
        return [math.log2(v) if (v is not None and not pd.isna(v) and v > 0) else None
                for v in ratio.tolist()]

    log_count_ratio = safe_log_ratio(m["count_g"],  m["count_l"])
    log_vw_ratio    = safe_log_ratio(m["vw_sum_g"],  m["vw_sum_l"])
    log_mc_ratio    = safe_log_ratio(m["mc_sum_g"],  m["mc_sum_l"])

    def log_ratio_colors(vals):
        return ["#2ecc71" if (v is not None and v >= 0) else "#e74c3c" for v in vals]

    # Step 4: generate plots.

    # Plot 1 – gainer vs loser count per day (grouped bar)
    fig1 = go.Figure([
        go.Bar(name="Gainers", x=xs, y=count_g, marker_color="#2ecc71"),
        go.Bar(name="Losers",  x=xs, y=count_l,  marker_color="#e74c3c"),
    ])
    fig1.update_layout(title="Daily Gainer vs Loser Count", barmode="group",
                       xaxis_title="Date", yaxis_title="Count", height=380)

    # Plot 2 – highest gain% vs deepest loss% per day (grouped bar)
    fig2 = go.Figure([
        go.Bar(name="Max Gain %", x=xs, y=extreme_g, marker_color="#27ae60"),
        go.Bar(name="Max Loss %", x=xs, y=extreme_l, marker_color="#c0392b"),
    ])
    fig2.update_layout(title="Highest Daily Gain% vs Loss%", barmode="group",
                       xaxis_title="Date", yaxis_title="Change %", height=380)

    # Plot 3 – log2 ratio of gainer count to loser count per day (bar)
    fig3 = go.Figure([
        go.Bar(x=xs, y=log_count_ratio, marker_color=log_ratio_colors(log_count_ratio),
               name="log2(Gainers / Losers)"),
    ])
    fig3.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="parity")
    fig3.update_layout(title="Log2 Ratio of Gainer Count to Loser Count",
                       xaxis_title="Date", yaxis_title="log2(G / L)", height=380)

    # Plot 4 – log2 ratio of total indexed vol-weighted gain% to loss% per day (bar)
    fig4 = go.Figure([
        go.Bar(x=xs, y=log_vw_ratio, marker_color=log_ratio_colors(log_vw_ratio),
               name="log2(Gainer / Loser Indexed-VW)"),
    ])
    fig4.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="parity")
    fig4.update_layout(
        title="Log2 Ratio of Total Indexed Vol-Weighted Change%: Gainers / |Losers|",
        xaxis_title="Date", yaxis_title="log2(G / |L|)", height=380,
    )

    # Plot 5 – log2 ratio of total market-cap change: gainers / |losers| per day (bar)
    fig5 = go.Figure([
        go.Bar(x=xs, y=log_mc_ratio, marker_color=log_ratio_colors(log_mc_ratio),
               name="log2(Gainer / Loser MCap Change)"),
    ])
    fig5.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="parity")
    fig5.update_layout(
        title="Log2 Ratio of Total Market-Cap Change: Gainers / |Losers|",
        xaxis_title="Date", yaxis_title="log2(G / |L|)", height=380,
    )

    return [fig1, fig2, fig3, fig4, fig5]


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def df_to_html(df: pd.DataFrame, title: str = "") -> str:
    df = df.copy()
    for col in df.select_dtypes("float").columns:
        df[col] = df[col].round(4)
    table = df.to_html(index=False, border=0, classes="data-table")
    return f'<div class="tbl-wrap"><h4>{title}</h4>{table}</div>'


def top_appearances(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return (
        df.groupby(["symbol", "shortName"])
        .size()
        .reset_index(name="appearances")
        .nlargest(n, "appearances")
        .reset_index(drop=True)
    )


def top_indexed_vol_weighted(df: pd.DataFrame, n: int = 10, ascending: bool = False) -> pd.DataFrame:
    return (
        df.groupby(["symbol", "shortName"])["regIndexedVolWeightedChangePercent"]
        .sum()
        .reset_index(name="totalIdxVolWeightedChg%")
        .sort_values("totalIdxVolWeightedChg%", ascending=ascending)
        .head(n)
        .reset_index(drop=True)
    )


def top_consecutive(df: pd.DataFrame, period_dates: list, n: int = 10) -> pd.DataFrame:
    """Top symbols by longest streak ending at the most recent date in period_dates."""
    present = set(zip(df["symbol"], df["run_date"]))
    sym_name = (
        df[["symbol", "shortName"]].drop_duplicates()
        .set_index("symbol")["shortName"]
    )
    results = []
    for sym in df["symbol"].unique():
        streak = 0
        for d in reversed(period_dates):
            if (sym, d) in present:
                streak += 1
            else:
                break
        if streak > 0:
            results.append({"symbol": sym, "shortName": sym_name.get(sym, ""), "streak": streak})
    if not results:
        return pd.DataFrame(columns=["symbol", "shortName", "streak"])
    return (
        pd.DataFrame(results)
        .nlargest(n, "streak")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Top boards
# ---------------------------------------------------------------------------

def make_top_boards(df_g: pd.DataFrame, df_l: pd.DataFrame,
                    dates_all: list, periods: dict) -> list:
    """Return list of (topic_title, html_string) — one entry per topic,
    each laid out as a 3-column x 2-row grid across all periods.
    periods: ordered dict of label -> number of trading days."""

    # Pre-compute filtered data for every period.
    period_slices = []
    for label, n_days in periods.items():
        cutoff = trading_days_cutoff(dates_all, n_days)
        g = df_g[df_g["run_date"] > cutoff]
        l = df_l[df_l["run_date"] > cutoff]
        period_dates = [d for d in dates_all if d > cutoff]
        period_slices.append((label, g, l, period_dates))

    # Three topics; each produces one cell per period.
    topics = [
        ("Most Appearances",
         lambda g, l, pd: (top_appearances(g), top_appearances(l))),
        ("Top Indexed Vol-Weighted Change%",
         lambda g, l, pd: (top_indexed_vol_weighted(g, ascending=False),
                           top_indexed_vol_weighted(l, ascending=True))),
        ("Most Consecutive Appearances",
         lambda g, l, pd: (top_consecutive(g, pd), top_consecutive(l, pd))),
    ]

    sections = []
    for topic_title, compute in topics:
        cells = []
        for label, g, l, period_dates in period_slices:
            g_tbl, l_tbl = compute(g, l, period_dates)
            cell = (
                f'<div class="period-label">{label}</div>'
                + df_to_html(g_tbl, "Gainers")
                + df_to_html(l_tbl, "Losers")
            )
            cells.append(cell)

        # 6 periods → 2 rows of 3
        row1 = three_col_divs(cells[0], cells[1], cells[2])
        row2 = three_col_divs(cells[3], cells[4], cells[5])
        sections.append((topic_title, row1 + row2))

    return sections


# ---------------------------------------------------------------------------
# U-Turn boards
# ---------------------------------------------------------------------------

def make_uturn_boards(df_g: pd.DataFrame, df_l: pd.DataFrame, dates_all: list) -> str:
    sym_name = (
        pd.concat([df_g[["symbol", "shortName"]], df_l[["symbol", "shortName"]]])
        .drop_duplicates()
        .set_index("symbol")["shortName"]
    )

    configs = [(5, 10), (10, 20), (25, 50)]
    html_parts = []

    for short_d, long_d in configs:
        sc = trading_days_cutoff(dates_all, short_d)
        lc = trading_days_cutoff(dates_all, long_d)

        g_short = df_g[df_g["run_date"] > sc].groupby("symbol").size()
        l_short = df_l[df_l["run_date"] > sc].groupby("symbol").size()
        g_long  = df_g[df_g["run_date"] > lc].groupby("symbol").size()
        l_long  = df_l[df_l["run_date"] > lc].groupby("symbol").size()

        # Bullish u-turn: more gainer in short window than loser in long window,
        # AND at least 1 loser appearance in the long window (true reversal).
        l_long_aligned = l_long.reindex(g_short.index, fill_value=0)
        gainer_syms = g_short.index[
            (g_short > l_long_aligned) & (l_long_aligned >= 1)
        ]
        # Bearish u-turn: more loser in short window than gainer in long window,
        # AND at least 1 gainer appearance in the long window (true reversal).
        g_long_aligned = g_long.reindex(l_short.index, fill_value=0)
        loser_syms = l_short.index[
            (l_short > g_long_aligned) & (g_long_aligned >= 1)
        ]

        def build(syms, a_series, b_series, a_col, b_col):
            rows = [
                {"symbol": s,
                 "shortName": sym_name.get(s, ""),
                 a_col: int(a_series.get(s, 0)),
                 b_col: int(b_series.get(s, 0))}
                for s in syms
            ]
            if not rows:
                return pd.DataFrame(columns=["symbol", "shortName", a_col, b_col])
            return pd.DataFrame(rows).sort_values(a_col, ascending=False).reset_index(drop=True)

        g_tbl = build(gainer_syms, g_short, l_long_aligned,
                      f"Gainer ({short_d}d)", f"Loser ({long_d}d)")
        l_tbl = build(loser_syms, l_short, g_long_aligned,
                      f"Loser ({short_d}d)", f"Gainer ({long_d}d)")

        left  = df_to_html(g_tbl, f"More Gainer (last {short_d}d) than Loser (last {long_d}d)")
        right = df_to_html(l_tbl, f"More Loser (last {short_d}d) than Gainer (last {long_d}d)")
        html_parts.append(two_col_divs(left, right))

    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# HTML assembly
# ---------------------------------------------------------------------------

CSS = """
* { box-sizing: border-box; }
body { font-family: Arial, sans-serif; margin: 0; padding: 20px;
       background: #f0f2f5; color: #333; }
h1 { font-size: 1.6rem; margin-bottom: 4px; }
h2 { font-size: 1.2rem; border-bottom: 2px solid #ccc;
     padding-bottom: 6px; margin-top: 30px; }
h3 { font-size: 1rem; margin: 10px 0 6px; color: #555; }
h4 { font-size: 0.85rem; margin: 6px 0 4px; color: #666; }
p.meta { color: #888; font-size: 0.85rem; margin-bottom: 20px; }
.section { margin-bottom: 30px; }
.two-col { display: flex; gap: 16px; margin: 10px 0; flex-wrap: wrap; }
.two-col .col { flex: 1 1 45%; background: #fff; padding: 12px;
                border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
                overflow-x: auto; min-width: 280px; }
.full-col { background: #fff; padding: 12px; border-radius: 6px;
            box-shadow: 0 1px 4px rgba(0,0,0,.08); margin: 10px 0; }
.topic-block { background: #f7f8fa; border: 1px solid #e0e3e8;
               border-radius: 6px; padding: 12px; margin: 10px 0; }
.three-col { display: flex; gap: 12px; margin: 8px 0; flex-wrap: wrap; }
.three-col .col3 { flex: 1 1 30%; background: #fff; padding: 10px;
                   border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
                   overflow-x: auto; min-width: 220px; }
.period-label { font-weight: bold; font-size: 0.82rem; color: #3a7bd5;
                margin-bottom: 6px; padding-bottom: 4px;
                border-bottom: 1px solid #e0e3e8; }
.tbl-wrap { overflow-x: auto; }
.data-table { border-collapse: collapse; width: 100%; font-size: 11px; }
.data-table th { background: #3a7bd5; color: #fff;
                 padding: 5px 8px; text-align: left; }
.data-table td { padding: 3px 8px; border-bottom: 1px solid #eee; }
.data-table tr:nth-child(even) { background: #f6f8fc; }
"""


def assemble_html(trend_figs: list, top_sections: list,
                  uturn_html: str, generated: str, trend_date_range: str) -> str:
    plotlyjs = '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'

    trend_body = (
        two_col_divs(fig_div(trend_figs[0]), fig_div(trend_figs[1]))
        + two_col_divs(fig_div(trend_figs[2]), fig_div(trend_figs[3]))
        + one_col_div(fig_div(trend_figs[4]))
    )

    top_body = ""
    for topic_title, inner in top_sections:
        top_body += f'<div class="topic-block"><h3>{topic_title}</h3>{inner}</div>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gainer-Loser Report {generated}</title>
{plotlyjs}
<style>{CSS}</style>
</head>
<body>
<h1>Gainer-Loser Market Report</h1>
<p class="meta">Generated: {generated} &nbsp;|&nbsp; Market Cap filter: &gt; $1 B &nbsp;|&nbsp; Trend window: {trend_date_range}</p>

<div class="section">
  <h2>Trend Reports &mdash; Last 60 Trading Days</h2>
  {trend_body}
</div>

<div class="section">
  <h2>Top Boards</h2>
  {top_body}
</div>

<div class="section">
  <h2>U-Turn Boards</h2>
  <p>Symbols that shifted direction: recent short window vs earlier long window.</p>
  {uturn_html}
</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading data ...")
    df_g = load_data(GAINERS_DB, "gainers_history")
    df_l = load_data(LOSERS_DB, "losers_history")
    print(f"  Gainers: {len(df_g):,} rows   Losers: {len(df_l):,} rows")

    dates_all = sorted_dates(df_g, df_l)
    print(f"  Trading days: {len(dates_all)}  ({dates_all[0].date()} - {dates_all[-1].date()})")

    print("Building trend charts ...")
    trend_figs = make_trend_charts(df_g, df_l, dates_all)
    dates_60 = last_n_days(dates_all, 60)
    trend_date_range = f"{dates_60[0].strftime('%Y-%m-%d')} to {dates_60[-1].strftime('%Y-%m-%d')} (60 trading days)"

    print("Building top boards ...")
    periods = {
        "5 Days": 5, "10 Days": 10, "15 Days": 15,
        "20 Days": 20, "25 Days": 25, "50 Days": 50,
    }
    top_sections = make_top_boards(df_g, df_l, dates_all, periods)

    print("Building u-turn boards ...")
    uturn_html = make_uturn_boards(df_g, df_l, dates_all)

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("Assembling HTML ...")
    html = assemble_html(trend_figs, top_sections, uturn_html, generated, trend_date_range)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report written -> {OUTPUT_HTML}")


if __name__ == "__main__":
    main()

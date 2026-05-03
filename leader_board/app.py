import argparse
import sqlite3

import dash
from dash import dcc, html, dash_table, Input, Output, State

import report as rpt


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------

def _search_db(db_path: str, symbol: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
        SELECT scraped_at, symbol, name, last, change, percent_change,
               volume, avg_volume, market_cap, pe_ratio, _52wk_change, _52wk_range
        FROM gainers
        WHERE UPPER(symbol) = UPPER(?)
        ORDER BY scraped_at ASC
        """,
        (symbol,),
    )
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, row)) for row in c.fetchall()]
    conn.close()
    return rows


def _parse_price(s) -> float:
    # stored values may be comma-formatted (e.g. "1,234.56") — strip before float()
    return float(str(s).replace(",", "").strip())


def _add_price_change_pct(rows: list[dict]) -> list[dict]:
    for i, r in enumerate(rows):
        if i == 0:
            r["price_chg_pct"] = "—"
        else:
            try:
                curr = _parse_price(rows[i]["last"])
                prev = _parse_price(rows[i - 1]["last"])
                pct = (curr - prev) / prev * 100 if prev != 0 else float("nan")
                r["price_chg_pct"] = f"{pct:+.2f}%"
            except (ValueError, TypeError):
                r["price_chg_pct"] = ""
    return rows


# ---------------------------------------------------------------------------
# Shared table styling and column helpers
# ---------------------------------------------------------------------------

_TABLE_STYLE = dict(
    sort_action="native",
    style_table={"overflowX": "auto", "marginBottom": "24px"},
    style_header={
        "backgroundColor": "#1f618d", "color": "#fff",
        "fontWeight": "bold", "whiteSpace": "nowrap",
    },
    style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#eaf4fb"}],
    style_cell={"fontSize": "13px", "padding": "6px 10px", "whiteSpace": "nowrap"},
)

_BASE_COLS = [
    ("rank",           "Rank"),
    ("symbol",         "Symbol"),
    ("name",           "Name"),
    ("last",           "Price"),
    ("change",         "Change"),
    ("percent_change", "% Change"),
    ("volume",         "Volume"),
    ("avg_volume",     "Avg Vol"),
    ("market_cap",     "Mkt Cap"),
    ("pe_ratio",       "P/E"),
    ("_52wk_change",   "52Wk Chg"),
    ("_52wk_range",    "52Wk Range"),
]


def _col_defs(extras: list[tuple], base: list[tuple] = _BASE_COLS) -> list[dict]:
    return [{"id": k, "name": label} for k, label in extras + base]


def _datatable(table_id: str, rows: list[dict], col_defs: list[dict]) -> dash_table.DataTable:
    return dash_table.DataTable(id=table_id, columns=col_defs, data=rows, **_TABLE_STYLE)


# ---------------------------------------------------------------------------
# Tab content builders
# ---------------------------------------------------------------------------

_H2 = {"color": "#1f618d", "marginTop": "28px", "borderBottom": "2px solid #aed6f1", "paddingBottom": "6px"}


def _report_layout(db_path: str) -> html.Div:
    try:
        result = rpt.analyze(db_path)
    except ValueError as e:
        return html.Div(str(e), style={"color": "#922b21", "backgroundColor": "#fadbd8",
                                       "padding": "12px 16px", "borderRadius": "4px"})

    latest_date = result["latest_date"]
    prev_date = result["prev_date"]

    return html.Div([
        html.H1("52-Week Gainers — Monthly Leaderboard", style={"color": "#1a5276"}),
        html.P(f"Comparing {prev_date} → {latest_date}  |  Click any column header to sort.",
               style={"color": "#666", "marginBottom": "24px"}),

        html.H2("Top 20 Biggest Price Change % (between last two runs)", style=_H2),
        _datatable("t-price-chg", result["top_price_chg"],
                   _col_defs([("prev_last", "Prev Price"), ("price_chg_pct", "Price Chg %")])),

        html.H2("Top 20 Biggest Increase in 52-Week Change %", style=_H2),
        _datatable("t-52wk", result["top_52wk"],
                   _col_defs([("prev_52wk_change", "Prev 52Wk Chg"), ("wk52_chg_delta", "52Wk Chg ↑")])),

        html.H2("Top 20 Most Improved (biggest rank gain between last two runs)", style=_H2),
        _datatable("t-improved", result["top_improved"],
                   _col_defs([("prev_rank", "Prev Rank"), ("improvement", "Rank ↑")])),

        html.H2(f"Top 20 New Entrants (first appeared in {latest_date} run)", style=_H2),
        _datatable("t-new", result["top_new"], _col_defs([])),
    ])


def _search_layout() -> html.Div:
    return html.Div([
        html.H1("Search by Symbol", style={"color": "#1a5276"}),
        html.Div([
            dcc.Input(
                id="search-input", type="text", placeholder="e.g. AAPL",
                debounce=True,
                style={"fontSize": "15px", "padding": "7px 10px", "width": "180px",
                       "border": "1px solid #aed6f1", "borderRadius": "4px"},
            ),
            html.Button(
                "Search", id="search-btn", n_clicks=0,
                style={"marginLeft": "8px", "padding": "7px 18px", "fontSize": "15px",
                       "backgroundColor": "#1f618d", "color": "#fff",
                       "border": "none", "borderRadius": "4px", "cursor": "pointer"},
            ),
        ], style={"marginBottom": "20px"}),
        html.Div(id="search-results"),
    ])


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

_NAV_BASE = {
    "padding": "6px 14px",
    "cursor": "pointer",
    "fontSize": "14px",
    "borderLeft": "3px solid transparent",
    "userSelect": "none",
}
_NAV_ACTIVE = {**_NAV_BASE, "fontWeight": "bold", "borderLeft": "3px solid #1f618d",
               "backgroundColor": "#d6eaf8"}


def run(db_path: str = "yahoo_52wk_gainers.db", debug: bool = False):
    app = dash.Dash(__name__, suppress_callback_exceptions=True)

    app.layout = html.Div([
        dcc.Store(id="db-path-store", data=db_path),
        # Sidebar
        html.Div([
            html.Div("Report", id="nav-report", n_clicks=0, style=_NAV_ACTIVE),
            html.Div("Search", id="nav-search", n_clicks=0, style=_NAV_BASE),
        ], style={
            "width": "110px", "flexShrink": "0",
            "borderRight": "2px solid #aed6f1",
            "paddingTop": "16px",
            "backgroundColor": "#eaf4fb",
            "minHeight": "100vh",
        }),
        html.Div(id="tab-content",
                 style={"flex": 1, "padding": "24px 32px", "overflowY": "auto"}),
    ], style={"display": "flex", "fontFamily": "Arial, sans-serif",
              "minHeight": "100vh", "background": "#f7f7f7"})

    @app.callback(
        Output("tab-content", "children"),
        Output("nav-report", "style"),
        Output("nav-search", "style"),
        Input("nav-report", "n_clicks"),
        Input("nav-search", "n_clicks"),
        State("db-path-store", "data"),
    )
    def render_tab(_, __, db):
        from dash import ctx
        active = "search" if ctx.triggered_id == "nav-search" else "report"
        content = _report_layout(db) if active == "report" else _search_layout()
        return (
            content,
            _NAV_ACTIVE if active == "report" else _NAV_BASE,
            _NAV_ACTIVE if active == "search" else _NAV_BASE,
        )

    @app.callback(
        Output("search-results", "children"),
        Input("search-btn", "n_clicks"),
        Input("search-input", "value"),
        State("db-path-store", "data"),
        prevent_initial_call=True,
    )
    def do_search(_, symbol, db):
        if not symbol or not symbol.strip():
            return html.P("Enter a symbol above and press Enter or click Search.",
                          style={"color": "#666"})
        rows = _search_db(db, symbol.strip())
        if not rows:
            return html.Div(
                f'No records found for "{symbol.strip().upper()}".',
                style={"color": "#922b21", "backgroundColor": "#fadbd8",
                       "padding": "12px 16px", "borderRadius": "4px"},
            )
        rows = _add_price_change_pct(rows)
        base_no_rank = [c for c in _BASE_COLS if c[0] != "rank"]
        cols = _col_defs([("scraped_at", "Date"), ("price_chg_pct", "Price Chg %")],
                         base=base_no_rank)
        return dash_table.DataTable(columns=cols, data=rows, **_TABLE_STYLE)

    app.run(debug=debug)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Run the 52-week gainers Dash web app.")
    p.add_argument("--db", default="yahoo_52wk_gainers.db")
    p.add_argument("--debug", action="store_true")
    args = p.parse_args()
    run(db_path=args.db, debug=args.debug)

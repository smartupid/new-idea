import io
import sqlite3
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State, ctx, no_update

PRICE_DIR = Path(__file__).parent / "daily_price"

app = dash.Dash(__name__)

MA_WINDOWS = [5, 10, 15, 20, 25, 50]

RAW_ROWS = 5   # close+MA | scaled_vol, return | vol_ret, d1 | vol_d1, d2 | vol_d2, roc | vol_roc
LOG_ROWS = 4   # log+MA   | scaled_vol, d1     | vol_d1,  d2 | vol_d2, roc | vol_roc

BTN_STYLE = {
    "padding": "5px 14px",
    "border": "1px solid #d1d5db",
    "borderRadius": "4px",
    "backgroundColor": "white",
    "cursor": "pointer",
    "fontSize": "13px",
    "color": "#374151",
}
CONTROLS_STYLE_HIDDEN = {"display": "none"}
CONTROLS_STYLE_VISIBLE = {
    "display": "block",
    "marginBottom": "24px",
    "padding": "16px 20px",
    "border": "1px solid #e5e7eb",
    "borderRadius": "6px",
    "backgroundColor": "#fafafa",
}
WINDOW_DIV_STYLE = {
    "border": "1px solid #d1d5db",
    "borderRadius": "6px",
    "marginBottom": "20px",
    "padding": "8px 8px 4px",
    "backgroundColor": "white",
}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def _friendly_yf_error(symbol: str, raw: str) -> str:
    low = raw.lower()
    if any(k in low for k in ("no data found", "no timezone", "invalid ticker", "delisted")):
        return f"'{symbol}' was not found on Yahoo Finance. Verify the ticker symbol and try again."
    if any(k in low for k in ("connection", "timeout", "network", "ssl", "max retries")):
        return "Could not reach Yahoo Finance. Check your internet connection and try again."
    if any(k in low for k in ("too many requests", "rate limit", "429")):
        return "Yahoo Finance is rate-limiting requests. Please wait a moment and try again."
    return f"Yahoo Finance returned an error for '{symbol}': {raw}"


def fetch_data(symbol: str) -> pd.DataFrame:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
    except Exception as exc:
        raise RuntimeError(_friendly_yf_error(symbol, str(exc))) from exc

    if df is None or df.empty:
        raise RuntimeError(
            f"No trading data found for '{symbol}'. "
            "The symbol may be invalid, delisted, or not traded on a supported exchange."
        )

    df = df.reset_index()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    df["date"] = pd.to_datetime(df["date"]).dt.tz_convert(None)

    df["adj_close"] = df["close"]
    df["daily_range"] = df["high"] - df["low"]
    df["daily_mid"] = df["daily_range"] / 2
    df["daily_std"] = np.sqrt(df["high"] * df["low"])
    df["daily_return"] = df["adj_close"] / df["adj_close"].shift(1) - 1
    df["log_close"] = np.log(df["adj_close"])
    df["log_mid"] = np.log(df["daily_mid"].replace(0, np.nan))
    df["log_std"] = np.log(df["daily_std"].replace(0, np.nan))

    vol_std = df["volume"].std()
    df["scaled_volume"] = df["volume"] / vol_std
    df["vol_weighted_return"] = df["scaled_volume"] * df["daily_return"]

    _save_to_sqlite(df, symbol)

    return df


def _save_to_sqlite(df: pd.DataFrame, symbol: str) -> None:
    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{symbol}_{date.today().strftime('%Y%m%d')}.db"
    db_path = PRICE_DIR / filename
    with sqlite3.connect(db_path) as conn:
        df.to_sql("price_data", conn, if_exists="replace", index=False)


def compute_mas(df: pd.DataFrame, col: str) -> dict:
    """MA + momentum derivatives and their vol-weighted counterparts for each window."""
    result = {}
    sv = df["scaled_volume"]
    for w in MA_WINDOWS:
        ma = df[col].rolling(w).mean()
        d1 = ma.diff()
        d2 = d1.diff()
        roc = d1.diff() / d1.shift(1).abs()
        result[w] = {
            "ma": ma, "d1": d1, "d2": d2, "roc": roc,
            "vol_d1": d1 * sv, "vol_d2": d2 * sv, "vol_roc": roc * sv,
        }
    return result


def bar_colors(series: pd.Series) -> list[str]:
    return ["#16a34a" if v >= 0 else "#dc2626" for v in series.fillna(0)]


def slider_marks(dates: pd.Series) -> dict:
    """At most ~7 evenly-spaced marks with short month label."""
    n = len(dates)
    step = max(1, n // 6)
    indices = list(range(0, n, step))
    if n - 1 not in indices:
        indices.append(n - 1)
    return {i: dates.iloc[i].strftime("%b '%y") for i in indices}


# ---------------------------------------------------------------------------
# Figure builder — one figure per MA window
# ---------------------------------------------------------------------------

def build_window_figure(df_full: pd.DataFrame, w: int, mas: dict,
                         price_col: str, is_raw: bool, price_label: str,
                         x_range: tuple | None = None) -> go.Figure:
    """
    Build one subplot figure for a single MA window.

    is_raw=True  → 5 rows (includes daily-return row)
    is_raw=False → 4 rows (log section; no return row)

    MAs are always computed on the full 12-month df_full; x_range only zooms the view.
    """
    dates = df_full["date"]
    m = mas[w]

    if is_raw:
        n_rows = RAW_ROWS
        row_heights = [0.36, 0.16, 0.16, 0.16, 0.16]
        subplot_titles = [
            f"{price_label} & {w}d MA",  "Scaled Volume",
            "Daily Return",               "Vol × Return",
            "1st Momentum",               "Vol × 1st Momentum",
            "2nd Momentum",               "Vol × 2nd Momentum",
            "Rate of Change",             "Vol × Rate of Change",
        ]
    else:
        n_rows = LOG_ROWS
        row_heights = [0.40, 0.20, 0.20, 0.20]
        subplot_titles = [
            f"{price_label} & {w}d MA",  "Scaled Volume",
            "1st Momentum",               "Vol × 1st Momentum",
            "2nd Momentum",               "Vol × 2nd Momentum",
            "Rate of Change",             "Vol × Rate of Change",
        ]

    fig = make_subplots(
        rows=n_rows,
        cols=2,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
        vertical_spacing=0.08,
    )

    # --- Row 1: price + MA (left) | scaled volume (right) ---
    fig.add_trace(go.Scatter(
        x=dates, y=df_full[price_col], mode="lines", showlegend=False,
        line=dict(width=1, color="#2563eb"),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=m["ma"], mode="lines", showlegend=False,
        line=dict(width=1.5, dash="dash", color="#f59e0b"),
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=dates, y=df_full["scaled_volume"],
        marker_color="#60a5fa", showlegend=False,
    ), row=1, col=2)

    if is_raw:
        # --- Row 2 (raw only): daily return (left) | vol × return (right) ---
        fig.add_trace(go.Bar(
            x=dates, y=df_full["daily_return"],
            marker_color=bar_colors(df_full["daily_return"]), showlegend=False,
        ), row=2, col=1)
        fig.add_trace(go.Bar(
            x=dates, y=df_full["vol_weighted_return"],
            marker_color=bar_colors(df_full["vol_weighted_return"]), showlegend=False,
        ), row=2, col=2)
        d1_row, d2_row, roc_row = 3, 4, 5
    else:
        d1_row, d2_row, roc_row = 2, 3, 4

    # --- d1 (left) | vol_d1 (right) ---
    fig.add_trace(go.Bar(
        x=dates, y=m["d1"], marker_color=bar_colors(m["d1"]), showlegend=False,
    ), row=d1_row, col=1)
    fig.add_trace(go.Bar(
        x=dates, y=m["vol_d1"], marker_color=bar_colors(m["vol_d1"]), showlegend=False,
    ), row=d1_row, col=2)

    # --- d2 (left) | vol_d2 (right) ---
    fig.add_trace(go.Bar(
        x=dates, y=m["d2"], marker_color=bar_colors(m["d2"]), showlegend=False,
    ), row=d2_row, col=1)
    fig.add_trace(go.Bar(
        x=dates, y=m["vol_d2"], marker_color=bar_colors(m["vol_d2"]), showlegend=False,
    ), row=d2_row, col=2)

    # --- roc (left) | vol_roc (right) ---
    fig.add_trace(go.Bar(
        x=dates, y=m["roc"], marker_color=bar_colors(m["roc"]), showlegend=False,
    ), row=roc_row, col=1)
    fig.add_trace(go.Bar(
        x=dates, y=m["vol_roc"], marker_color=bar_colors(m["vol_roc"]), showlegend=False,
    ), row=roc_row, col=2)

    if x_range:
        fig.update_xaxes(range=list(x_range))

    fig.update_layout(
        height=n_rows * 185,
        margin=dict(l=55, r=40, t=55, b=20),
        paper_bgcolor="white",
        plot_bgcolor="#f9fafb",
        font=dict(color="#111827", size=10),
        bargap=0.1,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#e5e7eb")
    fig.update_yaxes(
        showgrid=True, gridcolor="#e5e7eb",
        zeroline=True, zerolinecolor="#9ca3af", zerolinewidth=1,
    )
    return fig


def build_section_components(df_full: pd.DataFrame, mas: dict,
                              price_col: str, is_raw: bool, price_label: str,
                              x_range: tuple | None = None) -> list:
    """Return a list of bordered html.Div components, one per MA window."""
    components = []
    for w in MA_WINDOWS:
        fig = build_window_figure(df_full, w, mas, price_col, is_raw, price_label, x_range)
        components.append(html.Div(
            dcc.Graph(figure=fig, config={"displayModeBar": True}),
            style=WINDOW_DIV_STYLE,
        ))
    return components


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

app.layout = html.Div(
    style={"backgroundColor": "white", "minHeight": "100vh",
           "fontFamily": "system-ui, sans-serif", "color": "#111827"},
    children=[
        html.Div(
            style={"maxWidth": "1600px", "margin": "0 auto", "padding": "24px"},
            children=[
                html.H1("Price Momentum Study",
                        style={"marginBottom": "20px", "fontSize": "22px", "fontWeight": "600"}),

                # Symbol input
                html.Div(
                    style={"display": "flex", "gap": "8px", "marginBottom": "16px", "alignItems": "center"},
                    children=[
                        dcc.Input(
                            id="symbol-input", type="text",
                            placeholder="Stock symbol (e.g. AAPL)",
                            debounce=False,
                            style={
                                "width": "220px", "padding": "8px 12px",
                                "border": "1px solid #d1d5db", "borderRadius": "4px",
                                "fontSize": "14px",
                            },
                        ),
                        html.Button("Analyze", id="analyze-btn", n_clicks=0, style={
                            "padding": "8px 20px", "backgroundColor": "#2563eb",
                            "color": "white", "border": "none",
                            "borderRadius": "4px", "cursor": "pointer", "fontSize": "14px",
                        }),
                    ],
                ),

                html.Div(id="error-msg",
                         style={"color": "#dc2626", "marginBottom": "12px", "fontSize": "14px",
                                "padding": "8px 12px", "borderRadius": "4px"}),

                # Date controls (hidden until data loads)
                html.Div(id="date-controls", style=CONTROLS_STYLE_HIDDEN, children=[
                    html.Div(
                        style={"display": "flex", "gap": "8px", "marginBottom": "14px", "alignItems": "center"},
                        children=[
                            html.Span("Quick select:", style={"fontSize": "13px", "color": "#6b7280"}),
                            html.Button("4W",  id="btn-4w",  n_clicks=0, style=BTN_STYLE),
                            html.Button("8W",  id="btn-8w",  n_clicks=0, style=BTN_STYLE),
                            html.Button("12W", id="btn-12w", n_clicks=0, style=BTN_STYLE),
                            html.Button("24W", id="btn-24w", n_clicks=0, style=BTN_STYLE),
                            html.Button("All", id="btn-all", n_clicks=0, style=BTN_STYLE),
                            html.Span(id="date-range-display",
                                      style={"marginLeft": "20px", "fontSize": "13px", "color": "#374151"}),
                        ],
                    ),
                    dcc.RangeSlider(
                        id="date-slider",
                        min=0, max=1, step=1, value=[0, 1], marks={},
                        tooltip={"always_visible": False},
                        allowCross=False,
                    ),
                ]),

                dcc.Store(id="df-store"),

                dcc.Loading(
                    id="loading-data",
                    type="circle",
                    color="#2563eb",
                    style={"minHeight": "40px"},
                    children=html.Div(id="data-status"),
                ),

                dcc.Loading(
                    id="loading-charts",
                    type="circle",
                    color="#2563eb",
                    style={"minHeight": "60px"},
                    children=[
                        html.Div(id="raw-section"),
                        html.Div(id="log-section"),
                    ],
                ),
            ],
        )
    ],
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("df-store", "data"),
    Output("date-slider", "min"),
    Output("date-slider", "max"),
    Output("date-slider", "marks"),
    Output("date-slider", "value"),
    Output("date-controls", "style"),
    Output("error-msg", "children"),
    Output("error-msg", "style"),
    Output("data-status", "children"),
    Input("analyze-btn", "n_clicks"),
    State("symbol-input", "value"),
    prevent_initial_call=True,
)
def load_data(_, symbol):
    hidden_err = {"display": "none"}
    visible_err = {
        "color": "#dc2626", "marginBottom": "12px", "fontSize": "14px",
        "backgroundColor": "#fef2f2", "padding": "8px 12px",
        "border": "1px solid #fecaca", "borderRadius": "4px",
    }

    if not symbol or not symbol.strip():
        return (no_update, no_update, no_update, no_update, no_update,
                CONTROLS_STYLE_HIDDEN, "Please enter a ticker symbol.", visible_err, None)

    symbol = symbol.strip().upper()
    try:
        df = fetch_data(symbol)
    except RuntimeError as exc:
        return (None, 0, 1, {}, [0, 1], CONTROLS_STYLE_HIDDEN,
                str(exc), visible_err, None)
    except Exception as exc:
        return (None, 0, 1, {}, [0, 1], CONTROLS_STYLE_HIDDEN,
                f"Unexpected error loading '{symbol}': {exc}", visible_err, None)

    n = len(df)
    marks = slider_marks(df["date"])
    df_json = df.to_json(date_format="iso", orient="split")
    return (df_json, 0, n - 1, marks, [0, n - 1],
            CONTROLS_STYLE_VISIBLE, "", hidden_err, None)


@app.callback(
    Output("date-slider", "value", allow_duplicate=True),
    Input("btn-4w",  "n_clicks"),
    Input("btn-8w",  "n_clicks"),
    Input("btn-12w", "n_clicks"),
    Input("btn-24w", "n_clicks"),
    Input("btn-all", "n_clicks"),
    State("df-store", "data"),
    prevent_initial_call=True,
)
def quick_select(b4, b8, b12, b24, ball, df_json):
    if df_json is None:
        return no_update

    df = pd.read_json(io.StringIO(df_json), orient="split")
    n = len(df)
    week_map = {"btn-4w": 4, "btn-8w": 8, "btn-12w": 12, "btn-24w": 24}
    triggered = ctx.triggered_id

    if triggered == "btn-all" or triggered not in week_map:
        return [0, n - 1]

    trading_days = week_map[triggered] * 5
    return [max(0, n - 1 - trading_days), n - 1]


@app.callback(
    Output("date-range-display", "children"),
    Output("raw-section", "children"),
    Output("log-section", "children"),
    Input("date-slider", "value"),
    State("df-store", "data"),
    prevent_initial_call=True,
)
def update_charts(slider_value, df_json):
    if df_json is None:
        return "", None, None

    df_full = pd.read_json(io.StringIO(df_json), orient="split")
    df_full["date"] = pd.to_datetime(df_full["date"])

    s, e = int(slider_value[0]), int(slider_value[1])
    x_range = (df_full["date"].iloc[s], df_full["date"].iloc[e])
    n_days = e - s + 1

    d0 = x_range[0].strftime("%b %d, %Y")
    d1_str = x_range[1].strftime("%b %d, %Y")
    label = f"{d0} – {d1_str}  ({n_days} trading days)"

    # Compute MAs on full 12-month data; x_range only zooms the view
    raw_mas = compute_mas(df_full, "adj_close")
    log_mas = compute_mas(df_full, "log_close")

    section_title_style = {
        "marginTop": "28px", "marginBottom": "12px",
        "fontSize": "17px", "fontWeight": "600",
    }

    raw_section = html.Div([
        html.H2("Raw Prices", style=section_title_style),
        *build_section_components(df_full, raw_mas, "adj_close", True, "Close", x_range),
    ])
    log_section = html.Div([
        html.H2("Log Prices", style=section_title_style),
        *build_section_components(df_full, log_mas, "log_close", False, "Log Close", x_range),
    ])

    return label, raw_section, log_section


if __name__ == "__main__":
    app.run(debug=True)

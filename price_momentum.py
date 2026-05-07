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

MA_WINDOWS = [5, 10, 20, 50]

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
SLIDER_LABEL_STYLE = {
    "fontSize": "12px", "color": "#6b7280",
    "display": "block", "marginBottom": "4px",
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


def _db_path(symbol: str) -> Path:
    return PRICE_DIR / f"{symbol}_{date.today().strftime('%Y%m%d')}.db"


def _load_from_cache(symbol: str) -> pd.DataFrame | None:
    """Return today's cached DataFrame, or None if not yet fetched today."""
    db = _db_path(symbol)
    if not db.exists():
        return None
    with sqlite3.connect(db) as conn:
        df = pd.read_sql("SELECT * FROM price_data", conn)
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_data(symbol: str) -> tuple[pd.DataFrame, bool]:
    """Return (df, from_cache). Loads today's SQLite cache when available."""
    cached = _load_from_cache(symbol)
    if cached is not None:
        return cached, True

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
    df["volume"] = df["volume"] / 100_000  # scale in place

    _save_to_sqlite(df, symbol)
    return df, False


def _save_to_sqlite(df: pd.DataFrame, symbol: str) -> None:
    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_db_path(symbol)) as conn:
        df.to_sql("price_data", conn, if_exists="replace", index=False)


def compute_mas(df: pd.DataFrame) -> dict:
    """MA, 1st momentum, and 20-day rolling sum of 1st momentum for each window."""
    result = {}
    for w in MA_WINDOWS:
        ma = df["adj_close"].rolling(w).mean()
        d1 = ma.diff()
        result[w] = {
            "ma": ma,
            "d1": d1,
            "d1_sum": d1.rolling(20).sum(),  # fixed 20-day window across all MA series
        }
    return result


def bar_colors(series: pd.Series) -> list[str]:
    return ["#16a34a" if v >= 0 else "#dc2626" for v in series.fillna(0)]


def slider_marks(n_days: int) -> dict:
    """Week-labelled marks spaced ~every 4 weeks."""
    n_weeks = n_days // 5
    step = max(1, n_weeks // 10)
    marks = {w: f"{w}w" for w in range(0, n_weeks + 1, step)}
    if n_weeks not in marks:
        marks[n_weeks] = f"{n_weeks}w"
    return marks


# ---------------------------------------------------------------------------
# Figure builder — one figure per MA window
# ---------------------------------------------------------------------------

def build_window_figure(df_full: pd.DataFrame, w: int, mas: dict,
                         x_range: tuple | None = None) -> go.Figure:
    """
    2 rows × 2 cols for a single MA window (equal row heights):
      (1,1): Close & MA line chart
      (1,2): Daily Return bar (left y) + Volume bar (right y)  — dual y-axis
      (2,1): 1st Momentum bar chart
      (2,2): Rolling Sum 20d Momentum line chart
    MAs are computed on the full 12-month df_full; x_range only zooms the view.
    """
    dates = df_full["date"]
    m = mas[w]

    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{}, {"secondary_y": True}],
               [{}, {}]],
        subplot_titles=[
            f"Close & {w}d MA",
            "Daily Return & Volume",
            "1st Momentum",
            "Rolling Sum (20d) Momentum",
        ],
        row_heights=[0.5, 0.5],
        vertical_spacing=0.18,
    )

    # (1,1): Close + MA
    fig.add_trace(go.Scatter(
        x=dates, y=df_full["adj_close"], mode="lines", showlegend=False,
        line=dict(width=1, color="#2563eb"),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=m["ma"], mode="lines", showlegend=False,
        line=dict(width=1.5, dash="dash", color="#f59e0b"),
    ), row=1, col=1)

    # (1,2): Daily return (primary/left y) + Volume (secondary/right y)
    fig.add_trace(go.Bar(
        x=dates, y=df_full["daily_return"],
        marker_color=bar_colors(df_full["daily_return"]),
        showlegend=False, name="Return",
    ), row=1, col=2)
    fig.add_trace(go.Bar(
        x=dates, y=df_full["volume"],
        marker_color="#93c5fd", opacity=0.45,
        showlegend=False, name="Volume",
    ), row=1, col=2, secondary_y=True)

    # (2,1): 1st momentum bar
    fig.add_trace(go.Bar(
        x=dates, y=m["d1"],
        marker_color=bar_colors(m["d1"]), showlegend=False,
    ), row=2, col=1)

    # (2,2): Rolling sum line
    fig.add_trace(go.Scatter(
        x=dates, y=m["d1_sum"], mode="lines", showlegend=False,
        line=dict(width=1.5, color="#6366f1"),
    ), row=2, col=2)

    if x_range:
        fig.update_xaxes(range=list(x_range))

    fig.update_xaxes(
        showgrid=False, zeroline=False, linecolor="#e5e7eb",
        tickformat="%Y-%m",
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="#e5e7eb",
        zeroline=True, zerolinecolor="#9ca3af", zerolinewidth=1,
    )
    fig.update_layout(
        height=520,
        margin=dict(l=55, r=55, t=55, b=20),
        paper_bgcolor="white",
        plot_bgcolor="#f9fafb",
        font=dict(color="#111827", size=10),
        bargap=0.1,
    )
    return fig


def build_section_components(df_full: pd.DataFrame, mas: dict,
                              x_range: tuple | None = None) -> list:
    """Return a list of bordered html.Div components, one per MA window."""
    return [
        html.Div(
            dcc.Graph(figure=build_window_figure(df_full, w, mas, x_range),
                      config={"displayModeBar": True}),
            style=WINDOW_DIV_STYLE,
        )
        for w in MA_WINDOWS
    ]


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

                # Symbol input — Enter key or Analyze button triggers load
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

                html.Div(id="error-msg", style={"display": "none"}),

                dcc.Store(id="df-store"),

                # First progress indicator — data loading
                dcc.Loading(
                    id="loading-data",
                    type="circle",
                    color="#2563eb",
                    style={"minHeight": "40px"},
                    children=html.Div(id="data-status",
                                      style={"fontSize": "13px", "color": "#6b7280",
                                             "marginBottom": "8px"}),
                ),

                # Date controls — hidden until data loads
                html.Div(id="date-controls", style=CONTROLS_STYLE_HIDDEN, children=[
                    # Quick-select buttons
                    html.Div(
                        style={"display": "flex", "gap": "8px", "marginBottom": "16px",
                               "alignItems": "center"},
                        children=[
                            html.Span("Quick select:",
                                      style={"fontSize": "13px", "color": "#6b7280"}),
                            html.Button("4W",  id="btn-4w",  n_clicks=0, style=BTN_STYLE),
                            html.Button("8W",  id="btn-8w",  n_clicks=0, style=BTN_STYLE),
                            html.Button("12W", id="btn-12w", n_clicks=0, style=BTN_STYLE),
                            html.Button("24W", id="btn-24w", n_clicks=0, style=BTN_STYLE),
                            html.Span(id="date-range-display",
                                      style={"marginLeft": "20px", "fontSize": "13px",
                                             "color": "#374151"}),
                        ],
                    ),
                    # Start slider (weeks)
                    html.Div(style={"marginBottom": "12px"}, children=[
                        html.Label("Start", style=SLIDER_LABEL_STYLE),
                        dcc.Slider(id="start-slider", min=0, max=1, step=1, value=0,
                                   marks={}, tooltip={"always_visible": False}),
                    ]),
                    # End slider (weeks)
                    html.Div(children=[
                        html.Label("End", style=SLIDER_LABEL_STYLE),
                        dcc.Slider(id="end-slider", min=0, max=1, step=1, value=1,
                                   marks={}, tooltip={"always_visible": False}),
                    ]),
                ]),

                # Second progress indicator — chart rendering
                html.Div(id="chart-status", style={"display": "none"},
                         children="Rendering charts…"),

                dcc.Loading(
                    id="loading-charts",
                    type="circle",
                    color="#2563eb",
                    style={"minHeight": "60px"},
                    children=html.Div(id="raw-section"),
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
    Output("start-slider", "min"),
    Output("start-slider", "max"),
    Output("start-slider", "marks"),
    Output("start-slider", "value"),
    Output("end-slider", "min"),
    Output("end-slider", "max"),
    Output("end-slider", "marks"),
    Output("end-slider", "value"),
    Output("date-controls", "style"),
    Output("error-msg", "children"),
    Output("error-msg", "style"),
    Output("data-status", "children"),
    Input("analyze-btn", "n_clicks"),
    Input("symbol-input", "n_submit"),
    State("symbol-input", "value"),
    prevent_initial_call=True,
)
def load_data(n_clicks, n_submit, symbol):
    hidden_err = {"display": "none"}
    visible_err = {
        "color": "#dc2626", "marginBottom": "12px", "fontSize": "14px",
        "backgroundColor": "#fef2f2", "padding": "8px 12px",
        "border": "1px solid #fecaca", "borderRadius": "4px",
    }

    if not symbol or not symbol.strip():
        return (no_update, no_update, no_update, no_update, no_update,
                no_update, no_update, no_update, no_update,
                CONTROLS_STYLE_HIDDEN, "Please enter a ticker symbol.", visible_err, None)

    symbol = symbol.strip().upper()
    try:
        df, from_cache = fetch_data(symbol)
    except RuntimeError as exc:
        return (None, 0, 1, {}, 0, 0, 1, {}, 1,
                CONTROLS_STYLE_HIDDEN, str(exc), visible_err, None)
    except Exception as exc:
        return (None, 0, 1, {}, 0, 0, 1, {}, 1,
                CONTROLS_STYLE_HIDDEN,
                f"Unexpected error loading '{symbol}': {exc}", visible_err, None)

    n = len(df)
    n_weeks = (n - 1) // 5
    marks = slider_marks(n)
    df_json = df.to_json(date_format="iso", orient="split")
    status = (f"Loaded from cache ({date.today()})."
              if from_cache else "Fetched from Yahoo Finance.")
    return (df_json,
            0, n_weeks, marks, 0,
            0, n_weeks, marks, n_weeks,
            CONTROLS_STYLE_VISIBLE, "", hidden_err, status)


@app.callback(
    Output("start-slider", "value", allow_duplicate=True),
    Output("end-slider", "value", allow_duplicate=True),
    Input("btn-4w",  "n_clicks"),
    Input("btn-8w",  "n_clicks"),
    Input("btn-12w", "n_clicks"),
    Input("btn-24w", "n_clicks"),
    State("df-store", "data"),
    prevent_initial_call=True,
)
def quick_select(b4, b8, b12, b24, df_json):
    if df_json is None:
        return no_update, no_update

    df = pd.read_json(io.StringIO(df_json), orient="split")
    n_weeks = (len(df) - 1) // 5
    week_map = {"btn-4w": 4, "btn-8w": 8, "btn-12w": 12, "btn-24w": 24}
    triggered = ctx.triggered_id

    if triggered not in week_map:
        return no_update, no_update

    return max(0, n_weeks - week_map[triggered]), n_weeks


@app.callback(
    Output("date-range-display", "children"),
    Output("chart-status", "style"),
    Output("raw-section", "children"),
    Input("start-slider", "value"),
    Input("end-slider", "value"),
    State("df-store", "data"),
    prevent_initial_call=True,
)
def update_charts(start_week, end_week, df_json):
    if df_json is None:
        return "", {"display": "none"}, None

    df_full = pd.read_json(io.StringIO(df_json), orient="split")
    df_full["date"] = pd.to_datetime(df_full["date"])
    n = len(df_full)

    s = min(int(start_week) * 5, n - 1)
    e = min(int(end_week) * 5 + 4, n - 1)
    if s > e:
        s, e = e, s

    x_range = (df_full["date"].iloc[s], df_full["date"].iloc[e])
    n_days = e - s + 1

    label = (f"{int(start_week)}w – {int(end_week)}w  "
             f"({n_days} trading days)")

    # Compute MAs on full 12-month data; x_range only zooms the view
    mas = compute_mas(df_full)

    section_title_style = {
        "marginTop": "28px", "marginBottom": "12px",
        "fontSize": "17px", "fontWeight": "600",
    }
    raw_section = html.Div([
        html.H2("Price Momentum", style=section_title_style),
        *build_section_components(df_full, mas, x_range),
    ])

    return label, {"display": "none"}, raw_section


if __name__ == "__main__":
    app.run(debug=True)

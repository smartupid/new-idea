import io
import sqlite3
from datetime import date
from pathlib import Path
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State, ctx, no_update

PRICE_DIR = Path(__file__).parent / "daily_price"
MA_WINDOWS = [5, 10, 20, 50]
PLOT_HEIGHT = 300

app = dash.Dash(__name__)

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
PLOT_DIV_STYLE = {
    "border": "1px solid #d1d5db",
    "borderRadius": "6px",
    "marginBottom": "20px",
    "padding": "8px 8px 4px",
    "backgroundColor": "white",
}
LAYOUT_BASE = dict(
    height=PLOT_HEIGHT,
    margin=dict(l=55, r=55, t=45, b=20),
    paper_bgcolor="white",
    plot_bgcolor="#f9fafb",
    font=dict(color="#111827", size=10),
    bargap=0.1,
    legend=dict(orientation="h", y=1.12),
)


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
    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    db_path = PRICE_DIR / f"{symbol}_{date.today().strftime('%Y%m%d')}.db"

    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql("SELECT * FROM price_data", conn)
            df["date"] = pd.to_datetime(df["date"])
            return df

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
    df["daily_return"] = df["adj_close"] / df["adj_close"].shift(1) - 1
    df["volume"] = df["volume"] / 100_000

    with sqlite3.connect(db_path) as conn:
        df.to_sql("price_data", conn, if_exists="replace", index=False)

    return df


def compute_mas(df: pd.DataFrame) -> dict:
    return {
        w: {"ma": df["adj_close"].rolling(w).mean(),
            "diff": df["adj_close"] - df["adj_close"].rolling(w).mean()}
        for w in MA_WINDOWS
    }


def bar_colors(series: pd.Series) -> list[str]:
    return ["#16a34a" if v >= 0 else "#dc2626" for v in series.fillna(0)]


def slider_marks(n: int) -> dict:
    step = max(1, n // 6)
    indices = list(range(0, n, step))
    if n - 1 not in indices:
        indices.append(n - 1)
    return {i: f"{round(i / 5)}w" for i in indices}


# ---------------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------------

def _apply_axes(fig, x_range, secondary_y_title: str):
    if x_range:
        fig.update_xaxes(range=list(x_range))
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#e5e7eb")
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False, secondary_y=False)
    fig.update_yaxes(showgrid=False, zeroline=True, zerolinecolor="#9ca3af",
                     title_text=secondary_y_title, secondary_y=True)


def build_price_figure(df: pd.DataFrame, x_range=None) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for col, name, color, dash in [
        ("high",      "High",  "#16a34a", "dot"),
        ("low",       "Low",   "#dc2626", "dot"),
        ("adj_close", "Close", "#2563eb", "solid"),
    ]:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df[col], name=name, mode="lines",
            line=dict(width=1, color=color, dash=dash),
        ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=df["date"], y=df["volume"], name="Volume (100K)",
        marker_color="#93c5fd", opacity=0.5,
    ), secondary_y=True)

    fig.update_layout(title="High / Low / Close  +  Volume (100K)", **LAYOUT_BASE)
    _apply_axes(fig, x_range, "Volume (100K)")
    return fig


def build_ma_figure(df: pd.DataFrame, w: int, ma: pd.Series, diff: pd.Series,
                    x_range=None) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["adj_close"], name="Close", mode="lines",
        line=dict(width=1, color="#2563eb"),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df["date"], y=ma, name=f"{w}d MA", mode="lines",
        line=dict(width=1.5, dash="dash", color="#f59e0b"),
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=df["date"], y=diff, name="Close − MA",
        marker_color=bar_colors(diff),
    ), secondary_y=True)

    fig.update_layout(title=f"{w}-Day Moving Average  +  Close − MA", **LAYOUT_BASE)
    _apply_axes(fig, x_range, "Close − MA")
    return fig


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

                html.Div(
                    style={"display": "flex", "gap": "8px", "marginBottom": "16px", "alignItems": "center"},
                    children=[
                        dcc.Input(
                            id="symbol-input", type="text",
                            placeholder="Stock symbol (e.g. AAPL)",
                            debounce=False, n_submit=0,
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
                         style={"color": "#dc2626", "marginBottom": "12px",
                                "fontSize": "14px", "padding": "8px 12px", "borderRadius": "4px"}),

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
                    children=html.Div(id="charts-section"),
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
    Input("symbol-input", "n_submit"),
    State("symbol-input", "value"),
    prevent_initial_call=True,
)
def load_data(_, _submit, symbol):
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
        return (None, 0, 1, {}, [0, 1], CONTROLS_STYLE_HIDDEN, str(exc), visible_err, None)
    except Exception as exc:
        return (None, 0, 1, {}, [0, 1], CONTROLS_STYLE_HIDDEN,
                f"Unexpected error loading '{symbol}': {exc}", visible_err, None)

    n = len(df)
    marks = slider_marks(n)
    df_json = df.to_json(date_format="iso", orient="split")
    return (df_json, 0, n - 1, marks, [0, n - 1], CONTROLS_STYLE_VISIBLE, "", hidden_err, None)


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
    Output("charts-section", "children"),
    Input("date-slider", "value"),
    State("df-store", "data"),
    prevent_initial_call=True,
)
def update_charts(slider_value, df_json):
    if df_json is None:
        return "", None

    df_full = pd.read_json(io.StringIO(df_json), orient="split")
    df_full["date"] = pd.to_datetime(df_full["date"])

    s, e = int(slider_value[0]), int(slider_value[1])
    x_range = (df_full["date"].iloc[s], df_full["date"].iloc[e])
    n_days = e - s + 1

    d0 = x_range[0].strftime("%b %d, %Y")
    d1_str = x_range[1].strftime("%b %d, %Y")
    label = f"{d0} – {d1_str}  ({n_days} trading days)"

    mas = compute_mas(df_full)

    def wrap(fig):
        return html.Div(
            dcc.Graph(figure=fig, config={"displayModeBar": True}),
            style=PLOT_DIV_STYLE,
        )

    charts = [wrap(build_price_figure(df_full, x_range))]
    for w in MA_WINDOWS:
        charts.append(wrap(build_ma_figure(df_full, w, mas[w]["ma"], mas[w]["diff"], x_range)))

    return label, html.Div(charts)


if __name__ == "__main__":
    app.run(debug=True)

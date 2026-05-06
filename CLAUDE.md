# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Daily pipeline that scrapes Yahoo Finance's unofficial screener API for top daily gainers and losers, then appends results to SQLite databases. Runs automatically via GitHub Actions Mon–Fri at midnight UTC.

## Running the Scripts

```bash
# Install dependencies
pip install -r requirements.txt

# Fetch and store daily gainers
python yahoo_daily_gainers.py

# Fetch and store daily losers
python yahoo_daily_losers.py
```

Each script produces two SQLite databases — a "long" version (all API fields) and a "short" version (9 display columns matching Yahoo Finance's UI).

## Architecture

Both scripts share an identical structure with only the `scrIds` parameter differing (`day_gainers` vs `day_losers`):

1. **Session warm-up**: A `GET` to the Yahoo Finance markets page first (e.g., `/markets/stocks/gainers/`) establishes cookies/session state before hitting the API.
2. **Pagination**: `fetch_page()` calls `query2.finance.yahoo.com/v1/finance/screener/predefined/saved` with `start` offsets up to `max_pages * count_per_page`. Loop breaks on empty `quotes`.
3. **Retry logic**: Up to 4 attempts per page with exponential backoff (`1.2 * attempt` seconds).
4. **Storage**: `save_to_sqlite()` appends rows with a `run_date` column. `clean_for_sqlite()` JSON-serializes any list/dict/set fields before insertion.

### Output databases (written to working directory)

| Database | Table | Contents |
| --- | --- | --- |
| `yahoo_gainers_long.db` | `gainers_history` | All API fields |
| `yahoo_gainers_short.db` | `gainers_history` | 9 display columns |
| `yahoo_losers_long.db` | `losers_history` | All API fields |
| `yahoo_losers_short.db` | `losers_history` | 9 display columns |

## GitHub Actions Workflow

`.github/workflows/daily_yahoo_finance.yml` runs both scripts sequentially, then commits all `*.db` files back to `main` with the message `Update database files - YYYY-MM-DD`.

- Schedule: `0 0 * * 1-5` (midnight UTC, Mon–Fri)
- Manual trigger: `workflow_dispatch` (Actions tab → Run workflow)
- Email notifications require four repository secrets: `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_TO` (and uses `GITHUB_TOKEN` automatically for push access)
- Workflow permissions must be set to **Read and write** in repository Settings → Actions → General

## Key Constraints

- `.db` files are **not** gitignored — they are intentionally committed by the workflow. Keep this in mind when running locally; your local databases will show as modified after a run.
- The Yahoo Finance API is unofficial and undocumented. If scraping breaks, check `scrIds` values and response shape at `data["finance"]["result"][0]["quotes"]`.
- Repository size grows with each daily commit. GitHub's 100 MB per-file limit is the ceiling; consider cloud storage if databases approach 50 MB.

---

## Price Momentum Study (`price_momentum.py`)

Interactive Dash web app for technical analysis of any stock ticker. Run with:

```bash
pip install yfinance plotly dash numpy
python price_momentum.py
# open http://127.0.0.1:8050
```

### Data pipeline (`fetch_data`)

Pulls 12 months of OHLCV from `yfinance` (split/dividend-adjusted close). Raises `RuntimeError` with a user-friendly message on API errors or empty results; `_friendly_yf_error()` maps raw exception text to readable explanations (invalid symbol, network failure, rate-limit). Derived columns:

| Column | Formula |
| --- | --- |
| `daily_range` | `high - low` |
| `daily_mid` | `daily_range / 2` |
| `daily_std` | `sqrt(high * low)` |
| `daily_return` | `adj_close / adj_close.shift(1) - 1` |
| `log_close` | `log(adj_close)` |
| `log_mid` | `log(daily_mid)` |
| `log_std` | `log(daily_std)` |
| `scaled_volume` | `volume / std(volume)` — normalised over full 12-month window |
| `vol_weighted_return` | `scaled_volume * daily_return` |

### Analysis (`compute_mas`)

For each of six windows — 5, 10, 15, 20, 25, 50 days — on `adj_close` (raw section) or `log_close` (log section):

- **MA**: rolling mean
- **d1**: first difference of MA (1st-order momentum)
- **d2**: second difference of MA (2nd-order momentum)
- **roc**: `d1.diff() / d1.shift(1).abs()` — rate of change of 1st-order momentum
- **vol_d1 / vol_d2 / vol_roc**: above three multiplied by `scaled_volume` for vol-weighted plotting

MAs are **always computed on the full 12-month dataset**. The display window only zooms the x-axis via `fig.update_xaxes(range=...)`, so MA values are never truncated by a short viewing window.

### Visualization (`build_window_figure` + `build_section_components`)

Each MA window is a **separate** `go.Figure` (via `build_window_figure`) wrapped in a bordered `html.Div`. `build_section_components` iterates over all six windows and returns the list of divs. Every subplot has its own title via `subplot_titles`.

**Raw Prices** — 5 rows × 2 cols per window (`height = 5 × 185 px`):

| Row | Left column | Right column |
| --- | --- | --- |
| 1 | Close & {w}d MA (line) | Scaled Volume (bar) |
| 2 | Daily Return (bar) | Vol × Return (bar) |
| 3 | 1st Momentum (bar) | Vol × 1st Momentum (bar) |
| 4 | 2nd Momentum (bar) | Vol × 2nd Momentum (bar) |
| 5 | Rate of Change (bar) | Vol × Rate of Change (bar) |

**Log Prices** — 4 rows × 2 cols per window (`height = 4 × 185 px`), same layout minus the return row:

| Row | Left column | Right column |
| --- | --- | --- |
| 1 | Log Close & {w}d MA (line) | Scaled Volume (bar) |
| 2 | 1st Momentum (bar) | Vol × 1st Momentum (bar) |
| 3 | 2nd Momentum (bar) | Vol × 2nd Momentum (bar) |
| 4 | Rate of Change (bar) | Vol × Rate of Change (bar) |

`vertical_spacing=0.08` per figure; section border via `WINDOW_DIV_STYLE` CSS on the wrapping div.

### UI / Dash layout

- **Symbol input + Analyze button** — triggers `load_data`, stores serialised DataFrame in `dcc.Store`
- **Two `dcc.Loading` spinners**: one covers the data-fetch phase (`data-status`), the second covers chart rendering (`raw-section`, `log-section`)
- **Error display** — styled red box (with background) appears on API errors; hidden when data loads successfully
- **Date controls** (appear after first successful load):
  - Quick-select buttons: 4W / 8W / 12W / 24W / All (trading days ≈ weeks × 5)
  - `dcc.RangeSlider` with two handles; marks capped at ~7 evenly-spaced labels in `"Apr '25"` format
  - Active date range and trading-day count displayed as text
- **Three callbacks**:
  1. `load_data` — fetches data, populates store + slider config; surfaces friendly error messages
  2. `quick_select` — translates week buttons to slider index values (`allow_duplicate=True`)
  3. `update_charts` — reads store + slider range, builds per-window figures with full-data MAs and zoomed x-axis

### Key implementation notes

- `pd.read_json` calls use `io.StringIO(df_json)` to avoid the pandas ≥ 2.x deprecation warning for literal JSON strings.
- Do **not** use a clientside callback and a server callback writing to the same output property — Dash raises a hash-lookup error even with `allow_duplicate=True`. Use `dcc.Loading` for loading feedback instead.
- `assets/style.css` is loaded automatically by Dash from the `assets/` directory.

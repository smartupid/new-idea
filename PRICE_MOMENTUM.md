# Objective

This file contains the instructions to gather price info on a stock symbol and then compute a set of momentum based metrics and plot them for inspection.

## Data

The daily quote data for a particular stock will be pulled from Yahoo! Finance for the last 12 months. If the Yahoo! Finance API returns an error message, display a meaningful interpretation on the UI. If the data for the said stock is already pulled for the day, skip data pull.

The data should at least contain the following columns. If the API returns more columns, keep them.

- date
- daily open
- daily high
- daily low
- daily close
- adjusted close
- volume

The following columns will be added:

- daily range = daily high - daily low
- daily return = adjusted close / prior day adjusted close - 1
- volume = volume / 100000

The data should be saved as a SQLite file in the ./daily_price folder with a name in the format of "symbol_yyyymmdd'.

## Analysis

The following moving averages will be computed over 5-day, 10-day, 20-day, and 50-day windows on adjusted close. The difference between the daily adjusted close and the various moving averages will be calculated.

## Visualization

The charts below will be displayed using the full width of the page. Each plot below should have its own title. Determine the best format for x-axis label. Keep the same height of all plots. Each plot should have a visual border.

- Three lines showing the high, low, and adjusted close of each day, and the daily volume as barchart overlaid in one plot
- For each moving average window, the moving average as a line chart and the difference between adjust close and the moving average as a barchart, overlaid in one plot

## UI

A web UI will be created. At start, there's a text box for the user to input a stock symbol. Once a symbol is entered (by clicking Enter or the Analyze button), the following visual elements will be displayed

- a progress bar indicating data is being pulled
- a set of buttons to allow quick selection of the date window being plotted: 4 weeks, 8 weeks, 12 weeks, 24 weeks
- two sliders to allow setting specific dates for the two ends of the window; the range labelled by number of weeks instead of calendar dates
- a message indicating analysis and plotting under way
- the set of plots as defined above

When the date window changes, all plots should be refreshed to reflect the change with a message indicating progress.

## Run

```bash
pip install yfinance plotly dash numpy
python price_momentum.py
# open http://127.0.0.1:8050
```

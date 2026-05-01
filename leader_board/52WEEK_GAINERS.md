# 52-week Gainers Analysis

This file contains instructions to extract the top 52-week gainers from Yahoo! Finance, conduct trend analysis, and generate a report HTML file.

## Data Pull

Source url: https://finance.yahoo.com/markets/stocks/52-week-gainers/

Two scraping options are provided:

- `bs_scraper.py` — uses `requests` + `BeautifulSoup`.
- `selenium_scraper.py` — uses Selenium with headless Chrome (via `webdriver-manager`).

BeautifulSoup has run successfully in all tries.

The code will run on the last day of each month after market close through Github workflows.


## Analysis and Report

Search through the data and produce following reports on a HTML file.
- Top 20 stocks that moved up the most between the last two runs, list in the descending order of improvement in ranks, include all columns from the data
- Top 20 stocks that had the biggest increase in 52-week change percentage, list in the descending order of the change, include all columns from the data
- Top 20 stocks that first entered the list in the last run, list in the descending order of their ranks, include all columns from the data

All tables should be interactive allowing sorting by any column.


## Run Book

Install:

```bash
pip install -r requirements.txt
```

Run (top 500 gainers, pulling with BeautifulSoup):

```bash
# Pull + report (default)
python pull_leaders.py --method bs --pages 5

# Report only (data already pulled today)
python pull_leaders.py --report-only

# Pull only, no report
python pull_leaders.py --method bs --pages 5 --no-report

# Custom output path
python pull_leaders.py --report-only --report-out ./output/report.html
```

# 52-week Gainers Analysis

This file contains instructions to extract the top 500 52-week gainers from Yahoo! Finance at each data pull, conduct trend analysis, and generate a web app that shows the trend report and allows search against the data.

A Github Action is set up to run the data pull on the last day of each month and send the trend report in email.

## Data Pull

Source url: [Yahoo Finance 52-week Gainers](https://finance.yahoo.com/markets/stocks/52-week-gainers/)

Two scraping options are provided:

- `bs_scraper.py` — uses `requests` + `BeautifulSoup`.
- `selenium_scraper.py` — uses Selenium with headless Chrome (via `webdriver-manager`).

BeautifulSoup has run successfully in all tries.

## UI

The UI contains a navigation sidebar and the main panel on the right.

The navigation sidebar contains two tabs fixed at one line of text heigth: 1. Report; 2. Search

On the Report tab, four buttons at the top allow the user to filter the data: Overall - no filter, Large - market cap above 100B, Mid - market cap between 10B and 100B, Small - market cap below 10B. By default, no filter is applied. Based on the user selection, the tables listed in Analysis and Report will be shown.

On the Search tab, the page will be initialized with a search box. When the user enters a stock symbol, the app will search for and show all records corresponding to the symbol from the available data. A price change percentage or return will be calculated between each pair of records adjacent in time and added as a column. If the symbol is not found, a meaningful error message should be shown.

## Analysis and Report

Based on the filter applied to market cap, search through the data and produce following reports.

- Top 20 stocks that had the most price change percentage between the last two runs, list in the descending order of the return, include all columns from the data
- Top 20 stocks that moved up the most between the last two runs, list in the descending order of improvement in ranks, include all columns from the data
- Top 20 stocks that had the biggest increase in 52-week change percentage, list in the descending order of the change, include all columns from the data
- Top 20 stocks that first entered the list in the last run, list in the descending order of their ranks, include all columns from the data

All tables should be interactive allowing sorting by any column when displayed on the UI.

## Run Book

Install:
```bash
pip install -r requirements.txt
```
Run:
```bash
python pull_leaders.py pull [--method bs|selenium] [--pages N] [--db PATH]
python pull_leaders.py report [--db PATH] [--out PATH]
python pull_leaders.py app [--db PATH] [--debug]
```

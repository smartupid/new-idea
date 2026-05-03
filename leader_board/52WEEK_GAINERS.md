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

The UI contains a navigation frame on the left and the main frame on the right.

The navigation panel contains two tabs: 1. Report; 2. Search

On the Report tab, the tables listed in Analysis and Report will be shown.

On the Search tab, the page will be initialized with a search box. When the user enters a stock symbol, the app will search for and show all records corresponding to the symbol from the available data. A price change percentage or return will be calculated between each pair of records adjacent in time and added as a column. If the symbol is not found, a meaningful error message should be shown.

## Analysis and Report

Search through the data and produce following reports.

- Top 20 stocks that had the most price change percentage between the last two runs, list in the descending order of the return, include all columns from the data
- Top 20 stocks that moved up the most between the last two runs, list in the descending order of improvement in ranks, include all columns from the data
- Top 20 stocks that had the biggest increase in 52-week change percentage, list in the descending order of the change, include all columns from the data
- Top 20 stocks that first entered the list in the last run, list in the descending order of their ranks, include all columns from the data

All tables should be interactive allowing sorting by any column when displayed on the UI.

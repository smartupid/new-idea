# Objective

This file contains the instructions to gather price info on a stock symbol and then compute a set of momentum based metrics and plot them for inspection. 


# Data

The daily quote data for a particular stock will be pulled from Yahoo! Finance for the last 12 months. If the Yahoo! Finance API returns an error message, display a meaningful interpretation on the UI.

The data should contain the following columns
- date
- daily open
- daily high
- daily low
- daily close
- adjusted close
- volume

The standard deviation of the daily volume over the 12 months will be calculated, then each daily volume will be converted to a scaled value using the standard deviation as the basis.

The following columns will be added
- daily range = daily high - daily low
- daily mid = daily range / 2
- daily std = sqrt(daily high * daily low)
- daily return = adjusted close / prior day adjusted close - 1
- log close = log(adjusted close)
- log mid = log(daily mid)
- log std = log(daily std)
- vol weighted return = scaled volume * daily return

The data should be saved as a SQLite file in the ./daily_price folder with a name in the format of "symbol_yyyymmdd'.

# Analysis

The following moving averages will be computed over 5-day, 10-day, 15-day, 20-day, 25-day, and 50-day windows on adjusted close and log close.

Then the 1st order and 2nd order momentums will be calculated for each moving average series above. A rate of change will also be calculated for the 1st order momentum over the previous day. The momentum values and the rate of change will then be multiplied by the scaled volume for plotting.


# Visualization

Each plot below should have its own title. All plots under each moving average window form a section. Each section should be separated from the next by a visual border.

## raw prices

Generate the following plots for each of the moving average window in a two-column layout:
left column in the listed order
- adjusted close and the moving average line chart
- daily return barchart
- 1st order momentum barchart
- 2nd order momentum barchart
- 1st order momentum rate of change barchart
right column in the list order
- scaled volume barchart
- vol weighted return barchart
- vol weighted 1st order momentum barcharts
- vol weighted 2nd order momentum barcharts
- vol weighted 1st momentum rate of change barchart

## log prices

Generate the following plots for each of the moving average window in a two-column layout:
left column in the listed order
- log close and the moving average line chart
- 1st order momentum barchart
- 2nd order momentum barchart
- 1st order momentum rate of change barchart
right column in the list order
- scaled volume barchart
- vol weighted 1st order momentum barcharts
- vol weighted 2nd order momentum barcharts
- vol weighted 1st momentum rate of change barchart


# UI

A web UI will be created. At start, there's a text box for the user to input a stock symbol. Once a symbol is entered, the following visual elements will be displayed
- a progress bar or a spinning wheel indicating data is being pulled
- a set of buttons to allow quick selection of the date window being plotted: 4 weeks, 8 weeks, 12 weeks, 24 weeks, and two sliders to select specific dates of the two ends of the window
- a second progress bar or spinning wheel indicating analysis and plotting under way
- the set of plots as defined above

When the date window changes, the second progress bar should reappear and all plots should be refreshed to reflect the change.

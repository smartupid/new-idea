# Gainer-Loser Report

This file contains a list of trend reports to be created based on the daily gainers and losers data. It serves as instruction to Claude to create the implementation code.


## data required

| Database | Table | Contents |
|---|---|---|
| `yahoo_gainers_long.db` | `gainers_history` | All API fields |
| `yahoo_losers_long.db` | `losers_history` | All API fields |

Columns to be used for the report include
- symbol
- shortName
- regularMarketPrice
- regularMarketChange
- regularMarketChangePercent
- regularMarketVolume
- averageDailyVolume3Month
- marketCap

Columns to be added
- regVolWeightedChangePercent = regularMarketVolume * regularMarketChangePercent
- regIndexedVolWeightedChangePercent = regularMarketVolume / averageDailyVolume3Month * regularMarketChangePercent
- marketCapChange = marketCap * regularMarketChangePercent

The data should be filtered by marketCap > 1B


## report requirements

The following plots or tables should be generated in a html file.

### trend reports
The following plots should be produced for the last 60 trading days and appear in two columns side by side
- number of daily gainers vs. losers barchart
- highest daily gain percentage vs. loss percentage barchart 
- ratio of gainers vs. losers line plot 
- ratio of daily total indexed volume weighted gain percentage vs. total indexed volume weighted loss percentage barchart
- ratio of daily total market gap change by gainers vs. by losers line chart


### top boards
The following tables should be generated for the last 1/2/4/8/12 weeks. The gainers table and the losers table should appear in two columns side by side. 
- top ten symbols with most gainer appearance 
- top ten symbols with most loser appearance 
- top ten symbols with highest indexed volume weighted gain percentage
- top ten symbols with highest indexed volume weighted loss percentage
- top ten symbols with most consecutive gainer appearances
- top ten symbols with most consecutive loser appearances

Some reports can be augmented with sector/industry information later.


### u-turn boards
The following tables should appear pairwise in two columns side by side. 
- symbols with more gainer appearance in last 2 weeks than loser appearances last 4 weeks
- symbols with more loser appearance in last 2 weeks than gainer appearances last 4 weeks
- symbols with more gainer appearance in last 4 weeks than loser appearances last 8 weeks
- symbols with more loser appearance in last 4 weeks than gainer appearances last 8 weeks
- symbols with more gainer appearance in last 6 weeks than loser appearances last 12 weeks
- symbols with more loser appearance in last 6 weeks than gainer appearances last 12 weeks

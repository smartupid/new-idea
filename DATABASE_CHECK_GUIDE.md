# How to Check Database Updates

This guide shows you multiple ways to verify that your database files have been updated with new records from the GitHub Actions workflow.

## Method 1: Check on GitHub (Quick Visual Check)

1. **Go to your repository on GitHub**
   - Navigate to: `https://github.com/YOUR_USERNAME/new-idea`

2. **Check the database files**
   - Look for these files in the repository:
     - `yahoo_gainers_long.db`
     - `yahoo_gainers_short.db`
     - `yahoo_losers_long.db`
     - `yahoo_losers_short.db`

3. **Check file modification dates**
   - Click on each `.db` file
   - Look at the "Last modified" date
   - It should show today's date if the workflow ran successfully

4. **Check commit history**
   - Go to the repository main page
   - Look at recent commits
   - You should see commits like: "Update database files - YYYY-MM-DD"
   - Click on a commit to see which files were changed

## Method 2: Download and Check Locally (Recommended)

### Step 1: Pull Latest Changes

```bash
git pull origin main
```

### Step 2: Run the Check Script

I've created a Python script to check the databases:

```bash
python check_database_updates.py
```

This will show you:
- Total number of records in each database
- Number of records added today
- Latest run date
- Sample records from today

### Step 3: Manual SQLite Check (Alternative)

If you prefer to check manually using SQLite:

```bash
# Windows (if SQLite is installed)
sqlite3 yahoo_gainers_long.db

# Then run these SQL commands:
.tables                    # List all tables
SELECT COUNT(*) FROM gainers_history;  # Total records
SELECT COUNT(*) FROM gainers_history WHERE run_date = date('now');  # Today's records
SELECT DISTINCT run_date FROM gainers_history ORDER BY run_date DESC LIMIT 10;  # Recent dates
SELECT * FROM gainers_history WHERE run_date = date('now') LIMIT 5;  # Sample from today
.quit
```

## Method 3: Check Workflow Logs

1. **Go to GitHub Actions**
   - Navigate to: `https://github.com/YOUR_USERNAME/new-idea/actions`

2. **Open the latest workflow run**
   - Click on the most recent run

3. **Check the output**
   - Look for the "Run Yahoo Daily Gainers Script" step
   - You should see: `"Retrieved X rows from API"`
   - And: `"Appended X rows to yahoo_gainers_long.db in table 'gainers_history'"`
   - Same for the losers script

4. **Check the commit step**
   - Look at "Commit and push database files" step
   - Should show: `"Update database files - YYYY-MM-DD"`
   - Should complete successfully

## Method 4: Using Python Pandas (Quick Query)

Create a simple script to query the databases:

```python
import sqlite3
import pandas as pd
from datetime import datetime

# Check gainers database
conn = sqlite3.connect('yahoo_gainers_long.db')
today = datetime.today().strftime("%Y-%m-%d")

# Get today's records
df = pd.read_sql_query(
    f"SELECT * FROM gainers_history WHERE run_date = '{today}'",
    conn
)

print(f"Records from today: {len(df)}")
print(df.head())

conn.close()
```

## Expected Results

After a successful workflow run, you should see:

✅ **Database files updated:**
- File modification dates show today's date
- File sizes may have increased

✅ **New records added:**
- Each database should have new records with today's `run_date`
- The `run_date` column format is: `YYYY-MM-DD` (e.g., `2025-01-14`)

✅ **Commit created:**
- A new commit with message: "Update database files - YYYY-MM-DD"
- The commit includes changes to all 4 database files

## Database Structure

### Gainers Databases:
- **yahoo_gainers_long.db** → Table: `gainers_history` (all columns from API)
- **yahoo_gainers_short.db** → Table: `gainers_history` (selected columns only)

### Losers Databases:
- **yahoo_losers_long.db** → Table: `losers_history` (all columns from API)
- **yahoo_losers_short.db** → Table: `losers_history` (selected columns only)

### Common Columns:
- `run_date`: Date when the data was collected (YYYY-MM-DD format)
- `symbol`: Stock ticker symbol
- `shortName`: Company name
- `regularMarketPrice`: Current price
- `regularMarketChange`: Price change
- `regularMarketChangePercent`: Percentage change
- And many more...

## Troubleshooting

**No records from today:**
- Check if the workflow actually ran (check Actions tab)
- Verify the workflow completed successfully
- Check if it's a weekend (workflow only runs Mon-Fri)
- Verify the timezone - workflow runs at midnight UTC

**Database files not updated:**
- Check if the commit step succeeded
- Verify workflow permissions are set correctly
- Check the workflow logs for errors

**Can't find database files:**
- Make sure you've pulled the latest changes: `git pull origin main`
- Check if `.gitignore` is excluding `.db` files (it shouldn't be)

## Quick Verification Command

Run this one-liner to quickly check if today's data exists:

```bash
# Windows PowerShell
python -c "import sqlite3; from datetime import datetime; conn = sqlite3.connect('yahoo_gainers_long.db'); today = datetime.today().strftime('%Y-%m-%d'); count = conn.execute(f\"SELECT COUNT(*) FROM gainers_history WHERE run_date = '{today}'\").fetchone()[0]; print(f'Today ({today}): {count} records'); conn.close()"
```


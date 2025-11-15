"""
Script to check if database files have been updated with new records.
This helps verify that the GitHub Actions workflow is working correctly.
"""

import sqlite3
from datetime import datetime, timedelta
import os

def check_database(db_name, table_name, description):
    """Check database for recent records."""
    if not os.path.exists(db_name):
        print(f"❌ {description}: Database file '{db_name}' not found")
        return
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        
        # Get today's date
        today = datetime.today().strftime("%Y-%m-%d")
        
        # Get records from today
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE run_date = ?", (today,))
        today_count = cursor.fetchone()[0]
        
        # Get unique dates
        cursor.execute(f"SELECT DISTINCT run_date FROM {table_name} ORDER BY run_date DESC LIMIT 10")
        recent_dates = [row[0] for row in cursor.fetchall()]
        
        # Get latest run_date
        cursor.execute(f"SELECT MAX(run_date) FROM {table_name}")
        latest_date = cursor.fetchone()[0]
        
        print(f"\n📊 {description} ({db_name})")
        print(f"   Total records: {total_count:,}")
        print(f"   Records from today ({today}): {today_count:,}")
        print(f"   Latest run date: {latest_date}")
        print(f"   Recent dates: {', '.join(recent_dates[:5])}")
        
        # Show sample records from today
        if today_count > 0:
            cursor.execute(f"SELECT * FROM {table_name} WHERE run_date = ? LIMIT 3", (today,))
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            print(f"\n   Sample records from today:")
            for i, row in enumerate(rows, 1):
                print(f"   {i}. {dict(zip(columns, row))}")
        
    except sqlite3.Error as e:
        print(f"❌ Error reading {db_name}: {e}")
    finally:
        conn.close()

def main():
    print("=" * 60)
    print("Yahoo Finance Database Update Checker")
    print("=" * 60)
    
    # Check gainers databases
    check_database("yahoo_gainers_long.db", "gainers_history", "Gainers (Full Dataset)")
    check_database("yahoo_gainers_short.db", "gainers_history", "Gainers (Short Dataset)")
    
    # Check losers databases
    check_database("yahoo_losers_long.db", "losers_history", "Losers (Full Dataset)")
    check_database("yahoo_losers_short.db", "losers_history", "Losers (Short Dataset)")
    
    print("\n" + "=" * 60)
    print("✅ Check complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()


import pandas as pd
import sqlite3
import time

# --- Selenium Imports ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def get_top_500_gainers_selenium():
    """
    Scrapes the top 500 stock gainers from Yahoo Finance using Selenium
    to control a web browser, handling dynamic JavaScript content.
    """
    # --- Setup Selenium WebDriver ---
    print("🚀 Setting up browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run browser in the background
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Automatically download and manage the correct driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    url = "https://finance.yahoo.com/screener/predefined/52_week_gainers"
    print(f"Navigating to {url}...")
    driver.get(url)

    all_stocks_df = pd.DataFrame()
    
    # We need to fetch 5 pages to get ~500 stocks if each page has 100
    # Yahoo's "52-week-gainers" screen shows 100 per page.
    pages_to_scrape = 5

    try:
        for i in range(pages_to_scrape):
            print(f" Scraping page {i + 1}...")

            # Wait for the main data table to be loaded and visible
            wait = WebDriverWait(driver, 20)
            table = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "table")))

            # Use pandas to read the HTML table directly from the page source
            # This is much easier than manually finding each row and cell
            html_table = table.get_attribute('outerHTML')
            df = pd.read_html(html_table)[0]
            
            all_stocks_df = pd.concat([all_stocks_df, df], ignore_index=True)

            # If it's the last page, we don't need to click "Next"
            if i < pages_to_scrape - 1:
                # Find and click the "Next" button
                next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test='next-page']")))
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(3) # Wait a moment for the next page to load

    except Exception as e:
        print(f"❌ An error occurred during scraping: {e}")
        return None
    finally:
        print("Closing browser...")
        driver.quit() # Always close the driver to free up resources

    if all_stocks_df.empty:
        print("Could not retrieve any stock data.")
        return None
        
    print(f"\n✅ Successfully fetched a total of {len(all_stocks_df)} stocks.")
    # Minor data cleaning for consistency
    all_stocks_df.rename(columns={'52-Week Change': '52WeekChange'}, inplace=True)
    return all_stocks_df


def save_to_sqlite(dataframe, db_name='stocks.db', table_name='top_500_gainers'):
    """Saves a pandas DataFrame to a SQLite database table."""
    if dataframe is None or dataframe.empty:
        print("DataFrame is empty. Nothing to save.")
        return
        
    try:
        conn = sqlite3.connect(db_name)
        dataframe.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"💾 Data successfully saved to the '{table_name}' table in '{db_name}'.")
        conn.close()
    except sqlite3.Error as e:
        print(f"An error occurred while saving to SQLite: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    top_gainers_df = get_top_500_gainers_selenium()
    save_to_sqlite(top_gainers_df)
import argparse
from datetime import datetime, UTC
from db import init_db, insert_rows
import bs_scraper
import selenium_scraper
import report as rpt

URL_TEMPLATE = "https://finance.yahoo.com/markets/stocks/52-week-gainers/?start={start}&count=100"


def urls_for_pages(pages: int):
    return [URL_TEMPLATE.format(start=(i * 100)) for i in range(pages)]


def run_bs(pages: int, db_path: str = "yahoo_52wk_gainers.db"):
    conn = init_db(db_path)
    all_count = 0
    for url in urls_for_pages(pages):
        rows = bs_scraper.scrape_url(url)
        insert_rows(conn, rows, datetime.now(UTC).date().isoformat())
        all_count += len(rows)
    conn.close()
    return all_count


def run_selenium(pages: int, db_path: str = "yahoo_52wk_gainers.db"):
    conn = init_db(db_path)
    all_count = 0
    for url in urls_for_pages(pages):
        rows = selenium_scraper.scrape_url(url)
        insert_rows(conn, rows, datetime.now(UTC).date().isoformat())
        all_count += len(rows)
    conn.close()
    return all_count


def main():
    p = argparse.ArgumentParser(description="Pull 52-week gainers from Yahoo Finance and/or generate a report.")
    p.add_argument("--method", choices=["bs", "selenium"], default="bs")
    p.add_argument("--pages", type=int, default=5, help="number of 100-row pages to scrape (default: 5 => 500)")
    p.add_argument("--db", default="yahoo_52wk_gainers.db")
    p.add_argument("--report-only", action="store_true",
                   help="skip data pull; generate report from existing database")
    p.add_argument("--report-out", default="52wk_gainers_report.html",
                   help="output path for the HTML report (default: 52wk_gainers_report.html)")
    p.add_argument("--no-report", action="store_true",
                   help="skip report generation after data pull")
    args = p.parse_args()

    if not args.report_only:
        if args.method == "bs":
            count = run_bs(args.pages, args.db)
        else:
            count = run_selenium(args.pages, args.db)
        print(f"Inserted {count} rows using {args.method}")

    if not args.no_report:
        try:
            result = rpt.analyze(args.db)
            out = rpt.generate_html(result, args.report_out)
            print(f"Report written to: {out}  (comparing {result['prev_date']} → {result['latest_date']})")
            print(
                f"  Price chg movers: {len(result['top_price_chg'])} | "
                f"52Wk chg movers: {len(result['top_52wk'])} | "
                f"Most improved: {len(result['top_improved'])} | "
                f"New entrants: {len(result['top_new'])}"
            )
        except ValueError as e:
            print(f"Report skipped: {e}")


if __name__ == "__main__":
    main()

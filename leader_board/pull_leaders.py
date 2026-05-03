import argparse
from datetime import datetime, UTC
from db import init_db, insert_rows
import bs_scraper
import selenium_scraper

URL_TEMPLATE = "https://finance.yahoo.com/markets/stocks/52-week-gainers/?start={start}&count=100"


def _urls_for_pages(pages: int) -> list[str]:
    return [URL_TEMPLATE.format(start=(i * 100)) for i in range(pages)]


def _run_scraper(method: str, pages: int, db_path: str) -> int:
    conn = init_db(db_path)
    scraper = bs_scraper if method == "bs" else selenium_scraper
    count = 0
    for url in _urls_for_pages(pages):
        rows = scraper.scrape_url(url)
        insert_rows(conn, rows, datetime.now(UTC).date().isoformat())
        count += len(rows)
    conn.close()
    return count


def cmd_pull(args):
    count = _run_scraper(args.method, args.pages, args.db)
    print(f"Inserted {count} rows using {args.method}")


def cmd_report(args):
    import report as rpt
    try:
        result = rpt.analyze(args.db)
        out = rpt.generate_html(result, args.out)
        print(f"Report written to: {out}  ({result['prev_date']} → {result['latest_date']})")
        print(
            f"  Price chg: {len(result['top_price_chg'])} | "
            f"52Wk chg: {len(result['top_52wk'])} | "
            f"Improved: {len(result['top_improved'])} | "
            f"New: {len(result['top_new'])}"
        )
    except ValueError as e:
        print(f"Report skipped: {e}")


def cmd_app(args):
    import app
    app.run(db_path=args.db, debug=args.debug)


def main():
    p = argparse.ArgumentParser(description="52-week gainers pipeline.")
    sub = p.add_subparsers(dest="command", required=True, help="pull | report | app")

    pull_p = sub.add_parser("pull", help="Scrape Yahoo Finance and store data in the database.")
    pull_p.add_argument("--method", choices=["bs", "selenium"], default="bs")
    pull_p.add_argument("--pages", type=int, default=5, help="pages of 100 rows each (default: 5 → 500 rows)")
    pull_p.add_argument("--db", default="yahoo_52wk_gainers.db")
    pull_p.set_defaults(func=cmd_pull)

    report_p = sub.add_parser("report", help="Generate HTML report from existing database.")
    report_p.add_argument("--db", default="yahoo_52wk_gainers.db")
    report_p.add_argument("--out", default="52wk_gainers_report.html")
    report_p.set_defaults(func=cmd_report)

    app_p = sub.add_parser("app", help="Run the interactive Dash web app.")
    app_p.add_argument("--db", default="yahoo_52wk_gainers.db")
    app_p.add_argument("--debug", action="store_true")
    app_p.set_defaults(func=cmd_app)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

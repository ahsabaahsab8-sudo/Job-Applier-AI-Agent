import time
import argparse
from datetime import datetime
from pipeline import run_pipeline

def run_daily_scheduler(hour: int = 9, minute: int = 0, limit: int = 100, live: bool = False):
    print("=" * 60)
    print(f"[*] AI Job Finder Daily Scheduler Initialized")
    print(f"[*] Scheduled to trigger daily at {hour:02d}:{minute:02d}")
    print(f"[*] Target Daily Jobs: {limit} | Mode: {'LIVE' if live else 'DRY-RUN'}")
    print("=" * 60)

    last_run_date = None

    while True:
        now = datetime.now()
        current_date = now.date()

        if now.hour == hour and now.minute == minute and last_run_date != current_date:
            print(f"\n[!] Triggering daily job application batch at {now.strftime('%Y-%m-%d %H:%M:%S')}...")
            try:
                run_pipeline(limit=limit, dry_run=not live)
                last_run_date = current_date
            except Exception as e:
                print(f"[!] Error during scheduled execution: {e}")

        time.sleep(30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily Scheduler for AI Job Finder")
    parser.add_argument("--hour", type=int, default=9, help="Hour to run (24h format, default: 9)")
    parser.add_argument("--minute", type=int, default=0, help="Minute to run (default: 0)")
    parser.add_argument("--limit", type=int, default=100, help="Number of jobs to apply to daily")
    parser.add_argument("--live", action="store_true", help="Enable live sending mode")

    args = parser.parse_args()
    run_daily_scheduler(hour=args.hour, minute=args.minute, limit=args.limit, live=args.live)

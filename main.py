#!/usr/bin/env python3
"""
music-autodl — main runner
==========================
Orchestrates the full recommendation → download pipeline.
Can be run once (python main.py) or on a schedule (set SCHEDULE env var).

Usage:
    python main.py          # run once then exit
    python main.py --daemon # run on SCHEDULE (cron syntax) forever
"""

import argparse
import logging
import sys
import time
from datetime import datetime

# ── Bootstrap logging before any local imports ──────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("autodl")

# ── Load .env if present (optional) ─────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

from config import cfg
from core.seen_db      import SeenDB
from core.recommender  import build_recommendations, register_casing
from core.downloader   import TidarrDownloader


def run_once():
    """Execute a single recommendation + download cycle."""
    log.info("━" * 60)
    log.info("  music-autodl  starting run  %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("━" * 60)

    # ── Validate Tidarr is up ────────────────────────────────────────────────
    dl = TidarrDownloader(cfg)
    if not dl.health_check():
        log.error("Tidarr is unreachable at %s — aborting", cfg.tidarr.url)
        return

    # ── Load seen DB ─────────────────────────────────────────────────────────
    seen = SeenDB(cfg.rec.seen_db)

    # existing_artists starts empty here;  build_recommendations will populate
    # it from Plex (and we'll merge the seen DB into it)
    existing_artists: set[str] = {name for name in seen._data}

    # ── Get recommendations ──────────────────────────────────────────────────
    candidates = build_recommendations(cfg, existing_artists)

    if not candidates:
        log.info("No new candidates found — nothing to download.")
        return

    log.info("Top 10 candidates:")
    for i, c in enumerate(candidates[:10], 1):
        log.info("  %2d. %-35s  score=%.2f  sources=%d", i, c.name, c.score, len(c.sources))

    # ── Download each candidate ──────────────────────────────────────────────
    total_queued = 0

    for candidate in candidates:
        if seen.seen(candidate.name):
            log.debug("Skipping (already queued before): %s", candidate.name)
            continue

        count = dl.queue_artist_albums(candidate.name)

        if count > 0:
            seen.mark(candidate.name)
            total_queued += count
            log.info("✓ Queued %d album(s) for %s", count, candidate.name)
        else:
            log.warning("✗ Could not queue: %s", candidate.name)

    log.info("━" * 60)
    log.info("  Run complete — %d album(s) added to Tidarr queue", total_queued)
    log.info("━" * 60)


def run_daemon():
    """Run on a schedule using the SCHEDULE env var (cron syntax)."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.error("APScheduler not installed — pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="UTC")
    trigger   = CronTrigger.from_crontab(cfg.rec.schedule)

    scheduler.add_job(run_once, trigger, id="autodl", max_instances=1)
    log.info("Daemon mode: scheduled as '%s' (UTC). Running first cycle now…", cfg.rec.schedule)

    # Run immediately on startup, then on schedule
    run_once()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Daemon stopped.")


def main():
    logging.getLogger().setLevel(getattr(logging, cfg.log_level.upper(), logging.INFO))

    parser = argparse.ArgumentParser(description="music-autodl — auto music recommender + downloader")
    parser.add_argument("--daemon", action="store_true", help="Run on a schedule (uses SCHEDULE env var)")
    parser.add_argument("--dry-run", action="store_true", help="Show candidates but don't queue anything")
    args = parser.parse_args()

    if args.dry_run:
        log.info("DRY RUN — no downloads will be queued")
        existing: set[str] = set()
        candidates = build_recommendations(cfg, existing)
        print(f"\n{'#':>3}  {'Artist':<40}  {'Score':>6}  Sources")
        print("─" * 75)
        for i, c in enumerate(candidates, 1):
            print(f"{i:>3}. {c.name:<40}  {c.score:>6.2f}  {len(c.sources)}")
        return

    if args.daemon:
        run_daemon()
    else:
        run_once()


if __name__ == "__main__":
    main()

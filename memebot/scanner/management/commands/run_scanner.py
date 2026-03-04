"""
Continuous scanner — runs pull_pairs + process_snapshots in a loop.

Usage:
    python manage.py run_scanner                  # default: every 60s
    python manage.py run_scanner --interval 30    # every 30s
    python manage.py run_scanner --once           # single run then exit

This is the only command you need to keep running.
It replaces manually running pull_pairs and process_snapshots.
"""

import time
import signal
import sys
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Run the full scanner loop (pull_pairs + process_snapshots) continuously"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="Seconds between each scan cycle (default: 60)",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run once and exit (no loop)",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        once = options["once"]

        # Graceful shutdown on Ctrl+C
        def shutdown(signum, frame):
            self.stdout.write(self.style.WARNING("\n\nShutting down scanner..."))
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        if once:
            self._run_cycle()
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"🚀 Memebot scanner started — scanning every {interval}s\n"
                f"   Press Ctrl+C to stop\n"
            )
        )

        cycle = 0
        while True:
            cycle += 1
            self.stdout.write(
                self.style.HTTP_INFO(f"\n{'='*60}")
            )
            self.stdout.write(
                self.style.HTTP_INFO(f"  Cycle #{cycle}  —  {time.strftime('%Y-%m-%d %H:%M:%S')}")
            )
            self.stdout.write(
                self.style.HTTP_INFO(f"{'='*60}\n")
            )

            self._run_cycle()

            self.stdout.write(
                f"\n  💤 Sleeping {interval}s until next cycle...\n"
            )
            time.sleep(interval)

    def _run_cycle(self):
        """Run one full scan cycle: discover tokens then process them."""
        try:
            self.stdout.write(self.style.MIGRATE_HEADING("\n--- Step 1: Discovering new tokens ---\n"))
            call_command("pull_pairs", stdout=self.stdout, stderr=self.stderr)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  pull_pairs failed: {e}"))

        try:
            self.stdout.write(self.style.MIGRATE_HEADING("\n--- Step 2: Processing & scoring ---\n"))
            call_command("process_snapshots", stdout=self.stdout, stderr=self.stderr)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  process_snapshots failed: {e}"))

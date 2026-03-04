"""
Pipeline orchestrator — the core job that processes new snapshots.

Usage:
    python manage.py process_snapshots

Flow for each unprocessed PairSnapshot:
    1. Check token age >= 2 minutes
    2. Call rug-check-mcp for safety flags
    3. Run hard risk filters
    4. Run behaviour analysis
    5. Score the token
    6. Save TokenScore
    7. Send Telegram alert if score >= threshold
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from scanner.models import Token, PairSnapshot
from risk.filters import fetch_token_flags, run_hard_filters
from behaviour.engine import behaviour_pass
from behaviour.models import TradeEvent
from scoring.engine import score_token
from scoring.models import TokenScore
from alerts.telegram import send_alert

logger = logging.getLogger(__name__)

ALERT_THRESHOLD = 10
MIN_AGE = timedelta(minutes=2)


class Command(BaseCommand):
    help = "Process new pair snapshots through the full pipeline"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        processed = 0
        alerted = 0

        # Get tokens that have snapshots but haven't been scored yet
        # (or have new snapshots since last scoring)
        tokens = Token.objects.filter(is_rejected=False)

        for token in tokens:
            # Get the latest snapshot for this token
            latest_snap = (
                PairSnapshot.objects
                .filter(token=token)
                .order_by("-captured_at")
                .first()
            )

            if not latest_snap:
                continue

            # Skip if we already scored this snapshot
            if token.last_scored_snapshot_id == latest_snap.id:
                continue

            # Time-based protection: token must be >= 2 minutes old
            age = now - token.created_at
            if age < MIN_AGE:
                self.stdout.write(f"  ⏳ {token.symbol} too young ({age.seconds}s), skipping")
                continue

            self.stdout.write(f"  🔍 Processing {token.symbol} ({token.mint[:12]}...)")

            # Step 1: Fetch safety flags from rug-check-mcp
            flags = fetch_token_flags(token.mint)

            # If rug-check-mcp is down, skip (don't reject) — retry next run
            if flags is None:
                self.stdout.write(
                    self.style.WARNING(f"  ⏭️  {token.symbol} skipped: Solsniffer unavailable (will retry)")
                )
                continue

            # Step 2: Run hard filters
            hard_pass, hard_reasons = run_hard_filters(latest_snap, flags)

            if not hard_pass:
                token.is_rejected = True
                token.save(update_fields=["is_rejected"])
                self.stdout.write(
                    self.style.WARNING(f"  ❌ {token.symbol} rejected: {', '.join(hard_reasons)}")
                )
                continue

            # Step 3: Behaviour analysis
            events = list(TradeEvent.objects.filter(token=token).order_by("timestamp")[:20])
            behaviour_passed, behaviour_reasons = behaviour_pass(events)

            if not behaviour_passed:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  {token.symbol} behaviour flags: {', '.join(behaviour_reasons)}")
                )

            # Step 4: Score the token
            score, breakdown = score_token(latest_snap, flags, behaviour_passed)

            # Step 5: Save / update TokenScore
            TokenScore.objects.update_or_create(
                token=token,
                defaults={"score": score, "breakdown": breakdown},
            )

            # Update token tracking
            token.last_scored_snapshot = latest_snap
            token.save(update_fields=["last_scored_snapshot"])

            self.stdout.write(f"  📊 {token.symbol} scored {score}/14")
            processed += 1

            # Step 6: Send alert if above threshold and not already alerted
            if score >= ALERT_THRESHOLD and not token.alert_sent:
                sent = send_alert(token, latest_snap, score, breakdown)
                if sent:
                    token.alert_sent = True
                    token.save(update_fields=["alert_sent"])
                    alerted += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  🚀 Alert sent for {token.symbol}!")
                    )

        self.stdout.write(
            self.style.SUCCESS(f"\nDone — processed {processed} tokens, sent {alerted} alerts")
        )

from django.core.management.base import BaseCommand
from scanner.services.dexscreener import fetch_latest_solana_pairs, save_pairs


class Command(BaseCommand):
    help = "Discover new Solana meme-coins from DexScreener (profiles + boosts)"

    def handle(self, *args, **kwargs):
        self.stdout.write("Discovering new Solana tokens from DexScreener...\n")
        pairs = fetch_latest_solana_pairs(stdout=self.stdout)
        self.stdout.write(f"\n  Found {len(pairs)} Solana pairs, saving...\n")
        saved, skipped = save_pairs(pairs, stdout=self.stdout)
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done — {saved} tokens saved, {skipped} skipped (non-Solana or missing data)"
            )
        )

"""
Behaviour engine — detects suspicious early trading patterns.
"""

from collections import Counter
from behaviour.models import TradeEvent


def behaviour_pass(events: list) -> tuple[bool, list[str]]:
    """
    Analyse early trade events for a token.
    Returns (passed: bool, reasons: list[str]).

    Rules (v1):
    1. First 3 buys must NOT be the same wallet.
    2. No repeated buy→sell→buy loops from a single wallet.
    3. No rapid wallet fan-out (single wallet funding many buys).
    """
    reasons = []

    if not events:
        # No events available — pass by default in v1
        return True, []

    buys = [e for e in events if e.side == "buy"]

    # Rule 1: first 3 buys are the same wallet
    if len(buys) >= 3:
        first_three_wallets = [b.wallet for b in buys[:3]]
        if len(set(first_three_wallets)) == 1:
            reasons.append("first 3 buys from same wallet")

    # Rule 2: buy→sell→buy loops from single wallet
    wallet_sequences: dict[str, list[str]] = {}
    for e in events:
        wallet_sequences.setdefault(e.wallet, []).append(e.side)

    for wallet, seq in wallet_sequences.items():
        seq_str = "".join(["B" if s == "buy" else "S" for s in seq])
        if "BSB" in seq_str:
            reasons.append(f"buy-sell-buy loop from wallet {wallet[:8]}...")
            break  # one violation is enough

    # Rule 3: rapid fan-out — one wallet makes > 50% of early buys
    if len(buys) >= 5:
        wallet_counts = Counter(b.wallet for b in buys[:10])
        most_common_wallet, count = wallet_counts.most_common(1)[0]
        if count / min(len(buys), 10) > 0.5:
            reasons.append(f"wallet fan-out: {most_common_wallet[:8]}... made {count} of first buys")

    passed = len(reasons) == 0
    return passed, reasons

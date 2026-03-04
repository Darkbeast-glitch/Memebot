"""
Scoring engine — produces a deterministic score for a token.
Max score = 14.  Alert threshold >= 10.
"""


def score_token(snapshot, token_flags: dict | None, behaviour_passed: bool) -> tuple[int, dict]:
    """
    Score a token based on safety flags, market data, and behaviour analysis.

    Returns (score: int, breakdown: dict).

    Scoring table:
        Mint disabled           +2
        Freeze disabled         +2
        Liquidity >= 20k        +2
        Top holder < 10%        +2
        Top 5 holders < 35%     +2
        Behaviour passed        +2
        Traders_1h > 10         +2
        ─────────────────────────
        Max                     14
    """
    breakdown = {}
    score = 0

    # Safety flags (from rug-check-mcp)
    if token_flags:
        if not token_flags.get("mint_authority_enabled"):
            score += 2
            breakdown["mint_disabled"] = 2
        else:
            breakdown["mint_disabled"] = 0

        if not token_flags.get("freeze_authority_enabled"):
            score += 2
            breakdown["freeze_disabled"] = 2
        else:
            breakdown["freeze_disabled"] = 0

        top_holder = token_flags.get("top_holder_pct", 100)
        if top_holder < 10:
            score += 2
            breakdown["top_holder_low"] = 2
        else:
            breakdown["top_holder_low"] = 0

        top5 = token_flags.get("top5_holders_pct", 100)
        if top5 < 35:
            score += 2
            breakdown["top5_holders_low"] = 2
        else:
            breakdown["top5_holders_low"] = 0
    else:
        breakdown["mint_disabled"] = 0
        breakdown["freeze_disabled"] = 0
        breakdown["top_holder_low"] = 0
        breakdown["top5_holders_low"] = 0

    # Market data (from PairSnapshot)
    if snapshot.liquidity_usd is not None and snapshot.liquidity_usd >= 20_000:
        score += 2
        breakdown["liquidity_ok"] = 2
    else:
        breakdown["liquidity_ok"] = 0

    if snapshot.traders_1h is not None and snapshot.traders_1h > 10:
        score += 2
        breakdown["traders_active"] = 2
    else:
        breakdown["traders_active"] = 0

    # Behaviour
    if behaviour_passed:
        score += 2
        breakdown["behaviour_passed"] = 2
    else:
        breakdown["behaviour_passed"] = 0

    return score, breakdown

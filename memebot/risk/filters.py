"""
Hard safety filters for token risk assessment.

Uses RugCheck.xyz API (free, no key required) to get contract safety data.

RugCheck response structure:
    mintAuthority      — null = disabled (safe), non-null = enabled (dangerous)
    freezeAuthority    — null = disabled (safe), non-null = enabled (dangerous)
    topHolders         — list of {address, pct, owner, insider, ...}
    score_normalised   — 0-100 safety score (higher = safer, but inverted logic)
    risks              — list of identified risk factors
    rugged             — bool, whether flagged as a rug pull
    totalMarketLiquidity — total liquidity across all markets
"""

import time
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

RUGCHECK_BASE = "https://api.rugcheck.xyz/v1/tokens"
REQUEST_DELAY = 1.5  # seconds between API calls (be polite to free API)


class RateLimitError(Exception):
    """Raised when the API returns 429 Too Many Requests."""
    pass


def fetch_token_flags(mint: str) -> dict | None:
    """
    Call the RugCheck.xyz API to get contract/holder safety data.

    Returns a normalized dict:
        mint_authority_enabled   (bool)  — True = DANGEROUS
        freeze_authority_enabled (bool)  — True = DANGEROUS
        lp_burned                (bool)  — True = SAFE (placeholder, always False)
        top_holder_pct           (float) — actual % of top holder
        top5_holders_pct         (float) — actual % of top 5 holders
        snif_score               (int)   — 0-100 (higher = safer)
        risks                    (list)  — risk descriptions from RugCheck
        rugged                   (bool)  — flagged as rug pull
    Returns None if the API is unreachable.
    """
    try:
        time.sleep(REQUEST_DELAY)  # be polite to the free API
        res = requests.get(
            f"{RUGCHECK_BASE}/{mint}/report",
            timeout=15,
        )
        if res.status_code == 429:
            logger.warning("RugCheck 429 rate-limited on %s", mint)
            raise RateLimitError("429 Too Many Requests")
        res.raise_for_status()
        data = res.json()
    except RateLimitError:
        raise
    except Exception as e:
        logger.warning("RugCheck API error for %s: %s", mint, e)
        return None

    try:
        # --- Authorities: null = disabled (safe) ---
        mint_authority = data.get("mintAuthority")       # null = safe
        freeze_authority = data.get("freezeAuthority")   # null = safe

        # --- Top holders ---
        holders = data.get("topHolders", [])
        top_holder_pct = holders[0]["pct"] if len(holders) >= 1 else 0.0
        top5_holders_pct = sum(h["pct"] for h in holders[:5]) if holders else 0.0

        # --- Score (RugCheck: higher = safer) ---
        score = data.get("score_normalised", 0) or 0

        # --- Risk list ---
        risks = [r.get("name", r.get("description", "unknown")) for r in data.get("risks", [])]

        return {
            "mint_authority_enabled":   mint_authority is not None,   # True = danger
            "freeze_authority_enabled": freeze_authority is not None, # True = danger
            "lp_burned":               False,   # RugCheck doesn't have this exact field
            "top_holder_pct":          top_holder_pct,
            "top5_holders_pct":        top5_holders_pct,
            "snif_score":              score,
            "risks":                   risks,
            "rugged":                  data.get("rugged", False),
        }
    except Exception as e:
        logger.warning("Failed to parse RugCheck response for %s: %s", mint, e)
        return None


def run_hard_filters(snapshot, token_flags: dict | None) -> tuple[bool, list[str]]:
    """
    Apply hard rejection rules.
    Returns (passed: bool, reasons: list[str]).
    If token_flags is None (API unavailable), the token is skipped (not rejected).
    """
    reasons = []

    # If RugCheck is unavailable, we can't verify — skip for now
    if token_flags is None:
        return False, ["RugCheck unavailable"]

    # Rule 0: Flagged as rugged
    if token_flags.get("rugged"):
        reasons.append("flagged as rug pull by RugCheck")

    # Rule 1: Liquidity must be >= $10,000
    if snapshot.liquidity_usd is not None and snapshot.liquidity_usd < 10_000:
        reasons.append(f"liquidity too low: ${snapshot.liquidity_usd:,.0f}")

    # Rule 2: Mint authority must be disabled
    if token_flags.get("mint_authority_enabled"):
        reasons.append("mint authority enabled")

    # Rule 3: Freeze authority must be disabled
    if token_flags.get("freeze_authority_enabled"):
        reasons.append("freeze authority enabled")

    # Rule 4: Top holder must be < 20%
    top_holder = token_flags.get("top_holder_pct", 0)
    if top_holder >= 20:
        reasons.append(f"top holder owns {top_holder:.1f}%")

    passed = len(reasons) == 0
    return passed, reasons

"""
Hard safety filters for token risk assessment.
Calls the Solsniffer API directly to get contract safety data.

Solsniffer v2 response structure:
    tokenData.auditRisk   — simple booleans (true = SAFE):
        mintDisabled      — true means mint authority IS disabled (safe)
        freezeDisabled    — true means freeze authority IS disabled (safe)
        lpBurned          — true means liquidity is locked/burned (safe)
        top10Holders      — true means top-10 distribution is healthy (safe)
    tokenData.score       — overall safety score 0-100 (higher = safer)
    tokenData.ownersList  — list of {address, amount, percentage}
"""

import json
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

SOLSNIFFER_BASE = "https://solsniffer.com/api/v2/token"


def fetch_token_flags(mint: str) -> dict | None:
    """
    Call the Solsniffer API to get contract/holder safety data.

    Returns a normalized dict:
        mint_authority_enabled   (bool)  — True = DANGEROUS
        freeze_authority_enabled (bool)  — True = DANGEROUS
        lp_burned                (bool)  — True = SAFE
        top_holder_pct           (float) — actual % of top holder
        top5_holders_pct         (float) — actual % of top 5 holders
        snif_score               (int)   — 0-100 (higher = safer)
    Returns None if the API is unreachable or no key is configured.
    """
    api_key = getattr(settings, "SOLSNIFFER_API_KEY", "")
    if not api_key:
        logger.warning("SOLSNIFFER_API_KEY not set — skipping %s", mint)
        return None

    try:
        res = requests.get(
            f"{SOLSNIFFER_BASE}/{mint}",
            headers={"X-API-KEY": api_key},
            timeout=15,
        )
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        logger.warning("Solsniffer API error for %s: %s", mint, e)
        return None

    try:
        td = data.get("tokenData", {})

        # --- auditRisk: simple booleans (true = safe) ---
        audit = td.get("auditRisk", {})
        mint_disabled   = audit.get("mintDisabled", False)    # True = safe
        freeze_disabled = audit.get("freezeDisabled", False)  # True = safe

        # --- Owner concentration from actual owner list ---
        owners = td.get("ownersList", [])
        top_holder_pct  = float(owners[0]["percentage"]) if len(owners) >= 1 else 0.0
        top5_holders_pct = sum(float(o["percentage"]) for o in owners[:5]) if owners else 0.0

        # --- Solsniffer score ---
        snif_score = td.get("score", 0) or 0

        return {
            "mint_authority_enabled":   not mint_disabled,      # inverted: True = danger
            "freeze_authority_enabled": not freeze_disabled,     # inverted: True = danger
            "lp_burned":               audit.get("lpBurned", False),
            "top_holder_pct":          top_holder_pct,
            "top5_holders_pct":        top5_holders_pct,
            "snif_score":              snif_score,
        }
    except Exception as e:
        logger.warning("Failed to parse Solsniffer response for %s: %s", mint, e)
        return None


def run_hard_filters(snapshot, token_flags: dict | None) -> tuple[bool, list[str]]:
    """
    Apply hard rejection rules.
    Returns (passed: bool, reasons: list[str]).
    If token_flags is None (API unavailable), the token is skipped (not rejected).
    """
    reasons = []

    # If Solsniffer is unavailable, we can't verify — skip for now
    if token_flags is None:
        return False, ["Solsniffer unavailable"]

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

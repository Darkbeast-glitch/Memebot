"""
Telegram alert service.
Sends formatted messages for high-scoring tokens.
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Characters that must be escaped for Telegram MarkdownV2
_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!"


def _esc(text):
    """Escape special characters for Telegram MarkdownV2."""
    s = str(text) if text is not None else ""
    for ch in _ESCAPE_CHARS:
        s = s.replace(ch, f"\\{ch}")
    return s


def send_alert(token, snapshot, score: int, breakdown: dict):
    """
    Send a Telegram alert for a token that scored above threshold.
    """
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not configured — skipping alert")
        return False

    dex_url = f"https://dexscreener.com/solana/{snapshot.pair_address}"

    # Safe number formatting
    liq = f"${snapshot.liquidity_usd:,.0f}" if snapshot.liquidity_usd else "$0"
    vol = f"${snapshot.volume_24h:,.0f}" if snapshot.volume_24h else "$0"
    p5m = f"{snapshot.price_change_5m}%" if snapshot.price_change_5m is not None else "n/a"

    # Build breakdown text
    breakdown_lines = "\n".join(
        f"  {'✅' if v > 0 else '❌'} {_esc(k)}: {v}" for k, v in breakdown.items()
    )

    message = (
        f"🚀 *NEW HIGH\\-SCORE TOKEN*\n\n"
        f"*{_esc(token.symbol)}* — {_esc(token.name)}\n"
        f"`{token.mint}`\n\n"
        f"Score: *{score}/14*\n"
        f"Liquidity: {_esc(liq)}\n"
        f"Volume 24h: {_esc(vol)}\n"
        f"Traders 1h: {snapshot.traders_1h}\n"
        f"Price Δ 5m: {_esc(p5m)}\n\n"
        f"Breakdown:\n{breakdown_lines}\n\n"
        f"[View on Dexscreener]({dex_url})"
    )

    try:
        res = requests.post(
            TELEGRAM_API.format(token=bot_token),
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        res.raise_for_status()
        logger.info("Telegram alert sent for %s (score=%d)", token.symbol, score)
        return True
    except Exception as e:
        logger.error("Failed to send Telegram alert: %s", e)
        return False

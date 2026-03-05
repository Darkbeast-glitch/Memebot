"""
Gemini AI token analysis — gives an AI-powered verdict on memecoin quality.

Uses Google Gemini 2.0 Flash (free tier: 15 RPM, 1M tokens/day).
Produces a short narrative + confidence rating (LOW / MEDIUM / HIGH).
"""

import logging
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

# Model config
MODEL_NAME = "gemini-2.0-flash"
MAX_TOKENS = 300


def _get_client():
    """
    Create and return a Gemini client.
    Returns None if no API key is set.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def analyse_token(
    symbol: str,
    name: str,
    score: int,
    breakdown: dict,
    liquidity_usd: float | None,
    volume_24h: float | None,
    buys_1h: int,
    sells_1h: int,
    traders_1h: int,
    price_change_5m: float | None,
    behaviour_passed: bool,
    safety_flags: dict | None,
    trade_count: int = 0,
) -> dict | None:
    """
    Ask Gemini to analyse a token and return a verdict.

    Returns dict: {confidence: str, summary: str}
    Or None if Gemini is unavailable.
    """
    client = _get_client()
    if client is None:
        logger.info("Gemini API key not set — skipping AI analysis")
        return None

    # Format the safety data
    safety_text = "No safety data available"
    if safety_flags:
        safety_text = (
            f"Mint authority: {'ENABLED (risky)' if safety_flags.get('mint_authority_enabled') else 'disabled (safe)'}\n"
            f"Freeze authority: {'ENABLED (risky)' if safety_flags.get('freeze_authority_enabled') else 'disabled (safe)'}\n"
            f"Top holder: {safety_flags.get('top_holder_pct', '?')}%\n"
            f"Top 5 holders: {safety_flags.get('top5_holders_pct', '?')}%\n"
            f"RugCheck score: {safety_flags.get('rugcheck_score', '?')}/100\n"
            f"Risks flagged: {', '.join(safety_flags.get('risk_names', [])) or 'None'}"
        )

    # Format breakdown
    breakdown_text = "\n".join(
        f"  {'PASS' if v > 0 else 'FAIL'} {k}: {v}/2"
        for k, v in breakdown.items()
    )

    prompt = f"""You are a Solana memecoin analyst. Analyse this token and give a short, actionable verdict.

TOKEN: {symbol} ({name})
SCORE: {score}/14

SAFETY CHECKS:
{safety_text}

SCORE BREAKDOWN:
{breakdown_text}

MARKET DATA:
  Liquidity: ${liquidity_usd or 0:,.0f}
  Volume 24h: ${volume_24h or 0:,.0f}
  Buys 1h: {buys_1h}
  Sells 1h: {sells_1h}
  Traders 1h: {traders_1h}
  Price change 5m: {price_change_5m or 0:.2f}%
  On-chain trades analysed: {trade_count}
  Wash-trading check: {'PASSED' if behaviour_passed else 'FAILED — suspicious patterns detected'}

INSTRUCTIONS:
1. Rate confidence as exactly one of: LOW, MEDIUM, or HIGH
2. Give a 2-3 sentence summary explaining why, focusing on the biggest risk or opportunity
3. Be direct and specific — mention actual numbers
4. NEVER recommend buying. Only assess quality and risk.

Respond in EXACTLY this format:
CONFIDENCE: <LOW|MEDIUM|HIGH>
SUMMARY: <your 2-3 sentence analysis>"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=MAX_TOKENS,
                temperature=0.3,
            ),
        )

        text = response.text.strip()
        return _parse_response(text)

    except Exception as e:
        logger.error("Gemini API error: %s", e)
        return None


def _parse_response(text: str) -> dict:
    """Parse the structured Gemini response into a dict."""
    confidence = "MEDIUM"
    summary = text  # fallback: use full text

    lines = text.strip().split("\n")
    for line in lines:
        upper = line.strip().upper()
        if upper.startswith("CONFIDENCE:"):
            raw = line.split(":", 1)[1].strip().upper()
            if raw in ("LOW", "MEDIUM", "HIGH"):
                confidence = raw
        elif upper.startswith("SUMMARY:"):
            summary = line.split(":", 1)[1].strip()
            # Grab any continuation lines
            idx = lines.index(line)
            for extra in lines[idx + 1:]:
                if extra.strip() and not extra.strip().upper().startswith("CONFIDENCE:"):
                    summary += " " + extra.strip()
            break

    return {
        "confidence": confidence,
        "summary": summary,
    }

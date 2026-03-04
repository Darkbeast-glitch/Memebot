from django.http import JsonResponse
from django.utils import timezone
from scanner.models import Token


def token_list(request):
    """
    GET /api/tokens?min_score=10

    Returns scored tokens as JSON.
    """
    min_score = int(request.GET.get("min_score", 0))

    tokens = (
        Token.objects
        .filter(is_rejected=False, score__isnull=False)
        .select_related("score", "last_scored_snapshot")
    )

    if min_score:
        tokens = tokens.filter(score__score__gte=min_score)

    tokens = tokens.order_by("-score__score")

    results = []
    for t in tokens:
        snap = t.last_scored_snapshot
        ts = t.score
        breakdown = ts.breakdown if ts else {}

        age_minutes = None
        if t.created_at:
            age_minutes = int((timezone.now() - t.created_at).total_seconds() / 60)

        # Derive behaviour status from the breakdown saved by scoring engine
        behaviour_passed = breakdown.get("behaviour_passed", 0) > 0

        results.append({
            "mint": t.mint,
            "symbol": t.symbol,
            "name": t.name,
            "score": ts.score if ts else None,
            "breakdown": breakdown,
            "liquidity_usd": snap.liquidity_usd if snap else None,
            "volume_24h": snap.volume_24h if snap else None,
            "buys_1h": snap.buys_1h if snap else None,
            "sells_1h": snap.sells_1h if snap else None,
            "traders_1h": snap.traders_1h if snap else None,
            "price_change_5m": snap.price_change_5m if snap else None,
            "age_minutes": age_minutes,
            "behaviour_passed": behaviour_passed,
            "dexscreener_url": f"https://dexscreener.com/solana/{snap.pair_address}" if snap else None,
            "alert_sent": t.alert_sent,
        })

    return JsonResponse({"count": len(results), "results": results})

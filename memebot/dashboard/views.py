from django.http import JsonResponse
from django.utils import timezone
from scanner.models import Token, PairSnapshot


def _serialize_token(t, now):
    """Serialize a single Token into a dict for the API."""
    snap = t.last_scored_snapshot
    ts = getattr(t, "score", None)
    breakdown = ts.breakdown if ts else {}

    age_minutes = None
    if t.created_at:
        age_minutes = int((now - t.created_at).total_seconds() / 60)

    behaviour_passed = breakdown.get("behaviour_passed", 0) > 0

    # If no scored snapshot, grab the latest snapshot for basic market data
    if not snap:
        snap = (
            PairSnapshot.objects
            .filter(token=t)
            .order_by("-captured_at")
            .first()
        )

    return {
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
        "is_rejected": t.is_rejected,
        "source": t.source,
    }


def token_list(request):
    """
    GET /api/tokens?min_score=10&view=top|all|new

    view=top  → scored tokens with score >= 12 (default)
    view=all  → all scored tokens
    view=new  → recently discovered tokens (last 100), including unscored
    """
    view = request.GET.get("view", "top")
    min_score = int(request.GET.get("min_score", 0))
    now = timezone.now()

    if view == "new":
        # Recently discovered tokens — newest first, including unscored
        tokens = (
            Token.objects
            .filter(is_rejected=False)
            .select_related("score", "last_scored_snapshot")
            .order_by("-created_at")[:100]
        )
    elif view == "all":
        # All scored tokens
        tokens = (
            Token.objects
            .filter(is_rejected=False, score__isnull=False)
            .select_related("score", "last_scored_snapshot")
            .order_by("-score__score")
        )
        if min_score:
            tokens = tokens.filter(score__score__gte=min_score)
    else:
        # Top picks — score >= 12
        tokens = (
            Token.objects
            .filter(is_rejected=False, score__isnull=False, score__score__gte=12)
            .select_related("score", "last_scored_snapshot")
            .order_by("-score__score", "-created_at")
        )

    results = [_serialize_token(t, now) for t in tokens]
    return JsonResponse({"count": len(results), "results": results})


def dashboard_stats(request):
    """
    GET /api/stats
    Summary stats for the dashboard header.
    """
    now = timezone.now()
    total_discovered = Token.objects.count()
    total_scored = Token.objects.filter(score__isnull=False).count()
    total_rejected = Token.objects.filter(is_rejected=True).count()
    total_alerted = Token.objects.filter(alert_sent=True).count()
    top_picks = Token.objects.filter(score__isnull=False, score__score__gte=12).count()

    return JsonResponse({
        "total_discovered": total_discovered,
        "total_scored": total_scored,
        "total_rejected": total_rejected,
        "total_alerted": total_alerted,
        "top_picks": top_picks,
    })

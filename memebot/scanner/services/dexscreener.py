import requests
from django.utils import timezone
from scanner.models import Token, PairSnapshot

API = "https://api.dexscreener.com"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_token_profiles():
    """Latest token profiles — newly created / updated tokens."""
    try:
        r = requests.get(f"{API}/token-profiles/latest/v1", timeout=15)
        r.raise_for_status()
        return r.json()          # list of {chainId, tokenAddress, ...}
    except Exception:
        return []


def _fetch_token_boosts():
    """Latest boosted tokens — trending / promoted."""
    try:
        r = requests.get(f"{API}/token-boosts/latest/v1", timeout=15)
        r.raise_for_status()
        return r.json()          # list of {chainId, tokenAddress, ...}
    except Exception:
        return []


def _fetch_pairs_for_tokens(addresses):
    """Full pair data for up to 30 token addresses (comma-separated)."""
    if not addresses:
        return []
    joined = ",".join(addresses)
    try:
        r = requests.get(f"{API}/latest/dex/tokens/{joined}", timeout=20)
        r.raise_for_status()
        return r.json().get("pairs") or []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_latest_solana_pairs(stdout=None):
    """
    Discover new Solana meme-coins via DexScreener.

    Sources:
      1. Token Profiles — freshly created / updated tokens
      2. Token Boosts   — trending / boosted tokens

    For every Solana address found, full pair data is fetched in
    batches of 30.
    """
    solana_addrs = []
    profiles = _fetch_token_profiles()
    boosts   = _fetch_token_boosts()

    n_profiles = 0
    for p in profiles:
        if p.get("chainId") == "solana" and p.get("tokenAddress"):
            solana_addrs.append(p["tokenAddress"])
            n_profiles += 1

    n_boosts = 0
    for b in boosts:
        if b.get("chainId") == "solana" and b.get("tokenAddress"):
            solana_addrs.append(b["tokenAddress"])
            n_boosts += 1

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for addr in solana_addrs:
        if addr not in seen:
            seen.add(addr)
            unique.append(addr)

    if stdout:
        stdout.write(
            f"  Sources → profiles: {n_profiles} Solana tokens, "
            f"boosts: {n_boosts} Solana tokens  "
            f"({len(unique)} unique addresses)"
        )

    # Fetch full pair data in batches of 30
    all_pairs = []
    seen_pairs = set()
    for i in range(0, len(unique), 30):
        batch = unique[i : i + 30]
        if stdout:
            stdout.write(f"  Fetching pair data  batch {i // 30 + 1} ({len(batch)} tokens)...")
        pairs = _fetch_pairs_for_tokens(batch)
        for p in pairs:
            pa = p.get("pairAddress")
            if pa and pa not in seen_pairs:
                seen_pairs.add(pa)
                all_pairs.append(p)

    return all_pairs


def save_pairs(pairs, stdout=None):
    """
    Persist discovered pairs as Token + PairSnapshot rows.
    Returns (saved, skipped) counts.
    """
    saved = 0
    skipped = 0

    for i, p in enumerate(pairs, 1):
        if p.get("chainId") != "solana":
            skipped += 1
            continue

        base = p.get("baseToken") or {}
        mint = base.get("address")
        if not mint:
            skipped += 1
            continue

        symbol  = base.get("symbol", "???")
        name    = base.get("name", "Unknown")
        liq     = (p.get("liquidity") or {}).get("usd")
        vol     = (p.get("volume") or {}).get("h24")
        dex     = p.get("dexId", "unknown")
        price5m = (p.get("priceChange") or {}).get("m5")
        buys    = (p.get("txns") or {}).get("h1", {}).get("buys", 0)
        sells   = (p.get("txns") or {}).get("h1", {}).get("sells", 0)

        token, created = Token.objects.get_or_create(
            mint=mint,
            defaults={
                "symbol": symbol,
                "name":   name,
                "created_at": timezone.now(),
                "source": "dexscreener",
            },
        )

        PairSnapshot.objects.create(
            token=token,
            pair_address=p.get("pairAddress", ""),
            dex_id=dex,
            liquidity_usd=liq,
            volume_24h=vol,
            buys_1h=buys,
            sells_1h=sells,
            price_change_5m=price5m,
            traders_1h=buys + sells,
        )

        saved += 1

        if stdout:
            tag     = "NEW" if created else "UPD"
            liq_s   = f"${liq:,.0f}" if liq else "$0"
            vol_s   = f"${vol:,.0f}" if vol else "$0"
            p5m_s   = f"{price5m:+.1f}%" if price5m is not None else "n/a"
            stdout.write(
                f"  [{tag}] {i:>3}. {symbol:<10} {name[:22]:<22}  "
                f"Liq: {liq_s:<14} Vol24h: {vol_s:<14} "
                f"Buys/Sells: {buys}/{sells}  Price5m: {p5m_s}  ({dex})"
            )

    return saved, skipped
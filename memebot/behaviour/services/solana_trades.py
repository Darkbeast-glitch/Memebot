"""
Solana on-chain trade fetcher — pulls individual swap events from Solana RPC.

Uses FREE public Solana RPC endpoints (no API key needed).
Rotates across multiple endpoints to avoid rate-limiting.
Fetches transactions from the pair (pool) address, parses token balance
changes to determine which wallets bought/sold and how much.

Supports: PumpSwap, Raydium, Orca, Jupiter — any DEX that changes
token balances in the transaction.
"""

import time
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Free public Solana RPC endpoints — rotated round-robin
SOLANA_RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-mainnet.rpc.extrnode.com",
    "https://solana-rpc.publicnode.com",
]

# DEX-related log keywords that indicate a swap/trade
SWAP_KEYWORDS = {"swap", "swap2", "buy", "sell", "buyexactquotein",
                 "sellexactquotein", "route", "exactin", "exactout"}

# Delay between RPC calls  (raised from 0.15 to avoid hammering)
RPC_DELAY = 0.6  # seconds

# Track which endpoint to use next (round-robin index)
_rpc_index = 0
# Temporarily disabled endpoints: endpoint -> re-enable timestamp
_disabled_until: dict[str, float] = {}


def _next_endpoint() -> str | None:
    """Pick the next healthy endpoint in round-robin order."""
    global _rpc_index
    now = time.time()
    n = len(SOLANA_RPC_ENDPOINTS)
    for _ in range(n):
        ep = SOLANA_RPC_ENDPOINTS[_rpc_index % n]
        _rpc_index += 1
        disable_ts = _disabled_until.get(ep, 0)
        if now >= disable_ts:
            return ep
    # All disabled — return the one that expires soonest
    return min(_disabled_until, key=_disabled_until.get, default=SOLANA_RPC_ENDPOINTS[0])


def _disable_endpoint(ep: str, seconds: int = 30):
    """Temporarily remove an endpoint from rotation."""
    _disabled_until[ep] = time.time() + seconds
    logger.info("Disabled %s for %ds", ep, seconds)


def _rpc_call(method: str, params: list, timeout: int = 20) -> dict | None:
    """
    Make a JSON-RPC call, rotating across free endpoints.
    Retries up to 4 times with exponential backoff on 429s.
    """
    max_retries = 4
    for attempt in range(max_retries):
        endpoint = _next_endpoint()
        backoff = 2 ** attempt  # 1s, 2s, 4s, 8s
        try:
            r = requests.post(
                endpoint,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                timeout=timeout,
            )
            if r.status_code == 429:
                logger.warning("RPC 429 at %s (attempt %d), backing off %ds",
                               endpoint, attempt + 1, backoff * 3)
                _disable_endpoint(endpoint, seconds=backoff * 15)
                time.sleep(backoff * 3)
                continue
            if r.status_code == 403:
                logger.warning("RPC 403 (forbidden) at %s — disabling", endpoint)
                _disable_endpoint(endpoint, seconds=300)
                continue
            data = r.json()
            if "error" in data:
                err = data["error"]
                logger.warning("RPC error from %s: %s", endpoint, err)
                # Disable if it's an access/auth error
                code = err.get("code", 0) if isinstance(err, dict) else 0
                if code in (-32052, -32600, -32601):
                    _disable_endpoint(endpoint, seconds=300)
                continue
            return data.get("result")
        except Exception as e:
            logger.warning("RPC call failed (%s): %s", endpoint, e)
            _disable_endpoint(endpoint, seconds=60)
            continue
    return None


def fetch_recent_signatures(address: str, limit: int = 30) -> list[tuple[str, int]]:
    """
    Fetch recent transaction signatures for an address.
    Returns list of (signature, block_time) tuples, skipping failed txs.
    """
    result = _rpc_call("getSignaturesForAddress", [address, {"limit": limit}])
    if not result:
        return []
    return [
        (s["signature"], s["blockTime"])
        for s in result
        if s.get("err") is None and s.get("blockTime")
    ]


def _is_swap_tx(logs: list[str]) -> bool:
    """Check if transaction logs indicate a swap/trade."""
    for log_line in logs:
        lower = log_line.lower()
        for keyword in SWAP_KEYWORDS:
            if keyword in lower:
                return True
    return False


def _extract_trades(tx: dict, target_mint: str, block_time: int) -> list[dict]:
    """
    Extract buy/sell events from a parsed transaction by comparing
    pre/post token balances for the target mint.
    
    Returns list of dicts with: wallet, side, amount, timestamp
    """
    meta = tx.get("meta", {})
    if not meta:
        return []

    # Build balance maps: (owner) -> amount
    pre_map = {}
    for b in meta.get("preTokenBalances", []):
        if b.get("mint") != target_mint:
            continue
        owner = b.get("owner")
        amt_str = b.get("uiTokenAmount", {}).get("uiAmountString")
        if owner and amt_str:
            pre_map[owner] = float(amt_str)

    post_map = {}
    for b in meta.get("postTokenBalances", []):
        if b.get("mint") != target_mint:
            continue
        owner = b.get("owner")
        amt_str = b.get("uiTokenAmount", {}).get("uiAmountString")
        if owner and amt_str:
            post_map[owner] = float(amt_str)

    # Calculate deltas
    all_owners = set(pre_map.keys()) | set(post_map.keys())
    trades = []
    for owner in all_owners:
        pre = pre_map.get(owner, 0.0)
        post = post_map.get(owner, 0.0)
        diff = post - pre
        if abs(diff) < 0.001:  # ignore dust
            continue
        trades.append({
            "wallet": owner,
            "side": "buy" if diff > 0 else "sell",
            "amount": abs(diff),
            "timestamp": datetime.fromtimestamp(block_time, tz=timezone.utc),
        })

    return trades


def fetch_trades_for_token(mint: str, pair_address: str, limit: int = 15) -> list[dict]:
    """
    Fetch recent trades for a token by looking at the pair (pool) address.
    
    Args:
        mint: Token mint address
        pair_address: DEX pair/pool address (where swaps happen)
        limit: Max number of transaction signatures to fetch
    
    Returns:
        List of trade dicts: {wallet, side, amount, timestamp}
        Sorted by timestamp ascending (earliest first).
    """
    # Step 1: Get recent signatures from the pair address
    sigs = fetch_recent_signatures(pair_address, limit=limit)
    if not sigs:
        logger.info("No signatures found for pair %s", pair_address[:16])
        return []

    logger.info("Fetched %d signatures for pair %s", len(sigs), pair_address[:16])

    # Step 2: Parse each transaction
    all_trades = []
    for sig, block_time in sigs:
        time.sleep(RPC_DELAY)

        tx = _rpc_call(
            "getTransaction",
            [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        )
        if not tx:
            continue

        # Check if it's a swap transaction
        logs = tx.get("meta", {}).get("logMessages", [])
        if not logs:
            continue

        # Even if logs don't match keywords, check for token balance changes
        # (some DEXes use non-standard instruction names)
        has_swap_log = _is_swap_tx(logs)

        trades = _extract_trades(tx, mint, block_time)

        if trades:
            # Filter out the pool itself — it's always the counterparty
            # The pool address will appear as buyer when someone sells and vice versa
            user_trades = [t for t in trades if t["wallet"] != pair_address]
            all_trades.extend(user_trades)

    # Sort by timestamp (earliest first)
    all_trades.sort(key=lambda t: t["timestamp"])

    logger.info(
        "Extracted %d trades (%d buys, %d sells) for mint %s",
        len(all_trades),
        sum(1 for t in all_trades if t["side"] == "buy"),
        sum(1 for t in all_trades if t["side"] == "sell"),
        mint[:16],
    )

    return all_trades

Below is a **clean, complete system architecture spec** you can paste straight into Claude (or give to any engineer) and let it scaffold the project inside your VSCode.

This is exactly the system we designed together.

It is intentionally **alert-only (manual trading)** and focused on Solana meme coins discovered via:

* **Dexscreener**
* (later optional realtime feed from) **Pump.fun**

---

# 📐 PROJECT ARCHITECTURE SPEC

### Project name: `memebot`

## Goal

Build a **private Django web app** that:

* scans new Solana meme tokens
* filters out obvious rugs
* scores candidates
* displays them in a dashboard
* sends Telegram alerts for high-quality setups

⚠️ No auto-trading in v1.

---

# 🧱 System overview

```
External APIs
   ↓
Scanner (Dexscreener / later Pump.fun WS)
   ↓
Storage (Postgres)
   ↓
Hard Risk Filters
   ↓
Behaviour Engine
   ↓
Scoring Engine
   ↓
Alert Service (Telegram)
   ↓
Dashboard API
   ↓
Web UI
```

---

# 🛠️ Tech stack

* Backend: Django + Django REST Framework
* DB: PostgreSQL
* Background jobs: Celery + Redis (or Django-crontab for v1)
* Frontend: separate dashboard (React / Vercel UI) OR Django templates
* Alerts: Telegram Bot API
* Solana contract checks: local MCP microservice (`rug-check-mcp`)

---

# 📦 Django apps layout

```
memebot/
  scanner/
  risk/
  behaviour/
  scoring/
  alerts/
  dashboard/
  core/
```

---

# 🧠 Responsibilities per app

---

## 1️⃣ scanner

Responsible for:

* pulling new Solana pairs
* saving token metadata
* saving rolling market snapshots

### External API used

```
GET https://api.dexscreener.com/latest/dex/search?q=solana
GET https://api.dexscreener.com/latest/dex/pairs/solana/{pairAddress}
```

---

### Models

#### Token

```
mint (unique)
symbol
name
created_at
source   (dexscreener | pumpfun)
```

#### PairSnapshot

```
token (FK)
pair_address
dex_id
liquidity_usd
volume_24h
buys_1h
sells_1h
traders_1h
price_change_5m
captured_at
```

---

### Services

```
scanner/services/dexscreener.py
```

Responsibilities:

* fetch latest Solana pairs
* normalize response
* store Token + PairSnapshot

---

### Jobs

```
pull_latest_pairs (runs every 30–60 seconds)
```

---

## 2️⃣ risk

Responsible for **hard safety filters**.

This layer decides:

➡️ should the token be considered at all?

---

### External dependency

Local MCP microservice:

```
rug-check-mcp
```

Django calls:

```
GET http://localhost:3333/check/{mint}
```

Returns:

* mint authority enabled
* freeze authority enabled
* top holder %
* top 5 holders %
* basic token info

---

### API exposed internally

```
risk/filters.py

run_hard_filters(snapshot, token_flags)
→ (passed: bool, reasons: list[str])
```

---

### Rules

Reject if:

```
liquidity < 10,000 USD
mint authority enabled
freeze authority enabled
top holder > 20%
```

---

## 3️⃣ behaviour

Responsible for detecting suspicious early trading patterns.

---

### Model

```
TradeEvent
  token
  wallet
  side (buy/sell)
  amount
  timestamp
```

---

### Engine

```
behaviour/engine.py
behaviour_pass(events)
→ (passed: bool, reasons)
```

---

### Behaviour rules (v1)

* first 3 buys are same wallet
* repeated buy → sell → buy loops
* rapid wallet fan-out from a single source wallet

---

⚠️ In v1, TradeEvent data can be stubbed or added later via:
Solana RPC / third-party feed.

---

## 4️⃣ scoring

Responsible for producing a deterministic score.

---

### Model

```
TokenScore
  token (OneToOne)
  score
  breakdown (JSON)
  created_at
```

---

### Engine

```
scoring/engine.py

score_token(snapshot, flags, behaviour_passed)
→ (score, breakdown)
```

---

### Scoring rules

| Rule                | Points |
| ------------------- | ------ |
| Mint disabled       | +2     |
| Freeze disabled     | +2     |
| Liquidity ≥ 20k     | +2     |
| Top holder < 10%    | +2     |
| Top 5 holders < 35% | +2     |
| Behaviour passed    | +2     |
| Traders_1h > 10     | +2     |

Max = 14

---

### Alert threshold

```
score >= 10
```

---

## 5️⃣ alerts

Responsible for sending notifications.

---

### External API

Telegram Bot API

```
POST https://api.telegram.org/bot<TOKEN>/sendMessage
```

---

### API

```
alerts/telegram.py

send_alert(token, snapshot, score, breakdown)
```

---

## 6️⃣ dashboard

Responsible for:

* serving read-only API for UI

---

### Endpoint

```
GET /api/tokens?min_score=10
```

Returns:

```
token symbol
token name
mint
score
liquidity_usd
top_holder_pct
age_minutes
price_change_5m
behaviour_pass
dexscreener_url
```

---

## 7️⃣ core (or pipeline app)

Responsible for orchestrating the full pipeline.

---

### Pipeline job

```
process_new_snapshots()
```

Pseudo flow:

```
for each PairSnapshot not yet processed:

    if token age < 2 minutes:
        skip

    flags = rug-check-mcp(mint)

    hard_pass, hard_reasons = run_hard_filters(snapshot, flags)

    if not hard_pass:
        mark rejected
        continue

    events = get TradeEvent for token (early window)
    behaviour_passed, behaviour_reasons = behaviour_pass(events)

    score, breakdown = score_token(snapshot, flags, behaviour_passed)

    save TokenScore

    if score >= threshold:
        send Telegram alert
```

---

# ⏳ Time-based protection

Tokens must be:

```
>= 2 minutes old
```

before scoring.

---

# 🗃️ Important internal fields to track

In Token or a separate status table:

```
last_scored_snapshot_id
is_rejected
alert_sent
```

This prevents duplicate alerts.

---

# 🖥️ Dashboard UI contract

The UI consumes only:

```
GET /api/tokens
```

The backend does NOT care about UI.

---

# 🔌 Pump.fun integration (future)

Pump.fun is used only as a discovery layer later.

Planned design:

```
Node websocket listener (Pump.fun frontend WS)
   ↓
POST /api/ingest/mint
   ↓
Django creates Token with source=pumpfun
```

Not required for v1.

---

# 🔐 Security & operational notes

* never store private keys
* never build auto-trading in the same service
* dashboard must be auth-protected
* alerts only contain public links

---

# 🧩 Deployment layout

```
Docker
  - Django app
  - PostgreSQL
  - Redis
  - rug-check-mcp container
```

---

# 📌 External dependencies summary

| Purpose                    | Tool                             |
| -------------------------- | -------------------------------- |
| Market + discovery         | Dexscreener REST                 |
| Contract & holder safety   | rug-check-mcp (local MCP server) |
| Realtime discovery (later) | Pump.fun websocket               |
| Alerts                     | Telegram Bot API                 |

---

# 🎯 Explicit non-goals (important for Claude)

* no trading execution
* no wallet management
* no MEV protection
* no PnL tracking
* no strategy optimization

This system is strictly:

> filtering + scoring + alerting + dashboard

---

# 🧠 Why this architecture works

It is:

* deterministic
* debuggable
* safe for small capital
* extendable into AI classification later
* compatible with your real goal ($20–$50/day without blowing up)

---

You can now give exactly this architecture to Claude and ask:

> “Scaffold this Django project with these apps, models, services and background jobs.”

This is a production-grade blueprint.

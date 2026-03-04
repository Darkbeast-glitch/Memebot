# Memebot — Solana Memecoin Scanner & Alert System

A private Django + Next.js system that **scans new Solana meme tokens**, filters rugs, scores candidates, displays them in a live dashboard, and sends **Telegram alerts** for high-quality setups.

> **No auto-trading.** This is strictly: filtering + scoring + alerting + dashboard.

---

## Architecture Overview

```
DexScreener APIs  (Token Profiles + Token Boosts)
       ↓
   Scanner         ← discovers new Solana meme-coins
       ↓
   PostgreSQL / SQLite
       ↓
   Hard Risk Filters   ← calls Solsniffer API for contract safety
       ↓
   Behaviour Engine    ← detects wash-trading / wallet fan-out
       ↓
   Scoring Engine      ← deterministic 0-14 point score
       ↓
   Telegram Alerts     ← fires when score >= 10
       ↓
   Dashboard API       ← GET /api/tokens
       ↓
   Next.js Frontend    ← live-polling dashboard
```

---

## Project Structure

```
Trading/
├── memebot/                  # Django backend
│   ├── scanner/              # Token discovery + Dexscreener integration
│   ├── risk/                 # Hard safety filters + Solsniffer API client
│   ├── behaviour/            # Suspicious trading pattern detection
│   ├── scoring/              # Deterministic 14-point scoring engine
│   ├── alerts/               # Telegram alert service
│   ├── dashboard/            # REST API for the frontend
│   └── memebot/              # Django project settings & URLs
│
├── Memebot-frontend/         # Next.js dashboard UI
│   ├── app/                  # App router (page, layout)
│   ├── components/dashboard/ # Header, TokenTable, DetailPanel, FilterControls
│   ├── hooks/                # useTokens() — fetches from Django API
│   └── types/                # TypeScript interfaces matching API response
│
└── env/                      # Python virtual environment
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) PostgreSQL — defaults to SQLite for local dev
- Solsniffer API key (set `SOLSNIFFER_API_KEY` in `memebot/memebot/settings.py`)

---

### 1. Backend Setup

```bash
cd Trading

# Activate existing virtual environment
source env/bin/activate

# Install Python dependencies (if not done)
pip install django django-cors-headers requests

# Navigate to Django project
cd memebot

# Run migrations
python manage.py migrate

# Create admin user (optional)
python manage.py createsuperuser

# Start the Django dev server
python manage.py runserver
```

The API will be available at **http://localhost:8000/api/tokens/**

---

### 2. Frontend Setup

```bash
cd Trading/Memebot-frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The dashboard will be available at **http://localhost:3000**

It automatically fetches data from the Django backend at `http://localhost:8000/api/`.

> The API URL is configurable in `.env.local`:
> ```
> NEXT_PUBLIC_API_URL=http://localhost:8000/api
> ```

---

### 3. Running the Pipeline

The system has two management commands:

#### Pull new token pairs from Dexscreener
```bash
cd memebot
python manage.py pull_pairs
```

#### Process & score all new snapshots
```bash
python manage.py process_snapshots
```

This runs the full pipeline:
1. Checks token age >= 2 minutes
2. Calls Solsniffer API for contract safety flags
3. Runs hard rejection filters (liquidity, mint authority, freeze authority, top holder)
4. Runs behaviour analysis (wash-trading, wallet fan-out)
5. Scores the token (0–14 points)
6. Saves the score
7. Sends Telegram alert if score >= 10 and not already alerted

#### Automating (cron / loop)

For continuous scanning, run in a loop or cron:
```bash
# Simple loop (every 60 seconds)
while true; do
  python manage.py pull_pairs
  python manage.py process_snapshots
  sleep 60
done
```

Or add to crontab:
```
* * * * * cd /path/to/memebot && /path/to/env/bin/python manage.py pull_pairs && /path/to/env/bin/python manage.py process_snapshots
```

---

## API Reference

### `GET /api/tokens/`

Returns all scored (non-rejected) tokens.

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_score` | int | 0 | Only return tokens with score >= this |

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "mint": "So1ana...",
      "symbol": "PEPE",
      "name": "Pepe Token",
      "score": 12,
      "breakdown": {
        "mint_disabled": 2,
        "freeze_disabled": 2,
        "top_holder_low": 2,
        "top5_holders_low": 2,
        "liquidity_ok": 2,
        "traders_active": 0,
        "behaviour_passed": 2
      },
      "liquidity_usd": 45000.0,
      "volume_24h": 120000.0,
      "buys_1h": 35,
      "sells_1h": 12,
      "traders_1h": 8,
      "price_change_5m": 3.2,
      "age_minutes": 15,
      "behaviour_passed": true,
      "dexscreener_url": "https://dexscreener.com/solana/...",
      "alert_sent": true
    }
  ]
}
```

---

## Scoring Table

| Rule | Points |
|------|--------|
| Mint authority disabled | +2 |
| Freeze authority disabled | +2 |
| Liquidity >= $20K | +2 |
| Top holder < 10% | +2 |
| Top 5 holders < 35% | +2 |
| Behaviour analysis passed | +2 |
| Traders 1h > 10 | +2 |
| **Max** | **14** |

**Alert threshold:** score >= 10

---

## Hard Rejection Rules

A token is **rejected** (never rescanned) if:
- Liquidity < $10,000
- Mint authority is enabled
- Freeze authority is enabled
- Top holder owns >= 20%

---

## Behaviour Detection Rules (v1)

- First 3 buys from the same wallet
- Buy → Sell → Buy wash loops from a single wallet
- One wallet making > 50% of early buys (fan-out)

> In v1, `TradeEvent` data can be stubbed. Behaviour defaults to PASS when no events exist.

---

## Telegram Alerts

### Setup

Add your bot credentials to `memebot/memebot/settings.py`:

```python
TELEGRAM_BOT_TOKEN = "your-bot-token-here"
TELEGRAM_CHAT_ID = "your-chat-id-here"
```

### How to get these:
1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → copy the token
2. Send a message to your bot, then visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   Find your `chat.id` in the response.

### Alert format
```
🚀 NEW HIGH-SCORE TOKEN

PEPE — Pepe Token
So1ana...

Score: 12/14
Liquidity: $45,000
Volume 24h: $120,000
Traders 1h: 47
Price Δ 5m: 3.2%

Breakdown:
  ✅ mint_disabled: 2
  ✅ freeze_disabled: 2
  ✅ top_holder_low: 2
  ...

View on Dexscreener
```

---

## Frontend Dashboard

The Next.js dashboard provides:

- **Live data** — polls `/api/tokens` every 30 seconds
- **Filter controls** — min score slider, min liquidity, behaviour-only toggle
- **Token table** — sorted by score, color-coded rows
- **Detail panel** — click a token to see full breakdown, market stats, behaviour status
- **Direct links** — opens Dexscreener for any token

---

## External Dependencies

| Purpose | Service |
|---------|---------|
| Market discovery | [Dexscreener REST API](https://docs.dexscreener.com) |
| Contract safety | [Solsniffer API](https://solsniffer.com) |
| Alerts | Telegram Bot API |
| Future discovery | Pump.fun websocket (not implemented in v1) |

---

## What's NOT in scope (v1)

- No auto-trading / execution
- No wallet management or private keys
- No MEV protection
- No PnL tracking
- No strategy optimization
- No Pump.fun integration (planned for v2)

---

## Switching to PostgreSQL (production)

In `memebot/memebot/settings.py`, replace the DATABASES block:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "memebot",
        "USER": "your_user",
        "PASSWORD": "your_password",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

Then:
```bash
pip install psycopg2-binary
python manage.py migrate
```

---

## License

Private project — not for public distribution.

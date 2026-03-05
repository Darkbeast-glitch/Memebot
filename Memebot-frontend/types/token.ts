// Matches the Django /api/tokens response shape
export interface Token {
  mint: string
  symbol: string
  name: string
  score: number | null
  breakdown: Record<string, number>
  liquidity_usd: number | null
  volume_24h: number | null
  buys_1h: number | null
  sells_1h: number | null
  traders_1h: number | null
  price_change_5m: number | null
  age_minutes: number | null
  behaviour_passed: boolean
  dexscreener_url: string | null
  alert_sent: boolean
  is_rejected: boolean
  source: string
}

export interface TokensApiResponse {
  count: number
  results: Token[]
}

export interface DashboardStats {
  total_discovered: number
  total_scored: number
  total_rejected: number
  total_alerted: number
  top_picks: number
}

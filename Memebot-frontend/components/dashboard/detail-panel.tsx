'use client'

import { Token } from '@/types/token'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertCircle, CheckCircle, ExternalLink, Bell } from 'lucide-react'

interface DetailPanelProps {
  token: Token
}

function formatUsd(value: number | null): string {
  if (value === null || value === undefined) return '—'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`
  return `$${value.toFixed(0)}`
}

// Map breakdown keys to human-readable labels
const BREAKDOWN_LABELS: Record<string, { label: string; max: number }> = {
  mint_disabled: { label: 'Mint Disabled', max: 2 },
  freeze_disabled: { label: 'Freeze Disabled', max: 2 },
  top_holder_low: { label: 'Top Holder < 10%', max: 2 },
  top5_holders_low: { label: 'Top 5 Holders < 35%', max: 2 },
  liquidity_ok: { label: 'Liquidity >= $20K', max: 2 },
  traders_active: { label: 'Traders 1h > 10', max: 2 },
  behaviour_passed: { label: 'Behaviour Passed', max: 2 },
}

export default function DetailPanel({ token }: DetailPanelProps) {
  const breakdown = token.breakdown || {}

  return (
    <div className="space-y-4">
      {/* Token Header */}
      <Card className="bg-card p-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xl font-bold text-foreground">
              {token.symbol}
            </h3>
            <p className="text-sm text-muted-foreground">{token.name}</p>
            <p className="mt-1 font-mono text-xs text-muted-foreground truncate max-w-[200px]">
              {token.mint}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {token.alert_sent && (
              <Badge className="bg-blue-900/40 text-blue-300 border-blue-700/50 border">
                <Bell className="mr-1 h-3 w-3" />
                Alerted
              </Badge>
            )}
            <Badge
              variant="secondary"
              className={
                token.score >= 12
                  ? 'bg-green-900/40 text-green-300 border-green-700/50 border text-lg px-3 py-1'
                  : token.score >= 10
                    ? 'bg-yellow-900/40 text-yellow-300 border-yellow-700/50 border text-lg px-3 py-1'
                    : 'bg-red-900/40 text-red-300 border-red-700/50 border text-lg px-3 py-1'
              }
            >
              {token.score}/14
            </Badge>
          </div>
        </div>
      </Card>

      {/* Market Stats */}
      <Card className="bg-card p-4">
        <h4 className="mb-3 font-semibold text-foreground text-sm">Market Data</h4>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Liquidity</span>
            <span className="font-mono font-semibold text-accent">
              {formatUsd(token.liquidity_usd)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Volume 24h</span>
            <span className="font-mono font-semibold text-foreground">
              {formatUsd(token.volume_24h)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Buys 1h</span>
            <span className="font-mono font-semibold text-green-300">
              {token.buys_1h ?? '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Sells 1h</span>
            <span className="font-mono font-semibold text-red-300">
              {token.sells_1h ?? '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Traders 1h</span>
            <span className="font-mono font-semibold text-foreground">
              {token.traders_1h ?? '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Age</span>
            <span className="font-mono font-semibold text-foreground">
              {token.age_minutes !== null ? `${token.age_minutes} min` : '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Price Change 5m</span>
            <span
              className={`font-mono font-semibold ${
                (token.price_change_5m ?? 0) >= 0 ? 'text-green-300' : 'text-red-300'
              }`}
            >
              {token.price_change_5m !== null
                ? `${token.price_change_5m > 0 ? '+' : ''}${token.price_change_5m.toFixed(2)}%`
                : '—'}
            </span>
          </div>
        </div>
      </Card>

      {/* Score Breakdown — real data from API */}
      <Card className="bg-card p-4">
        <h4 className="mb-3 font-semibold text-foreground text-sm">
          Score Breakdown ({token.score}/14)
        </h4>
        <div className="space-y-2">
          {Object.entries(BREAKDOWN_LABELS).map(([key, { label, max }]) => {
            const points = breakdown[key] ?? 0
            const passed = points > 0
            return (
              <div key={key} className="flex items-center gap-2">
                {passed ? (
                  <CheckCircle className="h-4 w-4 text-green-300 flex-shrink-0" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
                )}
                <span className="flex-1 text-xs text-foreground">{label}</span>
                <span className={`font-mono text-xs font-semibold ${passed ? 'text-green-300' : 'text-red-400'}`}>
                  {points}/{max}
                </span>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Behaviour Status */}
      <Card className={`bg-card p-4 ${!token.behaviour_passed ? 'border-yellow-700/50' : 'border-green-700/50'}`}>
        <div className="flex items-center gap-2">
          {token.behaviour_passed ? (
            <CheckCircle className="h-4 w-4 text-green-300" />
          ) : (
            <AlertCircle className="h-4 w-4 text-yellow-300" />
          )}
          <span className="text-sm font-semibold text-foreground">
            Behaviour: {token.behaviour_passed ? 'Passed' : 'Failed'}
          </span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {token.behaviour_passed
            ? 'No suspicious early trading patterns detected.'
            : 'Suspicious trading patterns flagged (same-wallet buys, wash loops, or fan-out).'}
        </p>
      </Card>

      {/* External Link */}
      {token.dexscreener_url && (
        <Button
          onClick={() => window.open(token.dexscreener_url!, '_blank')}
          className="w-full bg-accent hover:bg-accent/90 text-accent-foreground"
        >
          <ExternalLink className="mr-2 h-4 w-4" />
          View on Dexscreener
        </Button>
      )}
    </div>
  )
}

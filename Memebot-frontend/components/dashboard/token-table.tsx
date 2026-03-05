'use client'

import { Token } from '@/types/token'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ExternalLink, Loader2 } from 'lucide-react'

interface TokenTableProps {
  tokens: Token[]
  selectedToken: Token | null
  onSelectToken: (token: Token) => void
  loading?: boolean
}

function getScoreBadgeColor(score: number | null) {
  if (score === null) return 'bg-slate-900/40 text-slate-300 border-slate-700/50'
  if (score >= 12) return 'bg-green-900/40 text-green-300 border-green-700/50'
  if (score >= 10) return 'bg-yellow-900/40 text-yellow-300 border-yellow-700/50'
  return 'bg-red-900/40 text-red-300 border-red-700/50'
}

function getBehaviourColor(passed: boolean) {
  return passed
    ? 'bg-green-900/40 text-green-300 border-green-700/50'
    : 'bg-red-900/40 text-red-300 border-red-700/50'
}

function formatUsd(value: number | null): string {
  if (value === null || value === undefined) return '—'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`
  return `$${value.toFixed(0)}`
}

export default function TokenTable({
  tokens,
  selectedToken,
  onSelectToken,
  loading,
}: TokenTableProps) {
  if (loading) {
    return (
      <Card className="flex items-center justify-center bg-card p-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-3 text-sm text-muted-foreground">Loading tokens...</span>
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden bg-card">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/20">
              <th className="px-4 py-3 text-left font-semibold text-foreground">
                Token
              </th>
              <th className="px-4 py-3 text-left font-semibold text-foreground">
                Score
              </th>
              <th className="px-4 py-3 text-right font-semibold text-foreground">
                Liquidity
              </th>
              <th className="px-4 py-3 text-right font-semibold text-foreground">
                Volume 24h
              </th>
              <th className="px-4 py-3 text-center font-semibold text-foreground">
                Behaviour
              </th>
              <th className="px-4 py-3 text-right font-semibold text-foreground">
                Age (mins)
              </th>
              <th className="px-4 py-3 text-right font-semibold text-foreground">
                Price 5m
              </th>
              <th className="px-4 py-3 text-center font-semibold text-foreground">
                Link
              </th>
            </tr>
          </thead>
          <tbody>
            {tokens.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-muted-foreground">
                  No tokens match your filters
                </td>
              </tr>
            ) : (
              tokens.map(token => (
                <tr
                  key={token.mint}
                  onClick={() => onSelectToken(token)}
                  className={`border-b border-border transition-colors cursor-pointer hover:bg-secondary/20
                    ${(token.score ?? 0) >= 12 ? 'bg-green-900/10' : (token.score ?? 0) >= 10 ? 'bg-yellow-900/10' : ''}
                    ${selectedToken?.mint === token.mint ? 'bg-accent/20' : ''}
                  `}
                >
                  <td className="px-4 py-3">
                    <div className="font-semibold text-foreground">
                      {token.symbol}
                    </div>
                    <div className="text-xs text-muted-foreground truncate max-w-[120px]">
                      {token.name}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant="secondary"
                      className={`${getScoreBadgeColor(token.score)} border`}
                    >
                      {token.score !== null ? `${token.score}/14` : '—'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-foreground">
                    {formatUsd(token.liquidity_usd)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-foreground">
                    {formatUsd(token.volume_24h)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge
                      variant="secondary"
                      className={`${getBehaviourColor(token.behaviour_passed)} border`}
                    >
                      {token.behaviour_passed ? 'PASS' : 'FAIL'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-foreground">
                    {token.age_minutes ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    <span
                      className={
                        (token.price_change_5m ?? 0) >= 0
                          ? 'text-green-300'
                          : 'text-red-300'
                      }
                    >
                      {token.price_change_5m !== null
                        ? `${token.price_change_5m > 0 ? '+' : ''}${token.price_change_5m.toFixed(2)}%`
                        : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {token.dexscreener_url && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-accent hover:bg-accent/20"
                        onClick={(e) => {
                          e.stopPropagation()
                          window.open(token.dexscreener_url!, '_blank')
                        }}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

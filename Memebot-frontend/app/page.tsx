'use client'

import { useState } from 'react'
import DashboardHeader from '@/components/dashboard/header'
import FilterControls from '@/components/dashboard/filter-controls'
import TokenTable from '@/components/dashboard/token-table'
import DetailPanel from '@/components/dashboard/detail-panel'
import { Token } from '@/types/token'
import { useTokens, useStats, TokenView } from '@/hooks/use-tokens'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'

export default function DashboardPage() {
  const [activeView, setActiveView] = useState<TokenView>('top')
  const { tokens, loading, error, lastRefresh, refetch } = useTokens(activeView)
  const stats = useStats()
  const [selectedToken, setSelectedToken] = useState<Token | null>(null)
  const [minScore, setMinScore] = useState(0)
  const [minLiquidity, setMinLiquidity] = useState(0)
  const [behaviourPassedOnly, setBehaviourPassedOnly] = useState(false)

  const filteredTokens = tokens.filter(token => {
    if ((token.score ?? 0) < minScore) return false
    if ((token.liquidity_usd ?? 0) < minLiquidity) return false
    if (behaviourPassedOnly && !token.behaviour_passed) return false
    return true
  })

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader lastRefresh={lastRefresh} onRefresh={refetch} />
      
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 rounded-lg border border-red-700/50 bg-red-900/20 p-4 text-sm text-red-300">
            Failed to load data: {error}. Make sure the Django backend is running on port 8000.
          </div>
        )}

        {/* Stats bar */}
        {stats && (
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <StatCard label="Discovered" value={stats.total_discovered} />
            <StatCard label="Scored" value={stats.total_scored} />
            <StatCard label="Top Picks" value={stats.top_picks} color="text-green-400" />
            <StatCard label="Alerted" value={stats.total_alerted} color="text-yellow-400" />
            <StatCard label="Rejected" value={stats.total_rejected} color="text-red-400" />
          </div>
        )}

        {/* View Tabs */}
        <Tabs value={activeView} onValueChange={(v) => setActiveView(v as TokenView)} className="mb-6">
          <TabsList className="bg-card border border-border">
            <TabsTrigger value="top" className="data-[state=active]:bg-green-900/30 data-[state=active]:text-green-300">
              🔥 Top Picks
              {stats && (
                <Badge variant="secondary" className="ml-2 bg-green-900/40 text-green-300 border-green-700/50 border text-xs">
                  {stats.top_picks}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="all" className="data-[state=active]:bg-yellow-900/30 data-[state=active]:text-yellow-300">
              📊 All Scored
              {stats && (
                <Badge variant="secondary" className="ml-2 bg-yellow-900/40 text-yellow-300 border-yellow-700/50 border text-xs">
                  {stats.total_scored}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="new" className="data-[state=active]:bg-blue-900/30 data-[state=active]:text-blue-300">
              🆕 New Discoveries
              {stats && (
                <Badge variant="secondary" className="ml-2 bg-blue-900/40 text-blue-300 border-blue-700/50 border text-xs">
                  {stats.total_discovered}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main content */}
          <div className="lg:col-span-2">
            {activeView !== 'new' && (
              <FilterControls
                minScore={minScore}
                onMinScoreChange={setMinScore}
                minLiquidity={minLiquidity}
                onMinLiquidityChange={setMinLiquidity}
                behaviourPassedOnly={behaviourPassedOnly}
                onBehaviourPassedOnlyChange={setBehaviourPassedOnly}
              />
            )}
            
            <TokenTable
              tokens={filteredTokens}
              selectedToken={selectedToken}
              onSelectToken={setSelectedToken}
              loading={loading}
            />
          </div>

          {/* Detail panel */}
          <div className="lg:col-span-1">
            {selectedToken ? (
              <DetailPanel token={selectedToken} />
            ) : (
              <div className="rounded-lg border border-border bg-card p-6">
                <p className="text-center text-sm text-muted-foreground">
                  Select a token to view details
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3 text-center">
      <div className={`text-2xl font-bold ${color || 'text-foreground'}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  )
}

'use client'

import { useState } from 'react'
import DashboardHeader from '@/components/dashboard/header'
import FilterControls from '@/components/dashboard/filter-controls'
import TokenTable from '@/components/dashboard/token-table'
import DetailPanel from '@/components/dashboard/detail-panel'
import { Token } from '@/types/token'
import { useTokens } from '@/hooks/use-tokens'

export default function DashboardPage() {
  const { tokens, loading, error, lastRefresh, refetch } = useTokens()
  const [selectedToken, setSelectedToken] = useState<Token | null>(null)
  const [minScore, setMinScore] = useState(0)
  const [minLiquidity, setMinLiquidity] = useState(0)
  const [behaviourPassedOnly, setBehaviourPassedOnly] = useState(false)

  const filteredTokens = tokens.filter(token => {
    if (token.score < minScore) return false
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

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main content */}
          <div className="lg:col-span-2">
            <FilterControls
              minScore={minScore}
              onMinScoreChange={setMinScore}
              minLiquidity={minLiquidity}
              onMinLiquidityChange={setMinLiquidity}
              behaviourPassedOnly={behaviourPassedOnly}
              onBehaviourPassedOnlyChange={setBehaviourPassedOnly}
            />
            
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

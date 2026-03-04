'use client'

import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'

interface DashboardHeaderProps {
  lastRefresh: Date | null
  onRefresh: () => void
}

export default function DashboardHeader({ lastRefresh, onRefresh }: DashboardHeaderProps) {
  const timeStr = lastRefresh
    ? lastRefresh.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : '—'

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Memecoin Risk Dashboard
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Live scoring & alerts for Solana meme tokens
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Last refresh</p>
              <p className="font-mono text-sm font-semibold text-accent">
                {timeStr}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>
        </div>
      </div>
    </header>
  )
}

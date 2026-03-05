'use client'

import { useState, useEffect, useCallback } from 'react'
import { Token, TokensApiResponse, DashboardStats } from '@/types/token'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
const POLL_INTERVAL = 30_000 // 30 seconds

export type TokenView = 'top' | 'all' | 'new'

export function useTokens(view: TokenView = 'top') {
  const [tokens, setTokens] = useState<Token[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const fetchTokens = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/tokens/?view=${view}`)
      if (!res.ok) throw new Error(`API error: ${res.status}`)
      const data: TokensApiResponse = await res.json()
      setTokens(data.results)
      setError(null)
      setLastRefresh(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tokens')
    } finally {
      setLoading(false)
    }
  }, [view])

  useEffect(() => {
    setLoading(true)
    fetchTokens()
    const interval = setInterval(fetchTokens, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchTokens])

  return { tokens, loading, error, lastRefresh, refetch: fetchTokens }
}

export function useStats() {
  const [stats, setStats] = useState<DashboardStats | null>(null)

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/stats/`)
      if (!res.ok) return
      const data: DashboardStats = await res.json()
      setStats(data)
    } catch {
      // non-critical, ignore
    }
  }, [])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchStats])

  return stats
}

'use client'

import { useState, useEffect, useCallback } from 'react'
import { Token, TokensApiResponse } from '@/types/token'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
const POLL_INTERVAL = 30_000 // 30 seconds

export function useTokens() {
  const [tokens, setTokens] = useState<Token[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const fetchTokens = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/tokens/`)
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
  }, [])

  useEffect(() => {
    fetchTokens()
    const interval = setInterval(fetchTokens, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchTokens])

  return { tokens, loading, error, lastRefresh, refetch: fetchTokens }
}

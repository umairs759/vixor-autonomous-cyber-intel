"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"

export default function CorrelationsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [correlations, setCorrelations] = useState<any[]>([])

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    loadCorrelations()
  }, [router])

  async function loadCorrelations() {
    try {
      const data = await api.get<any[]>("/scans/0/correlations")
      setCorrelations(data)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load correlations")
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }

  return (
    <div className="min-h-screen">
      <nav className="border-b border-border/50 bg-surface sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-mono font-bold text-text tracking-tight">
            <div className="w-6 h-6 rounded bg-primary text-background flex items-center justify-center text-xs">V</div>
            VIXOR
          </div>
          <Button onClick={() => router.push("/dashboard")}>Dashboard</Button>
          <Button onClick={() => { clearAccessToken(); router.push("/login") }}>Sign out</Button>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-40 font-mono font-bold text-text mb-8">Correlations</h1>

        {correlations.length === 0 ? (
          <div className="text-muted text-center py-20">No correlated findings yet.</div>
        ) : (
          <div className="space-y-2">
            {correlations.map((c: any) => (
              <div key={c.id} className="card p-4">
                <h3 className="font-mono font-bold text-text">{c.title}</h3>
                <p className="text-sm text-muted mb-2">{c.narrative}</p>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm">Score: {c.combined_score}</span>
                  <span className="font-mono text-sm">Findings: {c.finding_ids?.length || 0}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"

export default function DashboardPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<any>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    fetchSummary()
  }, [router])

  async function fetchSummary() {
    try {
      const data = await api.get<any>("/dashboard/summary")
      setSummary(data)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load dashboard. Please try again.")
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-2 text-muted font-mono">
          Loading...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <nav className="border-b border-border/50 bg-surface sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-mono font-bold text-text tracking-tight">
            <div className="w-6 h-6 rounded bg-primary text-background flex items-center justify-center text-xs">
              V
            </div>
            VIXOR
          </div>
          <Button variant="outline" onClick={() => router.push("/login")}>Sign out</Button>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-40 font-mono font-bold text-text mb-8">Dashboard</h1>

        {!summary ? (
          <div className="text-muted text-center py-20">No data available.</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Total Scans" value={summary.total_scans ?? 0} />
            <StatCard title="Open Findings" value={summary.open_findings ?? 0} />
            <StatCard title="Critical" value={summary.critical_findings ?? 0} accent="critical" />
            <StatCard title="Assets" value={summary.total_assets ?? 0} />
          </div>
        )}
      </main>
    </div>
  )
}

function StatCard({ title, value, accent }: { title: string; value: number; accent?: string }) {
  const color = accent === "critical" ? "text-critical" : "text-primary"
  return (
    <div className="card">
      <p className="text-sm text-muted">{title}</p>
      <p className={`text-2xl font-mono font-bold mt-2 ${color}`}>{value}</p>
    </div>
  )
}

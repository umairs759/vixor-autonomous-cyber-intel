"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"

export default function FindingsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [findings, setFindings] = useState<any[]>([])

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    loadFindings()
  }, [router])

  async function loadFindings() {
    try {
      // In a real app, this would filter by scan
      const data = await api.get<any[]>("/scans/0/findings")
      setFindings(data)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load findings")
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
        <h1 className="text-40 font-mono font-bold text-text mb-8">Findings</h1>

        {findings.length === 0 ? (
          <div className="text-muted text-center py-20">No findings yet.</div>
        ) : (
          <div className="space-y-2">
            {findings.map((f: any) => (
              <div key={f.id} className="card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-mono font-bold text-text">{f.title}</h3>
                    <p className="text-sm text-muted">{f.severity_raw} &bull; {f.source_tool}</p>
                  </div>
                  <Button onClick={() => router.push(`/findings/${f.id}`)}>View</Button>
                </div>
                <p className="text-sm text-muted mt-2">{f.description}</p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

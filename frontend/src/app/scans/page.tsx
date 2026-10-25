"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Play, RefreshCw } from "lucide-react"

export default function ScansPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scans, setScans] = useState<any[]>([])
  const [domainId, setDomainId] = useState("")

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    loadScans()
  }, [router])

  async function loadScans() {
    try {
      const data = await api.get<any[]>("/scans")
      setScans(data)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load scans")
      }
    } finally {
      setLoading(false)
    }
  }

  async function launchScan() {
    try {
      await api.post("/scans", {
        domain_id: domainId,
        asset_ids: [],
      })
      setDomainId("")
      await loadScans()
    } catch (err: any) {
      setError(err?.detail || "Failed to launch scan")
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
        <h1 className="text-40 font-mono font-bold text-text mb-8">Scans</h1>

        <div className="flex gap-2 mb-6">
          <Input
            placeholder="Domain ID"
            value={domainId}
            onChange={e => setDomainId(e.target.value)}
          />
          <Button onClick={launchScan}>Launch Scan</Button>
          <Button variant="outline" onClick={loadScans}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>

        {scans.length === 0 ? (
          <div className="text-muted text-center py-20">No scans yet.</div>
        ) : (
          <div className="space-y-2">
            {scans.map((s: any) => (
              <div key={s.id} className="card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-mono font-bold text-text">Scan {s.id.slice(0, 8)}</h3>
                    <p className="text-sm text-muted">
                      Domain: {s.domain_id} &bull; Status: {s.status}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={() => router.push(`/scans/${s.id}`)}>View</Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

function Input(props: any) {
  return (
    <input
      className="input"
      {...props}
    />
  )
}

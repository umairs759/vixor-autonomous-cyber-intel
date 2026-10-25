"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Download } from "lucide-react"

export default function ReportsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reports, setReports] = useState<any[]>([])

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    loadReports()
  }, [router])

  async function loadReports() {
    try {
      // Get reports from the first scan
      const data = await api.get<any[]>("/scans/0/reports")
      setReports(data)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load reports")
      }
    } finally {
      setLoading(false)
    }
  }

  async function generateReport(scanId: string) {
    try {
      const data = await api.post(`/scans/${scanId}/report`)
      await loadReports()
    } catch (err: any) {
      setError(err?.detail || "Failed to generate report")
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
        <h1 className="text-40 font-mono font-bold text-text mb-8">Reports</h1>

        <div className="mb-6">
          <Button
            onClick={() => generateReport("0")}
            className="flex items-center gap-2"
          >
            <Download className="w-4 h-4" /> Generate Report
          </Button>
        </div>

        {reports.length === 0 ? (
          <div className="text-muted text-center py-20">No reports yet.</div>
        ) : (
          <div className="space-y-2">
            {reports.map((r: any) => (
              <div key={r.id} className="card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-mono font-bold text-text">Report {r.id.slice(0, 8)}</h3>
                    <p className="text-sm text-muted">Scan: {r.scan_id}</p>
                  </div>
                  <Button onClick={() => {}}>Download</Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

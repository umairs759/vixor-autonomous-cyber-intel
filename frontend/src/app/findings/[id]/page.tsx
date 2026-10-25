"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"

export default function FindingDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [finding, setFinding] = useState<any>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    loadFinding()
  }, [router, params.id])

  async function loadFinding() {
    try {
      const data = await api.get<any>(`/findings/${params.id}`)
      setFinding(data)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load finding")
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }

  if (!finding) {
    return <div className="min-h-screen flex items-center justify-center">Not found</div>
  }

  return (
    <div className="min-h-screen">
      <nav className="border-b border-border/50 bg-surface sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-mono font-bold text-text tracking-tight">
            <div className="w-6 h-6 rounded bg-primary text-background flex items-center justify-center text-xs">V</div>
            VIXOR
          </div>
          <Button onClick={() => router.push("/findings")}>Back</Button>
          <Button onClick={() => { clearAccessToken(); router.push("/login") }}>Sign out</Button>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-40 font-mono font-bold text-text mb-8">Finding Details</h1>

        <div className="card mb-8">
          <h2 className="font-mono font-bold text-text mb-4">{finding.title}</h2>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="p-2 bg-elevated rounded">
              <p className="text-xs text-muted">Severity</p>
              <p className="font-mono text-sm">{finding.severity_raw}</p>
            </div>
            <div className="p-2 bg-elevated rounded">
              <p className="text-xs text-muted">Source</p>
              <p className="font-mono text-sm">{finding.source_tool}</p>
            </div>
            <div className="p-2 bg-elevated rounded">
              <p className="text-xs text-muted">CVSS</p>
              <p className="font-mono text-sm">{finding.cvss || "N/A"}</p>
            </div>
            <div className="p-2 bg-elevated rounded">
              <p className="text-xs text-muted">CVE IDs</p>
              <p className="font-mono text-sm">{finding.cve_ids?.join(", ") || "None"}</p>
            </div>
          </div>
          <div className="mb-4">
            <p className="text-sm text-muted mb-2">Description</p>
            <p className="font-mono text-sm">{finding.description}</p>
          </div>
          <div className="mb-4">
            <p className="text-sm text-muted mb-2">Remediation</p>
            <p className="font-mono text-sm">{finding.remediation || "No remediation guidance available."}</p>
          </div>
          <div className="mb-4">
            <p className="text-sm text-muted mb-2">Evidence</p>
            <pre className="font-mono text-xs text-muted bg-surface p-2 rounded">{JSON.stringify(finding.evidence, null, 2)}</pre>
          </div>
        </div>
      </main>
    </div>
  )
}

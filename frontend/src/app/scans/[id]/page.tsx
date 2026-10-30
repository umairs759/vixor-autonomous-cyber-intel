"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableRow, TableCell, TableBody } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { X } from "lucide-react"

interface ScanDetail {
  id: string
  project_id: string
  domain_id: string
  status: string
  started_at: string | null
  finished_at: string | null
  error_summary: string | null
}

interface Finding {
  id: string
  asset_id: string
  fingerprint: string
  source_tool: string
  title: string
  description: string
  severity_raw: string
  cvss: number | null
  cve_ids: string[]
  evidence: Record<string, any>
  remediation: string | null
  created_at: string
}

export default function ScanDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const { id } = params
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [findingsLoading, setFindingsLoading] = useState(true)

  const loadScan = useCallback(async () => {
    try {
      const data = await api.get<ScanDetail>(`/scans/${id}`)
      setScan(data)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load scan details")
      }
    } finally {
      setLoading(false)
    }
  }, [id, router])

  const loadFindings = useCallback(async () => {
    try {
      const data = await api.get<Finding[]>(`/scans/${id}/findings`)
      setFindings(data)
      setFindingsLoading(false)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setFindings([])
      }
    } finally {
      setFindingsLoading(false)
    }
  }, [id, router])

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    void loadScan()
    void loadFindings()
  }, [id, loadFindings, loadScan, router])

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading scan...</div>
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

  if (!scan) {
    return <div className="min-h-screen flex items-center justify-center">Scan not found</div>
  }

  // Compute High/Med/Low counts
  const highCount = findings.filter((f) => f.severity_raw?.toLowerCase() === "high").length
  const medCount = findings.filter((f) => f.severity_raw?.toLowerCase() === "medium").length
  const lowCount = findings.filter((f) => f.severity_raw?.toLowerCase() === "low" || f.severity_raw?.toLowerCase() === "info").length

  return (
    <div className="min-h-screen pt-16">
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-40 font-mono font-bold text-text">
            Scan {scan.id.slice(0, 8)}
          </h1>
          <Button onClick={() => router.push("/scans")}>
            <X className="w-4 h-4 mr-2" /> Back to Scans
          </Button>
        </div>

        {/* Scan Metadata */}
        <div className="card p-6 mb-8">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-muted mb-2">Scan ID</p>
              <p className="font-mono font-bold text-text">{scan.id}</p>
            </div>
            <div>
              <p className="text-xs text-muted mb-2">Domain</p>
              <p className="font-mono font-bold text-text">{scan.domain_id}</p>
            </div>
            <div>
              <p className="text-xs text-muted mb-2">Target URL</p>
              <p className="font-mono font-bold text-text">{scan.domain_id}</p>
            </div>
          </div>
          <div className="mt-6 pt-4 border-t border-border/50">
            <p className="text-xs text-muted mb-2">Status</p>
            <Badge
              className={
                scan.status === "completed"
                  ? "bg-green-100 text-green-800 border-green-200"
                  : scan.status === "failed"
                  ? "bg-red-100 text-red-800 border-red-200"
                  : "bg-yellow-100 text-yellow-800 border-yellow-200"
              }
              variant="outline"
            >
              {scan.status.toUpperCase()}
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <p className="text-xs text-muted mb-2">Started At</p>
              <p className="font-mono text-sm">{scan.started_at ? new Date(scan.started_at).toLocaleString() : "N/A"}</p>
            </div>
            <div>
              <p className="text-xs text-muted mb-2">Completed At</p>
              <p className="font-mono text-sm">{scan.finished_at ? new Date(scan.finished_at).toLocaleString() : "N/A"}</p>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="card p-4">
            <p className="text-xs text-muted mb-2">Total Findings</p>
            <p className="text-3x font-mono font-bold text-text">{findings.length}</p>
          </div>
          <div className="card p-4 bg-red-100 text-red-800 border-red-200 p-4">
            <p className="text-xs text-muted mb-2">High</p>
            <p className="text-3x font-mono font-bold text-red-600">{highCount}</p>
          </div>
          <div className="card p-4 bg-yellow-100 text-yellow-800 border-yellow-200 p-4">
            <p className="text-xs text-muted mb-2">Medium</p>
            <p className="text-3x font-mono font-bold text-yellow-600">{medCount}</p>
          </div>
          <div className="card p-4 bg-green-100 text-green-800 border-green-200 p-4">
            <p className="text-xs text-muted mb-2">Low</p>
            <p className="text-3x font-mono font-bold text-green-600">{lowCount}</p>
          </div>
        </div>

        {/* Findings Table */}
        {findingsLoading ? (
          <div className="card p-6 text-muted">Loading findings...</div>
        ) : findings.length > 0 ? (
          <div className="card p-6 mb-8">
            <h2 className="text-20 font-mono font-bold text-text mb-4">Findings</h2>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableCell>Title</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Tool</TableCell>
                  <TableCell>CVSS</TableCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {findings.map((f: Finding) => (
                  <TableRow key={f.id}>
                    <TableCell className="font-mono text-sm">{f.title}</TableCell>
                    <TableCell>
                      <Badge
                        className={
                          f.severity_raw?.toLowerCase() === "critical"
                            ? "bg-critical/20 text-critical border-critical/30"
                            : f.severity_raw?.toLowerCase() === "high"
                            ? "bg-high/20 text-high border-high/30"
                            : f.severity_raw?.toLowerCase() === "medium"
                            ? "bg-medium/20 text-medium border-medium/30"
                            : "bg-low/20 text-low border-low/30"
                        }
                        variant="outline"
                      >
                        {f.severity_raw?.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{f.source_tool}</TableCell>
                    <TableCell className="font-mono text-sm">{f.cvss || "N/A"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="text-xs text-muted mt-3">
              <a href="/findings" className="text-primary hover:underline">
                View all findings
              </a>
            </p>
          </div>
        ) : (
          <div className="card p-6 text-muted">
            <p>No findings found for this scan.</p>
          </div>
        )}

        {/* Back to Project button */}
        <div className="mt-8 pt-8 border-t border-border/50">
          <Button
            variant="outline"
            onClick={() => router.push(`/projects/${scan.project_id}`)}
          >
            Back to Project
          </Button>
        </div>
      </main>
    </div>
  )
}

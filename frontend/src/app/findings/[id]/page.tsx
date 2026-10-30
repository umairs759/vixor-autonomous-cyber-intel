"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"

interface FindingScore {
  risk_score: number
  risk_class: string
  model_version: string
  features: Record<string, any>
  shap_values: Record<string, number>
  narrative: string
  scored_by: string
}

interface Finding {
  id: string
  asset_id: string
  scan_id: string
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
  score?: FindingScore | null
  regression_status?: string | null
}

export default function FindingDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [finding, setFinding] = useState<Finding | null>(null)

  const loadFinding = useCallback(async () => {
    try {
      const data = await api.get<Finding>(`/findings/${params.id}`)
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
  }, [params.id, router])

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    void loadFinding()
  }, [loadFinding, router])

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }

  if (!finding) {
    return error ? (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Alert variant="destructive">
          <AlertTitle>Unable to load finding</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    ) : <div className="min-h-screen flex items-center justify-center">Not found</div>
  }

  const severityColor = {
    critical: "bg-critical/20 text-critical border-critical/30",
    high: "bg-high/20 text-high border-high/30",
    medium: "bg-medium/20 text-medium border-medium/30",
    low: "bg-low/20 text-low border-low/30",
    info: "bg-info/20 text-info border-info/30",
  }[finding.severity_raw?.toLowerCase()] || "bg-muted/20 text-muted border-muted/30"

  const regressionStatus = finding.regression_status?.toLowerCase() ?? "unknown"
  const regressionColor = {
    new: "bg-primary/20 text-primary border-primary/30",
    recurring: "bg-accent/20 text-accent border-accent/30",
    reintroduced: "bg-high/20 text-high border-high/30",
    resolved: "bg-low/20 text-low border-low/30",
  }[regressionStatus] || "bg-muted/20 text-muted border-muted/30"

  const riskScore = finding.score?.risk_score ?? 0
  const riskClass = finding.score?.risk_class ?? "low"
  const riskColor = riskClass === "critical" ? "text-critical" : riskClass === "high" ? "text-high" : riskClass === "medium" ? "text-medium" : "text-low"

  // Prepare SHAP data for horizontal bar chart
  const shapData = finding.score?.shap_values
    ? Object.entries(finding.score.shap_values)
        .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
        .slice(0, 10)
        .map(([feature, value]) => ({ feature, value }))
    : []

  return (
    <div className="min-h-screen pt-16">
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-40 font-mono font-bold text-text">Finding Details</h1>
          <Badge className={severityColor} variant="outline">{finding.severity_raw?.toUpperCase()}</Badge>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            <div className="card">
              <h2 className="font-mono font-bold text-text mb-4">{finding.title}</h2>
              <div className="grid grid-cols-2 gap-4 mb-4">
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
                <div className="p-2 bg-elevated rounded">
                  <p className="text-xs text-muted">Fingerprint</p>
                  <p className="font-mono text-xs truncate">{finding.fingerprint}</p>
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
                <pre className="font-mono text-xs text-muted bg-surface p-2 rounded max-h-64 overflow-auto">{JSON.stringify(finding.evidence, null, 2)}</pre>
              </div>
            </div>

            {/* Regression Status & Narrative */}
            {finding.regression_status && (
              <div className="card">
                <div className="flex items-center gap-3 mb-4">
                  <h3 className="font-mono font-bold text-text">Regression Analysis</h3>
                  <Badge className={regressionColor} variant="outline">
                    {finding.regression_status.toUpperCase()}
                  </Badge>
                </div>
                {finding.score?.narrative && (
                  <div className="p-3 bg-elevated rounded border border-border/50">
                    <p className="text-sm text-text">{finding.score.narrative}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar: ML Risk Score & SHAP Chart */}
          <div className="space-y-6">
            <div className="card text-center">
              <p className="text-xs text-muted mb-2">ML RISK SCORE</p>
              <div className="relative w-32 h-32 mx-auto mb-4">
                <svg viewBox="0 0 128 128">
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    fill="none"
                    stroke="rgb(31 41 55)"
                    strokeWidth="8"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    fill="none"
                    stroke={`rgb(${riskClass === "critical" ? "244 63 94" : riskClass === "high" ? "249 115 22" : riskClass === "medium" ? "245 184 61" : "56 189 248"})`}
                    strokeWidth="8"
                    strokeDasharray={`${(riskScore / 100) * 352} 352`}
                    strokeLinecap="round"
                    transform="rotate(-90 64 64)"
                    style={{ transition: "stroke-dasharray 0.5s ease" }}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className={`text-4xl font-mono font-bold ${riskColor}`}>{riskScore}</span>
                </div>
              </div>
              <p className="text-xs text-muted capitalize">{riskClass} risk</p>
              <p className="text-xs text-muted mt-1">Model: {finding.score?.model_version || "N/A"}</p>
              <p className="text-xs text-muted">Scored by: {finding.score?.scored_by || "N/A"}</p>
            </div>

            {shapData.length > 0 && (
              <div className="card">
                <h3 className="font-mono font-bold text-text mb-4 text-center">SHAP Feature Contributions</h3>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={shapData} layout="vertical" margin={{ left: 10, right: 10, top: 10, bottom: 10 }}>
                      <YAxis
                        type="category"
                        dataKey="feature"
                        width={140}
                        tick={{ fontSize: 10, fill: "rgb(139 152 169)", fontFamily: "JetBrains Mono, monospace" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 10, fill: "rgb(139 152 169)", fontFamily: "JetBrains Mono, monospace" }}
                        axisLine={{ stroke: "rgb(31 41 55)" }}
                        tickLine={{ stroke: "rgb(31 41 55)" }}
                        domain={["auto", "auto"]}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "rgb(21 28 39)",
                          border: "1px solid rgb(31 41 55)",
                          borderRadius: "8px",
                          color: "rgb(230 237 243)",
                        }}
                        formatter={(value: number) => [value.toFixed(4), "SHAP value"]}
                      />
                      <Bar
                        dataKey="value"
                        radius={[0, 4, 4, 0]}
                        barSize={16}
                      >
                        {shapData.map((_, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={shapData[index].value >= 0 ? "rgb(244 63 94)" : "rgb(56 189 248)"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-xs text-muted text-center mt-2">
                  Red = increases risk | Blue = decreases risk
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

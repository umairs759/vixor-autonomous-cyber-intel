"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter, useParams } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"

export default function ProjectDetailPage() {
  const { id } = useParams()
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [project, setProject] = useState<any>(null)
  const [domains, setDomains] = useState<any[]>([])
  const [assets, setAssets] = useState<any[]>([])
  const [refreshKey, setRefreshKey] = useState(0)

  const loadProject = useCallback(async () => {
    if (!id) {
      return
    }
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    try {
      // Fetch project details
      const projData = await api.get<any>(`/projects/${id}`)
      setProject(projData)

      // Fetch domains associated with this project
      const domainsData = await api.get<any[]>(`/projects/${id}/domains`)
      setDomains(domainsData)

      // Fetch assets for verified domains
      const verifiedDomains = domainsData.filter((d: any) => d.status === "verified")
      if (verifiedDomains.length > 0) {
        const assetsPromises = verifiedDomains.map((d: any) =>
          api.get<any[]>(`/domains/${d.id}/assets`)
        )
        const assetsResults = await Promise.allSettled(assetsPromises)
        const allAssets: any[] = []
        assetsResults.forEach((result) => {
          if (result.status === "fulfilled") {
            allAssets.push(...result.value)
          }
        })
        setAssets(allAssets)
      }
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load project details. The project may have been deleted or you may not have permission.")
      }
    } finally {
      setLoading(false)
    }
  }, [id, router])

  useEffect(() => {
    if (!id) {
      router.push("/projects")
      return
    }
    void loadProject()
  }, [id, loadProject, refreshKey, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-2 text-muted font-mono">
          Loading project...
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
        <Button onClick={() => setRefreshKey((r) => r + 1)} className="mt-4">
          Retry
        </Button>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-20 font-mono text-text mb-4">Project Not Found</h2>
          <Button onClick={() => router.push("/projects")}>Back to Projects</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen pt-16">
      <main className="max-w-7xl mx-auto px-4 py-8">

        <div className="card p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-40 font-mono font-bold text-text">
              {project.name}
            </h1>
          </div>
          <p className="text-sm text-muted">{project.description || "No description"}</p>
        </div>

        {/* Registered Domains Section */}
        {domains.length > 0 || project.name ? (
          <div className="card p-6 mb-8">
            <h2 className="text-20 font-mono font-bold text-text mb-4">
              Registered Domains ({domains.length})
            </h2>
            <div className="space-y-4">
              {domains.map((d: any) => {
                const isVerified = d.status === "verified"
                const badgeClass = isVerified
                  ? "bg-green-100 text-green-800 border-green-200"
                  : "bg-red-100 text-red-800 border-red-200"
                return (
                  <div key={d.id} className="flex items-center gap-3 p-3 rounded border">
                    <span className={`badge ${badgeClass} text-xs font-mono`}>
                      {isVerified ? "VERIFIED" : "UNVERIFIED"}
                    </span>
                    <div>
                      <p className="font-mono font-bold text-text">{d.root_domain}</p>
                      <p className="text-xs text-muted">
                        Method: {d.verification_method}
                      </p>
                      {isVerified && (
                        <p className="text-xs text-muted">
                          Token: {d.verification_token || "N/A"}
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ) : (
          <div className="card p-6 mb-8 text-muted">
            <p>No domains registered for this project.</p>
          </div>
        )}

        {/* Assets Section */}
        {assets.length > 0 ? (
          <div className="card p-6 mb-8">
            <h2 className="text-20 font-mono font-bold text-text mb-4">
              Assets Associated ({assets.length})
            </h2>
            <div className="space-y-3">
              {assets.map((a: any) => (
                <div key={a.id} className="flex items-center gap-3 p-2 rounded border">
                  <span className="w-8 h-8 rounded bg-elevated flex items-center justify-center text-sm font-mono">
                    {a.hostname?.slice(0, 3) || "—"}
                  </span>
                  <div>
                    <p className="font-mono font-bold text-text">{a.hostname || "Unknown"}</p>
                    <p className="text-xs text-muted">
                      {a.ip_address || "No IP"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="card p-6 mb-8 text-muted">
            <p>No assets found for verified domains.</p>
          </div>
        )}

        {/* Launch Scan Section */}
        {!project.scans_completed || project.scans_completed < 1 ? (
          <div className="card p-6">
            <h2 className="text-20 font-mono font-bold text-text mb-4">
              Launch New Scan
            </h2>
            <p className="text-sm text-muted mb-4">
              Select a domain to initiate a security scan. Safe-only Nmap flags
              (sV, safe scripts) will be used. ZAP and Nuclei will run with
              non-destructive policies excluded.
            </p>
            <Button
              variant="default"
              onClick={() => router.push(`/scans?domain=${project.id}`)}
            >
              <svg
              className="w-4 h-4 mr-2"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="12" y1="1" x2="12" y2="23"></line>
              <line x1="5" y1="9" x2="12" y2="15"></line>
              <line x1="19" y1="9" x2="12" y2="15"></line>
            </svg>
              Launch Scan
            </Button>
          </div>
        ) : (
          <div className="card p-6">
            <h2 className="text-20 font-mono font-bold text-text mb-4">
              Scans Launched
            </h2>
            <p className="text-sm text-muted">
              {project.scan_count || 0} scan(s) have been launched for this project.
              View them in the Scans page.
            </p>
            <Button
              variant="outline"
              onClick={() => router.push("/scans")}
            >
              View Scans
            </Button>
          </div>
        )}

      </main>
    </div>
  )
}

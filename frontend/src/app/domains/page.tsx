"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export default function DomainsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [domains, setDomains] = useState<any[]>([])
  const [projects, setProjects] = useState<any[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState("")
  const [newDomain, setNewDomain] = useState("")
  const [method, setMethod] = useState("dns_txt")

  const loadDomains = useCallback(async () => {
    try {
      setError(null)
      const projectList = await api.get<any[]>("/projects")
      setProjects(projectList)
      if (projectList.length === 0) {
        setSelectedProjectId("")
        setDomains([])
        return
      }

      const activeProject = projectList.find((project) => project.id === selectedProjectId) ?? projectList[0]
      setSelectedProjectId(activeProject.id)
      const projectDomains = await Promise.all(
        projectList.map((project) => api.get<any[]>(`/projects/${project.id}/domains`))
      )
      setDomains(projectDomains.flat())
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load domains")
      }
    } finally {
      setLoading(false)
    }
  }, [router, selectedProjectId])

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    void loadDomains()
  }, [loadDomains, router])

  async function registerDomain(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedProjectId) {
      setError("Create or select a project before registering a domain.")
      return
    }
    try {
      await api.post(`/projects/${selectedProjectId}/domains`, {
        root_domain: newDomain,
        verification_method: method,
      })
      setNewDomain("")
      await loadDomains()
    } catch (err: any) {
      setError(err?.message || "Failed to register domain")
    }
  }

  async function verifyDomain(domain: any) {
    try {
      await api.post(`/projects/domains/${domain.id}/verify`, {
        verification_method: domain.verification_method,
      })
      await loadDomains()
    } catch (err: any) {
      setError(err?.message || "Verification failed")
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
        <h1 className="text-40 font-mono font-bold text-text mb-8">Domains</h1>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={registerDomain} className="card mb-8">
          <div className="flex gap-2">
            <select
              aria-label="Project"
              value={selectedProjectId}
              onChange={(event) => setSelectedProjectId(event.target.value)}
              className="input"
              required
            >
              <option value="" disabled>Select a project</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
            <Input
              placeholder="example.com"
              value={newDomain}
              onChange={e => setNewDomain(e.target.value)}
              required
            />
            <select value={method} onChange={e => setMethod(e.target.value)} className="input">
              <option value="dns_txt">DNS TXT</option>
              <option value="file">File</option>
            </select>
            <Button type="submit">Register</Button>
          </div>
        </form>

        {domains.length === 0 ? (
          <div className="text-muted text-center py-20">No domains yet. Register one to begin.</div>
        ) : (
          <div className="space-y-2">
            {domains.map((d: any) => (
              <div key={d.id} className="card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-mono font-bold text-text">{d.root_domain}</h3>
                    <p className="text-sm text-muted">
                      Status: {d.status} &bull; Method: {d.verification_method}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {d.status !== "verified" ? (
                      <Button onClick={() => verifyDomain(d)}>Verify</Button>
                    ) : (
                      <Button variant="outline" disabled>Verified</Button>
                    )}
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

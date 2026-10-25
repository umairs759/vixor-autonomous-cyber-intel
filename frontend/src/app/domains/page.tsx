"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus } from "lucide-react"

export default function DomainsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [domains, setDomains] = useState<any[]>([])
  const [newDomain, setNewDomain] = useState("")
  const [method, setMethod] = useState("dns_txt")

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    loadDomains()
  }, [router])

  async function loadDomains() {
    try {
      // Get all domains - in a real app this would be filtered by project
      const data = await api.get<any[]>("/domains")
      setDomains(data)
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
  }

  async function registerDomain(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.post("/projects/0/domains", {
        root_domain: newDomain,
        verification_method: method,
      })
      setNewDomain("")
      await loadDomains()
    } catch (err: any) {
      setError(err?.detail || "Failed to register domain")
    }
  }

  async function verifyDomain(domain: any) {
    try {
      await api.post(`/domains/${domain.id}/verify`, {
        verification_method: domain.verification_method,
      })
      await loadDomains()
    } catch (err: any) {
      setError(err?.detail || "Verification failed")
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

        <form onSubmit={registerDomain} className="card mb-8">
          <div className="flex gap-2">
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

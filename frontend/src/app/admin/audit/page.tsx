"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

export default function AdminAuditPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<any[]>([])

  const loadLogs = useCallback(async () => {
    try {
      const data = await api.get<any[]>("/users/audit-logs")
      setLogs(data)
      setError(null)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load audit logs")
      }
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    void loadLogs()
  }, [loadLogs, router])

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }

  return (
    <div className="min-h-screen pt-16">
      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-40 font-mono font-bold text-text mb-8">Admin - Audit Logs</h1>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {logs.length === 0 ? (
          <div className="text-muted text-center py-20">No audit logs yet.</div>
        ) : (
          <div className="space-y-2">
            {logs.map((log: any) => (
              <div key={log.id} className="card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-mono font-bold text-text">{log.action}</h3>
                    <p className="text-sm text-muted">{log.resource_type} &bull; {new Date(log.created_at).toLocaleString()}</p>
                  </div>
                  <span className="font-mono text-xs">{log.user_id || "system"}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

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

export default function ProjectsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [projects, setProjects] = useState<any[]>([])
  const [newName, setNewName] = useState("")
  const [newDesc, setNewDesc] = useState("")

  useEffect(() => {
    if (!isAuthenticated()) {
      clearAccessToken()
      router.push("/login")
      return
    }
    loadProjects()
  }, [router])

  async function loadProjects() {
    try {
      const data = await api.get<any[]>("/projects")
      setProjects(data)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load projects")
      }
    } finally {
      setLoading(false)
    }
  }

  async function createProject(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.post("/projects", { name: newName, description: newDesc })
      setNewName("")
      setNewDesc("")
      await loadProjects()
    } catch (err: any) {
      setError(err?.detail || "Failed to create project")
    }
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }

  if (error) {
    return <Alert variant="destructive"><AlertTitle>Error</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>
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
        <h1 className="text-40 font-mono font-bold text-text mb-8">Projects</h1>

        <form onSubmit={createProject} className="card mb-8">
          <div className="flex gap-2">
            <Input placeholder="Project name" value={newName} onChange={e => setNewName(e.target.value)} required />
            <Input placeholder="Description (optional)" value={newDesc} onChange={e => setNewDesc(e.target.value)} />
            <Button type="submit">Create</Button>
          </div>
        </form>

        {projects.length === 0 ? (
          <div className="text-muted text-center py-20">No projects yet. Create one to get started.</div>
        ) : (
          <div className="space-y-2">
            {projects.map((p: any) => (
              <div key={p.id} className="card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-mono font-bold text-text">{p.name}</h3>
                    <p className="text-sm text-muted">{p.description || "No description"}</p>
                  </div>
                  <Button onClick={() => router.push(`/projects/${p.id}`)}>Open</Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

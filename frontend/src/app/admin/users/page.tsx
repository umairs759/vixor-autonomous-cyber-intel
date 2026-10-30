"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"
import { isAuthenticated, clearAccessToken } from "@/lib/auth"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function AdminUsersPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [users, setUsers] = useState<any[]>([])
  const [newEmail, setNewEmail] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [newRole, setNewRole] = useState("analyst")

  const loadUsers = useCallback(async () => {
    try {
      const data = await api.get<any[]>("/users")
      setUsers(data)
    } catch (err: any) {
      if (err.status === 401) {
        clearAccessToken()
        router.push("/login")
      } else {
        setError("Failed to load users")
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
    void loadUsers()
  }, [loadUsers, router])

  async function createUser(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.post("/users", {
        email: newEmail,
        password: newPassword,
        role: newRole,
      })
      setNewEmail("")
      setNewPassword("")
      setNewRole("analyst")
      await loadUsers()
    } catch (err: any) {
      setError(err?.detail || "Failed to create user")
    }
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }

  return (
    <div className="min-h-screen pt-16">
      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-40 font-mono font-bold text-text mb-8">Admin - Users</h1>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={createUser} className="card mb-8">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" placeholder="user@example.com" value={newEmail} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewEmail(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label>Password</Label>
              <Input type="password" placeholder="••••••••" value={newPassword} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewPassword(e.target.value)} required />
            </div>
            <div className="space-y-2 flex items-end">
              <select value={newRole} onChange={e => setNewRole(e.target.value)} className="input">
                <option value="admin">Admin</option>
                <option value="analyst">Analyst</option>
                <option value="viewer">Viewer</option>
              </select>
              <Button type="submit">Create User</Button>
            </div>
          </div>
        </form>

        {users.length === 0 ? (
          <div className="text-muted text-center py-20">No users found.</div>
        ) : (
          <div className="space-y-2">
            {users.map((u: any) => (
              <div key={u.id} className="card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-mono font-bold text-text">{u.email}</h3>
                    <p className="text-sm text-muted">Role: {u.role} &bull; Active: {u.is_active ? "Yes" : "No"}</p>
                  </div>
                  <Button variant="outline" disabled>Edit</Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

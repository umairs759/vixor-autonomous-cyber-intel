"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { LoginSchema, type LoginInput } from "@/lib/schemas"
import { api } from "@/lib/api"
import { storeAccessToken, clearAccessToken } from "@/lib/auth"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2 } from "lucide-react"

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState<LoginInput>({ email: "", password: "" })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const parsed = LoginSchema.safeParse(form)
      if (!parsed.success) {
        setError("Invalid email or password.")
        setLoading(false)
        return
      }

      const data = await api.post<{ access_token: string; token_type: string }>(
        "/auth/login",
        parsed.data
      )
      storeAccessToken(data.access_token)
      const callbackUrl = new URLSearchParams(
        typeof window !== "undefined" ? window.location.search : ""
      ).get("callbackUrl")
      router.push(callbackUrl ?? "/dashboard")
    } catch (err: any) {
      // Generic error message — never reveal whether email exists
      setError("Invalid email or password.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="card w-full max-w-md">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded bg-primary text-background flex items-center justify-center font-mono text-sm font-bold">
            V
          </div>
          <h1 className="font-mono font-bold text-text tracking-tight">VIXOR</h1>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Login failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="admin@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
              autoComplete="email"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              autoComplete="current-password"
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Signing in...
              </>
            ) : (
              "Sign in"
            )}
          </Button>
        </form>

        <p className="mt-6 text-sm text-muted text-center">
          Management stakeholders: read-only executive summary view.
        </p>
      </div>
    </div>
  )
}

/** VIXOR — Auth helpers.

Access token is kept in memory only (never localStorage). Refresh token
is an httpOnly cookie set by the backend; refresh requests go through a
Next.js server action / API route that forwards the cookie.
 */

import { setAccessToken, getAccessToken } from "./api"

export function isAuthenticated(): boolean {
  return getAccessToken() !== null
}

export function storeAccessToken(token: string | null) {
  setAccessToken(token)
}

export function clearAccessToken() {
  setAccessToken(null)
}

export function parseJwtPayload(token: string): { role?: string; exp?: number; sub?: string } | null {
  try {
    const payload = token.split(".")[1]
    if (!payload) return null
    const decoded = Buffer.from(payload, "base64").toString("utf-8")
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

export function getTokenExpiry(token: string): number | null {
  const payload = parseJwtPayload(token)
  return payload?.exp ?? null
}

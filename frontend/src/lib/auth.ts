/** Auth helpers. Tokens are held in memory; cookies are HttpOnly on the server. */

import { getAccessToken, setAccessToken } from "./api"

const USER_EMAIL_STORAGE_KEY = "vixor_user_email"
const USER_ROLE_STORAGE_KEY = "vixor_user_role"

export function isAuthenticated(): boolean {
  return getAccessToken() !== null || getStoredUserEmail() !== null
}

/** Browser code cannot read the server's HttpOnly access-token cookie. */
export function getAccessTokenFromCookie(): string | null {
  return getAccessToken()
}

export function storeAccessToken(
  token: string | null,
  userEmail?: string,
  userRole?: string
) {
  setAccessToken(token)
  if (typeof localStorage === "undefined") return
  try {
    if (userEmail !== undefined) {
      if (userEmail) localStorage.setItem(USER_EMAIL_STORAGE_KEY, userEmail)
      else localStorage.removeItem(USER_EMAIL_STORAGE_KEY)
    }
    if (userRole !== undefined) {
      if (userRole) localStorage.setItem(USER_ROLE_STORAGE_KEY, userRole)
      else localStorage.removeItem(USER_ROLE_STORAGE_KEY)
    }
  } catch {
    // localStorage may be unavailable in some environments.
  }
}

export function clearAccessToken() {
  setAccessToken(null)
  try {
    localStorage.removeItem(USER_EMAIL_STORAGE_KEY)
    localStorage.removeItem(USER_ROLE_STORAGE_KEY)
  } catch {
    // localStorage may be unavailable in some environments.
  }
}

export function getStoredUserEmail(): string | null {
  if (typeof localStorage === "undefined") return null
  try {
    return localStorage.getItem(USER_EMAIL_STORAGE_KEY)
  } catch {
    return null
  }
}

export function getStoredUserRole(): string | null {
  if (typeof localStorage === "undefined") return null
  try {
    return localStorage.getItem(USER_ROLE_STORAGE_KEY)
  } catch {
    return null
  }
}

export function parseJwtPayload(
  token: string
): { role?: string; exp?: number; sub?: string } | null {
  try {
    const payload = token.split(".")[1]
    if (!payload) return null
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/")
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4)
    return JSON.parse(atob(padded))
  } catch {
    return null
  }
}

export function getTokenExpiry(token: string): number | null {
  return parseJwtPayload(token)?.exp ?? null
}

/** VIXOR — API client wrapper.

Uses fetch with the access token from an in-memory store. Refresh token
is httpOnly (managed by browser), so refresh is handled via the
/backend route that forwards the cookie.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

async function request<T>(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init?.headers ?? {}),
  }

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`
  }

  const response = await fetch(`${API_BASE_URL}${input.toString().replace(API_BASE_URL, "")}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const error = new Error(body.detail ?? `Request failed: ${response.status}`)
    ;(error as any).status = response.status
    ;(error as any).body = body
    throw error
  }

  if (response.status === 204) {
    return undefined as unknown as T
  }

  return response.json()
}

export const api = {
  get: <T>(path: string, init?: RequestInit) => request<T>(path, { ...init, method: "GET" }),
  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, { ...init, method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, { ...init, method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, { ...init, method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string, init?: RequestInit) => request<T>(path, { ...init, method: "DELETE" }),
}

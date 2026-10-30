/** API client: access tokens stay in memory and refresh tokens stay HttpOnly. */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:8001/api/v1"
    : "https://localhost:8000/api/v1")

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

function requestUrl(input: RequestInfo | URL): string {
  const path = input instanceof Request ? input.url : input.toString()
  if (/^https?:\/\//i.test(path)) return path
  return `${API_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`
}

function requestHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers)
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)
  return headers
}

export async function apiResponse(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const url = requestUrl(input)
  const options: RequestInit = {
    ...init,
    headers: requestHeaders(init),
    credentials: "include",
  }

  let response = await fetch(url, options)
  if (
    response.status === 401 &&
    !url.endsWith("/auth/login") &&
    !url.endsWith("/auth/refresh")
  ) {
    const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    }).catch(() => null)
    if (refreshResponse?.ok) {
      const refreshed = await refreshResponse.json().catch(() => null)
      if (typeof refreshed?.access_token === "string") {
        setAccessToken(refreshed.access_token)
        response = await fetch(url, { ...options, headers: requestHeaders(init) })
      }
    }
  }

  return response
}

async function request<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await apiResponse(input, init)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const error = new Error(body.detail ?? `Request failed: ${response.status}`)
    ;(error as Error & { status?: number; body?: unknown }).status = response.status
    ;(error as Error & { status?: number; body?: unknown }).body = body
    throw error
  }

  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  get: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { ...init, method: "GET" }),
  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      ...init,
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  put: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      ...init,
      method: "PUT",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      ...init,
      method: "PATCH",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  delete: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { ...init, method: "DELETE" }),
}

export async function getFirstScanId(): Promise<string | null> {
  try {
    const scans = await api.get<Array<{ id: string }>>("/scans")
    return scans[0]?.id ?? null
  } catch {
    return null
  }
}

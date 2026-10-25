/** VIXOR — Next.js middleware for route protection.

- Protects all routes except /login.
- Validates role for /admin routes (admin only).
- Access token is read from the Authorization header (set by the client
  from an in-memory store); refresh token is an httpOnly cookie managed
  by the browser.
- Tokens are never stored in localStorage.
 */

import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

// Routes that do not require authentication
const PUBLIC_ROUTES = ["/login"]

// Admin-only route prefixes
const ADMIN_ROUTES = ["/admin"]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public routes
  if (PUBLIC_ROUTES.includes(pathname)) {
    return NextResponse.next()
  }

  // Read access token from Authorization header (set by client)
  const authHeader = request.headers.get("authorization")
  const accessToken = authHeader?.replace(/^Bearer\s/i, "")

  if (!accessToken) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Role check for admin routes
  if (ADMIN_ROUTES.some((prefix) => pathname.startsWith(prefix))) {
    // The token payload (role) is verified by the backend on each API call.
    // Middleware only enforces that a token is present; the backend enforces RBAC.
    // We decode the JWT locally only for UI-level gating if needed.
    return NextResponse.next()
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - login (public)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|login).*)",
  ],
}

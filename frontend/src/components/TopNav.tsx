"use client"

import React, { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import Link from "next/link"
import { getStoredUserEmail, getStoredUserRole, clearAccessToken } from "@/lib/auth"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { LogOut, LayoutDashboard, BarChart2, FileText, ShieldAlert, FileCheck, User } from "lucide-react"

interface NavLink {
  href: string
  label: string
  icon: React.ElementType
  role?: string
}

const NAV_LINKS: NavLink[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: BarChart2 },
  { href: "/findings", label: "Findings", icon: ShieldAlert },
  { href: "/correlations", label: "Correlations", icon: FileCheck },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/admin", label: "Admin", icon: User, role: "admin" },
]

export function TopNav() {
  const pathname = usePathname()
  const router = useRouter()
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)

  useEffect(() => {
    setUserEmail(getStoredUserEmail())
    setUserRole(getStoredUserRole())
  }, [])

  const isAuthenticated = Boolean(userEmail)

  const handleSignOut = async () => {
    await api.post("/auth/logout", {}).catch(() => undefined)
    clearAccessToken()
    router.push("/login")
  }

  // Not authenticated: render nothing (login page is the public entry point).
  if (!isAuthenticated) return null

  return (
    <nav className="fixed top-0 left-0 right-0 z-40 bg-surface border-b border-border">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2 font-mono font-bold text-text tracking-tight hover:text-primary transition-colors" onClick={(e) => { e.preventDefault(); router.push("/dashboard") }}>
          <div className="w-6 h-6 rounded bg-primary text-background flex items-center justify-center text-xs">V</div>
          VIXOR
        </Link>

        {/* Module links */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map((link) => {
            if (link.role && userRole !== link.role) return null
            const isActive = pathname === link.href
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`
                  flex items-center gap-2 px-3 py-2 rounded-md text-sm font-mono text-muted transition-colors
                  ${isActive ? "bg-primary/10 text-primary border border-primary/20" : "hover:text-text hover:bg-elevated"}
                `}
              >
                <link.icon className="w-4 h-4" />
                {link.label}
              </Link>
            )
          })}
        </div>

        {/* User email + sign out */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 px-3 py-2 rounded-md bg-elevated text-xs text-muted font-mono">
            <User className="w-3 h-3" />
            {userEmail ?? "user"}
          </div>
          <Button variant="outline" size="sm" onClick={handleSignOut}>
            <LogOut className="w-3 h-3 mr-1.5" />
            Sign out
          </Button>
        </div>
      </div>
    </nav>
  )
}

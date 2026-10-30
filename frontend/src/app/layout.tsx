import type { Metadata } from "next"
import "./globals.css"
import { TopNav } from "@/components/TopNav"

// Render TopNav on all routes except /login
const showTopNav = !["/login"].includes(typeof window !== "undefined" ? window.location.pathname : "")

export const metadata: Metadata = {
  title: "VIXOR — Vulnerability Intelligence Platform",
  description: "AI-assisted continuous vulnerability intelligence",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="bg-[#07090D] text-[#E6EDF3] min-h-screen antialiased">
      <body className={`bg-[#07090D] text-[#E6EDF3] min-h-screen antialiased`}>
        {showTopNav && <TopNav />}
        {children}
      </body>
    </html>
  )
}

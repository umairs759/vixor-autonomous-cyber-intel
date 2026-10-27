"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect } from "react"
import { Shield, BarChart3, FileText, Users, PlayCircle } from "lucide-react"

export default function HomePage() {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (pathname === "/") {
      router.replace("/login")
    }
  }, [pathname, router])

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="border-b border-border/50 bg-surface/80 backdrop-blur sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-primary text-background flex items-center justify-center font-mono text-sm font-bold">
                V
              </div>
              <span className="font-mono font-semibold text-text tracking-tight">VIXOR</span>
            </div>
            <div className="hidden md:flex items-center gap-6">
              <a href="/dashboard" className="text-sm font-medium text-muted hover:text-text transition-colors">
                Dashboard
              </a>
              <a href="/projects" className="text-sm font-medium text-muted hover:text-text transition-colors">
                Projects
              </a>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/login" className="btn-outline">
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <main className="flex-1">
        <div className="max-w-7xl mx-auto py-12 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h1 className="text-40 font-mono font-bold text-text mb-4 tracking-tight">
              VIXOR
            </h1>
            <p className="text-lg text-muted max-w-2xl mx-auto">
              AI-assisted continuous vulnerability intelligence. Attack surface
              discovery, ML risk scoring with SHAP explanations, regression
              tracking, and correlation — for domains you own and authorize.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3 lg:grid-cols-4">
            <FeatureCard
              icon={<Shield className="w-6 h-6" />}
              title="Ownership Verification"
              description="Prove domain control via DNS TXT or .well-known file before any scan runs."
            />
            <FeatureCard
              icon={<BarChart3 className="w-6 h-6" />}
              title="ML Risk Scoring"
              description="RandomForest + XGBoost with SHAP explanations — never LLM scoring."
            />
            <FeatureCard
              icon={<FileText className="w-6 h-6" />}
              title="Regression Intelligence"
              description="Classify findings as NEW, RECURRING, REINTRODUCED, or RESOLVED across scans."
            />
            <FeatureCard
              icon={<Users className="w-6 h-6" />}
              title="Correlation & Reporting"
              description="Group findings into attack narratives and export professional PDF reports."
            />
          </div>

          <div className="mt-16 flex justify-center">
            <a
              href="/login"
              className="btn-primary flex items-center gap-2"
            >
              <PlayCircle className="w-4 h-4" />
              Get started
            </a>
          </div>
        </div>
      </main>

      <footer className="border-t border-border/50 bg-surface py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-sm text-muted">
            VIXOR — Ethical scanning only. Ownership-verified domains, scope-guard enforced,
            safe scanner templates. For authorized security testing.
          </p>
        </div>
      </footer>
    </div>
  )
}

interface FeatureCardProps {
  icon: React.ReactNode
  title: string
  description: string
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="card">
      <div className="w-10 h-10 rounded bg-elevated flex items-center justify-center text-primary mb-4">
        {icon}
      </div>
      <h3 className="font-mono font-semibold text-text mb-2">{title}</h3>
      <p className="text-sm text-muted leading-relaxed">{description}</p>
    </div>
  )
}

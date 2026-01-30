import Link from 'next/link'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-center text-center">
        {/* Hero Section */}
        <div className="mb-12">
          <h1 className="mb-4 text-6xl font-bold tracking-tight gradient-text">
            Lead Intelligence Portal
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Uncover high-intent opportunities with AI-powered insights and
            intelligent lead discovery
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex gap-4 justify-center mb-16">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-lg bg-primary px-8 py-3 text-lg font-semibold text-primary-foreground shadow-lg hover:bg-primary/90 transition-all hover:scale-105"
          >
            Sign In
          </Link>
          <Link
            href="/signup"
            className="inline-flex items-center justify-center rounded-lg border border-input bg-background px-8 py-3 text-lg font-semibold hover:bg-accent hover:text-accent-foreground transition-all"
          >
            Get Started
          </Link>
        </div>

        {/* Features Grid */}
        <div className="grid text-left md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div className="rounded-lg border bg-card p-6 hover:shadow-lg transition-shadow">
            <div className="mb-3 text-3xl">🎯</div>
            <h3 className="mb-2 text-xl font-semibold">Real-Time Intelligence</h3>
            <p className="text-sm text-muted-foreground">
              Access up-to-date lead information with AI-powered event detection
              and scoring algorithms.
            </p>
          </div>

          <div className="rounded-lg border bg-card p-6 hover:shadow-lg transition-shadow">
            <div className="mb-3 text-3xl">🗺️</div>
            <h3 className="mb-2 text-xl font-semibold">Territory Management</h3>
            <p className="text-sm text-muted-foreground">
              State-based access control with flexible permissions and daily
              usage quotas.
            </p>
          </div>

          <div className="rounded-lg border bg-card p-6 hover:shadow-lg transition-shadow">
            <div className="mb-3 text-3xl">📊</div>
            <h3 className="mb-2 text-xl font-semibold">Smart Filtering</h3>
            <p className="text-sm text-muted-foreground">
              Advanced search and filtering by state, score, status, and custom
              criteria.
            </p>
          </div>
        </div>

        {/* Status Badge */}
        <div className="mt-16 flex justify-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-sm text-primary">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            <span>Setup Complete - Ready to Deploy</span>
          </div>
        </div>
      </div>

      {/* Background gradient */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-primary/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-secondary/20 blur-3xl"></div>
      </div>
    </main>
  )
}

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding/Illustration */}
      <div className="hidden lg:flex lg:w-2/5 bg-gradient-to-br from-primary-600 via-primary-500 to-secondary-500 p-12 flex-col justify-between relative overflow-hidden">
        {/* Animated background elements */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-72 h-72 bg-white rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-white rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        </div>

        {/* Content */}
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-lg bg-white/20 backdrop-blur-sm flex items-center justify-center text-2xl font-bold text-white">
              L
            </div>
            <span className="text-2xl font-bold text-white">
              Lead Intelligence
            </span>
          </div>

          <blockquote className="space-y-2">
            <p className="text-lg text-white/90">
              "This platform has transformed how we identify and pursue business opportunities. The intelligence-driven approach gives us a competitive edge."
            </p>
            <footer className="text-sm text-white/70">
              — Sarah Johnson, VP of Sales
            </footer>
          </blockquote>
        </div>

        <div className="relative z-10 text-white/70 text-sm">
          <p>© 2026 Lead Intelligence Portal. All rights reserved.</p>
        </div>
      </div>

      {/* Right side - Auth forms */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-md">
          {children}
        </div>
      </div>
    </div>
  )
}

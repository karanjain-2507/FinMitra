import { Link, useLocation } from 'react-router-dom'
import { Leaf } from 'lucide-react'

export default function TopBar() {
  const { pathname } = useLocation()

  const navLinks = [
    { to: '/',       label: 'Home' },
    { to: '/demo',   label: 'Demos' },
    { to: '/assess', label: 'Assess' },
    { to: '/what-if', label: 'What If' },
    { to: '/passport', label: 'Passport' },
    { to: '/verifier', label: 'Verify' },
  ]

  return (
    <header className="sticky top-0 z-50 bg-sage-surface-low border-b border-sage-outline-var">
      <div className="max-w-6xl mx-auto px-3 sm:px-6 h-16 flex items-center justify-between">
        {/* Wordmark */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <span className="w-8 h-8 rounded-full bg-sage-primary flex items-center justify-center shadow-level1">
            <Leaf size={16} className="text-white" />
          </span>
          <span className="hidden sm:inline text-title-lg font-jakarta text-sage-on-surface tracking-tight">
            FinMitra
          </span>
        </Link>

        {/* Nav */}
        <nav className="flex items-center gap-0.5 overflow-x-auto scrollbar-hide">
          {navLinks.map(({ to, label }) => {
            const active = pathname === to
            return (
              <Link
                key={to}
                to={to}
                className={`
                  px-1.5 sm:px-3 py-2 rounded-full text-label-sm sm:text-label-lg font-jakarta whitespace-nowrap transition-colors duration-150
                  ${active
                    ? 'bg-sage-primary-container text-sage-on-primary-container'
                    : 'text-sage-on-surface-var hover:bg-sage-surface-med'}
                `}
              >
                {label}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

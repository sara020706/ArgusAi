import { useEffect, useState } from 'react'
import { Menu, X } from 'lucide-react'
import { getHealth } from '../api/argus'

export default function Navbar() {
  const [scrolled, setScrolled]   = useState(false)
  const [mobileOpen, setMobile]   = useState(false)
  const [apiOnline, setApiOnline]  = useState(null)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    async function check() {
      const h = await getHealth()
      setApiOnline(h?.status !== 'unreachable')
    }
    check()
    const id = setInterval(check, 10000)
    return () => clearInterval(id)
  }, [])

  const scrollTo = (id) => {
    setMobile(false)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }

  const navLinks = [
    { label: 'How It Works', id: 'how-it-works' },
    { label: 'Features',     id: 'features'     },
    { label: 'Live Demo',    id: 'demo'          },
  ]

  return (
    <nav className={`sticky top-0 z-50 border-b border-gray-100 transition-all duration-200
      ${scrolled ? 'bg-white/80 backdrop-blur-sm shadow-sm' : 'bg-white'}`}>
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="flex items-center gap-2 font-bold text-lg text-argus-500 hover:text-argus-600 transition-colors">
          👁️ Argus
        </button>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          {navLinks.map(l => (
            <button key={l.id} onClick={() => scrollTo(l.id)}
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
              {l.label}
            </button>
          ))}
          <a href="https://github.com/yourname/argus" target="_blank" rel="noreferrer"
            className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
            GitHub
          </a>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {/* API status */}
          <div className="hidden sm:flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full
            bg-gray-50 border border-gray-200">
            <span className={`w-1.5 h-1.5 rounded-full ${
              apiOnline === null ? 'bg-gray-400' :
              apiOnline ? 'bg-green-500 animate-pulse' : 'bg-red-500'
            }`} />
            <span className="text-gray-600">
              {apiOnline === null ? 'Checking…' : apiOnline ? 'API Online' : 'API Offline'}
            </span>
          </div>

          <button onClick={() => scrollTo('demo')}
            className="hidden sm:inline-flex items-center px-4 py-2 bg-argus-500 hover:bg-argus-600
              text-white text-sm font-semibold rounded-lg transition-colors">
            Try Demo
          </button>

          {/* Mobile hamburger */}
          <button onClick={() => setMobile(o => !o)}
            className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors">
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white px-6 py-4 flex flex-col gap-4">
          {navLinks.map(l => (
            <button key={l.id} onClick={() => scrollTo(l.id)}
              className="text-left text-sm font-medium text-gray-700 hover:text-argus-500 transition-colors">
              {l.label}
            </button>
          ))}
          <a href="https://github.com/yourname/argus" target="_blank" rel="noreferrer"
            className="text-sm font-medium text-gray-700 hover:text-argus-500 transition-colors">
            GitHub
          </a>
          <div className="flex items-center gap-1.5 text-xs font-medium">
            <span className={`w-1.5 h-1.5 rounded-full ${
              apiOnline ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="text-gray-600">{apiOnline ? 'API Online' : 'API Offline'}</span>
          </div>
        </div>
      )}
    </nav>
  )
}

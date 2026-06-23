import { useState, useEffect } from 'react'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav style={{
      position: 'sticky', top: 0, zIndex: 100,
      background: scrolled ? 'rgba(240,242,245,0.94)' : 'rgba(240,242,245,0.92)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--ground-2)',
    }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56 }}>
        <a href="#" style={{ fontFamily: "'Syne',system-ui,sans-serif", fontWeight: 800, fontSize: 18, letterSpacing: '-0.02em', color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 22, height: 22, border: '2px solid var(--accent)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ width: 7, height: 7, background: 'var(--accent)', borderRadius: '50%' }} />
          </span>
          ARGUS AI
        </a>

        <ul style={{ display: 'flex', alignItems: 'center', gap: 32, listStyle: 'none', margin: 0, padding: 0 }} className="nav-links-desktop">
          {[['#pipeline','How it scores'],['#output','Output'],['#signals','Signals'],['#install','Install']].map(([href, label]) => (
            <li key={href}>
              <a href={href} style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-2)', transition: 'color 0.15s', letterSpacing: '0.01em' }}
                onMouseEnter={e => e.target.style.color = 'var(--text)'}
                onMouseLeave={e => e.target.style.color = 'var(--text-2)'}
              >{label}</a>
            </li>
          ))}
        </ul>

        <a href="#install" style={{
          fontFamily: 'var(--mono,"IBM Plex Mono",monospace)', fontSize: 12, fontWeight: 600,
          padding: '7px 16px', background: 'var(--text)', color: 'var(--ground)',
          borderRadius: 4, letterSpacing: '0.02em', transition: 'background 0.15s',
        }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--accent)'}
          onMouseLeave={e => e.currentTarget.style.background = 'var(--text)'}
        >pip install argus</a>
      </div>
    </nav>
  )
}

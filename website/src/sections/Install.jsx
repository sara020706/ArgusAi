import { useState } from 'react'

const TABS = [
  { id: 'pkg',    label: 'Python package',          cmd: 'pip install argus'                                      },
  { id: 'api',    label: 'REST API server',          cmd: 'pip install "argus[api]" && argus-serve --port 8000'   },
  { id: 'docker', label: 'Full stack (API + dashboard)', cmd: 'cp .env.example .env && docker-compose up'         },
]

export default function Install() {
  const [active, setActive]   = useState('pkg')
  const [copied, setCopied]   = useState(false)

  function copy(text) {
    navigator.clipboard.writeText(text).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }

  const activeCmd = TABS.find(t => t.id === active)?.cmd ?? ''

  return (
    <section id="install" style={{ padding: '96px 0', background: 'var(--text)' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 32px', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 40 }}>
        <h2 style={{ fontFamily: "'Syne',system-ui,sans-serif", fontSize: 'clamp(28px,4vw,46px)', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.08, color: '#F0F2F5', maxWidth: 520 }}>
          Three ways in.<br /><em style={{ fontStyle: 'normal', color: 'var(--accent)' }}>Pick one and go.</em>
        </h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%', maxWidth: 620 }}>
          {TABS.map(tab => (
            <div key={tab.id}
              onClick={() => setActive(tab.id)}
              style={{ background: 'rgba(240,242,245,0.05)', border: `1px solid ${active === tab.id ? 'rgba(232,137,12,0.4)' : 'rgba(240,242,245,0.1)'}`, borderRadius: 8, overflow: 'hidden', cursor: 'pointer' }}
            >
              <div style={{ padding: '14px 20px' }}>
                <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: active === tab.id ? 'var(--accent)' : 'rgba(240,242,245,0.5)' }}>
                  {tab.label}
                </span>
              </div>
              {active === tab.id && (
                <div style={{ padding: '0 20px 18px', fontFamily: "'IBM Plex Mono',monospace", fontSize: 14, fontWeight: 500, color: '#F0F2F5', display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ color: 'rgba(240,242,245,0.3)' }}>$</span>
                  <span style={{ flex: 1 }}>{tab.cmd}</span>
                  <button
                    onClick={e => { e.stopPropagation(); copy(tab.cmd) }}
                    style={{ padding: '4px 10px', fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--accent)', border: '1px solid rgba(232,137,12,0.3)', borderRadius: 3, background: 'none', cursor: 'pointer', transition: 'background 0.15s, color 0.15s' }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.color = 'var(--text)' }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = 'var(--accent)' }}
                  >
                    {copied ? 'copied' : 'copy'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        <p style={{ fontSize: 13, color: 'rgba(240,242,245,0.35)' }}>
          MIT license.{' '}
          <a href="https://github.com/yourname/argus" target="_blank" rel="noreferrer" style={{ color: 'rgba(240,242,245,0.55)', textDecoration: 'underline', textUnderlineOffset: 3 }}>GitHub</a>
          {' · '}
          <a href="https://github.com/yourname/argus/blob/main/docs/architecture.md" target="_blank" rel="noreferrer" style={{ color: 'rgba(240,242,245,0.55)', textDecoration: 'underline', textUnderlineOffset: 3 }}>Architecture docs</a>
        </p>
      </div>
    </section>
  )
}

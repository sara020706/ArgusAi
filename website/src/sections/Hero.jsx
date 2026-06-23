import Gauge from '../components/Gauge'

const S = {
  section: { minHeight: 'calc(100vh - 56px)', display: 'grid', gridTemplateColumns: '1fr 1fr', alignItems: 'center', gap: 64, padding: '80px 32px', maxWidth: 1080, margin: '0 auto' },
  kicker:  { fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 10 },
  h1:      { fontFamily: "'Syne',system-ui,sans-serif", fontSize: 'clamp(36px,5vw,58px)', fontWeight: 800, lineHeight: 1.04, letterSpacing: '-0.03em', color: 'var(--text)' },
  body:    { fontSize: 16, color: 'var(--text-2)', lineHeight: 1.65, maxWidth: 420 },
  actions: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, marginTop: 8 },
  meta:    { display: 'flex', gap: 20, flexWrap: 'wrap', marginTop: 4 },
  stat:    { fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: 'var(--text-3)', letterSpacing: '0.04em' },
}

export default function Hero() {
  return (
    <section>
      <div style={S.section}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div style={S.kicker}>
            <span style={{ width: 28, height: 1, background: 'var(--accent)' }} />
            Behavioral Anomaly Detection
          </div>

          <h1 style={S.h1}>
            Knows when<br />
            <em style={{ fontStyle: 'normal', color: 'var(--accent)' }}>normal</em><br />
            becomes dangerous.
          </h1>

          <p style={S.body}>
            Argus AI learns how each user behaves — which hours they work,
            how much they download, which devices they use — and scores
            every event against that baseline. Scores arrive in milliseconds,
            with a plain-language explanation of every point.
          </p>

          <div style={S.actions}>
            <a href="#install"
              style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 13, fontWeight: 600, padding: '12px 24px', background: 'var(--text)', color: 'var(--ground)', borderRadius: 4, letterSpacing: '0.02em', display: 'inline-flex', alignItems: 'center', gap: 8, transition: 'background 0.15s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--accent)'}
              onMouseLeave={e => e.currentTarget.style.background = 'var(--text)'}
            >
              pip install argus
              <svg width="14" height="14" fill="none" viewBox="0 0 16 16"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </a>
            <a href="#output"
              style={{ fontSize: 13, fontWeight: 500, padding: '12px 20px', color: 'var(--text-2)', border: '1px solid var(--ground-2)', borderRadius: 4, background: 'var(--surface)', transition: 'border-color 0.15s, color 0.15s' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor='var(--text-3)'; e.currentTarget.style.color='var(--text)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor='var(--ground-2)'; e.currentTarget.style.color='var(--text-2)' }}
            >
              See sample output
            </a>
          </div>

          <div style={S.meta}>
            <span style={S.stat}><strong style={{ color: 'var(--text)', fontWeight: 600 }}>81</strong> tests passing</span>
            <span style={S.stat}><strong style={{ color: 'var(--text)', fontWeight: 600 }}>0</strong> required dependencies</span>
            <span style={S.stat}>MIT license</span>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <Gauge />
        </div>
      </div>
    </section>
  )
}

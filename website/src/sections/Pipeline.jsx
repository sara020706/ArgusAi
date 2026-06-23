const CELLS = [
  { n: '01 / FEATURE', title: 'Feature extraction',     body: 'Login hour, weekend flag, cyclic sin/cos encoding, raw download size, file count, IP and device novelty check.',                                               badge: '13 features'     },
  { n: '02 / RULES',   title: 'Heuristic rules',        body: 'Seven deterministic rules: night access (+35), large download (+30–50, scaled), new IP (+20), new device (+20), and three more.',                              badge: 'up to +160 pts'  },
  { n: '03 / STATS',   title: 'Statistical deviation',  body: 'Z-score bands against each user\'s personal baseline (Welford online algorithm — no stored history, no batch retraining).',                                     badge: 'up to +30 pts'   },
  { n: '04–06 / LAYERS',title: 'ML + Intel + Correlation',body: 'Optional IsolationForest (+20), AbuseIPDB IP reputation (+40), and multi-event attack pattern detection over a 24 h window (+40).', badge: 'opt-in'          },
]

export default function Pipeline() {
  return (
    <section id="pipeline" style={{ padding: '96px 0', background: 'var(--surface)', borderTop: '1px solid var(--ground-2)' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 32px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 20, height: 1, background: 'var(--accent)' }} />
          Scoring engine
        </div>
        <h2 style={{ fontFamily: "'Syne',system-ui,sans-serif", fontSize: 'clamp(26px,3.5vw,38px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.1, color: 'var(--text)', maxWidth: 560, marginBottom: 60 }}>
          Six layers from raw event to explained score.
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', border: '1px solid var(--ground-2)', borderRadius: 8, overflow: 'hidden' }}>
          {CELLS.map((c, i) => (
            <div key={c.n}
              style={{ padding: '28px 24px', borderRight: i < 3 ? '1px solid var(--ground-2)' : 'none', background: 'var(--surface)', transition: 'background 0.2s', cursor: 'default' }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--ground)'}
              onMouseLeave={e => e.currentTarget.style.background = 'var(--surface)'}
            >
              <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, fontWeight: 600, color: 'var(--accent)', letterSpacing: '0.08em', marginBottom: 14 }}>{c.n}</div>
              <div style={{ fontFamily: "'Syne',system-ui,sans-serif", fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 8 }}>{c.title}</div>
              <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.55 }}>{c.body}</p>
              <span style={{ display: 'inline-block', marginTop: 12, fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-3)', background: 'var(--ground-2)', padding: '3px 8px', borderRadius: 3 }}>{c.badge}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

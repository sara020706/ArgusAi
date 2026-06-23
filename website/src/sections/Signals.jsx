const CARDS = [
  { metric: '+35', unit: 'pts', name: 'Night access',     desc: 'Login between 00:00 and 05:59. Hardcoded, not configurable — this is a bright line.' },
  { metric: '+50', unit: 'pts', name: 'Large download',   desc: 'Scales from +30 pts at 1 GB to +50 pts at 5 GB and above. Linear between the two.' },
  { metric: '+25', unit: 'pts', name: 'Excessive files',  desc: 'More than 100 files accessed in a single event window triggers this rule.' },
  { metric: '+20', unit: 'pts', name: 'New IP / device',  desc: '+20 pts each for a login from a source the user has never used before. Suppressed on first-ever event.' },
  { metric: '+30', unit: 'pts', name: 'Stat deviation',   desc: 'Combined z-score contribution for download size and file count, weighted by band (z ≥ 3 doubles the contribution).' },
  { metric: '+40', unit: 'pts', name: 'Correlation bonus',desc: 'Account-takeover indicators: new IP + new device + off-hours in the same 24 h window. Capped so total stays ≤ 100.' },
]

export default function Signals() {
  return (
    <section id="signals" style={{ padding: '96px 0', background: 'var(--surface)', borderTop: '1px solid var(--ground-2)' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 32px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 20, height: 1, background: 'var(--accent)' }} />
          Detection signals
        </div>
        <h2 style={{ fontFamily: "'Syne',system-ui,sans-serif", fontSize: 'clamp(26px,3.5vw,38px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.1, color: 'var(--text)', maxWidth: 480, marginBottom: 60 }}>
          What Argus AI watches, and how much it charges for each signal.
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '1px', background: 'var(--ground-2)', border: '1px solid var(--ground-2)', borderRadius: 8, overflow: 'hidden' }}>
          {CARDS.map(c => (
            <div key={c.name}
              style={{ background: 'var(--surface)', padding: '28px 24px', display: 'flex', flexDirection: 'column', gap: 10, transition: 'background 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--ground)'}
              onMouseLeave={e => e.currentTarget.style.background = 'var(--surface)'}
            >
              <div style={{ fontFamily: "'Syne',system-ui,sans-serif", fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--text)', lineHeight: 1 }}>
                {c.metric}<span style={{ fontSize: 18, fontWeight: 600, color: 'var(--accent)' }}>{c.unit}</span>
              </div>
              <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-3)' }}>{c.name}</div>
              <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.5 }}>{c.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

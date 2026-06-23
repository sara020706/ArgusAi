const INSIGHTS = [
  {
    icon: <svg width="14" height="14" fill="none" viewBox="0 0 16 16"><path d="M8 2v12M2 8h12" stroke="var(--accent)" strokeWidth="1.6" strokeLinecap="round"/></svg>,
    title: 'Cold-start safe.',
    body: "A brand-new user's first event is never penalized for using an unrecognized IP or device — the baseline seeds itself.",
  },
  {
    icon: <svg width="14" height="14" fill="none" viewBox="0 0 16 16"><circle cx="8" cy="8" r="5.5" stroke="var(--accent)" strokeWidth="1.5"/><path d="M8 5.5v3l2 1.5" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round"/></svg>,
    title: 'Correlation over time.',
    body: 'Five multi-event attack patterns run across a 24 h sliding window — slow exfiltration, repeated night logins, account-takeover indicators.',
  },
  {
    icon: <svg width="14" height="14" fill="none" viewBox="0 0 16 16"><rect x="2" y="3" width="12" height="10" rx="1.5" stroke="var(--accent)" strokeWidth="1.5"/><path d="M5 7h6M5 10h4" stroke="var(--accent)" strokeWidth="1.3" strokeLinecap="round"/></svg>,
    title: 'JSON-serializable output.',
    body: (<><code style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, background: 'var(--ground-2)', padding: '1px 5px', borderRadius: 3 }}>summarize_result()</code> returns a dict you can log, forward to a SIEM, or store as-is.</>),
  },
]

export default function Output() {
  return (
    <section id="output" style={{ padding: '96px 0', background: 'var(--ground)', borderTop: '1px solid var(--ground-2)' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 32px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 56, alignItems: 'start' }}>

        <div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 20, height: 1, background: 'var(--accent)' }} />
            Explainer output
          </div>
          <h2 style={{ fontFamily: "'Syne',system-ui,sans-serif", fontSize: 'clamp(26px,3.5vw,38px)', fontWeight: 800, letterSpacing: '-0.025em', lineHeight: 1.1, color: 'var(--text)', maxWidth: 560, marginBottom: 24 }}>
            Every score ships with a receipt.
          </h2>

          <div style={{ background: '#0F1923', borderRadius: 8, overflow: 'hidden', boxShadow: '0 4px 32px rgba(15,25,35,0.18)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.03)' }}>
              <span style={{ width: 11, height: 11, borderRadius: '50%', background: '#FF5F57' }} />
              <span style={{ width: 11, height: 11, borderRadius: '50%', background: '#FFBD2E' }} />
              <span style={{ width: 11, height: 11, borderRadius: '50%', background: '#28C840' }} />
              <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.05em', marginLeft: 6 }}>argus · build_explanation(result)</span>
            </div>
            <pre style={{ padding: '20px 20px 24px', fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, lineHeight: 1.7, color: '#8896A8', overflowX: 'auto', margin: 0 }}>
{`+-------------------------------------+
|  ARGUS AI THREAT ASSESSMENT         |`}
<span style={{color:'#CBD5E0'}}>{'|  User:  '}</span><span style={{color:'#93C5FD'}}>john</span>{'\n'}
<span style={{color:'#CBD5E0'}}>{'|  Time:  '}</span>{'2026-06-16 02:15:00\n'}
<span style={{color:'#CBD5E0'}}>{'|  Score: '}</span><span style={{color:'#E8890C',fontWeight:600}}>94</span><span style={{color:'#CBD5E0'}}>/100  </span><span style={{color:'#A78BFA',fontWeight:600}}>[CRITICAL]</span>{'\n'}
<span style={{color:'#CBD5E0'}}>{'+-------------------------------------+\n'}</span>
{`Contributing Factors:
  `}<span style={{color:'#F6AD55'}}>#1 (+35 pts)</span> <span style={{color:'#E2E8F0'}}>Login during night hours (00:00–05:00)</span>{'\n'}
{'  '}<span style={{color:'#F6AD55'}}>#2 (+30 pts)</span> <span style={{color:'#E2E8F0'}}>Large download: 5000 MB</span>{'\n'}
{'  '}<span style={{color:'#F6AD55'}}>#3 (+20 pts)</span> <span style={{color:'#E2E8F0'}}>Login from unrecognized IP</span>{'\n'}
{'  '}<span style={{color:'#F6AD55'}}>#4 (+20 pts)</span> <span style={{color:'#E2E8F0'}}>Login from unrecognized device</span>{'\n'}
{'  '}<span style={{color:'#F6AD55'}}>#5 (+15 pts)</span> <span style={{color:'#E2E8F0'}}>Download 4.2× above personal average</span>{'\n\n'}
{`Recommended Action:
  `}<span style={{color:'#68D391'}}>Escalate to security team — possible active threat</span>
            </pre>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, paddingTop: 64 }}>
          <p style={{ fontSize: 15, color: 'var(--text-2)', lineHeight: 1.7 }}>
            Argus AI never hands you a number without telling you why. Every scored event includes a ranked list of contributing factors so the analyst deciding whether to act has context, not just a score.
          </p>
          <p style={{ fontSize: 15, color: 'var(--text-2)', lineHeight: 1.7 }}>
            <strong style={{ color: 'var(--text)', fontWeight: 600 }}>No black boxes.</strong> The rule engine is deterministic and auditable. The statistical layer uses Welford's online algorithm — no stored event history, no periodic retraining job.
          </p>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 14 }}>
            {INSIGHTS.map(ins => (
              <li key={ins.title} style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                <div style={{ width: 28, height: 28, borderRadius: 4, background: 'var(--surface)', border: '1px solid var(--ground-2)', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 1 }}>
                  {ins.icon}
                </div>
                <span style={{ fontSize: 14, color: 'var(--text-2)', lineHeight: 1.55 }}>
                  <strong style={{ color: 'var(--text)', fontWeight: 600 }}>{ins.title}</strong> {ins.body}
                </span>
              </li>
            ))}
          </ul>
        </div>

      </div>
    </section>
  )
}

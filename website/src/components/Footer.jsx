export default function Footer() {
  return (
    <footer style={{ background: 'var(--text)', borderTop: '1px solid rgba(240,242,245,0.07)', padding: '32px 0' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
        <span style={{ fontFamily: "'Syne',system-ui,sans-serif", fontWeight: 800, fontSize: 15, letterSpacing: '-0.02em', color: 'rgba(240,242,245,0.5)' }}>ARGUS AI</span>
        <ul style={{ display: 'flex', gap: 24, listStyle: 'none', flexWrap: 'wrap' }}>
          {[
            ['https://github.com/yourname/argus', 'GitHub'],
            ['https://github.com/yourname/argus/blob/main/docs/architecture.md', 'Docs'],
            ['https://github.com/yourname/argus', 'API Reference'],
          ].map(([href, label]) => (
            <li key={label}>
              <a href={href} target="_blank" rel="noreferrer"
                style={{ fontSize: 12, color: 'rgba(240,242,245,0.35)', transition: 'color 0.15s', fontFamily: "'IBM Plex Mono',monospace", letterSpacing: '0.03em' }}
                onMouseEnter={e => e.target.style.color = 'var(--accent)'}
                onMouseLeave={e => e.target.style.color = 'rgba(240,242,245,0.35)'}
              >{label}</a>
            </li>
          ))}
        </ul>
        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: 'rgba(240,242,245,0.2)', letterSpacing: '0.05em' }}>MIT · Python 3.10+</span>
      </div>
    </footer>
  )
}

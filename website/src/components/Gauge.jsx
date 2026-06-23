import { useEffect, useRef } from 'react'

function levelName(s) {
  if (s >= 86) return 'CRITICAL'
  if (s >= 61) return 'HIGH'
  if (s >= 31) return 'MEDIUM'
  return 'LOW'
}

function levelClass(s) {
  return levelName(s).toLowerCase().replace('critical', 'crit')
}

const RISK_COLORS = { crit: '#7C3AED', high: '#DC2626', medium: '#D97706', low: '#16A34A' }

export default function Gauge() {
  const canvasRef  = useRef(null)
  const numberRef  = useRef(null)
  const levelRef   = useRef(null)
  const streamRef  = useRef(null)
  const stateRef   = useRef({ current: 0, target: 0, idx: 0 })

  const EVENTS = [
    { user: 'john',  desc: 'Night access (02:15)',    pts: 35, level: 'crit' },
    { user: 'sarah', desc: 'New device detected',     pts: 20, level: 'med'  },
    { user: 'mike',  desc: '1.2 GB download',         pts: 31, level: 'high' },
    { user: 'alice', desc: 'Off-hours login (19:42)', pts: 20, level: 'med'  },
    { user: 'john',  desc: '5000 MB · 600 files',     pts: 50, level: 'crit' },
    { user: 'admin', desc: 'Unrecognized IP address',  pts: 20, level: 'high' },
  ]

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const W = 260, H = 150, cx = 130, cy = 130, R = 105, SW = 14

    function draw(score) {
      ctx.clearRect(0, 0, W, H)
      const frac = Math.min(score / 100, 1)

      ctx.beginPath()
      ctx.arc(cx, cy, R, Math.PI, 0)
      ctx.strokeStyle = '#E3E6EB'
      ctx.lineWidth = SW
      ctx.lineCap = 'round'
      ctx.stroke()

      if (frac > 0) {
        const grad = ctx.createLinearGradient(cx - R, cy, cx + R, cy)
        grad.addColorStop(0,    '#16A34A')
        grad.addColorStop(0.35, '#D97706')
        grad.addColorStop(0.65, '#DC2626')
        grad.addColorStop(1,    '#7C3AED')
        ctx.beginPath()
        ctx.arc(cx, cy, R, Math.PI, Math.PI + Math.PI * frac)
        ctx.strokeStyle = grad
        ctx.lineWidth = SW
        ctx.lineCap = 'round'
        ctx.stroke()
      }

      for (let i = 0; i <= 10; i++) {
        const a = Math.PI + (Math.PI * i / 10)
        ctx.beginPath()
        ctx.moveTo(cx + (R + SW/2 + 6) * Math.cos(a), cy + (R + SW/2 + 6) * Math.sin(a))
        ctx.lineTo(cx + (R - SW/2 - 2) * Math.cos(a), cy + (R - SW/2 - 2) * Math.sin(a))
        ctx.strokeStyle = i % 3 === 0 ? '#8896A8' : '#C4CBD6'
        ctx.lineWidth   = i % 3 === 0 ? 1.5 : 1
        ctx.stroke()
      }

      ctx.font = '10px "IBM Plex Mono", monospace'
      ctx.fillStyle = '#8896A8'
      ctx.textAlign = 'center'
      ;[[0,'0'],[50,'50'],[100,'100']].forEach(([val, lbl]) => {
        const a = Math.PI + (Math.PI * val / 100)
        ctx.fillText(lbl, cx + (R + SW/2 + 18) * Math.cos(a), cy + (R + SW/2 + 18) * Math.sin(a) + 4)
      })
    }

    function animate() {
      const s = stateRef.current
      if (Math.abs(s.current - s.target) > 0.3) {
        s.current += (s.target - s.current) * 0.08
        draw(s.current)
        const score = Math.round(s.current)
        const lc    = levelClass(score)
        const color = RISK_COLORS[lc] || RISK_COLORS.low
        if (numberRef.current) {
          numberRef.current.textContent = score
          numberRef.current.style.color = color
        }
        if (levelRef.current) {
          levelRef.current.textContent = levelName(score)
          levelRef.current.style.color = color
        }
      }
      requestAnimationFrame(animate)
    }

    function addRow(ev) {
      const stream = streamRef.current
      if (!stream) return
      const now = new Date()
      const t = [now.getHours(), now.getMinutes(), now.getSeconds()]
        .map(n => String(n).padStart(2,'0')).join(':')
      const ptColors = { crit: '#7C3AED', high: '#DC2626', med: '#D97706' }

      const row = document.createElement('div')
      row.style.cssText = 'display:flex;align-items:baseline;gap:8px;font-family:"IBM Plex Mono",monospace;font-size:10.5px;line-height:1.5;opacity:0;transform:translateY(4px);animation:row-in 0.3s ease forwards'
      row.innerHTML =
        `<span style="color:var(--text-3);flex-shrink:0">${t}</span>` +
        `<span style="color:var(--accent-2,#2563EB);font-weight:600;flex-shrink:0">${ev.user}</span>` +
        `<span style="color:var(--text-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${ev.desc}</span>` +
        `<span style="margin-left:auto;flex-shrink:0;font-weight:600;color:${ptColors[ev.level]||'#D97706'}">+${ev.pts}</span>`
      stream.insertBefore(row, stream.firstChild)
      while (stream.children.length > 5) stream.removeChild(stream.lastChild)
    }

    function nextEvent() {
      const s  = stateRef.current
      const ev = EVENTS[s.idx++ % EVENTS.length]
      addRow(ev)
      s.target = Math.min(100, s.current + ev.pts)
      setTimeout(() => { s.target = Math.max(0, s.target - ev.pts - 5) }, ev.level === 'crit' ? 3200 : 2400)
      setTimeout(nextEvent, 1600 + Math.random() * 1200)
    }

    draw(0)
    animate()
    setTimeout(nextEvent, 800)
  }, [])

  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--ground-2)', borderRadius: 8, padding: '32px 28px 24px', width: '100%', maxWidth: 400, boxShadow: '0 2px 16px rgba(15,25,35,0.06)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-3)' }}>
          Risk Monitor — live
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', color: 'var(--risk-low)' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor', animation: 'pulse-dot 2s ease-in-out infinite' }} />
          WATCHING
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
        <canvas ref={canvasRef} width={260} height={150} style={{ display: 'block', margin: '0 auto' }} />
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, marginTop: -8 }}>
          <div ref={numberRef} style={{ fontFamily: "'Syne',system-ui,sans-serif", fontSize: 52, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1, color: 'var(--text)', transition: 'color 0.6s' }}>0</div>
          <div ref={levelRef}  style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-3)', transition: 'color 0.6s' }}>SCORING</div>
        </div>
      </div>

      <div ref={streamRef} style={{ marginTop: 20, borderTop: '1px solid var(--ground-2)', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 110, overflow: 'hidden' }} />
    </div>
  )
}

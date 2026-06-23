import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Github } from 'lucide-react'

function FloatingParticles() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let W = canvas.offsetWidth
    let H = canvas.offsetHeight
    canvas.width  = W
    canvas.height = H

    const particles = Array.from({ length: 55 }, () => ({
      x:   Math.random() * W,
      y:   Math.random() * H,
      r:   Math.random() * 1.5 + 0.4,
      vx:  (Math.random() - 0.5) * 0.3,
      vy:  (Math.random() - 0.5) * 0.3,
      a:   Math.random() * 0.5 + 0.15,
    }))

    let raf
    function draw() {
      ctx.clearRect(0, 0, W, H)
      for (const p of particles) {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(124,58,237,${p.a})`
        ctx.fill()
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0) p.x = W
        if (p.x > W) p.x = 0
        if (p.y < 0) p.y = H
        if (p.y > H) p.y = 0
      }
      raf = requestAnimationFrame(draw)
    }
    draw()

    const onResize = () => {
      W = canvas.offsetWidth; H = canvas.offsetHeight
      canvas.width = W; canvas.height = H
    }
    window.addEventListener('resize', onResize)
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', onResize) }
  }, [])

  return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />
}

export default function Hero() {
  const scrollToDemo = () => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })

  return (
    <section
      className="relative min-h-[92vh] flex items-center justify-center overflow-hidden hero-grid"
      style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)' }}
    >
      <FloatingParticles />

      <div className="relative z-10 max-w-4xl mx-auto px-6 py-24 flex flex-col items-center text-center gap-8">
        {/* Label pill */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 border border-white/20 rounded-full px-4 py-1.5 text-white/80 text-sm font-medium"
        >
          👁️ AI-Powered Insider Threat Detection
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-5xl md:text-7xl font-black text-white leading-[1.05] tracking-tight"
        >
          Detect threats before<br />
          <span className="text-argus-500">they become breaches.</span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-lg md:text-xl text-gray-300 max-w-2xl leading-relaxed"
        >
          Argus continuously monitors user behavior, learns what normal looks like,
          and alerts your team the moment something changes.
          Built for developers. Deployable in minutes.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center gap-4"
        >
          <button
            onClick={scrollToDemo}
            className="inline-flex items-center gap-2 px-6 py-3.5 bg-argus-500 hover:bg-argus-600
              text-white font-semibold rounded-xl text-base transition-colors shadow-lg shadow-argus-500/25"
          >
            Try Live Demo <ArrowRight size={18} />
          </button>
          <a
            href="https://github.com/yourname/argus"
            target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3.5 border border-white/30 hover:border-white/60
              text-white font-semibold rounded-xl text-base transition-colors"
          >
            <Github size={18} /> View on GitHub
          </a>
        </motion.div>

        {/* Stat pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.45 }}
          className="flex flex-wrap justify-center gap-3 mt-2"
        >
          {['81 Tests Passing', 'Zero Dependencies (core)', 'MIT License'].map(s => (
            <span key={s}
              className="px-3.5 py-1.5 rounded-full bg-white/10 text-white/70 text-xs font-medium border border-white/10">
              {s}
            </span>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

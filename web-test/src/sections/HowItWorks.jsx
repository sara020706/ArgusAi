import { useEffect, useRef, useState } from 'react'
import { Activity, Cpu, Layers, ShieldCheck, ArrowRight } from 'lucide-react'
import SectionHeader from '../components/SectionHeader'

const STEPS = [
  {
    icon: Activity,
    title: 'Event Received',
    desc: 'A user logs in, downloads a file, or accesses a resource. Your app sends one event to Argus.',
  },
  {
    icon: Cpu,
    title: 'Feature Extraction',
    desc: 'Login time, IP history, download size vs. personal average, device recognition — converted to a feature vector.',
  },
  {
    icon: Layers,
    title: 'Three-Layer Scoring',
    desc: 'Hard rules catch obvious threats. Z-score statistics catch personal deviations. Isolation Forest catches subtle patterns.',
  },
  {
    icon: ShieldCheck,
    title: 'Score + Explanation',
    desc: 'Every event gets a 0–100 risk score with a human-readable breakdown of exactly why — not a black box.',
  },
]

const TERMINAL_TEXT = `+-------------------------------------+
|  ARGUS THREAT ASSESSMENT            |
|  User: john                         |
|  Time: 2026-06-16 02:15:00          |
|  Risk Score: 94/100 [CRITICAL]      |
+-------------------------------------+

Contributing Factors:
  #1 (+35 pts) Login during night hours (00:00-05:00)
  #2 (+30 pts) Large download: 5000 MB (threshold: 1000 MB)
  #3 (+20 pts) Login from unrecognized IP address
  #4 (+20 pts) Login from unrecognized device
  #5 (+15 pts) Download 4.2x above personal average

Recommended Action: Escalate to security team - possible active threat`

function TypingTerminal() {
  const [displayed, setDisplayed] = useState('')
  const [done, setDone]           = useState(false)
  const idx = useRef(0)
  const ref = useRef(null)
  const started = useRef(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true
          const interval = setInterval(() => {
            idx.current++
            setDisplayed(TERMINAL_TEXT.slice(0, idx.current))
            if (idx.current >= TERMINAL_TEXT.length) {
              clearInterval(interval)
              setDone(true)
            }
          }, 14)
        }
      },
      { threshold: 0.3 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={ref}
      className="rounded-xl bg-gray-950 border border-gray-800 overflow-hidden shadow-2xl">
      {/* Terminal chrome */}
      <div className="flex items-center gap-1.5 px-4 py-3 border-b border-gray-800 bg-gray-900">
        <span className="w-3 h-3 rounded-full bg-red-500/80" />
        <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
        <span className="w-3 h-3 rounded-full bg-green-500/80" />
        <span className="ml-3 text-xs text-gray-500 font-mono">argus output</span>
      </div>
      <pre className={`p-5 text-sm font-mono text-green-400 leading-relaxed whitespace-pre overflow-x-auto
        ${!done ? 'typing-cursor' : ''}`}>
        {displayed}
      </pre>
    </div>
  )
}

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-white py-24">
      <div className="max-w-6xl mx-auto px-6">
        <SectionHeader
          label="How It Works"
          title="From raw event to risk score in milliseconds"
          subtitle="A four-stage pipeline runs every time a user does anything in your system."
        />

        {/* Steps */}
        <div className="flex flex-col md:flex-row items-start gap-0 mb-16">
          {STEPS.map((step, i) => {
            const Icon = step.icon
            return (
              <div key={i} className="flex flex-col md:flex-row items-center flex-1 min-w-0">
                <div className="flex flex-col items-center text-center px-4 flex-1">
                  <div className="w-12 h-12 rounded-2xl bg-argus-50 flex items-center justify-center mb-4">
                    <Icon size={22} className="text-argus-500" />
                  </div>
                  <div className="w-7 h-7 rounded-full bg-argus-500 text-white text-xs font-bold
                    flex items-center justify-center mb-3">
                    {i + 1}
                  </div>
                  <h3 className="font-bold text-gray-900 mb-2">{step.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed max-w-[200px]">{step.desc}</p>
                </div>
                {i < STEPS.length - 1 && (
                  <ArrowRight size={20} className="text-gray-300 flex-shrink-0 rotate-90 md:rotate-0 my-4 md:my-0" />
                )}
              </div>
            )
          })}
        </div>

        {/* Terminal */}
        <TypingTerminal />
      </div>
    </section>
  )
}

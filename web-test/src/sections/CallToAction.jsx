import { useState } from 'react'
import { Check } from 'lucide-react'

const DEPLOYMENT_OPTIONS = [
  { cmd: 'pip install argus',         label: 'Python package' },
  { cmd: 'docker-compose up',          label: 'Full stack'      },
  { cmd: 'argus-serve --port 8000',   label: 'API only'        },
]

export default function CallToAction() {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText('pip install argus').catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section className="py-24" style={{ background: '#0f172a' }}>
      <div className="max-w-4xl mx-auto px-6 flex flex-col items-center text-center gap-8">
        <h2 className="text-4xl md:text-5xl font-black text-white leading-tight">
          Ready to protect your organization?
        </h2>
        <p className="text-lg text-gray-300 max-w-xl leading-relaxed">
          Argus is open source, MIT licensed, and deployable in under 5 minutes with Docker.
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-4">
          <button onClick={handleCopy}
            className="inline-flex items-center gap-2.5 px-6 py-3.5 bg-argus-500 hover:bg-argus-600
              text-white font-semibold rounded-xl transition-colors font-mono text-sm">
            {copied ? <><Check size={16} /> Copied!</> : 'pip install argus'}
          </button>
          <a href="https://github.com/yourname/argus/blob/main/docs/architecture.md"
            target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3.5 border border-white/30
              hover:border-white/60 text-white font-semibold rounded-xl transition-colors text-sm">
            Read the Docs →
          </a>
        </div>

        {/* Deployment options */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full mt-4">
          {DEPLOYMENT_OPTIONS.map(opt => (
            <div key={opt.cmd}
              className="flex flex-col items-center gap-2 px-5 py-4 rounded-2xl
                bg-white/5 border border-white/10">
              <code className="font-mono text-sm text-argus-500 font-semibold">{opt.cmd}</code>
              <span className="text-xs text-gray-400">{opt.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

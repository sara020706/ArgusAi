import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react'
import SectionHeader from '../components/SectionHeader'
import RiskBadge from '../components/RiskBadge'
import ScoreGauge from '../components/ScoreGauge'
import { useArgusScore } from '../hooks/useArgusScore'

const PRESETS = {
  night: {
    label: '😴 Night Threat',
    data: {
      user_id: 'john', ip: '185.45.67.10', device_id: 'unknown-device-44',
      download_mb: 5000, files_accessed: 600, action: 'download',
      timestamp: (() => { const d = new Date(); d.setHours(2,15,0,0); return d.toISOString().slice(0,16) })(),
    },
  },
  normal: {
    label: '✅ Normal User',
    data: {
      user_id: 'alice', ip: '192.168.1.10', device_id: 'laptop-01',
      download_mb: 45, files_accessed: 12, action: 'login',
      timestamp: (() => { const d = new Date(); d.setHours(9,30,0,0); return d.toISOString().slice(0,16) })(),
    },
  },
  exfil: {
    label: '🔥 Data Exfil',
    data: {
      user_id: 'admin', ip: '91.108.4.0', device_id: 'unknown-server-99',
      download_mb: 9800, files_accessed: 950, action: 'download',
      timestamp: (() => { const d = new Date(); d.setHours(3,0,0,0); return d.toISOString().slice(0,16) })(),
    },
  },
}

function defaultTimestamp() {
  const d = new Date()
  d.setHours(2, 15, 0, 0)
  return d.toISOString().slice(0, 16)
}

function ContributionBar({ reason, points, maxPoints }) {
  const width = Math.round((points / maxPoints) * 100)
  const color =
    points >= 30 ? 'bg-red-400' :
    points >= 20 ? 'bg-amber-400' :
    'bg-blue-400'

  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="flex-1 min-w-0">
        <div className="text-sm text-gray-700 truncate" title={reason}>{reason}</div>
        <div className="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${color}`}
            initial={{ width: 0 }}
            animate={{ width: `${width}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        </div>
      </div>
      <span className="text-xs font-semibold text-gray-500 flex-shrink-0">+{Math.round(points)} pts</span>
    </div>
  )
}

function ScoreResult({ result }) {
  const [expanded, setExpanded] = useState(false)

  const allContributions = {
    ...result.rule_contributions,
    ...result.stat_contributions,
  }
  const maxPts = Math.max(...Object.values(allContributions), 1)

  const reasons = result.reasons ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-center gap-2">
        <ScoreGauge score={result.risk_score} level={result.risk_level} size={180} />
        <RiskBadge level={result.risk_level} size="md" />
      </div>

      {reasons.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Contributing Factors</h4>
          <div className="flex flex-col divide-y divide-gray-50">
            {reasons.map((r, i) => {
              const pts = Object.values(allContributions)[i] ?? 10
              return (
                <ContributionBar key={i} reason={r} points={pts} maxPoints={maxPts} />
              )
            })}
          </div>
        </div>
      )}

      {/* Raw details collapsible */}
      <div className="border border-gray-100 rounded-xl overflow-hidden">
        <button
          onClick={() => setExpanded(e => !e)}
          className="w-full flex items-center justify-between px-4 py-3
            text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Raw Details
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        {expanded && (
          <div className="px-4 pb-4 text-xs font-mono text-gray-500 bg-gray-50 border-t border-gray-100">
            <div className="mt-3 space-y-1">
              <div className="font-semibold text-gray-600 mb-1">Rules:</div>
              {Object.entries(result.rule_contributions ?? {}).map(([k, v]) => (
                <div key={k}>{k}: <span className="text-gray-900">{typeof v === 'number' ? v.toFixed(1) : JSON.stringify(v)}</span></div>
              ))}
              <div className="font-semibold text-gray-600 mt-2 mb-1">Stats:</div>
              {Object.entries(result.stat_contributions ?? {}).map(([k, v]) => (
                <div key={k}>{k}: <span className="text-gray-900">{typeof v === 'number' ? v.toFixed(1) : JSON.stringify(v)}</span></div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function EmptyResult() {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[300px] gap-4
      border-2 border-dashed border-gray-200 rounded-2xl p-8 text-center">
      <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center text-2xl">👁️</div>
      <p className="text-gray-400 text-sm leading-relaxed max-w-[240px]">
        Fill in the form and click <strong>Score This Event</strong> to see Argus analyze this event.
      </p>
    </div>
  )
}

export default function LiveDemo() {
  const { result, loading, error, apiOnline, score } = useArgusScore()

  const [form, setForm] = useState({
    user_id: 'john', ip: '185.45.67.10', device_id: 'unknown-device-44',
    download_mb: 5000, files_accessed: 600, action: 'download',
    timestamp: defaultTimestamp(),
  })

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }
  function applyPreset(key) { setForm(PRESETS[key].data) }

  function handleSubmit(e) {
    e.preventDefault()
    score({
      user_id:        form.user_id,
      timestamp:      form.timestamp + ':00',
      ip:             form.ip,
      device_id:      form.device_id,
      download_mb:    Number(form.download_mb),
      files_accessed: Number(form.files_accessed),
      action:         form.action,
    })
  }

  const inputCls = `w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm
    focus:outline-none focus:ring-2 focus:ring-argus-500/30 focus:border-argus-500 transition-colors`

  return (
    <section id="demo" className="bg-white py-24">
      <div className="max-w-6xl mx-auto px-6">
        <SectionHeader
          label="Live Demo"
          title="Score a user event right now"
          subtitle="Adjust the fields below and see how Argus scores the behavior in real time."
        />

        {apiOnline === false && (
          <div className="flex items-center gap-3 mb-8 px-4 py-3.5 bg-amber-50 border border-amber-200
            rounded-xl text-sm text-amber-700">
            <AlertTriangle size={18} className="flex-shrink-0" />
            Argus API is offline. Start it with <code className="font-mono bg-amber-100 px-1 rounded">argus-serve --port 8000</code> to enable live scoring.
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {/* Presets */}
            <div className="flex flex-wrap gap-2">
              {Object.entries(PRESETS).map(([k, p]) => (
                <button key={k} type="button" onClick={() => applyPreset(k)}
                  className="px-3.5 py-1.5 border border-gray-200 hover:border-argus-500 hover:text-argus-600
                    rounded-lg text-sm font-medium text-gray-600 transition-colors">
                  {p.label}
                </button>
              ))}
            </div>

            {/* Fields */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">User ID</label>
                <input className={inputCls} value={form.user_id}
                  onChange={e => set('user_id', e.target.value)} placeholder="john" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">IP Address</label>
                <input className={inputCls} value={form.ip}
                  onChange={e => set('ip', e.target.value)} placeholder="185.45.67.10" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Device ID</label>
                <input className={inputCls} value={form.device_id}
                  onChange={e => set('device_id', e.target.value)} placeholder="unknown-device-44" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Timestamp</label>
                <input type="datetime-local" className={inputCls} value={form.timestamp}
                  onChange={e => set('timestamp', e.target.value)} />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">
                Download (MB) — <span className="text-argus-500 font-bold">{form.download_mb} MB</span>
              </label>
              <input type="range" min={0} max={10000} step={50}
                value={form.download_mb}
                onChange={e => set('download_mb', e.target.value)}
                className="w-full accent-argus-500 mb-2" />
              <input type="number" className={inputCls} value={form.download_mb} min={0} max={10000}
                onChange={e => set('download_mb', e.target.value)} />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">
                Files Accessed — <span className="text-argus-500 font-bold">{form.files_accessed}</span>
              </label>
              <input type="range" min={0} max={1000} step={5}
                value={form.files_accessed}
                onChange={e => set('files_accessed', e.target.value)}
                className="w-full accent-argus-500 mb-2" />
              <input type="number" className={inputCls} value={form.files_accessed} min={0} max={1000}
                onChange={e => set('files_accessed', e.target.value)} />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Action</label>
              <select className={inputCls} value={form.action} onChange={e => set('action', e.target.value)}>
                <option value="login">login</option>
                <option value="download">download</option>
                <option value="file_access">file_access</option>
                <option value="logout">logout</option>
              </select>
            </div>

            <button type="submit" disabled={loading || apiOnline === false}
              className="flex items-center justify-center gap-2 py-3.5 px-6 bg-argus-500
                hover:bg-argus-600 disabled:opacity-50 disabled:cursor-not-allowed
                text-white font-semibold rounded-xl transition-colors text-base">
              {loading ? <><Loader2 size={18} className="animate-spin" /> Scoring…</> : 'Score This Event →'}
            </button>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
          </form>

          {/* Result panel */}
          <div className="flex flex-col">
            <AnimatePresence mode="wait">
              {result ? (
                <motion.div key="result"
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={{ duration: 0.35 }}>
                  <ScoreResult result={result} />
                </motion.div>
              ) : (
                <motion.div key="empty"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
                  <EmptyResult />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  )
}

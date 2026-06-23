import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Radio } from 'lucide-react'
import SectionHeader from '../components/SectionHeader'
import RiskBadge from '../components/RiskBadge'
import { useAlertFeed } from '../hooks/useAlertFeed'
import { useArgusScore } from '../hooks/useArgusScore'

const BORDER_COLOR = {
  CRITICAL: 'border-l-purple-500',
  HIGH:     'border-l-red-500',
  MEDIUM:   'border-l-amber-500',
  LOW:      'border-l-green-500',
}

function timeAgo(isoStr) {
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000
  if (diff < 60)  return `${Math.round(diff)}s ago`
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`
  return `${Math.round(diff / 3600)}h ago`
}

function AlertCard({ alert }) {
  const [expanded, setExpanded] = useState(false)
  const border = BORDER_COLOR[alert.risk_level] ?? 'border-l-gray-300'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.3 }}
      className={`bg-white rounded-xl border border-gray-100 border-l-4 ${border}
        shadow-sm hover:shadow-md transition-shadow cursor-pointer overflow-hidden`}
      onClick={() => setExpanded(e => !e)}
    >
      <div className="flex items-center gap-4 px-5 py-4">
        <RiskBadge level={alert.risk_level} size="sm" />
        <span className="font-semibold text-gray-900 text-sm flex-shrink-0">{alert.user_id}</span>
        <span className="text-sm text-gray-500 flex-1 truncate min-w-0">
          {alert.reasons?.[0] ?? 'Anomalous behavior detected'}
        </span>
        <span className="text-sm font-bold text-gray-700 flex-shrink-0">
          {Math.round(alert.risk_score)}<span className="font-normal text-gray-400">/100</span>
        </span>
        <span className="text-xs text-gray-400 flex-shrink-0">{timeAgo(alert.timestamp)}</span>
      </div>

      <AnimatePresence>
        {expanded && alert.reasons?.length > 1 && (
          <motion.div
            initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-gray-100 bg-gray-50 px-5 py-3"
          >
            <ul className="space-y-1">
              {alert.reasons.map((r, i) => (
                <li key={i} className="text-xs text-gray-600 flex items-start gap-2">
                  <span className="text-argus-500 font-bold flex-shrink-0">•</span>{r}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function AlertFeed() {
  const { apiOnline } = useArgusScore()
  const { alerts, isLive } = useAlertFeed(apiOnline)

  return (
    <section className="bg-gray-50 py-24">
      <div className="max-w-6xl mx-auto px-6">
        <SectionHeader
          label="Live Alert Feed"
          title="Real-time threat activity"
          subtitle="Every scored event above MEDIUM threshold appears here instantly."
        />

        {!isLive && (
          <div className="flex items-center gap-2 mb-6 px-4 py-2.5 bg-amber-50 border border-amber-200
            rounded-lg text-sm text-amber-700">
            <Radio size={16} className="flex-shrink-0 animate-pulse" />
            Demo Mode — connect Argus API for live data
          </div>
        )}
        {isLive && (
          <div className="flex items-center gap-2 mb-6 px-4 py-2.5 bg-green-50 border border-green-200
            rounded-lg text-sm text-green-700">
            <Radio size={16} className="flex-shrink-0 animate-pulse" />
            Live Mode — showing real alerts from Argus API
          </div>
        )}

        <div className="flex flex-col gap-3">
          <AnimatePresence initial={false}>
            {alerts.length === 0 ? (
              <motion.div key="empty"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="text-center py-16 text-gray-400 text-sm">
                Waiting for alerts…
              </motion.div>
            ) : (
              alerts.map(alert => (
                <AlertCard key={alert.id ?? alert.timestamp} alert={alert} />
              ))
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  )
}

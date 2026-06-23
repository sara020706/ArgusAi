const RISK_CONFIG = {
  LOW:      { bg: 'bg-green-100',  text: 'text-green-700',  dot: 'bg-green-500'  },
  MEDIUM:   { bg: 'bg-amber-100',  text: 'text-amber-700',  dot: 'bg-amber-500'  },
  HIGH:     { bg: 'bg-red-100',    text: 'text-red-700',    dot: 'bg-red-500'    },
  CRITICAL: { bg: 'bg-purple-100', text: 'text-purple-700', dot: 'bg-purple-500' },
}

export default function RiskBadge({ level, size = 'md' }) {
  const cfg = RISK_CONFIG[level] ?? RISK_CONFIG.LOW
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-xs px-2.5 py-1'
  const dotSize   = size === 'sm' ? 'w-1.5 h-1.5' : 'w-1.5 h-1.5'

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold ${sizeClass} ${cfg.bg} ${cfg.text}`}>
      <span className={`${dotSize} rounded-full ${cfg.dot}`} />
      {level}
    </span>
  )
}

import { useEffect, useState } from 'react'

function scoreColor(score) {
  if (score <= 30) return '#22c55e'
  if (score <= 60) return '#f59e0b'
  if (score <= 85) return '#ef4444'
  return '#7c3aed'
}

export default function ScoreGauge({ score = 0, level = 'LOW', size = 200 }) {
  const [animated, setAnimated] = useState(0)

  useEffect(() => {
    setAnimated(0)
    const raf = requestAnimationFrame(() => {
      setTimeout(() => setAnimated(score), 30)
    })
    return () => cancelAnimationFrame(raf)
  }, [score])

  const cx = size / 2
  const cy = size / 2
  const r  = (size / 2) - 18
  // Semicircle: from 180° (left) to 0° (right), sweeping through bottom
  const startAngle = Math.PI        // left
  const endAngle   = 0              // right
  const totalArc   = Math.PI        // 180°

  const fraction = Math.min(Math.max(animated / 100, 0), 1)
  const arcAngle  = fraction * totalArc

  // Arc runs from left (180°) clockwise to right (0°)
  // SVG angles: 0 = right, increases clockwise
  // Start: 180° = left  → SVG angle = π
  // End after fraction:  angle = π - arcAngle  (moving toward 0)
  const sx = cx + r * Math.cos(startAngle)
  const sy = cy + r * Math.sin(startAngle)
  const ex = cx + r * Math.cos(startAngle - arcAngle)
  const ey = cy + r * Math.sin(startAngle - arcAngle)

  const largeArc = arcAngle > Math.PI ? 1 : 0

  // Background arc (full semicircle)
  const bgEx = cx + r * Math.cos(0)
  const bgEy = cy + r * Math.sin(0)

  const color = scoreColor(score)
  const strokeW = size * 0.075

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size * 0.62} viewBox={`0 0 ${size} ${size * 0.62}`}>
        {/* Background track */}
        <path
          d={`M ${sx} ${sy} A ${r} ${r} 0 0 1 ${bgEx} ${bgEy}`}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeW}
          strokeLinecap="round"
        />
        {/* Filled arc */}
        {animated > 0 && (
          <path
            d={`M ${sx} ${sy} A ${r} ${r} 0 ${largeArc} 1 ${ex} ${ey}`}
            fill="none"
            stroke={color}
            strokeWidth={strokeW}
            strokeLinecap="round"
            style={{ transition: 'all 0.8s cubic-bezier(0.4,0,0.2,1)' }}
          />
        )}
        {/* Score number */}
        <text
          x={cx}
          y={size * 0.48}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={size * 0.22}
          fontWeight="800"
          fontFamily="Inter, system-ui, sans-serif"
          fill={color}
          style={{ transition: 'fill 0.5s' }}
        >
          {Math.round(animated)}
        </text>
      </svg>
      <div className="text-sm font-medium text-gray-500 -mt-1">/ 100</div>
    </div>
  )
}

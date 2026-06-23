import { useState } from 'react'
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps'
import SectionHeader from '../components/SectionHeader'
import { useThreatMap } from '../hooks/useThreatMap'
import { useArgusScore } from '../hooks/useArgusScore'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

const RISK_COLORS = {
  LOW:      '#22c55e',
  MEDIUM:   '#f59e0b',
  HIGH:     '#ef4444',
  CRITICAL: '#7c3aed',
}

function markerRadius(score) {
  return 4 + (score / 100) * 10
}

function ThreatMarker({ point }) {
  const [hovered, setHovered] = useState(false)
  const color  = RISK_COLORS[point.level] ?? RISK_COLORS.LOW
  const radius = markerRadius(point.score)

  return (
    <Marker coordinates={[point.lon, point.lat]}>
      {/* Pulse ring */}
      <circle
        r={radius + 4}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        opacity={0.35}
        style={{
          animation: 'pulse-ring-svg 2s ease-out infinite',
          transformOrigin: 'center',
          transformBox: 'fill-box',
        }}
      />
      {/* Main dot */}
      <circle
        r={radius}
        fill={color}
        fillOpacity={0.85}
        stroke="#fff"
        strokeWidth={1.5}
        style={{ cursor: 'pointer' }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />
      {/* Tooltip */}
      {hovered && (
        <g>
          <rect x={radius + 6} y={-22} width={130} height={46} rx={5} fill="#1e293b" />
          <text x={radius + 12} y={-7} fontSize={10} fill="#f1f5f9" fontFamily="Inter, sans-serif" fontWeight="600">
            {point.user} · {point.level}
          </text>
          <text x={radius + 12} y={8} fontSize={9} fill="#94a3b8" fontFamily="Inter, sans-serif">
            Score: {point.score} · {point.city}
          </text>
        </g>
      )}
    </Marker>
  )
}

export default function ThreatMap() {
  const { apiOnline } = useArgusScore()
  const { points }    = useThreatMap(apiOnline)

  return (
    <section className="bg-white py-24">
      <div className="max-w-6xl mx-auto px-6">
        <SectionHeader
          label="Threat Map"
          title="Where are threats coming from?"
          subtitle="IP geolocation of flagged login attempts across your organization."
        />

        <div className="rounded-2xl border border-gray-100 shadow-sm overflow-hidden bg-[#f8fafc]">
          <style>{`
            @keyframes pulse-ring-svg {
              0%   { r: 0; opacity: 0.6; }
              100% { r: 18; opacity: 0; }
            }
          `}</style>
          <ComposableMap
            projection="geoMercator"
            projectionConfig={{ scale: 130, center: [10, 20] }}
            style={{ width: '100%', height: '450px' }}
          >
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map(geo => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#e5e7eb"
                    stroke="#d1d5db"
                    strokeWidth={0.5}
                    style={{
                      default: { outline: 'none' },
                      hover:   { fill: '#d1d5db', outline: 'none' },
                      pressed: { outline: 'none' },
                    }}
                  />
                ))
              }
            </Geographies>

            {points.map((p, i) => (
              <ThreatMarker key={i} point={p} />
            ))}
          </ComposableMap>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-6 mt-5 justify-center">
          {Object.entries(RISK_COLORS).map(([level, color]) => (
            <div key={level} className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: color }} />
              <span className="text-sm text-gray-600">{level}</span>
            </div>
          ))}
          <span className="text-xs text-gray-400 ml-2">
            Marker size indicates risk score. Connect Argus API for live threat data.
          </span>
        </div>
      </div>
    </section>
  )
}

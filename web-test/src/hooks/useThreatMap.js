import { useEffect, useState } from 'react'
import { getAlerts } from '../api/argus'

const IP_TO_LOCATION = {
  '185.45.67.10':  { lat: 55.7558,  lon: 37.6173,  city: 'Moscow'       },
  '103.21.244.0':  { lat: 1.3521,   lon: 103.8198, city: 'Singapore'    },
  '91.108.4.0':    { lat: 52.5200,  lon: 13.4050,  city: 'Berlin'       },
  '45.142.212.0':  { lat: 48.8566,  lon: 2.3522,   city: 'Paris'        },
  '185.220.101.0': { lat: 50.1109,  lon: 8.6821,   city: 'Frankfurt'    },
  '104.21.0.0':    { lat: 37.7749,  lon: -122.4194, city: 'San Francisco'},
  '198.51.100.0':  { lat: 51.5074,  lon: -0.1278,  city: 'London'       },
  '203.0.113.0':   { lat: 35.6762,  lon: 139.6503, city: 'Tokyo'        },
  '192.0.2.0':     { lat: -33.8688, lon: 151.2093, city: 'Sydney'       },
  '5.188.206.0':   { lat: 59.9139,  lon: 10.7522,  city: 'Oslo'         },
  '185.176.26.0':  { lat: 55.6761,  lon: 12.5683,  city: 'Copenhagen'   },
  '62.210.0.0':    { lat: 48.2082,  lon: 16.3738,  city: 'Vienna'       },
}

const DEMO_POINTS = [
  { lat: 51.5074,  lon: -0.1278,  level: 'HIGH',     user: 'john',   score: 78,  city: 'London'        },
  { lat: 40.7128,  lon: -74.006,  level: 'MEDIUM',   user: 'alice',  score: 45,  city: 'New York'      },
  { lat: 35.6762,  lon: 139.6503, level: 'CRITICAL', user: 'admin',  score: 94,  city: 'Tokyo'         },
  { lat: 55.7558,  lon: 37.6173,  level: 'HIGH',     user: 'mike',   score: 71,  city: 'Moscow'        },
  { lat: 19.0760,  lon: 72.8777,  level: 'MEDIUM',   user: 'bob',    score: 38,  city: 'Mumbai'        },
  { lat: -33.8688, lon: 151.2093, level: 'LOW',      user: 'sarah',  score: 12,  city: 'Sydney'        },
]

const FALLBACK_CITIES = [
  { lat: 48.8566,  lon: 2.3522,   city: 'Paris'     },
  { lat: 52.5200,  lon: 13.4050,  city: 'Berlin'    },
  { lat: 41.9028,  lon: 12.4964,  city: 'Rome'      },
  { lat: 31.2304,  lon: 121.4737, city: 'Shanghai'  },
  { lat: -23.5505, lon: -46.6333, city: 'São Paulo' },
]

function ipToCoords(ip) {
  if (!ip) return null
  // Exact match
  if (IP_TO_LOCATION[ip]) return IP_TO_LOCATION[ip]
  // Prefix match (first three octets)
  const prefix = ip.split('.').slice(0, 3).join('.')
  const match = Object.entries(IP_TO_LOCATION).find(([k]) => k.startsWith(prefix))
  if (match) return match[1]
  // Hash-based fallback to a world city
  const sum = ip.split('.').reduce((acc, oct) => acc + parseInt(oct || 0, 10), 0)
  return FALLBACK_CITIES[sum % FALLBACK_CITIES.length]
}

export function useThreatMap(apiOnline) {
  const [points, setPoints] = useState(DEMO_POINTS)

  useEffect(() => {
    if (!apiOnline) {
      setPoints(DEMO_POINTS)
      return
    }
    async function fetch() {
      const alerts = await getAlerts(50, 'LOW')
      if (!alerts.length) return
      const mapped = alerts
        .map(a => {
          const coords = ipToCoords(a.ip)
          if (!coords) return null
          return {
            lat:   coords.lat,
            lon:   coords.lon,
            city:  coords.city ?? a.ip,
            level: a.risk_level,
            user:  a.user_id,
            score: a.risk_score,
          }
        })
        .filter(Boolean)
      if (mapped.length) setPoints(mapped)
    }
    fetch()
    const id = setInterval(fetch, 15000)
    return () => clearInterval(id)
  }, [apiOnline])

  return { points }
}

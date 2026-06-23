import { useEffect, useRef, useState } from 'react'
import { getAlerts } from '../api/argus'

const FAKE_USERS   = ['alice', 'bob', 'john', 'sarah', 'mike', 'admin']
const FAKE_REASONS = [
  'Login during night hours (00:00–05:00)',
  'Large download: {N} MB',
  'Login from unrecognized IP address',
  'Login from unrecognized device',
  'Download {N}x above personal average',
  'Pattern: slow exfiltration detected',
  'Pattern: account takeover indicators',
  'IP flagged as suspicious (AbuseIPDB)',
]
const RISK_LEVELS = ['MEDIUM', 'MEDIUM', 'HIGH', 'HIGH', 'CRITICAL']

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function fakeReason() {
  const r = FAKE_REASONS[randomInt(0, FAKE_REASONS.length - 1)]
  return r.replace('{N}', randomInt(2, 50))
}

function generateFakeAlert() {
  const level = RISK_LEVELS[randomInt(0, RISK_LEVELS.length - 1)]
  const scoreMap = { MEDIUM: randomInt(31, 60), HIGH: randomInt(61, 85), CRITICAL: randomInt(86, 100) }
  return {
    id:         `fake-${Date.now()}-${Math.random()}`,
    user_id:    FAKE_USERS[randomInt(0, FAKE_USERS.length - 1)],
    risk_level: level,
    risk_score: scoreMap[level],
    reasons:    [fakeReason(), fakeReason()].slice(0, randomInt(1, 2)),
    timestamp:  new Date().toISOString(),
  }
}

export function useAlertFeed(apiOnline) {
  const [alerts, setAlerts] = useState([])
  const seenIds = useRef(new Set())

  // Real API polling
  useEffect(() => {
    if (!apiOnline) return
    async function poll() {
      const data = await getAlerts(20, 'MEDIUM')
      if (!data.length) return
      setAlerts(prev => {
        const newOnes = data.filter(a => !seenIds.current.has(a.id ?? a.timestamp))
        newOnes.forEach(a => seenIds.current.add(a.id ?? a.timestamp))
        if (!newOnes.length) return prev
        return [...newOnes, ...prev].slice(0, 15)
      })
    }
    poll()
    const id = setInterval(poll, 5000)
    return () => clearInterval(id)
  }, [apiOnline])

  // Fake data when offline
  useEffect(() => {
    if (apiOnline) return

    // Seed with a few initial fake alerts
    const initial = Array.from({ length: 5 }, generateFakeAlert)
    setAlerts(initial)

    const id = setInterval(() => {
      setAlerts(prev => [generateFakeAlert(), ...prev].slice(0, 15))
    }, 3000)
    return () => clearInterval(id)
  }, [apiOnline])

  return { alerts, isLive: !!apiOnline }
}

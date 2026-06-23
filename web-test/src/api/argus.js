const BASE_URL = import.meta.env.VITE_ARGUS_API_URL ?? 'http://localhost:8000'

async function fetchWithTimeout(url, options = {}, timeoutMs = 5000) {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url, { ...options, signal: controller.signal })
    clearTimeout(id)
    return res
  } catch (err) {
    clearTimeout(id)
    throw err
  }
}

export async function scoreEvent(eventData) {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/v1/events/score`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(eventData),
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function getAlerts(limit = 20, minRiskLevel = 'LOW') {
  try {
    const res = await fetchWithTimeout(
      `${BASE_URL}/v1/alerts?limit=${limit}&min_risk_level=${minRiskLevel}`
    )
    if (!res.ok) return []
    return await res.json()
  } catch {
    return []
  }
}

export async function getAlertStats() {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/v1/alerts/stats`)
    if (!res.ok) return {}
    return await res.json()
  } catch {
    return {}
  }
}

export async function getHealth() {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/health`, {}, 3000)
    if (!res.ok) return { status: 'unreachable' }
    return await res.json()
  } catch {
    return { status: 'unreachable' }
  }
}

export async function getMetrics() {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/metrics`)
    if (!res.ok) return {}
    return await res.json()
  } catch {
    return {}
  }
}

export async function getUserProfile(userId) {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/v1/users/${encodeURIComponent(userId)}/profile`)
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

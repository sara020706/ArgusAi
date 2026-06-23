import { useEffect, useState } from 'react'
import { scoreEvent, getHealth } from '../api/argus'

export function useArgusScore() {
  const [result,    setResult]    = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)
  const [apiOnline, setApiOnline] = useState(null)

  useEffect(() => {
    async function check() {
      const h = await getHealth()
      setApiOnline(h?.status !== 'unreachable')
    }
    check()
  }, [])

  async function score(formData) {
    setLoading(true)
    setError(null)
    const res = await scoreEvent(formData)
    if (res) {
      setResult(res)
    } else {
      setError('Could not reach Argus API. Is it running on :8000?')
    }
    setLoading(false)
  }

  return { result, loading, error, apiOnline, score }
}

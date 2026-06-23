import { createContext, useContext, useState, useEffect } from 'react'

export const API_BASE = 'http://localhost:8000'

const ApiContext = createContext()

export function ApiProvider({ children }) {
  const [online, setOnline] = useState(false)

  async function ping() {
    try {
      const r = await fetch(`${API_BASE}/`, { signal: AbortSignal.timeout(3000) })
      setOnline(r.ok)
    } catch {
      setOnline(false)
    }
  }

  useEffect(() => {
    ping()
    const id = setInterval(ping, 10000)
    return () => clearInterval(id)
  }, [])

  async function post(endpoint, formData) {
    const r = await fetch(`${API_BASE}${endpoint}`, { method: 'POST', body: formData })
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }))
      throw new Error(err.detail || `HTTP ${r.status}`)
    }
    return r.json()
  }

  async function get(endpoint) {
    const r = await fetch(`${API_BASE}${endpoint}`)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    return r.json()
  }

  return (
    <ApiContext.Provider value={{ online, post, get }}>
      {children}
    </ApiContext.Provider>
  )
}

export function useApi() {
  return useContext(ApiContext)
}

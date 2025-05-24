import type { Config } from '@/types'

export function useConfig() {
  const loadConfig = async (): Promise<Config> => {
    // In development, Vue dev server runs on 5173 but API is on FastAPI (8000)
    // In production, everything is served from the same port
    let apiBase = ''
    if (window.location.port === '5173') {
      // Development mode: connect to FastAPI server on port 8000
      apiBase = `${window.location.protocol}//${window.location.hostname}:8000`
    }
    
    const response = await fetch(`${apiBase}/api/config`)
    if (!response.ok) {
      throw new Error('Failed to load configuration')
    }
    return response.json()
  }

  return {
    loadConfig
  }
} 
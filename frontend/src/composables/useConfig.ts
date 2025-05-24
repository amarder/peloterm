import type { Config } from '@/types'

export function useConfig() {
  const loadConfig = async (): Promise<Config> => {
    const response = await fetch('/api/config')
    if (!response.ok) {
      throw new Error('Failed to load configuration')
    }
    return response.json()
  }

  return {
    loadConfig
  }
} 
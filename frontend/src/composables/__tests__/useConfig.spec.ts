import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useConfig } from '../useConfig'
import type { Config } from '@/types'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('useConfig', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const mockConfig: Config = {
    iframe_url: 'https://example.com/video',
    ride_duration_minutes: 45,
    ride_start_time: 1640995200,
    iframe_options: {
      autoplay: '1',
      muted: '1'
    },
    metrics: [
      {
        name: 'Power',
        key: 'power',
        symbol: 'W',
        color: '#ff6b6b'
      },
      {
        name: 'Speed',
        key: 'speed',
        symbol: 'mph',
        color: '#4ecdc4'
      }
    ]
  }

  it('should load config successfully in production environment', async () => {
    // Mock production environment
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'https:',
        hostname: 'example.com',
        port: '443'
      },
      writable: true
    })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockConfig)
    })

    const { loadConfig } = useConfig()
    const result = await loadConfig()

    expect(mockFetch).toHaveBeenCalledWith('/api/config')
    expect(result).toEqual(mockConfig)
  })

  it('should load config successfully in development environment', async () => {
    // Mock development environment
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'http:',
        hostname: 'localhost',
        port: '5173'
      },
      writable: true
    })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockConfig)
    })

    const { loadConfig } = useConfig()
    const result = await loadConfig()

    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/config')
    expect(result).toEqual(mockConfig)
  })

  it('should throw error when fetch fails', async () => {
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'https:',
        hostname: 'example.com',
        port: '443'
      },
      writable: true
    })

    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found'
    })

    const { loadConfig } = useConfig()

    await expect(loadConfig()).rejects.toThrow('Failed to load configuration')
    expect(mockFetch).toHaveBeenCalledWith('/api/config')
  })

  it('should throw error when network request fails', async () => {
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'https:',
        hostname: 'example.com',
        port: '443'
      },
      writable: true
    })

    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    const { loadConfig } = useConfig()

    await expect(loadConfig()).rejects.toThrow('Network error')
  })

  it('should handle malformed JSON response', async () => {
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'https:',
        hostname: 'example.com',
        port: '443'
      },
      writable: true
    })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.reject(new Error('Invalid JSON'))
    })

    const { loadConfig } = useConfig()

    await expect(loadConfig()).rejects.toThrow('Invalid JSON')
  })
}) 
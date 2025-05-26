import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { useWebSocket } from '../useWebSocket'
import type { MetricsData } from '@/types'

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.CONNECTING
  url: string
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(url: string) {
    this.url = url
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 10)
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'))
    }
  }

  send(data: string) {
    // Mock send method
  }

  // Helper method to simulate receiving a message
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }))
    }
  }

  // Helper method to simulate an error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'))
    }
  }
}

// Mock global WebSocket
global.WebSocket = MockWebSocket as any

describe('useWebSocket', () => {
  let mockCallback: vi.MockedFunction<(data: MetricsData) => void>
  let consoleLogSpy: vi.SpyInstance
  let consoleErrorSpy: vi.SpyInstance

  beforeEach(() => {
    mockCallback = vi.fn()
    consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  // Helper to create a component that uses the composable
  const createTestComponent = () => {
    return defineComponent({
      setup() {
        const websocket = useWebSocket()
        return { websocket }
      },
      template: '<div></div>'
    })
  }

  it('should initialize with correct default values', () => {
    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    
    expect(wrapper.vm.websocket.isConnected.value).toBe(false)
  })

  it('should connect to WebSocket and update connection status', async () => {
    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    
    wrapper.vm.websocket.connect(mockCallback)
    
    // Initially not connected
    expect(wrapper.vm.websocket.isConnected.value).toBe(false)
    
    // Advance timers to simulate connection
    vi.advanceTimersByTime(20)
    
    expect(wrapper.vm.websocket.isConnected.value).toBe(true)
    expect(consoleLogSpy).toHaveBeenCalledWith('WebSocket connected')
  })

  it('should use correct WebSocket URL in development', () => {
    // Mock development environment
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'http:',
        hostname: 'localhost',
        host: 'localhost:5173',
        port: '5173'
      },
      writable: true
    })

    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    wrapper.vm.websocket.connect(mockCallback)

    expect(consoleLogSpy).toHaveBeenCalledWith(
      'Connecting to WebSocket:', 
      'ws://localhost:8000/ws'
    )
  })

  it('should use correct WebSocket URL in production', () => {
    // Mock production environment
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'https:',
        hostname: 'example.com',
        host: 'example.com',
        port: '443'
      },
      writable: true
    })

    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    wrapper.vm.websocket.connect(mockCallback)

    expect(consoleLogSpy).toHaveBeenCalledWith(
      'Connecting to WebSocket:', 
      'wss://example.com/ws'
    )
  })

  it('should process live metrics data immediately when not processing history', async () => {
    let mockWs: MockWebSocket

    // Override WebSocket constructor to capture instance
    global.WebSocket = class extends MockWebSocket {
      constructor(url: string) {
        super(url)
        mockWs = this
      }
    } as any

    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    wrapper.vm.websocket.connect(mockCallback)
    
    vi.advanceTimersByTime(20) // Connect

    // Wait for history processing to complete and clear the timeout
    vi.advanceTimersByTime(1100)

    // Clear any previous calls from history processing
    mockCallback.mockClear()

    const testData: MetricsData = {
      power: 250,
      speed: 25.5,
      cadence: 90,
      heart_rate: 150,
      timestamp: Date.now()
    }

    mockWs!.simulateMessage(testData)

    expect(mockCallback).toHaveBeenCalledWith(testData)
  })

  it('should buffer and sort historical data during history processing', async () => {
    let mockWs: MockWebSocket

    global.WebSocket = class extends MockWebSocket {
      constructor(url: string) {
        super(url)
        mockWs = this
      }
    } as any

    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    wrapper.vm.websocket.connect(mockCallback)
    
    vi.advanceTimersByTime(20) // Connect

    // Send historical data out of order
    const data1: MetricsData = { power: 100, timestamp: 1000 }
    const data2: MetricsData = { power: 200, timestamp: 500 }
    const data3: MetricsData = { power: 300, timestamp: 1500 }

    mockWs!.simulateMessage(data1)
    mockWs!.simulateMessage(data2)
    mockWs!.simulateMessage(data3)

    // Data should not be processed immediately during history mode
    expect(mockCallback).not.toHaveBeenCalled()

    // Advance past history timeout
    vi.advanceTimersByTime(1100)

    // Should be called in sorted order
    expect(mockCallback).toHaveBeenCalledTimes(3)
    expect(mockCallback).toHaveBeenNthCalledWith(1, data2) // timestamp: 500
    expect(mockCallback).toHaveBeenNthCalledWith(2, data1) // timestamp: 1000
    expect(mockCallback).toHaveBeenNthCalledWith(3, data3) // timestamp: 1500
  })

  it('should handle malformed JSON messages gracefully', async () => {
    let mockWs: MockWebSocket

    global.WebSocket = class extends MockWebSocket {
      constructor(url: string) {
        super(url)
        mockWs = this
      }
    } as any

    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    wrapper.vm.websocket.connect(mockCallback)
    
    vi.advanceTimersByTime(20) // Connect

    // Simulate malformed message
    if (mockWs!.onmessage) {
      mockWs!.onmessage(new MessageEvent('message', { data: 'invalid json' }))
    }

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Error parsing WebSocket message:',
      expect.any(Error)
    )
    expect(mockCallback).not.toHaveBeenCalled()
  })

  it('should reconnect automatically on connection close', async () => {
    let mockWs: MockWebSocket

    global.WebSocket = class extends MockWebSocket {
      constructor(url: string) {
        super(url)
        mockWs = this
      }
    } as any

    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    wrapper.vm.websocket.connect(mockCallback)
    
    vi.advanceTimersByTime(20) // Connect
    expect(wrapper.vm.websocket.isConnected.value).toBe(true)

    // Simulate connection close
    mockWs!.close()
    expect(wrapper.vm.websocket.isConnected.value).toBe(false)
    expect(consoleLogSpy).toHaveBeenCalledWith('WebSocket disconnected')

    // Should attempt reconnection after 3 seconds
    vi.advanceTimersByTime(3020)
    expect(consoleLogSpy).toHaveBeenCalledWith('Connecting to WebSocket:', expect.any(String))
  })

  it('should handle WebSocket errors', async () => {
    let mockWs: MockWebSocket

    global.WebSocket = class extends MockWebSocket {
      constructor(url: string) {
        super(url)
        mockWs = this
      }
    } as any

    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    wrapper.vm.websocket.connect(mockCallback)
    
    vi.advanceTimersByTime(20) // Connect

    mockWs!.simulateError()

    expect(consoleErrorSpy).toHaveBeenCalledWith('WebSocket error:', expect.any(Event))
  })

  it('should disconnect properly and clean up resources', async () => {
    let mockWs: MockWebSocket

    global.WebSocket = class extends MockWebSocket {
      constructor(url: string) {
        super(url)
        mockWs = this
      }
    } as any

    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    wrapper.vm.websocket.connect(mockCallback)
    
    vi.advanceTimersByTime(20) // Connect
    expect(wrapper.vm.websocket.isConnected.value).toBe(true)

    const closeSpy = vi.spyOn(mockWs!, 'close')

    wrapper.vm.websocket.disconnect()

    expect(closeSpy).toHaveBeenCalled()
    expect(wrapper.vm.websocket.isConnected.value).toBe(false)
  })

  it('should clear history timeout on disconnect', async () => {
    let mockWs: MockWebSocket

    global.WebSocket = class extends MockWebSocket {
      constructor(url: string) {
        super(url)
        mockWs = this
      }
    } as any

    const TestComponent = createTestComponent()
    const wrapper = mount(TestComponent)
    wrapper.vm.websocket.connect(mockCallback)
    
    vi.advanceTimersByTime(20) // Connect

    // Send some historical data to trigger timeout
    mockWs!.simulateMessage({ power: 100, timestamp: 1000 })

    // Disconnect before timeout completes
    wrapper.vm.websocket.disconnect()

    // Advance past where timeout would have fired
    vi.advanceTimersByTime(1100)

    // Callback should not have been called since we disconnected
    expect(mockCallback).not.toHaveBeenCalled()
  })
}) 
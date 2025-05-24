import { ref, onUnmounted } from 'vue'
import type { MetricsData } from '@/types'

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const isProcessingHistory = ref(false)
  const historicalBuffer = ref<MetricsData[]>([])
  let historyTimeout: number | null = null
  let onMetricsUpdate: ((data: MetricsData) => void) | null = null

  const connect = (metricsUpdateCallback: (data: MetricsData) => void) => {
    onMetricsUpdate = metricsUpdateCallback
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`
    
    ws.value = new WebSocket(wsUrl)
    
    ws.value.onopen = () => {
      console.log('WebSocket connected')
      isConnected.value = true
      isProcessingHistory.value = true
      historicalBuffer.value = []
    }
    
    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as MetricsData
        
        if (isProcessingHistory.value) {
          historicalBuffer.value.push(data)
          
          if (historyTimeout) {
            clearTimeout(historyTimeout)
          }
          
          historyTimeout = window.setTimeout(() => {
            // Sort historical data by timestamp
            historicalBuffer.value.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))
            
            // Process all historical data
            historicalBuffer.value.forEach(histData => {
              if (onMetricsUpdate) {
                onMetricsUpdate(histData)
              }
            })
            
            historicalBuffer.value = []
            isProcessingHistory.value = false
            console.log('Finished processing historical data')
          }, 1000)
        } else {
          // Process live data immediately
          if (onMetricsUpdate) {
            onMetricsUpdate(data)
          }
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }
    
    ws.value.onclose = () => {
      console.log('WebSocket disconnected')
      isConnected.value = false
      setTimeout(() => connect(metricsUpdateCallback), 3000)
    }
    
    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  const disconnect = () => {
    if (historyTimeout) {
      clearTimeout(historyTimeout)
      historyTimeout = null
    }
    
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    
    isConnected.value = false
    onMetricsUpdate = null
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connect,
    disconnect,
    isConnected
  }
} 
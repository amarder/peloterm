import { ref, reactive } from 'vue'

export interface Alert {
  id: string
  message: string
  type: 'success' | 'error' | 'info'
  timestamp: number
}

const alerts = ref<Alert[]>([])

export function useAlerts() {
  const showAlert = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const alert: Alert = {
      id: Date.now().toString(),
      message,
      type,
      timestamp: Date.now()
    }
    
    alerts.value.push(alert)
    
    // Auto-remove alert after 5 seconds
    setTimeout(() => {
      removeAlert(alert.id)
    }, 5000)
  }
  
  const removeAlert = (id: string) => {
    const index = alerts.value.findIndex(alert => alert.id === id)
    if (index > -1) {
      alerts.value.splice(index, 1)
    }
  }
  
  const clearAllAlerts = () => {
    alerts.value = []
  }
  
  return {
    alerts,
    showAlert,
    removeAlert,
    clearAllAlerts
  }
} 
<template>
  <div class="control-buttons">
    <button 
      class="control-btn record-btn"
      :class="{ 'recording': isRecording, 'paused': isPaused }"
      @click="toggleRecording"
      :disabled="isProcessing"
      :title="recordButtonText"
    >
      <span class="btn-icon">{{ recordButtonIcon }}</span>
    </button>
    
    <button 
      class="control-btn save-btn"
      @click="saveRecording"
      :disabled="!hasRecordedData || isProcessing"
      title="Save"
    >
      <span class="btn-icon">💾</span>
    </button>
    
    <button 
      class="control-btn upload-btn"
      @click="uploadToStrava"
      :disabled="!hasRecordedData || isProcessing"
      title="Upload to Strava"
    >
      <span class="btn-icon">📤</span>
    </button>
    
    <button 
      class="control-btn clear-btn"
      @click="clearRecording"
      :disabled="(!hasRecordedData && !isRecording && !isPaused) || isProcessing"
      title="Clear"
    >
      <span class="btn-icon">🗑️</span>
    </button>
    
    <div v-if="statusMessage" class="status-message" :class="statusType">
      {{ statusMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRecordingState } from '@/composables/useRecordingState'

// Local UI state
const isProcessing = ref(false)

// Global recording state
const { isRecording, isPaused, hasRecordedData, updateRecordingState } = useRecordingState()

// Status messaging
const statusMessage = ref('')
const statusType = ref<'success' | 'error' | 'info'>('info')

// Computed properties for record button
const recordButtonIcon = computed(() => {
  if (isRecording.value) return '⏸️'
  if (isPaused.value) return '▶️'
  return '🔴'
})

const recordButtonText = computed(() => {
  if (isRecording.value) return 'Pause'
  if (isPaused.value) return 'Resume'
  return 'Record'
})

// WebSocket connection for sending commands
let ws: WebSocket | null = null

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  
  // In development, Vue dev server runs on 5173 but WebSocket is on FastAPI (8000)
  // In production, everything is served from the same port
  let wsHost = window.location.host
  if (window.location.port === '5173') {
    // Development mode: connect to FastAPI server on port 8000
    wsHost = `${window.location.hostname}:8000`
  }
  
  const wsUrl = `${protocol}//${wsHost}/ws/control`
  console.log('Connecting to Control WebSocket:', wsUrl)
  
  ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    console.log('Control WebSocket connected')
  }
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleControlResponse(data)
    } catch (error) {
      console.error('Error parsing control response:', error)
    }
  }
  
  ws.onclose = () => {
    console.log('Control WebSocket disconnected')
    // Attempt to reconnect after a delay
    setTimeout(connectWebSocket, 3000)
  }
  
  ws.onerror = (error) => {
    console.error('Control WebSocket error:', error)
  }
}

const sendControlCommand = (command: string, data: any = {}) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ command, ...data }))
  } else {
    showStatus('Connection lost. Please refresh the page.', 'error')
  }
}

const handleControlResponse = (data: any) => {
  switch (data.type) {
    case 'status':
      // Initial status update
      updateRecordingState(
        data.is_recording || false,
        data.is_paused || false,
        data.has_data || false
      )
      break
      
    case 'recording_started':
      updateRecordingState(true, false, false)
      showStatus('Recording started', 'success')
      break
      
    case 'recording_paused':
      updateRecordingState(false, true, true) // We have data when paused
      showStatus('Recording paused', 'info')
      break
      
    case 'recording_resumed':
      updateRecordingState(true, false, true)
      showStatus('Recording resumed', 'success')
      break
      
    case 'recording_stopped':
      updateRecordingState(false, false, true)
      showStatus('Recording stopped', 'info')
      break
      
    case 'recording_cleared':
      updateRecordingState(false, false, false)
      isProcessing.value = false
      showStatus('Recording cleared', 'info')
      break
      
    case 'save_success':
      isProcessing.value = false
      showStatus(`Saved to: ${data.filename}`, 'success')
      break
      
    case 'upload_success':
      isProcessing.value = false
      showStatus('Successfully uploaded to Strava!', 'success')
      break
      
    case 'error':
      isProcessing.value = false
      showStatus(data.message || 'An error occurred', 'error')
      break
      
    default:
      console.log('Unknown control response:', data)
  }
}

const showStatus = (message: string, type: 'success' | 'error' | 'info') => {
  statusMessage.value = message
  statusType.value = type
  
  // Clear status after 5 seconds
  setTimeout(() => {
    statusMessage.value = ''
  }, 5000)
}

const toggleRecording = () => {
  if (isProcessing.value) return
  
  if (!isRecording.value && !isPaused.value) {
    // Start recording
    sendControlCommand('start_recording')
  } else if (isRecording.value) {
    // Pause recording
    sendControlCommand('pause_recording')
  } else if (isPaused.value) {
    // Resume recording
    sendControlCommand('resume_recording')
  }
}

const saveRecording = () => {
  if (isProcessing.value || !hasRecordedData.value) return
  
  isProcessing.value = true
  sendControlCommand('save_recording')
}

const uploadToStrava = () => {
  if (isProcessing.value || !hasRecordedData.value) return
  
  isProcessing.value = true
  sendControlCommand('upload_to_strava')
}

const clearRecording = () => {
  if (isProcessing.value) return
  
  sendControlCommand('clear_recording')
}

// Initialize WebSocket connection when component mounts
onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.control-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 0;
  padding: 0;
  margin: 0;
  width: 120px;
  flex-shrink: 0;
  background: transparent;
  height: 100px;
  position: relative;
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  margin: 0;
  border: 1px solid #30363d;
  border-radius: 0;
  background: #21262d;
  color: #e6edf3;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  height: 50px;
}

.control-btn:hover:not(:disabled) {
  background: #30363d;
  border-color: #484f58;
  transform: translateY(-1px);
}

.control-btn:active:not(:disabled) {
  transform: translateY(0);
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.record-btn.recording {
  background: #da3633;
  border-color: #f85149;
  animation: pulse 2s infinite;
}



.save-btn:hover:not(:disabled) {
  background: #30363d;
  border-color: #484f58;
}

.upload-btn:hover:not(:disabled) {
  background: #30363d;
  border-color: #484f58;
}

.clear-btn:hover:not(:disabled) {
  background: #30363d;
  border-color: #484f58;
}

.btn-icon {
  font-size: 14px;
}

.status-message {
  text-align: center;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 8px;
  font-weight: 500;
  margin-top: 4px;
  width: 100%;
  word-wrap: break-word;
  line-height: 1.1;
  position: absolute;
  bottom: -25px;
  left: 0;
  right: 0;
  grid-column: 1 / -1;
}

.status-message.success {
  background: rgba(35, 134, 54, 0.15);
  color: #2ea043;
  border: 1px solid rgba(35, 134, 54, 0.3);
}

.status-message.error {
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
  border: 1px solid rgba(248, 81, 73, 0.3);
}

.status-message.info {
  background: rgba(31, 111, 235, 0.15);
  color: #58a6ff;
  border: 1px solid rgba(31, 111, 235, 0.3);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

@media (max-width: 768px) {
  .control-buttons {
    flex-direction: row;
    width: 100%;
    height: auto;
    padding: 8px 0;
    justify-content: center;
    gap: 8px;
  }
  
  .control-btn {
    width: 36px;
    height: 36px;
  }
  
  .btn-icon {
    font-size: 16px;
  }
  
  .status-message {
    margin-top: 0;
    margin-left: 12px;
    flex: 1;
    font-size: 12px;
  }
}
</style> 
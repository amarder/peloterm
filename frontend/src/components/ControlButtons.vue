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
      @click="showUploadDialog"
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
  </div>
  
  <!-- Strava Upload Dialog -->
  <StravaUploadDialog
    :is-visible="showDialog"
    :ride-summary="rideSummary"
    :is-uploading="isUploading"
    @close="closeUploadDialog"
    @upload="handleUploadConfirm"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRecordingState } from '@/composables/useRecordingState'
import { useAlerts } from '@/composables/useAlerts'
import StravaUploadDialog from './StravaUploadDialog.vue'

// Local UI state
const isProcessing = ref(false)
const showDialog = ref(false)
const rideSummary = ref(null)
const isUploading = ref(false)

// Global recording state
const { isRecording, isPaused, hasRecordedData, updateRecordingState } = useRecordingState()

// Alert system
const { showAlert } = useAlerts()

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
    showAlert('Connection lost. Please refresh the page.', 'error')
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
      showAlert('Recording started', 'success')
      break
      
    case 'recording_paused':
      updateRecordingState(false, true, true) // We have data when paused
      showAlert('Recording paused', 'info')
      break
      
    case 'recording_resumed':
      updateRecordingState(true, false, true)
      showAlert('Recording resumed', 'success')
      break
      
    case 'recording_stopped':
      updateRecordingState(false, false, true)
      showAlert('Recording stopped', 'info')
      break
      
    case 'recording_cleared':
      updateRecordingState(false, false, false)
      isProcessing.value = false
      showAlert('Recording cleared', 'info')
      break
      
    case 'save_success':
      isProcessing.value = false
      showAlert(`Saved to: ${data.filename}`, 'success')
      break
      
    case 'upload_success':
      isProcessing.value = false
      isUploading.value = false
      showDialog.value = false
      rideSummary.value = null
      showAlert('Successfully uploaded to Strava!', 'success')
      break
      
    case 'error':
      isProcessing.value = false
      isUploading.value = false
      showAlert(data.message || 'An error occurred', 'error')
      break
      
    default:
      console.log('Unknown control response:', data)
  }
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

const showUploadDialog = async () => {
  if (isProcessing.value || !hasRecordedData.value) return
  
  try {
    // Fetch ride summary data
    const response = await fetch('/api/ride-summary')
    const data = await response.json()
    
    if (data.error) {
      showAlert(data.error, 'error')
      return
    }
    
    rideSummary.value = data
    showDialog.value = true
  } catch (error) {
    console.error('Error fetching ride summary:', error)
    showAlert('Failed to load ride summary', 'error')
  }
}

const closeUploadDialog = () => {
  if (!isUploading.value) {
    showDialog.value = false
    rideSummary.value = null
  }
}

const handleUploadConfirm = (name: string, description: string) => {
  if (isUploading.value) return
  
  isUploading.value = true
  
  // Send upload command with custom name and description
  sendControlCommand('upload_to_strava', {
    name: name,
    description: description
  })
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
    display: flex;
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
}
</style> 
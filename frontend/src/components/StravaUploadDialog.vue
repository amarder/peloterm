<template>
  <div v-if="isVisible" class="dialog-overlay" @click="handleOverlayClick">
    <div class="dialog-content" @click.stop>
      <div class="dialog-header">
        <h2>📤 Upload to Strava</h2>
        <button class="close-btn" @click="closeDialog">✕</button>
      </div>
      
      <div class="dialog-body">
        <div class="ride-summary">
          <h3>🚴 Ride Summary</h3>
          
          <div v-if="rideSummary" class="summary-grid">
            <div class="summary-item">
              <span class="summary-label">Duration:</span>
              <span class="summary-value">{{ formatDuration(rideSummary.duration) }}</span>
            </div>
            
            <div class="summary-item">
              <span class="summary-label">Data Points:</span>
              <span class="summary-value">{{ rideSummary.data_points }}</span>
            </div>
            
            <div v-if="rideSummary.avg_power" class="summary-item">
              <span class="summary-label">Avg Power:</span>
              <span class="summary-value">{{ Math.round(rideSummary.avg_power) }}W</span>
            </div>
            
            <div v-if="rideSummary.max_power" class="summary-item">
              <span class="summary-label">Max Power:</span>
              <span class="summary-value">{{ Math.round(rideSummary.max_power) }}W</span>
            </div>
            
            <div v-if="rideSummary.avg_heart_rate" class="summary-item">
              <span class="summary-label">Avg Heart Rate:</span>
              <span class="summary-value">{{ Math.round(rideSummary.avg_heart_rate) }} BPM</span>
            </div>
            
            <div v-if="rideSummary.max_heart_rate" class="summary-item">
              <span class="summary-label">Max Heart Rate:</span>
              <span class="summary-value">{{ Math.round(rideSummary.max_heart_rate) }} BPM</span>
            </div>
            
            <div v-if="rideSummary.avg_cadence" class="summary-item">
              <span class="summary-label">Avg Cadence:</span>
              <span class="summary-value">{{ Math.round(rideSummary.avg_cadence) }} RPM</span>
            </div>
            
            <div v-if="rideSummary.avg_speed" class="summary-item">
              <span class="summary-label">Avg Speed:</span>
              <span class="summary-value">{{ rideSummary.avg_speed.toFixed(1) }} km/h</span>
            </div>
          </div>
          
          <div v-else class="loading-summary">
            <span>Loading ride summary...</span>
          </div>
        </div>
        
        <div class="upload-details">
          <h3>📝 Activity Details</h3>
          
          <div class="form-group">
            <label for="activity-name">Activity Name:</label>
            <input 
              id="activity-name"
              v-model="activityName" 
              type="text" 
              class="form-input"
              placeholder="Enter activity name"
            />
          </div>
          
          <div class="form-group">
            <label for="activity-description">Description:</label>
            <textarea 
              id="activity-description"
              v-model="activityDescription" 
              class="form-textarea"
              placeholder="Enter activity description (optional)"
              rows="3"
            />
          </div>
        </div>
      </div>
      
      <div class="dialog-footer">
        <button class="btn btn-secondary" @click="closeDialog" :disabled="isUploading">
          Cancel
        </button>
        <button 
          class="btn btn-primary" 
          @click="confirmUpload" 
          :disabled="isUploading || !activityName.trim()"
        >
          <span v-if="isUploading">Uploading...</span>
          <span v-else>📤 Upload to Strava</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface RideSummary {
  duration: number
  data_points: number
  start_time?: number
  end_time?: number
  avg_power?: number
  max_power?: number
  min_power?: number
  avg_heart_rate?: number
  max_heart_rate?: number
  min_heart_rate?: number
  avg_cadence?: number
  max_cadence?: number
  avg_speed?: number
  max_speed?: number
}

interface Props {
  isVisible: boolean
  rideSummary?: RideSummary | null
  isUploading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isUploading: false,
  rideSummary: null
})

const emit = defineEmits<{
  close: []
  upload: [name: string, description: string]
}>()

const activityName = ref('')
const activityDescription = ref('Recorded with Peloterm, free open-source software for indoor cycling: https://andrewmarder.net/posts/peloterm/')

// Generate default activity name when dialog opens
watch(() => props.isVisible, (visible) => {
  if (visible && !activityName.value) {
    const now = new Date()
    activityName.value = `Peloterm Ride ${now.toLocaleDateString()} ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  }
})

const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  
  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

const handleOverlayClick = () => {
  if (!props.isUploading) {
    closeDialog()
  }
}

const closeDialog = () => {
  if (!props.isUploading) {
    emit('close')
  }
}

const confirmUpload = () => {
  if (activityName.value.trim() && !props.isUploading) {
    emit('upload', activityName.value.trim(), activityDescription.value.trim())
  }
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.dialog-content {
  background: #21262d;
  border: 1px solid #30363d;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #30363d;
}

.dialog-header h2 {
  margin: 0;
  color: #e6edf3;
  font-size: 20px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: #7d8590;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  color: #e6edf3;
  background: #30363d;
}

.dialog-body {
  padding: 24px;
}

.ride-summary {
  margin-bottom: 32px;
}

.ride-summary h3 {
  margin: 0 0 16px 0;
  color: #e6edf3;
  font-size: 16px;
  font-weight: 600;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
}

.summary-label {
  color: #7d8590;
  font-size: 14px;
}

.summary-value {
  color: #58a6ff;
  font-weight: 600;
  font-size: 14px;
}

.loading-summary {
  text-align: center;
  color: #7d8590;
  padding: 20px;
}

.upload-details h3 {
  margin: 0 0 16px 0;
  color: #e6edf3;
  font-size: 16px;
  font-weight: 600;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: #e6edf3;
  font-size: 14px;
  font-weight: 500;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 8px 12px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #e6edf3;
  font-size: 14px;
  font-family: inherit;
  transition: border-color 0.2s ease;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #58a6ff;
}

.form-textarea {
  resize: vertical;
  min-height: 60px;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 20px 24px;
  border-top: 1px solid #30363d;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 100px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #21262d;
  color: #e6edf3;
  border: 1px solid #30363d;
}

.btn-secondary:hover:not(:disabled) {
  background: #30363d;
}

.btn-primary {
  background: #238636;
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: #2ea043;
}

@media (max-width: 768px) {
  .dialog-content {
    width: 95%;
    margin: 20px;
  }
  
  .summary-grid {
    grid-template-columns: 1fr;
  }
  
  .dialog-footer {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style> 
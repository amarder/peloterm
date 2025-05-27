<template>
  <div class="time-widget">
    <div class="time-row">
      <span class="time-value">{{ currentTime }}</span>
    </div>
    <div class="progress-bar">
      <div 
        class="progress-fill" 
        :style="{ width: `${progress}%` }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

interface Props {
  rideDurationMinutes: number
  rideStartTime: number
}

const props = defineProps<Props>()

const currentTime = ref('')
const now = ref(Date.now())
let timeInterval: number | null = null

const progress = computed(() => {
  const targetSeconds = props.rideDurationMinutes * 60
  const elapsedSeconds = (now.value - props.rideStartTime * 1000) / 1000
  return Math.min((elapsedSeconds / targetSeconds) * 100, 100)
})

const updateTime = () => {
  const date = new Date()
  currentTime.value = date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit',
    hour12: false 
  })
  now.value = date.getTime()
}

onMounted(() => {
  updateTime()
  timeInterval = window.setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script>

<style scoped>
.time-widget {
  padding: 12px 16px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.time-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.time-value {
  font-size: 32px;
  font-weight: 700;
  color: #58a6ff;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Source Code Pro', monospace;
  line-height: 1;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #30363d;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 12px;
}

.progress-fill {
  height: 100%;
  background: #58a6ff;
  transition: width 0.3s ease;
}

@media (max-width: 768px) {
  .time-widget {
    width: 100%;
    border-right: none;
  }
}
</style> 
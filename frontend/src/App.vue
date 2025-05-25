<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import VideoPanel from './components/VideoPanel.vue'
import PelotermPanel from './components/PelotermPanel.vue'
import { useWebSocket } from './composables/useWebSocket'
import { useConfig } from './composables/useConfig'
import type { Config, MetricsData } from './types'

const isLoading = ref(true)
const config = ref<Config | null>(null)
const currentMetrics = ref<MetricsData>({})
const pelotermPanel = ref()

const { loadConfig } = useConfig()
const { connect, disconnect, isConnected } = useWebSocket()

const handleResize = () => {
  if (pelotermPanel.value?.resizeCharts) {
    pelotermPanel.value.resizeCharts()
  }
}

const handleMetricsUpdate = (data: MetricsData) => {
  currentMetrics.value = { ...data }
}

onMounted(async () => {
  try {
    config.value = await loadConfig()
    connect(handleMetricsUpdate)
    isLoading.value = false
  } catch (error) {
    console.error('Failed to initialize PeloTerm:', error)
    isLoading.value = false
  }
})

onUnmounted(() => {
  disconnect()
})
</script>

<template>
  <div class="app-container">
    <div v-if="isLoading" class="loading">
      <div>Loading PeloTerm...</div>
    </div>
    
    <div v-else class="container">
      <VideoPanel 
        :iframe-url="config?.iframe_url || ''"
        @resize="handleResize"
      />
      
      <PelotermPanel 
        :ride-duration-minutes="config?.ride_duration_minutes || 30"
        :ride-start-time="config?.ride_start_time || 0"
        :metrics-config="config?.metrics || []"
        :current-metrics="currentMetrics"
        :ref="pelotermPanel"
      />
    </div>
  </div>
</template>

<style scoped>
.app-container {
  height: 100vh;
  background: #0d1117;
  color: #e6edf3;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  font-size: 18px;
  color: #7d8590;
}

.container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

@media (max-width: 768px) {
  .container {
    flex-direction: column;
  }
}
</style>

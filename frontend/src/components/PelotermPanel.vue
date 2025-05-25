<template>
  <div class="peloterm-panel" ref="pelotermPanelRef">
    <TimeWidget 
      :ride-duration-minutes="rideDurationMinutes"
      :ride-start-time="rideStartTime"
    />
    
    <div class="metrics-container">
      <MetricCard
        v-for="metric in metricsConfig"
        :key="metric.key"
        :metric="metric"
        :value="currentMetrics[metric.key]"
        :timestamp="currentMetrics.timestamp"
        :ride-duration-minutes="rideDurationMinutes"
        :ride-start-time="rideStartTime"
        @chart-created="handleChartCreated"
        @metric-update="handleMetricUpdate"
      />
    </div>
    
    <ControlButtons />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import TimeWidget from './TimeWidget.vue'
import MetricCard from './MetricCard.vue'
import ControlButtons from './ControlButtons.vue'
import type { MetricConfig, MetricsData } from '@/types'

interface Props {
  rideDurationMinutes: number
  rideStartTime: number
  metricsConfig: MetricConfig[]
  currentMetrics: MetricsData
}

const props = defineProps<Props>()

const pelotermPanelRef = ref<HTMLElement>()
const charts = ref<Record<string, any>>({})

const handleChartCreated = (metricKey: string, chart: any) => {
  charts.value[metricKey] = chart
  console.log(`Chart registered for ${metricKey}`)
}

const handleMetricUpdate = (metricKey: string, value: number, timestamp: number) => {
  // This is called by MetricCard when data points are added
  console.log(`Metric update: ${metricKey} = ${value} at ${timestamp}`)
}

const resizeCharts = () => {
  Object.values(charts.value).forEach((chart: any) => {
    try {
      if (chart && chart.resize) {
        chart.resize()
      }
    } catch (error) {
      console.error('Error resizing chart:', error)
    }
  })
}

// Watch for metrics updates and handle historical data
watch(() => props.currentMetrics, (newMetrics) => {
  if (!newMetrics || !newMetrics.timestamp) return
  
  // For historical data, we need to trigger the MetricCard components to plot the data
  // This happens automatically through the :value prop binding in the template
  // The MetricCard will see the value change and call addDataPoint with the current timestamp
}, { deep: true })

// Expose resizeCharts method to parent
defineExpose({
  resizeCharts
})
</script>

<style scoped>
.peloterm-panel {
  background: #161b22;
  border-top: 1px solid #21262d;
  padding: 0;
  display: flex;
  min-height: 100px;
  height: 100px;
  flex-shrink: 1;
  overflow: hidden;
  gap: 0;
}

.metrics-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

@media (max-width: 768px) {
  .peloterm-panel {
    height: 200px;
    flex-direction: column;
    gap: 16px;
  }
  
  .metrics-container {
    flex-direction: column;
    gap: 12px;
  }
}
</style> 
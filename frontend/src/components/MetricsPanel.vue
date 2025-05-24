<template>
  <div class="metrics-panel" ref="metricsPanelRef">
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
        :ride-duration-minutes="rideDurationMinutes"
        :ride-start-time="rideStartTime"
        @chart-created="handleChartCreated"
        @metric-update="handleMetricUpdate"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import TimeWidget from './TimeWidget.vue'
import MetricCard from './MetricCard.vue'
import type { MetricConfig, MetricsData } from '@/types'

interface Props {
  rideDurationMinutes: number
  rideStartTime: number
  metricsConfig: MetricConfig[]
  currentMetrics: MetricsData
}

const props = defineProps<Props>()

const metricsPanelRef = ref<HTMLElement>()
const charts = ref<Record<string, any>>({})

const handleChartCreated = (metricKey: string, chart: any) => {
  charts.value[metricKey] = chart
}

const handleMetricUpdate = (metricKey: string, value: number, timestamp: number) => {
  const chart = charts.value[metricKey]
  if (!chart) return

  const elapsedSeconds = (timestamp - props.rideStartTime * 1000) / 1000

  // Add new data point
  chart.data.labels.push(elapsedSeconds)
  chart.data.datasets[0].data.push(value)

  // Update current value indicator (red dot)
  chart.data.datasets[1].data = Array(chart.data.labels.length - 1).fill(null)
  chart.data.datasets[1].data.push(value)

  // Keep only visible data points
  const maxPoints = props.rideDurationMinutes * 60
  if (chart.data.labels.length > maxPoints) {
    chart.data.labels.shift()
    chart.data.datasets.forEach((dataset: any) => dataset.data.shift())
  }

  chart.update('none')
}

const resizeCharts = () => {
  Object.values(charts.value).forEach((chart: any) => {
    chart.resize()
  })
}

// Watch for metrics updates
watch(() => props.currentMetrics, (newMetrics) => {
  if (!newMetrics.timestamp) return

  Object.entries(newMetrics).forEach(([key, value]) => {
    if (typeof value === 'number' && key !== 'timestamp') {
      handleMetricUpdate(key, value, newMetrics.timestamp!)
    }
  })
}, { deep: true })

// Expose resizeCharts method to parent
defineExpose({
  resizeCharts
})
</script>

<style scoped>
.metrics-panel {
  background: #161b22;
  border-top: 1px solid #21262d;
  padding: 12px;
  display: flex;
  min-height: 100px;
  height: 100px;
  flex-shrink: 1;
  overflow: hidden;
}

.metrics-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

@media (max-width: 768px) {
  .metrics-panel {
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
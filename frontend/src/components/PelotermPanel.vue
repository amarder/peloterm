<template>
  <div class="peloterm-panel" ref="pelotermPanelRef">
    <!-- 1. Clock and Progress Bar -->
    <div class="time-section">
      <TimeWidget 
        :ride-duration-minutes="rideDurationMinutes"
        :ride-start-time="rideStartTime"
      />
    </div>
    
    <!-- 2. Metric Cards -->
    <div class="metrics-section">
      <div class="metrics-container">
        <MetricCard
          v-for="metric in metricsConfig"
          :key="metric.key"
          :metric="metric"
          :value="currentMetrics[metric.key]"
          :timestamp="currentMetrics.timestamp"
          :ride-duration-minutes="rideDurationMinutes"
          :ride-start-time="rideStartTime"
          @metric-update="handleMetricUpdate"
        />
      </div>
    </div>
    
    <!-- 3. All Metrics Chart -->
    <div class="chart-section">
      <AllMetricsChart
        ref="allMetricsChartRef"
        :metrics-config="metricsConfig"
        :ride-duration-minutes="rideDurationMinutes"
        :ride-start-time="rideStartTime"
      />
    </div>
    
    <!-- 4. Control Buttons -->
    <div class="controls-section">
      <ControlButtons />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import TimeWidget from './TimeWidget.vue'
import MetricCard from './MetricCard.vue'
import AllMetricsChart from './AllMetricsChart.vue'
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
const allMetricsChartRef = ref()

const handleMetricUpdate = (metricKey: string, value: number, timestamp: number) => {
  // Forward metric updates to the all metrics chart
  if (allMetricsChartRef.value && allMetricsChartRef.value.addDataPoint) {
    allMetricsChartRef.value.addDataPoint(metricKey, value, timestamp)
  }
  console.log(`Metric update: ${metricKey} = ${value} at ${timestamp}`)
}

const resizeCharts = () => {
  // Resize the all metrics chart if it exists
  if (allMetricsChartRef.value && allMetricsChartRef.value.$refs.chartRef) {
    try {
      allMetricsChartRef.value.$refs.chartRef.resize()
    } catch (error) {
      console.error('Error resizing all metrics chart:', error)
    }
  }
}

// Watch for metrics updates and handle historical data
watch(() => props.currentMetrics, (newMetrics) => {
  if (!newMetrics || !newMetrics.timestamp) return
  
  // For each metric in the current metrics, update the chart
  props.metricsConfig.forEach(metric => {
    const value = newMetrics[metric.key]
    if (value !== undefined && allMetricsChartRef.value) {
      allMetricsChartRef.value.addDataPoint(metric.key, value, newMetrics.timestamp)
    }
  })
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
  flex-direction: row;
  height: 100px;
  min-height: 100px;
  max-height: 100px;
  flex-shrink: 0;
  overflow: hidden;
  gap: 0;
  width: 100%;
}

.time-section {
  flex: 0 0 150px;
  display: flex;
  align-items: center;
  border-right: 1px solid #21262d;
  padding: 0 12px;
}

.metrics-section {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  border-right: 1px solid #21262d;
}

.metrics-container {
  display: flex;
  flex-direction: row;
  height: 100%;
}

.chart-section {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 4px 8px;
  min-width: 0;
}

.controls-section {
  flex: 0 0 130px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 0 0 8px;
  margin-left: auto;
}

@media (max-width: 1200px) {
  .time-section {
    flex: 0 0 120px;
    padding: 0 8px;
  }
  
  .controls-section {
    flex: 0 0 120px;
    padding: 0 0 0 4px;
  }
}

@media (max-width: 768px) {
  .peloterm-panel {
    flex-direction: column;
    height: auto;
    min-height: 300px;
    max-height: none;
  }
  
  .time-section,
  .metrics-section,
  .chart-section,
  .controls-section {
    flex: 0 0 auto;
    border-right: none;
    border-bottom: 1px solid #21262d;
  }
  
  .metrics-container {
    flex-direction: column;
  }
  
  .chart-section {
    padding: 16px;
    min-height: 200px;
  }
  
  .controls-section {
    margin-left: 0;
    justify-content: center;
  }
}
</style> 
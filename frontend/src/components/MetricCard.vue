<template>
  <div class="metric-card">
    <div class="metric-row">
      <span class="metric-symbol">{{ metric.symbol }}</span>
      <span 
        class="metric-value"
        :class="metric.key"
      >
        {{ displayValue }}
      </span>
    </div>
    <div class="metric-chart">
      <v-chart 
        ref="chartRef"
        class="chart"
        :option="chartOption"
        autoresize
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import type { MetricConfig } from '@/types'

// Register ECharts components
use([CanvasRenderer, LineChart, GridComponent])

interface Props {
  metric: MetricConfig
  value?: number
  timestamp?: number
  rideDurationMinutes: number
  rideStartTime: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  chartCreated: [metricKey: string, chart: any]
  metricUpdate: [metricKey: string, value: number, timestamp: number]
}>()

const chartRef = ref()
const chartData = ref<Array<[number, number]>>([])

const displayValue = computed(() => {
  if (props.value === undefined) return '--'
  
  if (props.metric.key === 'speed') {
    return props.value.toFixed(1)
  }
  return Math.round(props.value).toString()
})

const chartRanges = {
  power: { min: 0, max: 400 },
  speed: { min: 0, max: 40 },
  cadence: { min: 0, max: 120 },
  heart_rate: { min: 40, max: 180 }
} as const

const chartOption = computed(() => {
  const range = chartRanges[props.metric.key as keyof typeof chartRanges] || { min: 0, max: 100 }
  const rideDurationSeconds = props.rideDurationMinutes * 60
  
  return {
    grid: {
      left: 0,
      right: 0,
      top: 0,
      bottom: 0
    },
    xAxis: {
      type: 'value',
      show: false,
      min: 0,
      max: rideDurationSeconds // Full ride duration
    },
    yAxis: {
      type: 'value',
      show: false,
      min: range.min,
      max: range.max
    },
    series: [{
      type: 'line',
      data: chartData.value,
      smooth: true,
      symbol: 'none',
      lineStyle: {
        color: '#58a6ff',
        width: 2
      },
      animation: false
    }]
  }
})

// Watch for value changes to update chart
watch(() => [props.value, props.timestamp], ([newValue, newTimestamp]) => {
  if (newValue !== undefined) {
    // Use the provided timestamp if available, otherwise use current time
    const timestamp = newTimestamp ? newTimestamp * 1000 : Date.now()
    addDataPoint(newValue, timestamp)
  }
})

// Function to add a data point to the chart
const addDataPoint = (value: number, timestamp?: number) => {
  const dataTimestamp = timestamp || Date.now()
  const elapsedSeconds = (dataTimestamp - props.rideStartTime * 1000) / 1000
  
  // Only add points that are within the ride duration
  const rideDurationSeconds = props.rideDurationMinutes * 60
  if (elapsedSeconds >= 0 && elapsedSeconds <= rideDurationSeconds) {
    // Check if we already have a data point at this time (avoid duplicates)
    const existingIndex = chartData.value.findIndex(([time]) => Math.abs(time - elapsedSeconds) < 1)
    
    if (existingIndex >= 0) {
      // Update existing point
      chartData.value[existingIndex] = [elapsedSeconds, value]
    } else {
      // Add new point
      chartData.value.push([elapsedSeconds, value])
      // Sort by time to maintain order
      chartData.value.sort((a, b) => a[0] - b[0])
    }
    
    emit('metricUpdate', props.metric.key, value, dataTimestamp)
  }
}

onMounted(() => {
  console.log(`✅ ECharts chart mounted for ${props.metric.key}`)
  if (chartRef.value) {
    emit('chartCreated', props.metric.key, chartRef.value)
  }
})
</script>

<style scoped>
.metric-card {
  padding: 12px 16px;
  min-width: 180px;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 16px;
  border-right: 1px solid #30363d;
}

.metric-card:last-child {
  border-right: none;
}

.metric-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 120px;
}

.metric-symbol {
  font-size: 24px;
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  color: #58a6ff;
}

.metric-chart {
  flex: 1;
  height: 30px;
  min-height: 30px;
  position: relative;
  background: #0d1117;
  border-radius: 4px;
  overflow: hidden;
}

.chart {
  width: 100% !important;
  height: 100% !important;
}

.power, .speed, .cadence, .heart_rate { 
  color: #58a6ff; 
}

@media (max-width: 768px) {
  .metric-card {
    min-width: unset;
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #30363d;
  }
  
  .metric-card:last-child {
    border-bottom: none;
  }
}
</style>
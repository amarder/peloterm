<template>
  <div class="all-metrics-chart">
    <v-chart 
      ref="chartRef"
      class="chart"
      :option="chartOption"
      autoresize
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import type { MetricConfig, MetricsData } from '@/types'
import { useRecordingState } from '@/composables/useRecordingState'

// Register ECharts components
use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

interface Props {
  metricsConfig: MetricConfig[]
  rideDurationMinutes: number
  rideStartTime: number
}

const props = defineProps<Props>()

const chartRef = ref()
const metricsData = ref<Record<string, Array<[number, number]>>>({})
const metricsMaxValues = ref<Record<string, number>>({})
const metricsMinValues = ref<Record<string, number>>({})
const actualRideStartTime = ref<number>(0)

// Get recording state
const { isActivelyRecording, hasRecordedData } = useRecordingState()

// Initialize data for each metric
watch(() => props.metricsConfig, (config) => {
  config.forEach(metric => {
    if (!metricsData.value[metric.key]) {
      metricsData.value[metric.key] = []
    }
    if (!metricsMaxValues.value[metric.key]) {
      metricsMaxValues.value[metric.key] = -Infinity
    }
    if (!metricsMinValues.value[metric.key]) {
      metricsMinValues.value[metric.key] = Infinity
    }
  })
}, { immediate: true })

// Clear chart data when recording is cleared
watch(() => hasRecordedData.value, (hasData) => {
  if (!hasData) {
    Object.keys(metricsData.value).forEach(key => {
      metricsData.value[key] = []
      metricsMaxValues.value[key] = -Infinity
      metricsMinValues.value[key] = Infinity
    })
    actualRideStartTime.value = 0
  }
})

const metricColors = {
  power: '#ff6b6b',
  speed: '#4ecdc4', 
  cadence: '#45b7d1',
  heart_rate: '#f39c12'
} as const

const metricUnits = {
  power: 'W',
  speed: 'km/h',
  cadence: 'rpm',
  heart_rate: 'bpm'
} as const

// Function to normalize data points using min-max normalization
const getNormalizedData = (metricKey: string) => {
  const rawData = metricsData.value[metricKey] || []
  const maxValue = metricsMaxValues.value[metricKey]
  const minValue = metricsMinValues.value[metricKey]
  
  // If we don't have valid min/max values, return empty data
  if (maxValue === -Infinity || minValue === Infinity || maxValue === minValue) {
    return rawData.map(([time, value]) => [time, 0])
  }
  
  const range = maxValue - minValue
  const normalizedData = rawData.map(([time, value]) => [
    time, 
    range > 0 ? (value - minValue) / range : 0
  ])
  
  if (normalizedData.length > 0) {
    console.log(`📊 Normalized data for ${metricKey}: ${normalizedData.length} points, min: ${minValue}, max: ${maxValue}, range: ${range}`)
    console.log(`📊 Sample points:`, normalizedData.slice(0, 3))
  }
  
  return normalizedData
}

const chartOption = computed(() => {
  const rideDurationSeconds = props.rideDurationMinutes * 60
  
  const series = props.metricsConfig.map(metric => {
    const data = getNormalizedData(metric.key)
    return {
      name: `${metric.symbol} ${metric.name}`,
      type: 'line',
      data: data,
      smooth: true,
      symbol: 'none',
      lineStyle: {
        color: metricColors[metric.key as keyof typeof metricColors] || '#58a6ff',
        width: 2
      },
      animation: false
    }
  })

  console.log(`📊 Chart series data:`, series.map(s => ({ name: s.name, dataPoints: s.data.length })))

  return {
    backgroundColor: 'transparent',
    grid: {
      left: 0,
      right: 0,
      top: 0,
      bottom: 0
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#21262d',
      borderColor: '#30363d',
      textStyle: {
        color: '#e6edf3',
        fontSize: 12
      },
      formatter: (params: any) => {
        if (!params || params.length === 0) return ''
        
        const time = params[0].value[0]
        const minutes = Math.floor(time / 60)
        const seconds = Math.floor(time % 60)
        const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`
        
        let tooltip = `<div style="margin-bottom: 4px; font-weight: bold; font-size: 11px;">Time: ${timeStr}</div>`
        
        params.forEach((param: any) => {
          const normalizedValue = param.value[1]
          const metricKey = props.metricsConfig.find(m => `${m.symbol} ${m.name}` === param.seriesName)?.key
          const maxValue = metricsMaxValues.value[metricKey || '']
          const minValue = metricsMinValues.value[metricKey || '']
          const range = maxValue - minValue
          const actualValue = Math.round(normalizedValue * range + minValue)
          const unit = metricUnits[metricKey as keyof typeof metricUnits] || ''
          const color = param.color
          
          tooltip += `<div style="margin: 2px 0; font-size: 11px;">
            <span style="display: inline-block; width: 8px; height: 8px; background: ${color}; border-radius: 50%; margin-right: 6px;"></span>
            ${param.seriesName}: ${actualValue}${unit} (${Math.round(normalizedValue * 100)}%)
          </div>`
        })
        
        return tooltip
      }
    },
    xAxis: {
      type: 'value',
      show: false,
      min: 0,
      max: rideDurationSeconds
    },
    yAxis: {
      type: 'value',
      show: false,
      min: 0,
      max: 1
    },
    series
  }
})

// Function to add a data point for a specific metric
const addDataPoint = (metricKey: string, value: number, timestamp?: number) => {
  console.log(`📊 AllMetricsChart.addDataPoint called: ${metricKey} = ${value}, recording: ${isActivelyRecording.value}`)
  
  const dataTimestamp = timestamp || Date.now()
  
  // If this is the first data point and we don't have a proper ride start time, use this timestamp
  if (actualRideStartTime.value === 0 && (props.rideStartTime === 0 || !props.rideStartTime)) {
    actualRideStartTime.value = dataTimestamp
    console.log(`📊 Setting actual ride start time to: ${actualRideStartTime.value}`)
  }
  
  const rideStart = actualRideStartTime.value || props.rideStartTime * 1000
  const elapsedSeconds = (dataTimestamp * 1000 - rideStart) / 1000
  
  console.log(`📊 Elapsed seconds: ${elapsedSeconds}, ride duration: ${props.rideDurationMinutes * 60}`)
  console.log(`📊 Data timestamp: ${dataTimestamp}, Ride start: ${rideStart}`)
  
  // Only add points that are within the ride duration
  const rideDurationSeconds = props.rideDurationMinutes * 60
  if (elapsedSeconds >= 0 && elapsedSeconds <= rideDurationSeconds) {
    if (!metricsData.value[metricKey]) {
      metricsData.value[metricKey] = []
    }
    
    // Update min and max values for this metric
    if (value > metricsMaxValues.value[metricKey]) {
      metricsMaxValues.value[metricKey] = value
      console.log(`📊 New max value for ${metricKey}: ${value}`)
    }
    if (value < metricsMinValues.value[metricKey]) {
      metricsMinValues.value[metricKey] = value
      console.log(`📊 New min value for ${metricKey}: ${value}`)
    }
    
    // Check if we already have a data point at this time (avoid duplicates)
    const existingIndex = metricsData.value[metricKey].findIndex(([time]) => Math.abs(time - elapsedSeconds) < 1)
    
    if (existingIndex >= 0) {
      // Update existing point
      metricsData.value[metricKey][existingIndex] = [elapsedSeconds, value]
      console.log(`📊 Updated existing point for ${metricKey}: [${elapsedSeconds}, ${value}]`)
    } else {
      // Add new point
      metricsData.value[metricKey].push([elapsedSeconds, value])
      // Sort by time to maintain order
      metricsData.value[metricKey].sort((a, b) => a[0] - b[0])
      console.log(`📊 Added new point for ${metricKey}: [${elapsedSeconds}, ${value}]. Total points: ${metricsData.value[metricKey].length}`)
    }
  } else {
    console.log(`📊 Point rejected - outside time range: ${elapsedSeconds} not in [0, ${rideDurationSeconds}]`)
  }
}

// Expose the addDataPoint method so parent can call it
defineExpose({
  addDataPoint
})

onMounted(() => {
  console.log('✅ All Metrics Chart mounted')
})
</script>

<style scoped>
.all-metrics-chart {
  background: #0d1117;
  border-radius: 4px;
  border: 1px solid #21262d;
  padding: 8px;
  height: 100%;
  width: 100%;
  margin: 0;
}

.chart {
  width: 100% !important;
  height: 100% !important;
}

@media (max-width: 768px) {
  .all-metrics-chart {
    height: 180px;
    margin: 8px 0;
    padding: 12px;
  }
}
</style> 
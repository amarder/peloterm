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
      <canvas 
        :ref="canvasRef"
        class="chart-canvas"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { Chart, type ChartConfiguration } from 'chart.js/auto'
import type { MetricConfig } from '@/types'

interface Props {
  metric: MetricConfig
  value?: number
  rideDurationMinutes: number
  rideStartTime: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  chartCreated: [metricKey: string, chart: Chart]
  metricUpdate: [metricKey: string, value: number, timestamp: number]
}>()

const canvasRef = ref<HTMLCanvasElement>()
const chart = ref<Chart | null>(null)

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

const setupChart = () => {
  if (!canvasRef.value) return

  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return

  const range = chartRanges[props.metric.key as keyof typeof chartRanges] || { min: 0, max: 100 }

  const config: ChartConfiguration = {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Historical',
        data: [],
        borderColor: '#58a6ff',
        borderWidth: 1,
        pointRadius: 0,
        pointHitRadius: 0,
        fill: false,
        tension: 0.1
      }, {
        label: 'Current',
        data: [],
        borderColor: '#ef4444',
        backgroundColor: '#ef4444',
        borderWidth: 0,
        pointRadius: 3,
        pointHitRadius: 0,
        fill: false
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          enabled: false
        }
      },
      scales: {
        x: {
          display: false,
          type: 'linear',
          min: 0,
          max: props.rideDurationMinutes * 60
        },
        y: {
          display: false,
          min: range.min,
          max: range.max,
          beginAtZero: true
        }
      }
    }
  }

  // Configure Chart.js defaults
  Chart.defaults.color = '#7d8590'
  Chart.defaults.borderColor = '#30363d'
  Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'

  chart.value = new Chart(ctx, config)
  emit('chartCreated', props.metric.key, chart.value)
}

onMounted(async () => {
  await nextTick()
  setupChart()
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
  position: relative;
  background: #0d1117;
  border-radius: 4px;
  overflow: hidden;
}

.chart-canvas {
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
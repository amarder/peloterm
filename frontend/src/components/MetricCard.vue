<template>
  <div class="metric-card">
    <div class="metric-content">
      <span class="metric-symbol">{{ metric.symbol }}</span>
      <div class="metric-info">
        <span 
          class="metric-value"
          :class="metric.key"
        >
          {{ displayValue }}
        </span>
        <span class="metric-name">{{ metric.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MetricConfig } from '@/types'

interface Props {
  metric: MetricConfig
  value?: number
  timestamp?: number
  rideDurationMinutes: number
  rideStartTime: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  metricUpdate: [metricKey: string, value: number, timestamp: number]
}>()

const displayValue = computed(() => {
  if (props.value === undefined) return '--'
  
  if (props.metric.key === 'speed') {
    return props.value.toFixed(1)
  }
  return Math.round(props.value).toString()
})

// Emit metric updates when value changes (for the main chart)
const emitMetricUpdate = () => {
  if (props.value !== undefined && props.timestamp) {
    emit('metricUpdate', props.metric.key, props.value, props.timestamp)
  }
}

// Watch for value changes and emit updates
import { watch } from 'vue'
watch(() => [props.value, props.timestamp], () => {
  emitMetricUpdate()
})
</script>

<style scoped>
.metric-card {
  padding: 8px 12px;
  min-width: 120px;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  border-right: 1px solid #30363d;
  background: #161b22;
  transition: background-color 0.2s ease;
  height: 100%;
}

.metric-card:hover {
  background: #1c2128;
}

.metric-card:last-child {
  border-right: none;
}

.metric-content {
  display: flex;
  align-items: center;
  gap: 8px;
  text-align: left;
}

.metric-symbol {
  font-size: 20px;
  opacity: 0.8;
}

.metric-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  color: #58a6ff;
}

.metric-name {
  font-size: 10px;
  color: #7d8590;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 500;
}

.power { color: #ff6b6b; }
.speed { color: #4ecdc4; }
.cadence { color: #45b7d1; }
.heart_rate { color: #f39c12; }

@media (max-width: 768px) {
  .metric-card {
    min-width: unset;
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #30363d;
    padding: 12px 16px;
  }
  
  .metric-card:last-child {
    border-bottom: none;
  }
  
  .metric-content {
    gap: 12px;
  }
  
  .metric-symbol {
    font-size: 28px;
  }
  
  .metric-value {
    font-size: 28px;
  }
}
</style>
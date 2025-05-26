import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AllMetricsChart from '../AllMetricsChart.vue'
import type { MetricConfig } from '@/types'

// Mock vue-echarts
vi.mock('vue-echarts', () => ({
  default: {
    name: 'VChart',
    template: '<div class="mock-chart" :option="option"></div>',
    props: ['option', 'autoresize'],
    setup() {
      return {}
    }
  }
}))

// Mock echarts modules
vi.mock('echarts/core', () => ({
  use: vi.fn()
}))

vi.mock('echarts/renderers', () => ({
  CanvasRenderer: {}
}))

vi.mock('echarts/charts', () => ({
  LineChart: {}
}))

vi.mock('echarts/components', () => ({
  GridComponent: {},
  TooltipComponent: {},
  LegendComponent: {}
}))

// Mock useRecordingState
import { ref } from 'vue'
const mockIsActivelyRecording = ref(false)
const mockHasRecordedData = ref(true)

vi.mock('@/composables/useRecordingState', () => ({
  useRecordingState: () => ({
    isActivelyRecording: mockIsActivelyRecording,
    hasRecordedData: mockHasRecordedData
  })
}))

describe('AllMetricsChart', () => {
  const mockMetricsConfig: MetricConfig[] = [
    { name: 'Power', key: 'power', symbol: 'W', color: '#ff6b6b' },
    { name: 'Speed', key: 'speed', symbol: 'km/h', color: '#4ecdc4' },
    { name: 'Cadence', key: 'cadence', symbol: 'rpm', color: '#45b7d1' },
    { name: 'Heart Rate', key: 'heart_rate', symbol: 'bpm', color: '#f39c12' }
  ]

  const defaultProps = {
    metricsConfig: mockMetricsConfig,
    rideDurationMinutes: 45,
    rideStartTime: 1640995200
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockHasRecordedData.value = true
    mockIsActivelyRecording.value = false
  })

  it('should render the chart container', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    expect(wrapper.find('.all-metrics-chart').exists()).toBe(true)
    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('should initialize data for each metric', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Check that data structures are initialized for each metric
    mockMetricsConfig.forEach(metric => {
      expect(vm.metricsData[metric.key]).toEqual([])
      expect(vm.metricsMaxValues[metric.key]).toBe(-Infinity)
      expect(vm.metricsMinValues[metric.key]).toBe(Infinity)
    })
  })

  it('should add data points correctly', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Add a data point
    vm.addDataPoint('power', 250, 1640995230) // 30 seconds after start
    
    expect(vm.metricsData.power).toHaveLength(1)
    expect(vm.metricsData.power[0]).toEqual([30, 250])
    expect(vm.metricsMaxValues.power).toBe(250)
    expect(vm.metricsMinValues.power).toBe(250)
  })

  it('should sort data points by timestamp', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Add data points out of order
    vm.addDataPoint('power', 200, 1640995230) // 30 seconds
    vm.addDataPoint('power', 150, 1640995210) // 10 seconds  
    vm.addDataPoint('power', 300, 1640995220) // 20 seconds
    
    expect(vm.metricsData.power).toHaveLength(3)
    expect(vm.metricsData.power[0]).toEqual([10, 150])
    expect(vm.metricsData.power[1]).toEqual([20, 300])
    expect(vm.metricsData.power[2]).toEqual([30, 200])
  })

  it('should update existing data point if timestamp is very close', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Add initial data point
    vm.addDataPoint('power', 200, 1640995230) // 30 seconds
    expect(vm.metricsData.power).toHaveLength(1)
    
    // Add another point at nearly the same time (should update existing)
    vm.addDataPoint('power', 250, 1640995230.5) // 30.5 seconds
    expect(vm.metricsData.power).toHaveLength(1)
    expect(vm.metricsData.power[0]).toEqual([30.5, 250])
  })

  it('should ignore data points outside ride duration', () => {
    const wrapper = mount(AllMetricsChart, {
      props: {
        ...defaultProps,
        rideDurationMinutes: 1 // 1 minute ride
      }
    })

    const vm = wrapper.vm as any
    
    // Add point within duration
    vm.addDataPoint('power', 200, 1640995230) // 30 seconds
    expect(vm.metricsData.power).toHaveLength(1)
    
    // Add point outside duration
    vm.addDataPoint('power', 300, 1640995320) // 120 seconds (2 minutes)
    expect(vm.metricsData.power).toHaveLength(1) // Should still be 1
  })

  it('should ignore data points before ride start', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Add point before ride start
    vm.addDataPoint('power', 200, 1640995100) // 100 seconds before start
    expect(vm.metricsData.power).toHaveLength(0)
  })

  it('should track min and max values correctly', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    vm.addDataPoint('power', 200, 1640995210)
    vm.addDataPoint('power', 350, 1640995220)
    vm.addDataPoint('power', 150, 1640995230)
    
    expect(vm.metricsMinValues.power).toBe(150)
    expect(vm.metricsMaxValues.power).toBe(350)
  })

  it('should generate normalized data correctly', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Add data points with known range
    vm.addDataPoint('power', 100, 1640995210) // min
    vm.addDataPoint('power', 200, 1640995220) // max
    vm.addDataPoint('power', 150, 1640995230) // middle
    
    const normalizedData = vm.getNormalizedData('power')
    
    expect(normalizedData).toHaveLength(3)
    expect(normalizedData[0]).toEqual([10, 0])    // min value = 0
    expect(normalizedData[1]).toEqual([20, 1])    // max value = 1
    expect(normalizedData[2]).toEqual([30, 0.5])  // middle value = 0.5
  })

  it('should generate chart options with correct series', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Add some data
    vm.addDataPoint('power', 200, 1640995210)
    vm.addDataPoint('speed', 25, 1640995210)
    
    const chartOption = vm.chartOption
    
    expect(chartOption.series).toHaveLength(2) // power and speed
    expect(chartOption.series[0].name).toBe('W Power')
    expect(chartOption.series[1].name).toBe('km/h Speed')
  })

  it('should clear data when recording is cleared', async () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Add some data
    vm.addDataPoint('power', 200, 1640995210)
    expect(vm.metricsData.power).toHaveLength(1)
    
    // Simulate recording being cleared
    mockHasRecordedData.value = false
    await wrapper.vm.$nextTick()
    
    expect(vm.metricsData.power).toHaveLength(0)
    expect(vm.metricsMaxValues.power).toBe(-Infinity)
    expect(vm.metricsMinValues.power).toBe(Infinity)
  })

  it('should handle multiple metrics simultaneously', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Add data for different metrics
    vm.addDataPoint('power', 200, 1640995210)
    vm.addDataPoint('speed', 25, 1640995210)
    vm.addDataPoint('cadence', 90, 1640995210)
    vm.addDataPoint('heart_rate', 150, 1640995210)
    
    expect(vm.metricsData.power).toHaveLength(1)
    expect(vm.metricsData.speed).toHaveLength(1)
    expect(vm.metricsData.cadence).toHaveLength(1)
    expect(vm.metricsData.heart_rate).toHaveLength(1)
  })

  it('should expose addDataPoint method', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    expect(typeof wrapper.vm.addDataPoint).toBe('function')
  })

  it('should handle tooltip formatting correctly', () => {
    const wrapper = mount(AllMetricsChart, {
      props: defaultProps
    })

    const vm = wrapper.vm as any
    
    // Add data to establish min/max values
    vm.addDataPoint('power', 100, 1640995210)
    vm.addDataPoint('power', 200, 1640995220)
    
    const chartOption = vm.chartOption
    const tooltipFormatter = chartOption.tooltip.formatter
    
    // Mock tooltip params
    const mockParams = [{
      value: [10, 0.5], // 10 seconds, 50% normalized
      seriesName: 'W Power',
      color: '#ff6b6b'
    }]
    
    const tooltip = tooltipFormatter(mockParams)
    
    expect(tooltip).toContain('Time: 0:10')
    expect(tooltip).toContain('W Power')
    expect(tooltip).toContain('150W') // 50% of range (100-200) + min = 150
  })
}) 
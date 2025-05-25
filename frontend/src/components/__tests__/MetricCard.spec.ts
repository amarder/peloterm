import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MetricCard from '../MetricCard.vue'
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

// Mock echarts
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
  GridComponent: {}
}))

describe('MetricCard', () => {
  const mockMetric: MetricConfig = {
    name: 'Power',
    key: 'power',
    symbol: 'W',
    color: '#ff6b6b'
  }

  const defaultProps = {
    metric: mockMetric,
    rideDurationMinutes: 45,
    rideStartTime: 1640995200
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render metric symbol and display value', () => {
    const wrapper = mount(MetricCard, {
      props: {
        ...defaultProps,
        value: 250
      }
    })

    expect(wrapper.find('.metric-symbol').text()).toBe('W')
    expect(wrapper.find('.metric-value').text()).toBe('250')
  })

  it('should display "--" when value is undefined', () => {
    const wrapper = mount(MetricCard, {
      props: defaultProps
    })

    expect(wrapper.find('.metric-value').text()).toBe('--')
  })

  it('should format speed values with one decimal place', () => {
    const speedMetric: MetricConfig = {
      name: 'Speed',
      key: 'speed',
      symbol: 'mph',
      color: '#4ecdc4'
    }

    const wrapper = mount(MetricCard, {
      props: {
        ...defaultProps,
        metric: speedMetric,
        value: 25.67
      }
    })

    expect(wrapper.find('.metric-value').text()).toBe('25.7')
  })

  it('should round non-speed values to integers', () => {
    const wrapper = mount(MetricCard, {
      props: {
        ...defaultProps,
        value: 89.7
      }
    })

    expect(wrapper.find('.metric-value').text()).toBe('90')
  })

  it('should apply correct CSS class based on metric key', () => {
    const wrapper = mount(MetricCard, {
      props: {
        ...defaultProps,
        value: 250
      }
    })

    expect(wrapper.find('.metric-value').classes()).toContain('power')
  })

  it('should emit chartCreated event on mount', async () => {
    const wrapper = mount(MetricCard, {
      props: defaultProps
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('chartCreated')).toBeTruthy()
    expect(wrapper.emitted('chartCreated')![0]).toEqual(['power', expect.any(Object)])
  })

  it('should emit metricUpdate when value changes', async () => {
    const wrapper = mount(MetricCard, {
      props: defaultProps
    })

    await wrapper.setProps({ value: 250, timestamp: 1640995260 })

    expect(wrapper.emitted('metricUpdate')).toBeTruthy()
    expect(wrapper.emitted('metricUpdate')![0]).toEqual([
      'power',
      250,
      expect.any(Number)
    ])
  })

  it('should add data points to chart when value updates', async () => {
    const wrapper = mount(MetricCard, {
      props: defaultProps
    })

    // Update props to trigger the watcher
    await wrapper.setProps({
      value: 200,
      timestamp: 1640995230 // 30 seconds after start
    })

    // Wait for the watcher to process
    await wrapper.vm.$nextTick()

    const vm = wrapper.vm as any
    expect(vm.chartData).toHaveLength(1)
    expect(vm.chartData[0]).toEqual([30, 200]) // [elapsed seconds, value]
  })

  it('should sort chart data by timestamp', async () => {
    const wrapper = mount(MetricCard, {
      props: defaultProps
    })

    const vm = wrapper.vm as any

    // Add data points out of order
    vm.addDataPoint(100, 1640995230000) // 30 seconds
    vm.addDataPoint(200, 1640995210000) // 10 seconds
    vm.addDataPoint(150, 1640995220000) // 20 seconds

    expect(vm.chartData).toHaveLength(3)
    expect(vm.chartData[0]).toEqual([10, 200])
    expect(vm.chartData[1]).toEqual([20, 150])
    expect(vm.chartData[2]).toEqual([30, 100])
  })

  it('should update existing data point if timestamp is very close', async () => {
    const wrapper = mount(MetricCard, {
      props: defaultProps
    })

    const vm = wrapper.vm as any

    // Add initial data point
    vm.addDataPoint(100, 1640995230000) // 30 seconds
    expect(vm.chartData).toHaveLength(1)

    // Add another point at nearly the same time (should update existing)
    vm.addDataPoint(150, 1640995230500) // 30.5 seconds
    expect(vm.chartData).toHaveLength(1)
    expect(vm.chartData[0]).toEqual([30.5, 150])
  })

  it('should ignore data points outside ride duration', async () => {
    const wrapper = mount(MetricCard, {
      props: {
        ...defaultProps,
        rideDurationMinutes: 1 // 1 minute ride
      }
    })

    const vm = wrapper.vm as any

    // Add point within duration
    vm.addDataPoint(100, 1640995230000) // 30 seconds
    expect(vm.chartData).toHaveLength(1)

    // Add point outside duration
    vm.addDataPoint(200, 1640995320000) // 120 seconds (2 minutes)
    expect(vm.chartData).toHaveLength(1) // Should still be 1
  })

  it('should ignore data points before ride start', async () => {
    const wrapper = mount(MetricCard, {
      props: defaultProps
    })

    const vm = wrapper.vm as any

    // Add point before ride start
    vm.addDataPoint(100, 1640995100000) // 100 seconds before start
    expect(vm.chartData).toHaveLength(0)
  })

  it('should generate correct chart options for power metric', () => {
    const wrapper = mount(MetricCard, {
      props: {
        ...defaultProps,
        value: 250
      }
    })

    const vm = wrapper.vm as any
    const chartOption = vm.chartOption

    expect(chartOption.xAxis.max).toBe(2700) // 45 minutes * 60 seconds
    expect(chartOption.yAxis.min).toBe(0)
    expect(chartOption.yAxis.max).toBe(400) // Power range
    expect(chartOption.series[0].data).toBe(vm.chartData)
  })

  it('should generate correct chart options for speed metric', () => {
    const speedMetric: MetricConfig = {
      name: 'Speed',
      key: 'speed',
      symbol: 'mph',
      color: '#4ecdc4'
    }

    const wrapper = mount(MetricCard, {
      props: {
        ...defaultProps,
        metric: speedMetric,
        value: 25.5
      }
    })

    const vm = wrapper.vm as any
    const chartOption = vm.chartOption

    expect(chartOption.yAxis.min).toBe(0)
    expect(chartOption.yAxis.max).toBe(40) // Speed range
  })

  it('should use default range for unknown metric keys', () => {
    const unknownMetric: MetricConfig = {
      name: 'Unknown',
      key: 'unknown',
      symbol: 'X',
      color: '#ffffff'
    }

    const wrapper = mount(MetricCard, {
      props: {
        ...defaultProps,
        metric: unknownMetric,
        value: 50
      }
    })

    const vm = wrapper.vm as any
    const chartOption = vm.chartOption

    expect(chartOption.yAxis.min).toBe(0)
    expect(chartOption.yAxis.max).toBe(100) // Default range
  })
}) 
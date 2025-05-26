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
}) 
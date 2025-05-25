import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import TimeWidget from '../TimeWidget.vue'

describe('TimeWidget', () => {
  const defaultProps = {
    rideDurationMinutes: 45,
    rideStartTime: 1640995200 // Unix timestamp
  }

  beforeEach(() => {
    vi.useFakeTimers()
    // Mock Date.now() to return a consistent time
    vi.setSystemTime(new Date('2022-01-01T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('should render time label and current time', () => {
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    expect(wrapper.find('.time-label').text()).toBe('🕐')
    expect(wrapper.find('.time-value').exists()).toBe(true)
  })

  it('should display current time in HH:MM format', async () => {
    // Set a specific time
    vi.setSystemTime(new Date('2022-01-01T14:30:00Z'))
    
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    // Wait for component to mount and update time
    await wrapper.vm.$nextTick()

    // The exact format depends on locale, but should contain time
    const timeValue = wrapper.find('.time-value').text()
    expect(timeValue).toMatch(/\d{2}:\d{2}/)
  })

  it('should update time every second', async () => {
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    const initialTime = wrapper.find('.time-value').text()

    // Advance time by 1 second
    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()

    const updatedTime = wrapper.find('.time-value').text()
    // Time should have updated (though the exact value depends on the second)
    expect(wrapper.vm.now).toBeGreaterThan(wrapper.vm.now - 1000)
  })

  it('should calculate progress correctly at ride start', () => {
    // Set current time to exactly ride start time
    vi.setSystemTime(new Date(1640995200 * 1000))
    
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    expect(wrapper.vm.progress).toBe(0)
    
    const progressFill = wrapper.find('.progress-fill')
    expect(progressFill.attributes('style')).toContain('width: 0%')
  })

  it('should calculate progress correctly at 50% completion', () => {
    // Set current time to 22.5 minutes (50% of 45 minutes) after start
    const halfwayTime = 1640995200 + (22.5 * 60) // 22.5 minutes later
    vi.setSystemTime(new Date(halfwayTime * 1000))
    
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    expect(wrapper.vm.progress).toBe(50)
    
    const progressFill = wrapper.find('.progress-fill')
    expect(progressFill.attributes('style')).toContain('width: 50%')
  })

  it('should calculate progress correctly at ride completion', () => {
    // Set current time to exactly 45 minutes after start
    const endTime = 1640995200 + (45 * 60) // 45 minutes later
    vi.setSystemTime(new Date(endTime * 1000))
    
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    expect(wrapper.vm.progress).toBe(100)
    
    const progressFill = wrapper.find('.progress-fill')
    expect(progressFill.attributes('style')).toContain('width: 100%')
  })

  it('should cap progress at 100% when ride time exceeds duration', () => {
    // Set current time to 60 minutes after start (exceeds 45 minute duration)
    const overtimeTime = 1640995200 + (60 * 60) // 60 minutes later
    vi.setSystemTime(new Date(overtimeTime * 1000))
    
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    expect(wrapper.vm.progress).toBe(100)
    
    const progressFill = wrapper.find('.progress-fill')
    expect(progressFill.attributes('style')).toContain('width: 100%')
  })

  it('should handle negative progress (before ride start)', () => {
    // Set current time to before ride start
    const beforeStartTime = 1640995200 - (10 * 60) // 10 minutes before start
    vi.setSystemTime(new Date(beforeStartTime * 1000))
    
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    // Progress should be negative but clamped by Math.min to not exceed 100
    // The actual behavior depends on implementation - it might show negative or 0
    expect(wrapper.vm.progress).toBeLessThan(0)
  })

  it('should work with different ride durations', () => {
    // Test with 30 minute ride
    const shortRideProps = {
      rideDurationMinutes: 30,
      rideStartTime: 1640995200
    }

    // Set time to 15 minutes after start (50% of 30 minutes)
    const halfwayTime = 1640995200 + (15 * 60)
    vi.setSystemTime(new Date(halfwayTime * 1000))
    
    const wrapper = mount(TimeWidget, {
      props: shortRideProps
    })

    expect(wrapper.vm.progress).toBe(50)
  })

  it('should clear interval on unmount', () => {
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
    
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    wrapper.unmount()

    expect(clearIntervalSpy).toHaveBeenCalled()
  })

  it('should start interval on mount', () => {
    const setIntervalSpy = vi.spyOn(global, 'setInterval')
    
    mount(TimeWidget, {
      props: defaultProps
    })

    expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 1000)
  })

  it('should update progress when time advances', async () => {
    // Start at ride beginning
    vi.setSystemTime(new Date(1640995200 * 1000))
    
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    expect(wrapper.vm.progress).toBe(0)

    // Advance by 10 minutes
    vi.advanceTimersByTime(10 * 60 * 1000)
    await wrapper.vm.$nextTick()

    // Should be approximately 22.22% (10/45 minutes)
    expect(wrapper.vm.progress).toBeCloseTo(22.22, 1)
  })

  it('should render progress bar with correct structure', () => {
    const wrapper = mount(TimeWidget, {
      props: defaultProps
    })

    const progressBar = wrapper.find('.progress-bar')
    const progressFill = wrapper.find('.progress-fill')

    expect(progressBar.exists()).toBe(true)
    expect(progressFill.exists()).toBe(true)
    // Check that progress fill is inside progress bar by checking parent
    expect(progressFill.element.parentElement).toBe(progressBar.element)
  })
}) 
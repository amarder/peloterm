import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ControlButtons from '../ControlButtons.vue'

// Mock the composables
import { ref } from 'vue'
const mockUpdateRecordingState = vi.fn()
const mockShowAlert = vi.fn()
const mockIsRecording = ref(false)
const mockIsPaused = ref(false)
const mockHasRecordedData = ref(false)

vi.mock('@/composables/useRecordingState', () => ({
  useRecordingState: () => ({
    isRecording: mockIsRecording,
    isPaused: mockIsPaused,
    hasRecordedData: mockHasRecordedData,
    updateRecordingState: mockUpdateRecordingState
  })
}))

vi.mock('@/composables/useAlerts', () => ({
  useAlerts: () => ({
    showAlert: mockShowAlert
  })
}))

// Mock StravaUploadDialog component
vi.mock('../StravaUploadDialog.vue', () => ({
  default: {
    name: 'StravaUploadDialog',
    template: '<div class="mock-strava-dialog"></div>',
    props: ['isVisible', 'rideSummary', 'isUploading'],
    emits: ['close', 'upload']
  }
}))

// Mock WebSocket
const mockWebSocket = {
  send: vi.fn(),
  close: vi.fn(),
  readyState: WebSocket.OPEN,
  onopen: null,
  onmessage: null,
  onclose: null,
  onerror: null
}

global.WebSocket = vi.fn().mockImplementation(() => {
  // Simulate connection opening immediately
  setTimeout(() => {
    if (mockWebSocket.onopen) {
      mockWebSocket.onopen({} as Event)
    }
  }, 0)
  return mockWebSocket
}) as any

// Mock fetch for ride summary
global.fetch = vi.fn()

describe('ControlButtons', () => {
  let wrapper: any

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Reset mock state
    mockIsRecording.value = false
    mockIsPaused.value = false
    mockHasRecordedData.value = false
    
    // Reset WebSocket mock
    mockWebSocket.readyState = WebSocket.OPEN
    
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'http:',
        host: 'localhost:5173',
        hostname: 'localhost',
        port: '5173'
      },
      writable: true
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  it('should render all control buttons', () => {
    wrapper = mount(ControlButtons)

    expect(wrapper.find('.record-btn').exists()).toBe(true)
    expect(wrapper.find('.save-btn').exists()).toBe(true)
    expect(wrapper.find('.upload-btn').exists()).toBe(true)
    expect(wrapper.find('.clear-btn').exists()).toBe(true)
  })

  it('should display correct record button icon when not recording', () => {
    wrapper = mount(ControlButtons)

    const recordBtn = wrapper.find('.record-btn .btn-icon')
    expect(recordBtn.text()).toBe('🔴')
  })

  it('should display correct record button title when not recording', () => {
    wrapper = mount(ControlButtons)

    const recordBtn = wrapper.find('.record-btn')
    expect(recordBtn.attributes('title')).toBe('Record')
  })

  it('should send start_recording command when record button clicked', async () => {
    wrapper = mount(ControlButtons)
    
    // Wait for WebSocket to connect
    await new Promise(resolve => setTimeout(resolve, 10))

    const recordBtn = wrapper.find('.record-btn')
    await recordBtn.trigger('click')

    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({ command: 'start_recording' })
    )
  })

  it('should send pause_recording command when recording and record button clicked', async () => {
    // Mock recording state
    mockIsRecording.value = true
    mockIsPaused.value = false
    mockHasRecordedData.value = false

    wrapper = mount(ControlButtons)
    
    // Wait for WebSocket to connect
    await new Promise(resolve => setTimeout(resolve, 10))
    await wrapper.vm.$nextTick()

    const recordBtn = wrapper.find('.record-btn')
    await recordBtn.trigger('click')

    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({ command: 'pause_recording' })
    )
  })

  it('should send resume_recording command when paused and record button clicked', async () => {
    // Mock paused state
    mockIsRecording.value = false
    mockIsPaused.value = true
    mockHasRecordedData.value = true

    wrapper = mount(ControlButtons)
    
    // Wait for WebSocket to connect
    await new Promise(resolve => setTimeout(resolve, 10))
    await wrapper.vm.$nextTick()

    const recordBtn = wrapper.find('.record-btn')
    await recordBtn.trigger('click')

    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({ command: 'resume_recording' })
    )
  })

  it('should send save_recording command when save button clicked', async () => {
    // Mock state with recorded data
    mockIsRecording.value = false
    mockIsPaused.value = false
    mockHasRecordedData.value = true

    wrapper = mount(ControlButtons)
    
    // Wait for WebSocket to connect
    await new Promise(resolve => setTimeout(resolve, 10))
    await wrapper.vm.$nextTick()

    const saveBtn = wrapper.find('.save-btn')
    await saveBtn.trigger('click')

    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({ command: 'save_recording' })
    )
  })

  it('should disable save button when no recorded data', () => {
    wrapper = mount(ControlButtons)

    const saveBtn = wrapper.find('.save-btn')
    expect(saveBtn.element.disabled).toBe(true)
  })

  it('should fetch ride summary when upload button clicked', async () => {
    // Mock state with recorded data
    mockIsRecording.value = false
    mockIsPaused.value = false
    mockHasRecordedData.value = true

    const mockRideSummary = {
      duration: 1800,
      data_points: 100,
      avg_power: 200,
      max_power: 350
    }

    vi.mocked(fetch).mockResolvedValueOnce({
      json: () => Promise.resolve(mockRideSummary)
    } as Response)

    wrapper = mount(ControlButtons)
    await wrapper.vm.$nextTick()

    const uploadBtn = wrapper.find('.upload-btn')
    await uploadBtn.trigger('click')

    expect(fetch).toHaveBeenCalledWith('/api/ride-summary')
  })

  it('should show upload dialog after fetching ride summary', async () => {
    // Mock state with recorded data
    mockIsRecording.value = false
    mockIsPaused.value = false
    mockHasRecordedData.value = true

    const mockRideSummary = {
      duration: 1800,
      data_points: 100
    }

    vi.mocked(fetch).mockResolvedValueOnce({
      json: () => Promise.resolve(mockRideSummary)
    } as Response)

    wrapper = mount(ControlButtons)
    await wrapper.vm.$nextTick()

    const uploadBtn = wrapper.find('.upload-btn')
    await uploadBtn.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.showDialog).toBe(true)
    expect(wrapper.vm.rideSummary).toEqual(mockRideSummary)
  })

  it('should disable upload button when no recorded data', () => {
    wrapper = mount(ControlButtons)

    const uploadBtn = wrapper.find('.upload-btn')
    expect(uploadBtn.element.disabled).toBe(true)
  })

  it('should send clear_recording command when clear button clicked', async () => {
    // Set state so clear button is enabled (has recorded data)
    mockHasRecordedData.value = true
    
    wrapper = mount(ControlButtons)
    
    // Wait for WebSocket to connect
    await new Promise(resolve => setTimeout(resolve, 10))

    const clearBtn = wrapper.find('.clear-btn')
    await clearBtn.trigger('click')

    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({ command: 'clear_recording' })
    )
  })

  it('should handle WebSocket connection in development mode', () => {
    wrapper = mount(ControlButtons)

    expect(WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws/control')
  })

  it('should handle WebSocket connection in production mode', () => {
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'https:',
        host: 'example.com',
        hostname: 'example.com',
        port: '443'
      },
      writable: true
    })

    wrapper = mount(ControlButtons)

    expect(WebSocket).toHaveBeenCalledWith('wss://example.com/ws/control')
  })

  it('should handle control response messages', async () => {
    wrapper = mount(ControlButtons)

    // Simulate WebSocket message
    const mockMessage = {
      data: JSON.stringify({
        type: 'recording_started'
      })
    }

    if (mockWebSocket.onmessage) {
      mockWebSocket.onmessage(mockMessage)
    }

    expect(mockUpdateRecordingState).toHaveBeenCalledWith(true, false, false)
    expect(mockShowAlert).toHaveBeenCalledWith('Recording started', 'success')
  })

  it('should handle error responses', async () => {
    wrapper = mount(ControlButtons)

    const mockMessage = {
      data: JSON.stringify({
        type: 'error',
        message: 'Test error'
      })
    }

    if (mockWebSocket.onmessage) {
      mockWebSocket.onmessage(mockMessage)
    }

    expect(mockShowAlert).toHaveBeenCalledWith('Test error', 'error')
  })

  it('should send upload command with custom name and description', async () => {
    wrapper = mount(ControlButtons)
    
    // Wait for WebSocket to connect
    await new Promise(resolve => setTimeout(resolve, 10))

    const customName = 'My Custom Ride'
    const customDescription = 'A great workout'

    wrapper.vm.handleUploadConfirm(customName, customDescription)

    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({
        command: 'upload_to_strava',
        name: customName,
        description: customDescription
      })
    )
  })

  it('should close WebSocket on component unmount', () => {
    wrapper = mount(ControlButtons)
    wrapper.unmount()

    expect(mockWebSocket.close).toHaveBeenCalled()
  })

}) 
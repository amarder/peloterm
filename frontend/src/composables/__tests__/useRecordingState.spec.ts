import { describe, it, expect, beforeEach } from 'vitest'
import { useRecordingState } from '../useRecordingState'

describe('useRecordingState', () => {
  beforeEach(() => {
    // Reset the global state before each test
    const { updateRecordingState } = useRecordingState()
    updateRecordingState(false, false, false)
  })

  it('should initialize with default values', () => {
    const { isRecording, isPaused, hasRecordedData, isActivelyRecording } = useRecordingState()

    expect(isRecording.value).toBe(false)
    expect(isPaused.value).toBe(false)
    expect(hasRecordedData.value).toBe(false)
    expect(isActivelyRecording.value).toBe(false)
  })

  it('should update recording state correctly', () => {
    const { isRecording, isPaused, hasRecordedData, updateRecordingState } = useRecordingState()

    updateRecordingState(true, false, false)

    expect(isRecording.value).toBe(true)
    expect(isPaused.value).toBe(false)
    expect(hasRecordedData.value).toBe(false)
  })

  it('should update paused state correctly', () => {
    const { isRecording, isPaused, hasRecordedData, updateRecordingState } = useRecordingState()

    updateRecordingState(false, true, true)

    expect(isRecording.value).toBe(false)
    expect(isPaused.value).toBe(true)
    expect(hasRecordedData.value).toBe(true)
  })

  it('should calculate isActivelyRecording correctly when recording', () => {
    const { isActivelyRecording, updateRecordingState } = useRecordingState()

    updateRecordingState(true, false, false)

    expect(isActivelyRecording.value).toBe(true)
  })

  it('should calculate isActivelyRecording correctly when paused', () => {
    const { isActivelyRecording, updateRecordingState } = useRecordingState()

    updateRecordingState(false, true, true)

    expect(isActivelyRecording.value).toBe(false)
  })

  it('should calculate isActivelyRecording correctly when not recording', () => {
    const { isActivelyRecording, updateRecordingState } = useRecordingState()

    updateRecordingState(false, false, false)

    expect(isActivelyRecording.value).toBe(false)
  })

  it('should share state between multiple instances', () => {
    const instance1 = useRecordingState()
    const instance2 = useRecordingState()

    instance1.updateRecordingState(true, false, false)

    expect(instance2.isRecording.value).toBe(true)
    expect(instance2.isPaused.value).toBe(false)
    expect(instance2.hasRecordedData.value).toBe(false)
    expect(instance2.isActivelyRecording.value).toBe(true)
  })

  it('should provide readonly access to state values', () => {
    const { isRecording, isPaused, hasRecordedData } = useRecordingState()

    // These should be readonly refs, so direct assignment should be ignored
    const originalIsRecording = isRecording.value
    const originalIsPaused = isPaused.value
    const originalHasRecordedData = hasRecordedData.value

    // @ts-expect-error - Testing readonly nature
    isRecording.value = true
    // @ts-expect-error - Testing readonly nature
    isPaused.value = true
    // @ts-expect-error - Testing readonly nature
    hasRecordedData.value = true

    // Values should remain unchanged due to readonly nature
    expect(isRecording.value).toBe(originalIsRecording)
    expect(isPaused.value).toBe(originalIsPaused)
    expect(hasRecordedData.value).toBe(originalHasRecordedData)
  })

  it('should handle recording workflow correctly', () => {
    const { isRecording, isPaused, hasRecordedData, isActivelyRecording, updateRecordingState } = useRecordingState()

    // Start recording
    updateRecordingState(true, false, false)
    expect(isRecording.value).toBe(true)
    expect(isPaused.value).toBe(false)
    expect(hasRecordedData.value).toBe(false)
    expect(isActivelyRecording.value).toBe(true)

    // Pause recording
    updateRecordingState(false, true, true)
    expect(isRecording.value).toBe(false)
    expect(isPaused.value).toBe(true)
    expect(hasRecordedData.value).toBe(true)
    expect(isActivelyRecording.value).toBe(false)

    // Resume recording
    updateRecordingState(true, false, true)
    expect(isRecording.value).toBe(true)
    expect(isPaused.value).toBe(false)
    expect(hasRecordedData.value).toBe(true)
    expect(isActivelyRecording.value).toBe(true)

    // Stop recording
    updateRecordingState(false, false, true)
    expect(isRecording.value).toBe(false)
    expect(isPaused.value).toBe(false)
    expect(hasRecordedData.value).toBe(true)
    expect(isActivelyRecording.value).toBe(false)

    // Clear recording
    updateRecordingState(false, false, false)
    expect(isRecording.value).toBe(false)
    expect(isPaused.value).toBe(false)
    expect(hasRecordedData.value).toBe(false)
    expect(isActivelyRecording.value).toBe(false)
  })

  it('should handle edge cases correctly', () => {
    const { isRecording, isPaused, hasRecordedData, isActivelyRecording, updateRecordingState } = useRecordingState()

    // Recording and paused at the same time (should not be actively recording)
    updateRecordingState(true, true, true)
    expect(isRecording.value).toBe(true)
    expect(isPaused.value).toBe(true)
    expect(hasRecordedData.value).toBe(true)
    expect(isActivelyRecording.value).toBe(false) // Not actively recording when paused
  })
}) 
import { ref, readonly, computed } from 'vue'

// Global recording state
const isRecording = ref(false)
const isPaused = ref(false)
const hasRecordedData = ref(false)

export function useRecordingState() {
  const updateRecordingState = (recording: boolean, paused: boolean, hasData: boolean) => {
    isRecording.value = recording
    isPaused.value = paused
    hasRecordedData.value = hasData
  }

  return {
    isRecording: readonly(isRecording),
    isPaused: readonly(isPaused),
    hasRecordedData: readonly(hasRecordedData),
    updateRecordingState,
    isActivelyRecording: computed(() => isRecording.value && !isPaused.value)
  }
} 
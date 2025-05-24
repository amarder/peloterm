<template>
  <div class="video-panel" ref="videoPanelRef">
    <iframe 
      :src="iframeUrl" 
      allowfullscreen
      class="video-iframe"
    />
    <div 
      class="resize-handle"
      :class="{ dragging: isResizing }"
      @mousedown="startResize"
      @dblclick="resetSize"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface Props {
  iframeUrl: string
}

defineProps<Props>()

const emit = defineEmits<{
  resize: []
}>()

const videoPanelRef = ref<HTMLElement>()
const isResizing = ref(false)
const defaultHeight = 100

let startY = 0
let startHeight = 0

const startResize = (event: MouseEvent) => {
  if (!videoPanelRef.value) return
  
  isResizing.value = true
  startY = event.clientY
  startHeight = videoPanelRef.value.offsetHeight
  document.body.style.cursor = 'row-resize'
  event.preventDefault()
}

const handleMouseMove = (event: MouseEvent) => {
  if (!isResizing.value || !videoPanelRef.value) return
  
  const deltaY = startY - event.clientY
  const newHeight = Math.max(300, Math.min(window.innerHeight - 200, startHeight + deltaY))
  videoPanelRef.value.style.height = `${newHeight}px`
  
  emit('resize')
}

const handleMouseUp = () => {
  if (isResizing.value) {
    isResizing.value = false
    document.body.style.cursor = ''
    emit('resize')
  }
}

const resetSize = () => {
  if (!videoPanelRef.value) return
  videoPanelRef.value.style.height = 'auto'
  emit('resize')
}

onMounted(() => {
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
})
</script>

<style scoped>
.video-panel {
  flex: 1;
  position: relative;
  background: #161b22;
  min-height: 300px;
}

.video-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.resize-handle {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: #30363d;
  cursor: row-resize;
  transition: background-color 0.2s;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: #58a6ff;
}

.resize-handle::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 50px;
  height: 2px;
  background: currentColor;
  opacity: 0;
  transition: opacity 0.2s;
}

.resize-handle:hover::after {
  opacity: 0.5;
}

@media (max-width: 768px) {
  .video-panel {
    height: 60vh;
  }
  
  .resize-handle {
    display: none;
  }
}
</style> 
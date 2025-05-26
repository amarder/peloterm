<template>
  <div class="alert-container">
    <transition-group name="alert" tag="div">
      <div
        v-for="alert in alerts"
        :key="alert.id"
        :class="['alert', `alert-${alert.type}`]"
        @click="removeAlert(alert.id)"
      >
        <span class="alert-message">{{ alert.message }}</span>
        <button class="alert-close" @click.stop="removeAlert(alert.id)">×</button>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { useAlerts } from '@/composables/useAlerts'

const { alerts, removeAlert } = useAlerts()
</script>

<style scoped>
.alert-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(8px);
  border: 1px solid;
  min-width: 300px;
  max-width: 400px;
  pointer-events: auto;
  cursor: pointer;
  transition: all 0.3s ease;
}

.alert:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

.alert-success {
  background: rgba(35, 134, 54, 0.9);
  color: #ffffff;
  border-color: #2ea043;
}

.alert-error {
  background: rgba(218, 54, 51, 0.9);
  color: #ffffff;
  border-color: #f85149;
}

.alert-info {
  background: rgba(31, 111, 235, 0.9);
  color: #ffffff;
  border-color: #58a6ff;
}

.alert-message {
  flex: 1;
  font-weight: 500;
  font-size: 14px;
  line-height: 1.4;
}

.alert-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  padding: 0;
  margin-left: 12px;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s ease;
}

.alert-close:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Transition animations */
.alert-enter-active,
.alert-leave-active {
  transition: all 0.3s ease;
}

.alert-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.alert-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.alert-move {
  transition: transform 0.3s ease;
}

@media (max-width: 768px) {
  .alert-container {
    top: 10px;
    right: 10px;
    left: 10px;
  }
  
  .alert {
    min-width: auto;
    max-width: none;
  }
}
</style> 
<template>
  <!-- 展开按钮（固定在左上角） -->
  <button
    v-show="showToggle"
    class="sidebar-toggle"
    :class="{ visible: showToggle }"
    aria-label="展开侧边栏"
    @click="expand"
  >
    <img src="/asset/sidebar.squares.leading.svg" class="asset-icon" alt="展开" />
  </button>
</template>

<script setup>
defineProps({
  showToggle: Boolean
})

const emit = defineEmits(['expand'])
function expand() {
  emit('expand')
}
</script>

<style scoped>
.sidebar-toggle {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 100;
  width: 44px;
  height: 44px;
  background: #FFFFFFEB;
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 12px;
  box-shadow:
    0 4px 16px rgba(0, 20, 60, 0.08),
    0 2px 4px rgba(0, 20, 60, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0;
  pointer-events: none;
  transform: scale(0.8);
}

.sidebar-toggle.visible {
  opacity: 1;
  pointer-events: auto;
  transform: scale(1);
}

.sidebar-toggle:hover {
  background: #FFFFFF;
  box-shadow:
    0 6px 20px rgba(0, 20, 60, 0.12),
    0 3px 6px rgba(0, 20, 60, 0.06);
  transform: scale(1.05);
}

.sidebar-toggle:active {
  transform: scale(0.95);
}
</style>

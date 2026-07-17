<template>
  <div class="search-box">
    <div class="search-inner">
      <button class="icon-btn" aria-label="附加">
        <img src="/asset/paperclip.svg" class="asset-icon" alt="附加" />
      </button>
      <input
        type="text"
        class="search-input"
        :placeholder="placeholder"
        :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value)"
        @keydown.enter="$emit('submit', modelValue)"
      />
      <div class="search-extension" @click="toggleModel" :title="'点击切换为' + nextModelLabel">
        {{ currentModel }}
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
      </div>
      <span class="search-divider"></span>
      <button class="icon-btn" aria-label="语音">
        <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '输入您的问题' },
  extensionLabel: { type: String, default: 'DeepSeek-V4-Flash' }
})

const emit = defineEmits(['update:modelValue', 'submit', 'model-change'])

const models = ['DeepSeek-V4-Flash', 'DeepSeek-V4-Pro']
const currentModel = ref(props.extensionLabel || models[0])
const nextModelLabel = computed(() => models.find(m => m !== currentModel.value) || models[0])

function toggleModel() {
  const next = models.find(m => m !== currentModel.value) || models[0]
  currentModel.value = next
  emit('model-change', next)
}
</script>

<style scoped>
.search-box {
  width: 100%;
  max-width: 640px;
}
.search-inner {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.06);
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.60);
  display: flex;
  align-items: center;
  padding: 6px 12px 6px 16px;
  gap: 8px;
}
.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 16px;
  color: #1f2937;
  padding: 15px 0;
  min-width: 0;
}
.search-input::placeholder {
  color: #9ca3af;
}

.search-extension {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 14px;
  color: #4b5563;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}
.search-extension:hover {
  background: rgba(0, 0, 0, 0.04);
}

.search-divider {
  width: 1px;
  height: 20px;
  background: #d1d5db;
  flex-shrink: 0;
}

.icon-btn {
  padding: 6px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.icon-btn:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #374151;
}

@media (max-width: 640px) {
  .search-inner {
    padding: 4px 8px 4px 12px;
    flex-wrap: wrap;
  }
}
</style>

<template>
  <div class="search-box" :class="{ 'search-box-dark': isDark }">
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
        @keydown.enter="$emit('submit', $event.target.value)"
      />
      <div class="search-extension" @click="toggleModel" :title="'点击切换为 ' + nextModelLabel">
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
  extensionLabel: { type: String, default: 'DeepSeek-V4-Flash' },
  isDark: { type: Boolean, default: false }
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
  background: var(--input-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: var(--input-shadow);
  border-radius: 9999px;
  border: 1px solid var(--input-border);
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
  color: var(--text-primary);
  padding: 15px 0;
  min-width: 0;
}
.search-input::placeholder {
  color: var(--text-faint);
}

.search-extension {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}
.search-extension:hover {
  background: var(--hover-bg);
}

.search-divider {
  width: 1px;
  height: 20px;
  background: var(--border-light);
  flex-shrink: 0;
}

.icon-btn {
  padding: 6px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.icon-btn:hover {
  background: var(--hover-bg);
  color: var(--text-secondary);
}

/* -- 深色模式下 paperclip 图标显示为白色 -- */
.search-box-dark .asset-icon {
  filter: brightness(0) invert(1);
}

@media (max-width: 640px) {
  .search-inner {
    padding: 4px 8px 4px 12px;
    flex-wrap: wrap;
  }
}
</style>

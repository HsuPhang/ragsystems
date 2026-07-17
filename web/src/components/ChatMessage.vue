<template>
  <div class="chat-message" :class="{ 'is-user': message.role === 'user' }">
    <div class="bubble" :class="{ 'is-user': message.role === 'user', 'is-ai': message.role === 'assistant' }">
      <div v-if="message.role === 'user'" class="bubble-content">{{ message.content }}</div>
      <div v-else class="bubble-content markdown-body" v-html="renderedContent"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  message: { type: Object, required: true },
  streaming: { type: Boolean, default: false },
})

const displayedText = ref('')
let typewriterTimer = null

const renderedContent = computed(() => {
  const text = displayedText.value
  if (!text) return ''
  return marked.parse(text, { breaks: true, gfm: true })
})

// 打字机效果：逐字显示
watch(
  () => props.message.content,
  (newContent) => {
    if (!newContent || !props.streaming) {
      displayedText.value = newContent || ''
      return
    }

    let idx = 0
    displayedText.value = ''

    function tick() {
      if (idx < newContent.length) {
        displayedText.value += newContent[idx++]
        typewriterTimer = setTimeout(tick, 20 + Math.random() * 20)
      }
    }
    tick()
  },
  { immediate: true }
)

onUnmounted(() => {
  if (typewriterTimer) clearTimeout(typewriterTimer)
})
</script>

<style scoped>
.chat-message {
  display: flex;
  margin-bottom: 8px;
}

.chat-message.is-user {
  justify-content: flex-end;
}

.bubble {
  max-width: 75%;
  padding: 12px 18px;
  border-radius: 18px;
  line-height: 1.6;
  font-size: 15px;
  word-break: break-word;
}

.bubble.is-user {
  background: #ffffff;
  color: #1f2937;
  border-bottom-right-radius: 4px;
}

.bubble.is-ai {
  background: #e8f0fe;
  color: #1f2937;
  border-bottom-left-radius: 4px;
}

.markdown-body :deep(p) {
  margin: 0 0 8px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 13px;
}

.markdown-body :deep(code) {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.markdown-body :deep(:not(pre) > code) {
  background: #f1f5f9;
  color: #2563eb;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.markdown-body :deep(li) {
  margin-bottom: 4px;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid #93c5fd;
  padding-left: 12px;
  margin: 8px 0;
  color: #475569;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 12px 0 6px;
  font-weight: 600;
}

.markdown-body :deep(a) {
  color: #2563eb;
  text-decoration: underline;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 14px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #d1d5db;
  padding: 6px 10px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f1f5f9;
  font-weight: 600;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #d1d5db;
  margin: 12px 0;
}
</style>

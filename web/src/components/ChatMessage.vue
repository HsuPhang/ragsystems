<template>
  <div class="chat-message" :class="{ 'is-user': message.role === 'user' }">
    <div class="bubble" :class="{ 'is-user': message.role === 'user', 'is-ai': message.role === 'assistant' }">
      <div v-if="message.role === 'user'" class="bubble-content">{{ message.content }}</div>
      <div v-else class="bubble-content markdown-body" v-html="displayHtml"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  message: { type: Object, required: true },
  streaming: { type: Boolean, default: false },
})

const displayedText = ref('')
let typewriterTimer = null

// Fully rendered markdown from complete content (only recomputes when full content changes, not during typewriter)
const finalRenderedContent = computed(() => {
  const text = props.message.content
  if (!text) return ''
  return DOMPurify.sanitize(marked.parse(text, { breaks: true, gfm: true }))
})

// Display HTML: during typewriter, show plain escaped text; when done, show rendered + sanitized markdown
const displayHtml = computed(() => {
  if (props.streaming) {
    return escapeHtml(displayedText.value)
  }
  return finalRenderedContent.value
})

function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

// 打字机效果：逐字显示
watch(
  () => props.message.content,
  (newContent) => {
    // Clear previous typewriter timer to prevent stale closures appending old content
    if (typewriterTimer) clearTimeout(typewriterTimer)

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

// 监控 streaming 变化：如果 streaming 关闭且内容已经完整，直接显示全部
watch(
  () => props.streaming,
  (isStreaming) => {
    if (!isStreaming && props.message.content) {
      displayedText.value = props.message.content
    }
  }
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
  background: var(--bubble-user-bg);
  color: var(--bubble-user-color);
  border-bottom-right-radius: 4px;
}

.bubble.is-ai {
  background: var(--bubble-ai-bg);
  color: var(--bubble-ai-color);
  border-bottom-left-radius: 4px;
  border: 1px solid var(--bubble-ai-border);
}

.markdown-body :deep(p) {
  margin: 0 0 8px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(pre) {
  background: var(--code-bg);
  color: var(--code-color);
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
  background: var(--hover-bg);
  color: var(--accent);
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
  border-left: 3px solid var(--accent-light);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--text-muted);
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 12px 0 6px;
  font-weight: 600;
}

.markdown-body :deep(a) {
  color: var(--accent);
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
  border: 1px solid var(--border-light);
  padding: 6px 10px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--hover-bg);
  font-weight: 600;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-light);
  margin: 12px 0;
}
</style>

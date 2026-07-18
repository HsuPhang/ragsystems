<template>
  <div class="app-wrapper">
    <!-- 移动端遮罩 -->
    <div class="sidebar-mask" :class="{ show: showMask }" @click="closeMobile"></div>

    <!-- 展开按钮 -->
    <SidebarToggle :show-toggle="showToggle" @expand="expand" />

    <!-- 侧边栏 -->
    <Sidebar
      :visible="sidebarVisible"
      :is-mobile="isMobile"
      :app-name="appName"
      :user-name="userName"
      :shortcut-text="shortcutText"
      :nav-items="navItems"
      :sections="sections"
      :recent-items="recentItems"
      @collapse="collapse"
      @new-chat="handleNewChat"
      @navigate="handleNavigate"
      @select-recent="handleSelectRecent"
      @logout="handleLogout"
    />

    <!-- 主内容 -->
    <MainContent
      :welcome-message="welcomeMessage"
      :search-placeholder="searchPlaceholder"
      :extension-label="extensionLabel"
      :is-authenticated="isAuthenticated"
      :user-name="userName"
      :messages="messages"
      @toggle-mobile="toggleMobile"
      @submit="handleSubmit"
      @login-success="handleLoginSuccess"
      @model-change="handleModelChange"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from '../components/Sidebar.vue'
import SidebarToggle from '../components/SidebarToggle.vue'
import MainContent from '../components/MainContent.vue'
import { useSidebar } from '../composables/useSidebar.js'
import { useAuth } from '../composables/useAuth.js'
import { getSystemConfig, getRecentSessions, sendChatMessage, getChatHistory } from '../services/api.js'

const { username: authUsername, isAuthenticated, logout } = useAuth()

// ===== 动态配置（从后端获取，失败时用默认值兜底） =====
const appName = ref('Gemini')
const userName = ref('Hsu Phang')
const shortcutText = ref('Ctrl+Shift+O')
const searchPlaceholder = ref('问问 Gemini')
const extensionLabel = ref('Flash 扩展')
const navItems = ref([
  { label: '合集', icon: 'circle.grid.2x2.svg', route: '/collections' }
])
const sections = ref([
  {
    title: '笔记本',
    items: [
      { label: '新建笔记本', icon: 'pencil.and.outline.svg', route: '/notes/new' }
    ]
  }
])
const recentItems = ref([])

// ===== 欢迎语（优先用后端值，否则从 userName 动态生成） =====
const welcomeMessage = ref('接下来想聊点什么？')
function updateWelcomeMessage(name, backendMessage) {
  welcomeMessage.value = backendMessage || `${name}，接下来想聊点什么？`
}

// ===== 侧边栏状态 =====
const {
  showToggle,
  showMask,
  sidebarVisible,
  isMobile,
  collapse,
  expand,
  toggleMobile,
  closeMobile
} = useSidebar()

// ===== 会话状态 =====
const currentSessionId = ref(null)
const messages = ref([])
const loadingRecent = ref(false)
let refreshTimer = null

// ===== 从后端加载用户配置和会话列表 =====
async function loadUserData() {
  const [configRes, sessionsRes] = await Promise.allSettled([
    getSystemConfig(),
    getRecentSessions(),
  ])

  if (configRes.status === 'fulfilled' && configRes.value?.data) {
    const cfg = configRes.value.data
    if (cfg.appName !== undefined) appName.value = cfg.appName
    if (cfg.userName !== undefined) userName.value = cfg.userName
    if (cfg.shortcutText !== undefined) shortcutText.value = cfg.shortcutText
    if (cfg.searchPlaceholder !== undefined) searchPlaceholder.value = cfg.searchPlaceholder
    if (cfg.extensionLabel !== undefined) extensionLabel.value = cfg.extensionLabel
    updateWelcomeMessage(cfg.userName || 'Hsu Phang', cfg.welcomeMessage)
    if (cfg.navItems?.length) navItems.value = cfg.navItems
    if (cfg.sections?.length) sections.value = cfg.sections
  } else {
    updateWelcomeMessage('Hsu Phang', null)
  }

  if (sessionsRes.status === 'fulfilled' && sessionsRes.value?.data) {
    const items = sessionsRes.value.data
    recentItems.value = items.length
      ? items.map(s => ({ id: s.id, title: s.title }))
      : []
  } else {
    recentItems.value = []
  }
}

// ===== 初始化：从后端加载数据 =====
onMounted(loadUserData)

function getDefaultRecentItems() {
  return [
    { id: '1', title: '仿ChatGPT UI界面代码分享' },
    { id: '2', title: '大模型知识库系统前端设计方案' },
    { id: '3', title: '高德地图 HTML 画圈示例' },
    { id: '4', title: 'ArkUI 状态栏重叠问题解决' },
    { id: '5', title: 'ArkUI 卡片遮挡标签栏的解决方案' },
    { id: '6', title: 'ArkUI 代码 Bug 修复指南' },
    { id: '7', title: 'ArkUI 沉浸式模糊过渡优化' },
    { id: '8', title: 'ArkUI 错误修复指南' },
  ]
}

// ===== 交互事件 =====
function handleNewChat() {
  currentSessionId.value = null
  messages.value = []
}

function handleNavigate(item) {
  console.log('导航:', item)
}

async function handleSelectRecent(item) {
  loadingRecent.value = true
  try {
    const res = await getChatHistory(item.id)
    if (res?.data) {
      currentSessionId.value = item.id
      messages.value = res.data.map(m => ({
        role: m.role,
        content: m.content,
      }))
    }
  } catch (e) {
    console.warn('加载会话历史失败:', e)
  } finally {
    loadingRecent.value = false
  }
}

async function handleSubmit(query) {
  if (!query?.trim()) return

  // 添加用户消息
  messages.value.push({ role: 'user', content: query })

  // 添加占位的 AI 消息（显示"思考中..."，用于打字机效果）
  const aiIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '思考中...', streaming: true })

  try {
    const res = await sendChatMessage(query, {
      session_id: currentSessionId.value,
      use_rerank: true,
    })
    currentSessionId.value = res.session_id

    // 通过数组索引更新，确保 Vue 响应式系统能检测到变化
    messages.value[aiIndex] = {
      role: 'assistant',
      content: res.answer,
      streaming: true,
    }

    // 打字机效果结束后关闭 streaming
    const totalLen = res.answer.length
    const typeDelay = totalLen * 40 + 500
    setTimeout(() => {
      const msg = messages.value[aiIndex]
      if (msg) msg.streaming = false
    }, Math.min(typeDelay, 10000))

    // 防抖刷新最近会话列表（2秒内只执行最后一次）
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = setTimeout(async () => {
      const sessionsRes = await getRecentSessions()
      if (sessionsRes?.data) {
        recentItems.value = sessionsRes.data.map(s => ({ id: s.id, title: s.title }))
      }
    }, 2000)
  } catch (e) {
    console.warn('请求失败:', e)
    messages.value[aiIndex] = {
      role: 'assistant',
      content: '抱歉，请求失败，请稍后重试。',
      streaming: false,
    }
  }
}

function handleLogout() {
  logout()
}

function handleLoginSuccess() {
  // 登录成功后重新加载用户配置和会话列表
  loadUserData()
}

const currentModel = ref('DeepSeek-V4-Flash')
function handleModelChange(model) {
  currentModel.value = model
  console.log('切换模型:', model)
}
</script>

<style scoped>
.app-wrapper {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(180deg, #ffffff 0%, #e8f2ff 50%, #dcebff 100%);
}
.sidebar-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.40);
  z-index: 999;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
}
.sidebar-mask.show {
  opacity: 1;
  pointer-events: auto;
}
</style>

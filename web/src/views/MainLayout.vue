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
      :is-authenticated="isAuthenticated"
      :is-dark="isDark"
      :app-name="appName"
      :user-name="userName"
      :avatar="authAvatar"
      :shortcut-text="shortcutText"
      :nav-items="navItems"
      :sections="sections"
      :recent-items="recentItems"
      @collapse="collapse"
      @new-chat="handleNewChat"
      @navigate="handleNavigate"
      @select-recent="handleSelectRecent"
      @logout="handleLogout"
      @login="handleShowLogin"
      @theme-change="toggleTheme"
      @avatar-change="handleAvatarChange"
    />

    <!-- 主内容 -->
    <MainContent
      ref="mainContentRef"
      :welcome-message="welcomeMessage"
      :search-placeholder="searchPlaceholder"
      :extension-label="extensionLabel"
      :is-authenticated="isAuthenticated"
      :is-dark="isDark"
      :user-name="userName"
      :avatar="authAvatar"
      :messages="messages"
      :is-thinking="isThinking"
      :loader-variant="currentLoaderVariant"
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
import { useTheme } from '../composables/useTheme.js'
import { getSystemConfig, getRecentSessions, sendChatMessage, getChatHistory, uploadAvatar } from '../services/api.js'

const { username: authUsername, avatar: authAvatar, isAuthenticated, logout, fetchProfile, setAvatar } = useAuth()
const { isDark, toggleTheme } = useTheme()

const mainContentRef = ref(null)

// ===== 动态配置（从后端获取，失败时用默认值兜底） =====
const appName = ref('MedKnow')
const userName = ref('Hello')
const shortcutText = ref('Ctrl+Shift+O')
const searchPlaceholder = ref('问问知康')
const extensionLabel = ref('DeepSeek-V4-Flash')
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
const isThinking = ref(false)
const currentLoaderVariant = ref('rose')
let refreshTimer = null

// ===== 从后端加载用户配置和会话列表 =====
async function loadUserData() {
  const [configRes, sessionsRes, profileRes] = await Promise.allSettled([
    getSystemConfig(),
    getRecentSessions(),
    isAuthenticated.value ? fetchProfile() : Promise.resolve(),
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

  // 显示思考动画（在气泡外部）
  currentLoaderVariant.value = nextLoaderVariant()
  isThinking.value = true

  try {
    const res = await sendChatMessage(query, {
      session_id: currentSessionId.value,
      use_rerank: true,
      model: currentModel.value,
    })
    currentSessionId.value = res.session_id

    // 思考结束，才出现 AI 气泡
    isThinking.value = false
    const aiIndex = messages.value.length
    messages.value.push({
      role: 'assistant',
      content: res.answer,
      streaming: true,
    })

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
    isThinking.value = false
    messages.value.push({
      role: 'assistant',
      content: '抱歉，请求失败，请稍后重试。',
      streaming: false,
    })
  }
}

function handleLogout() {
  logout()
  userName.value = 'User'
  recentItems.value = []
  currentSessionId.value = null
  messages.value = []
}

function handleShowLogin() {
  mainContentRef.value?.openModal()
}

function handleLoginSuccess() {
  // 登录成功后重新加载用户配置和会话列表
  loadUserData()
}

async function handleAvatarChange(file) {
  try {
    const res = await uploadAvatar(file)
    if (res?.data?.avatar) {
      setAvatar(res.data.avatar)
    }
  } catch (e) {
    console.error('上传头像失败:', e)
    alert('上传头像失败，请重试')
  }
}

const currentModel = ref('DeepSeek-V4-Flash')
function handleModelChange(model) {
  currentModel.value = model
  console.log('切换模型:', model)
}

// 加载曲线类型轮换
const loaderVariants = ['rose', 'original-thinking', 'lissajous', 'cardioid', 'hypotrochoid']
let loaderIndex = 0
function nextLoaderVariant() {
  const v = loaderVariants[loaderIndex % loaderVariants.length]
  loaderIndex++
  return v
}
</script>

<style scoped>
.app-wrapper {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(180deg, var(--bg-gradient-start) 0%, var(--bg-gradient-mid) 50%, var(--bg-gradient-end) 100%);
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

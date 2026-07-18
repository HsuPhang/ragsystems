<template>
  <!-- ===== 主内容 ===== -->
  <main class="main">
    <!-- 顶部工具栏 -->
    <div class="main-toolbar">
      <!-- 移动端菜单切换 -->
      <button class="icon-btn menu-btn" aria-label="菜单" @click="toggleMobile">
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      </button>

      <!-- 登录状态按钮 -->
      <button v-if="!isAuthenticated" class="btn-auth" @click="openModal">
        登录 / 注册
      </button>
      <button v-else class="btn-auth logged" :style="{ width: '36px', height: '36px', padding: '0', borderRadius: '50%' }">
        {{ userInitial }}
      </button>
    </div>

    <!-- 居中欢迎区 / 聊天区 -->
    <div class="main-center">
      <!-- 无消息时显示欢迎页 -->
      <template v-if="!messages || messages.length === 0">
        <h1 class="welcome-title">{{ welcomeMessage }}</h1>
      </template>

      <!-- 有消息时显示聊天记录 -->
      <div v-else ref="chatContainer" class="chat-container">
        <ChatMessage
          v-for="(msg, i) in messages"
          :key="i"
          :message="msg"
          :streaming="msg.streaming"
        />
      </div>

      <SearchBox
        v-model="searchText"
        :placeholder="searchPlaceholder"
        :extension-label="extensionLabel"
        @submit="handleSubmit"
        @model-change="(m) => $emit('model-change', m)"
      />
    </div>

    <!-- ===== 登录弹窗 ===== -->
    <div class="modal-overlay" :class="{ show: modalOpen }" @click="closeOnOverlay">
      <div class="modal" @click.stop @keydown="trapFocus">
        <!-- 关闭按钮 -->
        <button class="modal-close" @click="closeModal" aria-label="关闭">
          <svg viewBox="0 0 24 24"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>

        <div class="modal-body">
          <!-- Logo -->
          <div class="modal-logo">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" fill="url(#m-grad)" />
              <defs>
                <linearGradient id="m-grad" x1="2" y1="2" x2="22" y2="22">
                  <stop offset="0%" stop-color="#2563EB"/>
                  <stop offset="100%" stop-color="#60A5FA"/>
                </linearGradient>
              </defs>
            </svg>
            <span>医疗科普 RAG</span>
          </div>
          <p class="modal-subtitle">登录后即可使用全部功能</p>

          <!-- Tab 切换 -->
          <div class="modal-tabs">
            <button class="modal-tab" :class="{ active: activeTab === 'login' }" @click="activeTab = 'login'">登录</button>
            <button class="modal-tab" :class="{ active: activeTab === 'register' }" @click="activeTab = 'register'">注册</button>
          </div>

          <!-- 登录表单 -->
          <form v-if="activeTab === 'login'" @submit.prevent="handleLogin">
            <div class="form-group">
              <label class="form-label" for="login-username">用户名</label>
              <input id="login-username" ref="loginUsernameInput" v-model="loginForm.username" type="text" class="form-input" placeholder="请输入用户名" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="login-password">密码</label>
              <input id="login-password" v-model="loginForm.password" type="password" class="form-input" placeholder="请输入密码" required />
            </div>
            <div v-if="loginError" class="form-error">{{ loginError }}</div>
            <button type="submit" class="btn-submit" :disabled="loginLoading || !loginForm.username || !loginForm.password">
              {{ loginLoading ? '登录中...' : '登 录' }}
            </button>
          </form>

          <!-- 注册表单 -->
          <form v-else @submit.prevent="handleRegister">
            <div class="form-group">
              <label class="form-label" for="reg-username">用户名</label>
              <input id="reg-username" v-model="regForm.username" type="text" class="form-input" placeholder="请设置用户名" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="reg-password">密码</label>
              <input id="reg-password" v-model="regForm.password" type="password" class="form-input" placeholder="至少6位密码" minlength="6" required />
            </div>
            <div v-if="regError" class="form-error">{{ regError }}</div>
            <button type="submit" class="btn-submit" :disabled="regLoading">
              {{ regLoading ? '注册中...' : '注 册' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import SearchBox from './SearchBox.vue'
import ChatMessage from './ChatMessage.vue'
import { useAuth } from '../composables/useAuth.js'
import { register } from '../services/api.js'

const props = defineProps({
  welcomeMessage: { type: String, default: '接下来想聊点什么？' },
  searchPlaceholder: { type: String, default: '输入您的问题' },
  extensionLabel: { type: String, default: '扩展' },
  isAuthenticated: { type: Boolean, default: false },
  userName: { type: String, default: '' },
  messages: { type: Array, default: () => [] },
})

const emit = defineEmits(['toggle-mobile', 'submit', 'login-success', 'model-change'])

const { login } = useAuth()

const searchText = ref('')
const modalOpen = ref(false)
const activeTab = ref('login')
const loginLoading = ref(false)
const loginError = ref('')
const regError = ref('')
const loginForm = ref({ username: '', password: '' })
const regForm = ref({ username: '', password: '' })
const chatContainer = ref(null)
const loginUsernameInput = ref(null)
const regLoading = ref(false)

// 自动滚动到底部（监听最后一条消息内容变化，支持打字机效果）
watch(
  () => props.messages?.length ? props.messages[props.messages.length - 1].content : '',
  async () => {
    await nextTick()
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  }
)

const userInitial = computed(() => props.userName.charAt(0).toUpperCase())

function toggleMobile() {
  emit('toggle-mobile')
}

function handleSubmit(value) {
  emit('submit', value)
  searchText.value = ''
}

function openModal() {
  modalOpen.value = true
  loginError.value = ''
  regError.value = ''
  loginForm.value = { username: '', password: '' }
  regForm.value = { username: '', password: '' }
  nextTick(() => {
    loginUsernameInput.value?.focus()
  })
}

function closeModal() {
  modalOpen.value = false
}

function closeOnOverlay(e) {
  if (e.target.classList.contains('modal-overlay')) closeModal()
}

function trapFocus(e) {
  if (e.key !== 'Tab') return
  const modal = e.currentTarget
  const focusable = modal.querySelectorAll('input, button, [tabindex]:not([tabindex="-1"])')
  if (focusable.length === 0) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

async function handleLogin() {
  loginLoading.value = true
  loginError.value = ''
  try {
    await login(loginForm.value.username, loginForm.value.password)
    emit('login-success')
    closeModal()
  } catch (e) {
    loginError.value = e.message?.includes('401') ? '用户名或密码错误' : '登录失败，请检查网络'
  } finally {
    loginLoading.value = false
  }
}

async function handleRegister() {
  regLoading.value = true
  regError.value = ''
  if (!regForm.value.username || regForm.value.password.length < 6) {
    regError.value = '用户名不能为空，密码至少6位'
    regLoading.value = false
    return
  }
  try {
    const res = await register(regForm.value.username, regForm.value.password)
    await login(regForm.value.username, regForm.value.password)
    emit('login-success')
    closeModal()
  } catch (e) {
    const msg = e.message || ''
    if (msg.includes('409')) regError.value = '用户名已存在'
    else if (msg.includes('400')) regError.value = '用户名或密码格式不正确'
    else regError.value = '注册失败，请检查网络'
  } finally {
    regLoading.value = false
  }
}
</script>

<style scoped>
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #ffffff 0%, #e8f2ff 50%, #dcebff 100%);
  position: relative;
  min-width: 0;
}

/* -- 顶部工具栏 -- */
.main-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 20px 24px;
  gap: 12px;
}

.icon-btn {
  padding: 8px;
  border-radius: 9999px;
  border: none;
  background: transparent;
  color: #4b5563;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:hover {
  background: rgba(255, 255, 255, 0.50);
}
.icon-btn svg {
  width: 20px;
  height: 20px;
  stroke: currentColor;
  stroke-width: 1.8;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.menu-btn {
  display: none;
}

/* -- 登录/注册按钮 -- */
.btn-auth {
  padding: 8px 22px;
  background: #3B82F6;
  border: none;
  border-radius: 9999px;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
}
.btn-auth:hover {
  background: #2563EB;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.35);
}
.btn-auth:active {
  transform: translateY(0) scale(0.97);
}
.btn-auth.logged {
  background: linear-gradient(135deg, #3B82F6, #1D4ED8);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.30);
  font-size: 15px;
  font-weight: 600;
  cursor: default;
}

/* -- 居中欢迎区 / 聊天区 -- */
.main-center {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 16px 40px 16px;
}

.welcome-title {
  font-size: 36px;
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 40px;
  text-align: center;
}

/* ========== 弹窗遮罩 ========== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.modal-overlay.show {
  opacity: 1;
  pointer-events: auto;
}

/* ========== 弹窗主体 ========== */
.modal {
  width: 400px;
  max-width: 92vw;
  background: #fff;
  border-radius: 20px;
  box-shadow:
    0 24px 80px rgba(0, 0, 0, 0.18),
    0 8px 24px rgba(0, 0, 0, 0.08);
  position: relative;
  transform: translateY(30px) scale(0.95);
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.modal-overlay.show .modal {
  transform: translateY(0) scale(1);
}

/* -- 弹窗关闭按钮 -- */
.modal-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 10;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.05);
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}
.modal-close:hover {
  background: rgba(0, 0, 0, 0.10);
  color: #1f2937;
  transform: rotate(90deg);
}
.modal-close svg {
  width: 18px;
  height: 18px;
  stroke: currentColor;
  stroke-width: 2;
  fill: none;
  stroke-linecap: round;
}

/* -- 弹窗内容 -- */
.modal-body {
  padding: 40px 36px 32px 36px;
}

.modal-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 8px;
}
.modal-logo svg {
  width: 32px;
  height: 32px;
}
.modal-logo span {
  font-size: 22px;
  font-weight: 600;
  color: #1f2937;
}

.modal-subtitle {
  text-align: center;
  font-size: 14px;
  color: #9ca3af;
  margin-bottom: 28px;
}

/* -- Tab 切换 -- */
.modal-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 24px;
  background: #f3f4f6;
  border-radius: 12px;
  padding: 3px;
}
.modal-tab {
  flex: 1;
  padding: 10px 0;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s ease;
}
.modal-tab.active {
  background: #fff;
  color: #1f2937;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

/* -- 表单 -- */
.form-group {
  margin-bottom: 16px;
}
.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}
.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 1.5px solid #e5e7eb;
  border-radius: 12px;
  font-size: 15px;
  color: #1f2937;
  background: #fafafa;
  outline: none;
  transition: all 0.2s ease;
}
.form-input:focus {
  border-color: #4285F4;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.12);
}
.form-input::placeholder {
  color: #c0c4cc;
}

.form-error {
  color: #ef4444;
  font-size: 13px;
  text-align: center;
  margin-bottom: 4px;
}

/* -- 提交按钮 -- */
.btn-submit {
  width: 100%;
  padding: 13px 0;
  background: #60a5fa;
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 16px rgba(66, 133, 244, 0.30);
  margin-top: 8px;
}
.btn-submit:hover {
  box-shadow: 0 6px 24px rgba(66, 133, 244, 0.45);
  transform: translateY(-1px);
}
.btn-submit:active {
  transform: translateY(0) scale(0.98);
}
.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .welcome-title {
    font-size: 26px;
  }
}

@media (max-width: 640px) {
  .menu-btn {
    display: flex;
  }
  .main-toolbar {
    padding: 12px 16px;
  }
  .welcome-title {
    font-size: 22px;
    margin-bottom: 28px;
  }
  .modal-body {
    padding: 32px 24px 24px 24px;
  }
}

/* -- 聊天容器 -- */
.chat-container {
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: 800px;
  overflow-y: auto;
  padding: 16px 16px 16px;
  margin-bottom: 12px;
  scroll-behavior: smooth;
}

/* 美化的滚动条 */
.chat-container::-webkit-scrollbar {
  width: 6px;
}
.chat-container::-webkit-scrollbar-track {
  background: transparent;
}
.chat-container::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.2);
  border-radius: 3px;
  transition: background 0.2s ease;
}
.chat-container::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.4);
}
/* Firefox */
.chat-container {
  scrollbar-width: thin;
  scrollbar-color: rgba(59, 130, 246, 0.2) transparent;
}

/* 当有聊天消息时，改用 flex-start 布局 */
.main-center:has(.chat-container) {
  justify-content: flex-start;
  padding-top: 0;
}
.main-center:has(.chat-container) .welcome-title {
  display: none;
}
</style>

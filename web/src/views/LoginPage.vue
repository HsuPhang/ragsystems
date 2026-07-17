<template>
  <div class="min-h-screen flex items-center justify-center">
    <div class="max-w-sm w-full mx-4">
      <!-- 头部 -->
      <div class="text-center mb-8">
        <div class="flex items-center justify-center gap-1 mb-3">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="28" height="28" rx="6" fill="url(#logo_login_grad)"/>
            <path d="M7 11c2-2 4-4 7-4s7 3 7 6-2 7-7 7c-3 0-5-2-6-4" stroke="#fff" stroke-width="1.5" stroke-linecap="round" fill="none"/>
            <circle cx="12" cy="14" r="1.2" fill="#fff" opacity="0.8"/>
            <circle cx="16" cy="14" r="1.2" fill="#fff" opacity="0.8"/>
            <defs>
              <linearGradient id="logo_login_grad" x1="0" y1="0" x2="28" y2="28">
                <stop stop-color="#1a73e8"/><stop offset="1" stop-color="#0b4daa"/>
              </linearGradient>
            </defs>
          </svg>
          <span class="text-xl font-semibold text-gray-200">医疗科普 RAG</span>
        </div>
        <p class="text-sm text-gray-500">登录以继续使用</p>
      </div>

      <!-- 登录表单 -->
      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-xs text-gray-400 mb-1.5">用户名</label>
          <input
            v-model="form.username"
            type="text"
            placeholder="请输入用户名"
            class="w-full px-3 py-2.5 rounded-lg bg-[#2d2d2d] border border-[#3d3d3d] text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8] transition-colors"
            :disabled="loading"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-400 mb-1.5">密码</label>
          <input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            class="w-full px-3 py-2.5 rounded-lg bg-[#2d2d2d] border border-[#3d3d3d] text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8] transition-colors"
            :disabled="loading"
          />
        </div>

        <div v-if="errorMsg" class="text-red-400 text-xs text-center">{{ errorMsg }}</div>

        <button
          type="submit"
          :disabled="loading || !form.username || !form.password"
          class="w-full py-2.5 rounded-lg text-sm font-medium transition-all duration-200"
          :class="loading || !form.username || !form.password
            ? 'bg-[#1a73e8]/50 text-white/50 cursor-not-allowed'
            : 'bg-[#1a73e8] text-white hover:bg-[#1558b0] active:scale-[0.98]'"
        >
          <span v-if="loading" class="inline-flex items-center gap-2">
            <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            登录中...
          </span>
          <span v-else>登录</span>
        </button>
      </form>

      <p class="text-center text-xs text-gray-600 mt-6">
        首次登录将自动使用系统配置的默认管理员账号
      </p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth.js'

const router = useRouter()
const { login } = useAuth()

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  loading.value = true
  errorMsg.value = ''
  try {
    await login(form.username, form.password)
    router.replace('/')
  } catch (e) {
    errorMsg.value = e.message?.includes('401') ? '用户名或密码错误' : '登录失败，请检查网络连接'
  } finally {
    loading.value = false
  }
}
</script>

import { ref, computed } from 'vue'
import { login as loginApi, getProfile } from '../services/api.js'

const token = ref(localStorage.getItem('auth_token') || '')
const username = ref(localStorage.getItem('auth_username') || '')
const avatar = ref(localStorage.getItem('auth_avatar') || '')

function isTokenExpired(token) {
  if (!token) return true
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch { return true }
}

export function useAuth() {
  const isAuthenticated = computed(() => !!token.value && !isTokenExpired(token.value))

  async function login(usernameInput, password) {
    try {
      const res = await loginApi(usernameInput, password)
      const data = res.data || res
      token.value = data.access_token
      username.value = data.username
      avatar.value = data.avatar || ''
      localStorage.setItem('auth_token', data.access_token)
      localStorage.setItem('auth_username', data.username)
      localStorage.setItem('auth_avatar', data.avatar || '')
    } catch (e) {
      throw e
    }
  }

  async function fetchProfile() {
    try {
      const res = await getProfile()
      console.log('[useAuth] fetchProfile result:', res)
      const data = res.data || res
      if (data) {
        username.value = data.username || username.value
        avatar.value = data.avatar || ''
        console.log('[useAuth] fetchProfile - username:', username.value, 'avatar:', avatar.value)
        localStorage.setItem('auth_username', data.username || username.value)
        localStorage.setItem('auth_avatar', data.avatar || '')
      }
    } catch (e) {
      console.warn('获取用户信息失败:', e)
    }
  }

  function setAvatar(newAvatar) {
    console.log('[useAuth] setAvatar:', newAvatar)
    avatar.value = newAvatar
    localStorage.setItem('auth_avatar', newAvatar)
  }

  function logout() {
    token.value = ''
    username.value = ''
    avatar.value = ''
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_username')
    localStorage.removeItem('auth_avatar')
  }

  return {
    token,
    username,
    avatar,
    isAuthenticated,
    login,
    fetchProfile,
    setAvatar,
    logout,
  }
}

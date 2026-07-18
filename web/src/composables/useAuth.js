import { ref, computed } from 'vue'
import { login as loginApi } from '../services/api.js'

const token = ref(localStorage.getItem('auth_token') || '')
const username = ref(localStorage.getItem('auth_username') || '')

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
      token.value = res.access_token
      username.value = res.username
      localStorage.setItem('auth_token', res.access_token)
      localStorage.setItem('auth_username', res.username)
    } catch (e) {
      throw e
    }
  }

  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_username')
  }

  return {
    token,
    username,
    isAuthenticated,
    login,
    logout,
  }
}

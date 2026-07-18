const API_BASE = '/api'

function getToken() {
  return localStorage.getItem('auth_token') || ''
}

async function request(url, options = {}) {
  const { auth = true, ...fetchOptions } = options
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 30000)

  const headers = { 'Content-Type': 'application/json', ...fetchOptions.headers }
  if (auth) {
    const t = getToken()
    if (t) headers['Authorization'] = `Bearer ${t}`
  }

  try {
    const res = await fetch(`${API_BASE}${url}`, {
      headers,
      signal: controller.signal,
      ...fetchOptions,
    })
    if (!res.ok) {
      const text = await res.text()
      if (res.status === 401) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_username')
        if (window.location.pathname === '/') {
          return { success: false, message: '未登录' }
        }
        window.location.href = '/'
        return
      }
      throw new Error(`API ${res.status}: ${text}`)
    }
    return res.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

// ===== 认证 =====
export function login(username, password) {
  return request('/admin/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
    auth: false,
  })
}

export function register(username, password) {
  return request('/admin/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
    auth: false,
  })
}

// ===== 系统 =====
export function getSystemConfig() {
  return request('/system/config')
}

export function getRecentSessions(limit = 20) {
  return request(`/system/sessions?limit=${limit}`)
}

// ===== 聊天 =====
export function sendChatMessage(query, { session_id, use_rerank, top_k, category } = {}) {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({ query, session_id, use_rerank, top_k, category }),
  })
}

export function getChatHistory(session_id) {
  return request(`/chat/history/${session_id}`)
}

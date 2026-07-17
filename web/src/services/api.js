const API_BASE = '/api'

function getToken() {
  return localStorage.getItem('auth_token') || ''
}

async function request(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  const t = getToken()
  if (t) headers['Authorization'] = `Bearer ${t}`

  const res = await fetch(`${API_BASE}${url}`, {
    headers,
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    if (res.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_username')
      window.location.reload()
    }
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json()
}

// ===== 认证 =====
export function login(username, password) {
  return request('/admin/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function register(username, password) {
  return request('/admin/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
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

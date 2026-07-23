import { ref, watch } from 'vue'

const THEME_KEY = 'app_theme'

// 从 localStorage 读取初始主题，默认 light
const isDark = ref(localStorage.getItem(THEME_KEY) === 'dark')

// 初始化时应用主题
function applyTheme(dark) {
  if (dark) {
    document.documentElement.setAttribute('data-theme', 'dark')
  } else {
    document.documentElement.setAttribute('data-theme', 'light')
  }
}
applyTheme(isDark.value)

// 监听变化，持久化到 localStorage
watch(isDark, (dark) => {
  localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light')
  applyTheme(dark)
})

export function useTheme() {
  function toggleTheme() {
    isDark.value = !isDark.value
  }

  function setTheme(dark) {
    isDark.value = dark
  }

  return {
    isDark,
    toggleTheme,
    setTheme,
  }
}

import { ref, computed, onMounted, onUnmounted } from 'vue'

export function useSidebar() {
  const isCollapsed = ref(false)
  const isMobileOpen = ref(false)
  const isMobile = ref(false)

  const showToggle = computed(() => isCollapsed.value && !isMobile.value)
  const showMask = computed(() => isMobile.value && isMobileOpen.value)
  const sidebarVisible = computed(() => {
    if (isMobile.value) return isMobileOpen.value
    return !isCollapsed.value
  })

  function checkMobile() {
    isMobile.value = window.innerWidth <= 640
  }

  function collapse() {
    if (isMobile.value) {
      isMobileOpen.value = false
    } else {
      isCollapsed.value = true
    }
  }

  function expand() {
    if (isMobile.value) {
      isMobileOpen.value = true
    } else {
      isCollapsed.value = false
    }
  }

  function toggleMobile() {
    isMobileOpen.value = !isMobileOpen.value
  }

  function closeMobile() {
    isMobileOpen.value = false
  }

  onMounted(() => {
    checkMobile()
    window.addEventListener('resize', checkMobile)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', checkMobile)
  })

  return {
    isCollapsed,
    isMobileOpen,
    isMobile,
    showToggle,
    showMask,
    sidebarVisible,
    collapse,
    expand,
    toggleMobile,
    closeMobile
  }
}

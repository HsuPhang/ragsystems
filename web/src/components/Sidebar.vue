<template>
  <!-- ===== 侧边栏 ===== -->
  <aside class="sidebar" :class="{ collapsed: !visible && !isMobile, open: isMobile && visible }">
    <!-- 头部 -->
    <header class="sidebar-header">
      <div class="logo">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" fill="url(#g-grad)" />
          <defs>
            <linearGradient id="g-grad" x1="2" y1="2" x2="22" y2="22">
              <stop offset="0%" stop-color="#4285F4"/>
              <stop offset="33%" stop-color="#9C27B0"/>
              <stop offset="66%" stop-color="#EA4335"/>
              <stop offset="100%" stop-color="#FBBC05"/>
            </linearGradient>
          </defs>
        </svg>
        <span class="logo-text">{{ appName }}</span>
      </div>
      <div class="header-actions">

        <button class="icon-btn collapse-btn" aria-label="折叠侧边栏" @click="collapse">
          <img src="/asset/sidebar.squares.leading.svg" class="asset-icon" alt="折叠" />
        </button>
      </div>
    </header>

    <!-- 新对话 -->
    <div class="sidebar-new-chat">
      <button class="btn-new-chat" @click="$emit('new-chat')">
        <span class="btn-icon-wrapper">
          <img src="/asset/square.and.pencil.svg" class="asset-icon" alt="新聊天" />
        </span>
        <span>新聊天</span>
        <span class="shortcut">{{ shortcutText }}</span>
      </button>
    </div>

    <!-- 导航 -->
    <nav class="sidebar-nav">
      <a
        v-for="item in navItems"
        :key="item.label"
        href="#"
        class="nav-item"
        @click.prevent="$emit('navigate', item)"
      >
        <img :src="`/asset/${item.icon}`" class="asset-icon-sm" :alt="item.label" />
        <span>{{ item.label }}</span>
      </a>
    </nav>

    <!-- 分区标题 + 子导航 -->
    <template v-for="section in sections" :key="section.title">
      <div class="section-title">{{ section.title }}</div>
      <nav class="sidebar-nav">
        <a
          v-for="item in section.items"
          :key="item.label"
          href="#"
          class="nav-item"
          @click.prevent="$emit('navigate', item)"
        >
          <img :src="`/asset/${item.icon}`" class="asset-icon-sm" :alt="item.label" />
          <span>{{ item.label }}</span>
        </a>
      </nav>
    </template>

    <!-- 最近 -->
    <div class="section-title">最近</div>
    <div class="sidebar-recent no-scrollbar">
      <a
        v-for="item in recentItems"
        :key="item.id"
        href="#"
        class="recent-item"
        @click.prevent="$emit('select-recent', item)"
      >
        {{ item.title }}
      </a>
    </div>

    <!-- 底部用户 -->
    <footer class="sidebar-footer">
      <div class="user-profile" @click="toggleUserMenu">
        <div class="user-avatar">{{ userInitial }}</div>
        <span class="user-name">{{ userName }}</span>
        <span class="user-menu" :class="{ active: userMenuOpen }">
          <img src="/asset/gearshape.svg" class="asset-icon" alt="设置" />
        </span>
      </div>
      <!-- 用户菜单下拉 -->
      <div v-if="userMenuOpen" class="user-dropdown" @click.stop>
        <button class="dropdown-item" @click="handleLogout">
          <img src="/asset/rectangle.portrait.and.arrow.right.svg" class="asset-icon" alt="退出"  />
            退出登录
        </button>
      </div>
    </footer>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  visible: Boolean,
  isMobile: Boolean,
  appName: { type: String, default: 'Gemini' },
  userName: { type: String, default: 'User' },
  shortcutText: { type: String, default: 'Ctrl+Shift+O' },
  navItems: { type: Array, default: () => [] },
  sections: { type: Array, default: () => [] },
  recentItems: { type: Array, default: () => [] }
})

const emit = defineEmits(['collapse', 'new-chat', 'navigate', 'select-recent', 'logout'])

const userInitial = computed(() => props.userName.charAt(0).toUpperCase())
const userMenuOpen = ref(false)

function collapse() {
  emit('collapse')
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value
}

function handleLogout() {
  userMenuOpen.value = false
  emit('logout')
}

function closeMenuOnOutside(e) {
  if (!e.target.closest('.sidebar-footer')) {
    userMenuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', closeMenuOnOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', closeMenuOnOutside)
})
</script>

<style scoped>
/* ========== 侧边栏容器 ========== */
.sidebar {
  width: 280px;
  height: calc(100vh - 20px);
  margin: 10px 0 10px 10px;
  background: #FFFFFFEB;
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow:
    0 8px 32px rgba(0, 20, 60, 0.06),
    0 2px 8px rgba(0, 20, 60, 0.04);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-radius: 20px;
  isolation: isolate;
  position: relative;
  z-index: 10;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              margin 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 折叠状态 */
.sidebar.collapsed {
  transform: translateX(-100%);
  opacity: 0;
  margin-left: -280px;
}

/* -- 头部 -- */
.sidebar-header {
  padding: 16px 20px 8px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}
.logo-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
}
.logo-text {
  font-size: 20px;
  font-weight: 500;
  color: #1f2937;
  white-space: nowrap;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon-btn {
  padding: 6px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.icon-btn:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #374151;
}

/* -- 新对话按钮 -- */
.sidebar-new-chat {
  padding: 0 12px 8px 12px;
}
.btn-new-chat {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 9999px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
  white-space: nowrap;
}
.btn-new-chat:hover {
  background: rgba(0, 0, 0, 0.06);
}
.btn-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.shortcut {
  margin-left: auto;
  font-size: 12px;
  color: #9ca3af;
  font-weight: 400;
}

/* -- 导航 -- */
.sidebar-nav {
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  color: #374151;
  text-decoration: none;
  transition: all 0.2s ease;
  overflow: hidden;
  white-space: nowrap;
}
.nav-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

/* -- 分区标题 -- */
.section-title {
  padding: 16px 28px 4px 28px;
  font-size: 12px;
  font-weight: 500;
  color: #9ca3af;
  letter-spacing: 0.3px;
  white-space: nowrap;
}

/* -- 最近列表 -- */
.sidebar-recent {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.recent-item {
  display: block;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  color: #4b5563;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.2s;
}
.recent-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

/* -- 底部用户 -- */
.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}
.user-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;
}
.user-profile:hover {
  background: rgba(0, 0, 0, 0.04);
}
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 9999px;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  flex-shrink: 0;
}
.user-name {
  flex: 1;
  font-size: 14px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-menu {
  color: #6b7280;
  flex-shrink: 0;
}

/* -- 用户菜单下拉 -- */
.user-dropdown {
  position: absolute;
  bottom: 100%;
  width: 40%;
  left: 16px;
  right: 16px;
  margin-bottom: 4px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  z-index: 20;
}
.dropdown-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #ef4444;
  cursor: pointer;
  transition: background 0.15s;
}
.dropdown-item:hover {
  background: rgba(239, 68, 68, 0.06);
}
.user-menu.active {
  transform: rotate(45deg);
  transition: transform 0.2s;
}
.sidebar-footer {
  position: relative;
}

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
  .sidebar {
    width: 240px;
  }
}

@media (max-width: 640px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 1000;
    width: 280px;
    height: 100vh;
    margin: 0;
    border-radius: 0;
    box-shadow: 2px 0 20px rgba(0, 0, 0, 0.12);
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }
  .sidebar.collapsed {
    transform: translateX(-100%);
    margin-left: 0;
    opacity: 1;
  }
  .sidebar.open {
    transform: translateX(0);
  }
  .collapse-btn {
    display: none;
  }
}
</style>

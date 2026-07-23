# Tasks

- [x] Task 1: MainContent 背景透明化
  - [x] SubTask 1.1: 将 MainContent.vue 中 `.main` 的 `background` 改为 `transparent`，移除独立渐变
  - [x] SubTask 1.2: 确认 `.app-wrapper` 已使用主题变量渐变背景

- [x] Task 2: Sidebar 强化悬浮卡片感
  - [x] SubTask 2.1: 保留圆角(20px)、margin(10px)、阴影，作为悬浮卡片的视觉标识
  - [x] SubTask 2.2: 保留 `backdrop-filter: blur` 半透明玻璃效果，让底层背景隐约可见
  - [x] SubTask 2.3: 调整背景透明度（浅色 `rgba(255,255,255,0.60)` / 深色 `rgba(30,41,59,0.60)`），增加"穿透"感

- [x] Task 3: 主题过渡验证
  - [x] SubTask 3.1: 确认 style.css 全局 2s 过渡覆盖所有颜色属性
  - [x] SubTask 3.2: 确认 Sidebar 透明背景、MainContent 透明区域均与底层渐变同步过渡

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 1、Task 2

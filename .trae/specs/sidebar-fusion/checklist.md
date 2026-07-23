# Checklist

- [x] MainContent.vue `.main` 背景为透明，无独立渐变覆盖
- [x] `.app-wrapper` 覆盖全视口统一渐变背景
- [x] Sidebar 保留圆角、margin、阴影的悬浮卡片视觉效果
- [x] Sidebar 背景为半透明玻璃态（`backdrop-filter: blur`），可隐约看到底层渐变
- [x] Sidebar 与主内容区之间有空间层次感，不是左右拼接
- [x] 主题切换时所有区域在 2s 内平滑同步渐变
- [x] 移动端 Sidebar 行为正常（fixed overlay 模式）

# Sidebar 悬浮卡片融合 Spec

## Why
当前 Sidebar 与 MainContent 像左右两张面板拼接在一起，各有不同背景色，视觉断层强烈。用户需要的是：底层是统一背景的主体层（全宽），Sidebar 是漂浮在主体左上方的独立卡片组件。

## What Changes
- `.app-wrapper` 使用统一主题渐变背景（适配深浅模式），覆盖整个视口。
- `MainContent` 的背景改为透明，让 `.app-wrapper` 的统一背景穿透，不再有独立的区域背景。
- `Sidebar` 保持悬浮卡片感：圆角、阴影、`backdrop-filter: blur` 半透明玻璃效果、与边缘留有 margin，视觉上"漂浮"在主体层上方。
- Sidebar 与主体之间不再有硬拼接的"分割线"，而是通过阴影和 margin 自然形成层次感。
- 保持主题切换 2s 平滑渐变同步。

## Impact
- 受影响文件：
  - [MainLayout.vue](file:///e:/ragsystem/web/src/views/MainLayout.vue)
  - [MainContent.vue](file:///e:/ragsystem/web/src/components/MainContent.vue)
  - [Sidebar.vue](file:///e:/ragsystem/web/src/components/Sidebar.vue)
- 受影响能力：主题切换、侧边栏视觉层次、响应式布局。

## MODIFIED Requirements
### Requirement: 统一底层背景
The system SHALL render `.app-wrapper` as a full-viewport gradient background using theme CSS variables, shared by all child components.

#### Scenario: 深浅模式切换
- **WHEN** 用户切换主题
- **THEN** 整个视口背景在 2s 内平滑渐变

### Requirement: MainContent 透明穿透
The system SHALL set `MainContent` 主区域背景为透明，使 `.app-wrapper` 统一背景可见。

#### Scenario: 页面渲染
- **WHEN** 用户打开页面
- **THEN** 主内容区不显示独立背景色，展示底层统一渐变

### Requirement: Sidebar 悬浮卡片
The system SHALL render Sidebar 在主体层左侧上方，呈现圆角、阴影、半透明玻璃态的浮动卡片效果，保留 margin 与主体层形成空间层次。

#### Scenario: 桌面视图
- **WHEN** 用户打开页面
- **THEN** Sidebar 漂浮在左侧，透过半透明背景可隐约看到底层渐变，有明显悬浮层次感

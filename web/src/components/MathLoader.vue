<template>
  <div class="math-loader" :style="{ width: size + 'px', height: size + 'px', color: loaderColor }">
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <!-- 背景曲线路径（半透明全曲线） -->
      <path
        ref="bgPathRef"
        fill="none"
        stroke="currentColor"
        :stroke-width="strokeBg"
        opacity="0.15"
      />
      <!-- 转动的实线轨迹组 -->
      <g ref="rotatingGroupRef">
        <!-- 发光尾迹（粗、半透明） -->
        <path
          ref="glowPathRef"
          fill="none"
          stroke="currentColor"
          :stroke-width="strokeGlow"
          stroke-linecap="round"
          opacity="0.2"
        />
        <!-- 主线（细、高亮） -->
        <path
          ref="trailPathRef"
          fill="none"
          stroke="currentColor"
          :stroke-width="strokeMain"
          stroke-linecap="round"
          opacity="0.95"
        />
        <!-- 头部光点 -->
        <circle ref="headDotRef" fill="currentColor" :r="headDotR" opacity="1" />
      </g>
    </svg>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps({
  size: { type: Number, default: 64 },
  color: { type: String, default: '#000000ff' },
  variant: {
    type: String,
    default: 'rose',
    validator: v => ['rose', 'lissajous', 'cardioid', 'hypotrochoid', 'original-thinking'].includes(v),
  },
})

const loaderColor = computed(() => props.color)

// 曲线参数
const curveConfig = computed(() => {
  switch (props.variant) {
    case 'lissajous':
      return { baseR: 25, detail: 0, petals: 0, scale: 1.5, trailSpan: 0.30, rotateDuration: 24000, pulseDuration: 3800, duration: 4000, pathSteps: 400 }
    case 'cardioid':
      return { baseR: 18, detail: 6, petals: 1, scale: 2.2, trailSpan: 0.35, rotateDuration: 30000, pulseDuration: 4500, duration: 5000, pathSteps: 400 }
    case 'hypotrochoid':
      return { baseR: 30, detail: 4, petals: 5, scale: 1.5, trailSpan: 0.30, rotateDuration: 26000, pulseDuration: 4000, duration: 4800, pathSteps: 500 }
    case 'original-thinking':
      return { baseR: 7, detail: 3, petals: 7, scale: 3.9, trailSpan: 0.38, rotateDuration: 28000, pulseDuration: 4200, duration: 4600, pathSteps: 500 }
    default: // rose
      return { baseR: 22, detail: 0, petals: 6, scale: 1.8, trailSpan: 0.35, rotateDuration: 30000, pulseDuration: 4000, duration: 4800, pathSteps: 450 }
  }
})

const strokeBg = 0.6
const strokeGlow = 4.5
const strokeMain = 2.2
const headDotR = 2

// Refs
const bgPathRef = ref(null)
const rotatingGroupRef = ref(null)
const trailPathRef = ref(null)
const glowPathRef = ref(null)
const headDotRef = ref(null)
let animFrameId = null
let startedAt = 0

// ---- 数学曲线公式 ----
function normalizeProgress(p) {
  return ((p % 1) + 1) % 1
}

function getPoint(progress, detailScale) {
  const cfg = curveConfig.value
  const t = normalizeProgress(progress) * Math.PI * 2

  let x, y

  switch (props.variant) {
    case 'lissajous': {
      x = 30 * Math.sin(3 * t + Math.PI / 2)
      y = 30 * Math.sin(4 * t)
      break
    }
    case 'cardioid': {
      const r = cfg.baseR * (1 + Math.cos(t))
      x = r * Math.cos(t) - cfg.detail * detailScale * Math.cos(cfg.petals * t)
      y = r * Math.sin(t) - cfg.detail * detailScale * Math.sin(cfg.petals * t)
      break
    }
    case 'hypotrochoid': {
      const R = 28, r = 12, d = 8
      x = (R - r) * Math.cos(t) + d * Math.cos((R - r) / r * t) - cfg.detail * detailScale * Math.cos(cfg.petals * t)
      y = (R - r) * Math.sin(t) - d * Math.sin((R - r) / r * t) - cfg.detail * detailScale * Math.sin(cfg.petals * t)
      break
    }
    case 'original-thinking': {
      x = cfg.baseR * Math.cos(t) - cfg.detail * detailScale * Math.cos(cfg.petals * t)
      y = cfg.baseR * Math.sin(t) - cfg.detail * detailScale * Math.sin(cfg.petals * t)
      break
    }
    default: { // rose
      const r = cfg.baseR * Math.cos(cfg.petals * t)
      x = r * Math.cos(t)
      y = r * Math.sin(t)
      break
    }
  }

  return { x: 50 + x * cfg.scale, y: 50 + y * cfg.scale }
}

function buildPath(detailScale, steps) {
  const pts = []
  for (let i = 0; i <= steps; i++) {
    const p = getPoint(i / steps, detailScale)
    pts.push(`${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
  }
  return pts.join(' ')
}

function buildTrailPath(detailScale, progress, steps) {
  const cfg = curveConfig.value
  const trailStart = normalizeProgress(progress - cfg.trailSpan)
  const trailEnd = progress

  // trailStart might be > trailEnd if it wrapped around, so build in segments
  let pts = []
  if (trailStart <= trailEnd) {
    // Normal: start to end
    const segSteps = Math.round(steps * cfg.trailSpan)
    for (let i = 0; i <= segSteps; i++) {
      const p = getPoint(trailStart + (i / segSteps) * cfg.trailSpan, detailScale)
      pts.push(`${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    }
  } else {
    // Wrapped: start→1.0, then 0→end
    const segSteps1 = Math.round(steps * (1 - trailStart))
    for (let i = 0; i <= segSteps1; i++) {
      const frac = i / segSteps1
      const p = getPoint(trailStart + frac * (1 - trailStart), detailScale)
      pts.push(`${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    }
    const segSteps2 = Math.round(steps * trailEnd)
    for (let i = 1; i <= segSteps2; i++) {
      const frac = i / segSteps2
      const p = getPoint(frac * trailEnd, detailScale)
      pts.push(`L ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    }
  }
  return pts.join(' ')
}

function getDetailScale(time) {
  const cfg = curveConfig.value
  const pulseProgress = (time % cfg.pulseDuration) / cfg.pulseDuration
  const angle = pulseProgress * Math.PI * 2
  return 0.5 + ((Math.sin(angle + 0.55) + 1) / 2) * 0.45
}

function getRotation(time) {
  const cfg = curveConfig.value
  return -((time % cfg.rotateDuration) / cfg.rotateDuration) * 360
}

function renderFrame(time) {
  const cfg = curveConfig.value
  const progress = (time % cfg.duration) / cfg.duration
  const detailScale = getDetailScale(time)
  const rotation = getRotation(time)

  // 背景全曲线
  if (bgPathRef.value) {
    bgPathRef.value.setAttribute('d', buildPath(detailScale, cfg.pathSteps))
  }

  // 旋转
  if (rotatingGroupRef.value) {
    rotatingGroupRef.value.setAttribute('transform', `rotate(${rotation} 50 50)`)
  }

  // 实线轨迹（仅 trailSpan 部分）
  const trailD = buildTrailPath(detailScale, progress, cfg.pathSteps)
  if (trailPathRef.value) {
    trailPathRef.value.setAttribute('d', trailD)
  }
  if (glowPathRef.value) {
    glowPathRef.value.setAttribute('d', trailD)
  }

  // 头部光点
  if (headDotRef.value) {
    const head = getPoint(progress, detailScale)
    headDotRef.value.setAttribute('cx', head.x.toFixed(2))
    headDotRef.value.setAttribute('cy', head.y.toFixed(2))
  }
}

function tick(now) {
  if (!startedAt) startedAt = now
  renderFrame(now - startedAt)
  animFrameId = window.requestAnimationFrame(tick)
}

onMounted(() => {
  renderFrame(0)
  animFrameId = window.requestAnimationFrame(tick)
})

onUnmounted(() => {
  if (animFrameId) {
    window.cancelAnimationFrame(animFrameId)
    animFrameId = null
  }
})
</script>

<style scoped>
.math-loader {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #3B82F6;
}

.math-loader svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}
</style>

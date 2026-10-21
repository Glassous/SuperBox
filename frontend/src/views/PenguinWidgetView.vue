<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { PENGUIN_ACTIONS } from '../three/penguinClips'
import { createPenguinStage } from '../three/penguinScene'
import type { PenguinStage } from '../three/penguinScene'

const ACTIONS = PENGUIN_ACTIONS
// 模型托管在 COS，桶已允许本站与本地开发来源跨域读取，避免把 5MB 资源打进前端构建。
const MODEL_URL = 'https://superboxfiles.fiacloud.top/Iframe/%E5%87%91%E4%BC%81%E9%B9%85.glb'
const MESSAGE_TYPE = 'superbox:penguin'

// 接入方可用 ?action=1|2|3 指定初始动作，autoplay=0 保持静态，chrome=0 隐藏自身控件。
const search = new URLSearchParams(window.location.search)
const minimal = search.get('chrome') === '0'

function parseAction(value: unknown): 0 | 1 | 2 | null {
  if (value === 1 || value === '1') return 0
  if (value === 2 || value === '2') return 1
  if (value === 3 || value === '3') return 2
  return null
}

const initialAction = parseAction(search.get('action'))
const autoplay = search.get('autoplay') !== '0'

const host = ref<HTMLElement | null>(null)
const status = ref<'loading' | 'ready' | 'error'>('loading')
const error = ref('')
const loadedBytes = ref(0)
const totalBytes = ref(0)
const active = ref<0 | 1 | 2 | null>(null)

let stage: PenguinStage | null = null
let pendingAction: 0 | 1 | 2 | null = null

const progress = computed(() => {
  if (!totalBytes.value) return 0
  return Math.min(100, Math.round((loadedBytes.value / totalBytes.value) * 100))
})
const progressLabel = computed(() => {
  if (!totalBytes.value) {
    return loadedBytes.value ? `已加载 ${formatBytes(loadedBytes.value)}` : '正在准备资源'
  }
  return `${formatBytes(loadedBytes.value)} / ${formatBytes(totalBytes.value)} · ${progress.value}%`
})
const activeLabel = computed(() => (active.value === null ? '' : ACTIONS[active.value].label))
const statusText = computed(() => {
  if (status.value === 'loading') return '模型准备中…'
  if (status.value === 'error') return '加载失败，请重试'
  if (active.value === null) return '当前为静态姿态，点击动作按钮播放对应片段'
  return `${activeLabel.value}播放中 · 播完自动回到静态`
})

function formatBytes(bytes: number): string {
  if (!bytes) return '0 MB'
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function teardown() {
  stage?.dispose()
  stage = null
}

function mountStage() {
  if (!host.value) return
  teardown()
  status.value = 'loading'
  error.value = ''
  loadedBytes.value = 0
  totalBytes.value = 0
  active.value = null
  stage = createPenguinStage(host.value, MODEL_URL, {
    onProgress: (loaded, total) => {
      loadedBytes.value = loaded
      totalBytes.value = total
    },
    onReady: () => {
      status.value = 'ready'
      notifyParent({ type: 'superbox:penguin:ready' })
      const next = pendingAction ?? (autoplay ? initialAction : null)
      if (next !== null) setAction(next)
    },
    onError: message => {
      status.value = 'error'
      error.value = message
    },
    onSegmentEnd: () => {
      active.value = null
      notifyParent({ type: 'superbox:penguin:state', action: 0 })
    },
  })
}

function retry() {
  mountStage()
}

function setAction(index: 0 | 1 | 2 | null) {
  if (!stage || status.value !== 'ready') {
    pendingAction = index
    return
  }
  if (index === null) {
    stage.stop()
  } else {
    stage.play(index)
  }
  active.value = index
  notifyParent({
    type: 'superbox:penguin:state',
    action: index === null ? 0 : ((index + 1) as 1 | 2 | 3),
  })
}

function toggle(index: 0 | 1 | 2) {
  setAction(active.value === index ? null : index)
}

function notifyParent(payload: { type: string; action?: 0 | 1 | 2 | 3 }) {
  if (window.parent === window) return
  window.parent.postMessage(payload, '*')
}

/** 接入方通过 postMessage 控制：{ type: 'superbox:penguin', action: 1|2|3|0 }。 */
function onMessage(event: MessageEvent) {
  if (event.source !== window.parent) return
  const data = event.data as { type?: unknown; action?: unknown } | null
  if (!data || data.type !== MESSAGE_TYPE) return
  if (data.action === undefined) return
  if (data.action === null || data.action === 'stop' || data.action === 0 || data.action === '0') {
    setAction(null)
    return
  }
  const index = parseAction(data.action)
  if (index !== null) setAction(index)
}

onMounted(() => {
  mountStage()
  window.addEventListener('message', onMessage)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  teardown()
})
</script>

<template>
  <div class="relative flex h-[100dvh] min-h-[240px] w-full flex-col overflow-hidden">
    <p class="sr-only" aria-live="polite">{{ statusText }}</p>

    <main class="relative z-0 min-h-0 flex-1">
      <div ref="host" class="absolute inset-0 cursor-grab active:cursor-grabbing"></div>

      <div v-if="status === 'loading'" class="pointer-events-none absolute inset-0 z-20 grid place-items-center">
        <div class="flex flex-col items-center gap-2.5 rounded-2xl bg-slate-950/65 px-6 py-4 text-white shadow-lg backdrop-blur">
          <div class="relative size-9" aria-hidden="true">
            <div class="absolute inset-0 rounded-full border border-white/15"></div>
            <div class="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-indigo-400 motion-reduce:animate-none"></div>
          </div>
          <p class="text-[11px] font-semibold">正在加载 3D 模型</p>
          <p class="font-mono text-[10px] text-slate-300">{{ progressLabel }}</p>
          <div class="h-1 w-28 overflow-hidden rounded-full bg-white/15">
            <div class="h-full rounded-full bg-gradient-to-r from-indigo-400 to-sky-300 transition-[width] duration-300" :style="{ width: `${progress}%` }"></div>
          </div>
        </div>
      </div>

      <div v-if="status === 'error'" class="absolute inset-0 z-20 grid place-items-center px-5">
        <div class="flex max-w-xs flex-col items-center gap-2 rounded-2xl bg-slate-950/70 px-5 py-4 text-center text-white shadow-lg backdrop-blur">
          <div class="grid size-9 place-items-center rounded-full border border-rose-400/40 bg-rose-500/15 text-sm font-bold text-rose-300" aria-hidden="true">!</div>
          <p class="text-xs font-semibold">3D 模型加载失败</p>
          <p class="text-[11px] leading-5 text-slate-300">{{ error }}</p>
          <button
            type="button"
            class="mt-1 rounded-full bg-white/10 px-4 py-1.5 text-[11px] font-semibold transition hover:bg-white/20 active:scale-[0.98]"
            @click="retry"
          >
            重新加载
          </button>
        </div>
      </div>
    </main>

    <footer v-if="!minimal" class="relative z-10 flex shrink-0 justify-center px-3 pb-3">
      <div class="flex flex-wrap justify-center gap-1.5">
        <button
          v-for="action in ACTIONS"
          :key="action.index"
          type="button"
          :disabled="status !== 'ready'"
          class="inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[11px] font-semibold backdrop-blur transition duration-200 disabled:cursor-not-allowed disabled:opacity-40"
          :class="active === action.index
            ? 'bg-indigo-600 text-white shadow-[0_10px_24px_-14px_rgba(79,70,229,0.95)]'
            : 'bg-slate-950/45 text-slate-100 hover:bg-slate-950/65'"
          @click="toggle(action.index)"
        >
          {{ action.label }}
          <span class="font-mono text-[9px] opacity-70">{{ action.frames }}</span>
        </button>
      </div>
    </footer>
  </div>
</template>

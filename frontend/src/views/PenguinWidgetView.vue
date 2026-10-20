<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
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
const hintVisible = ref(true)
const standalone = window.self === window.top

let stage: PenguinStage | null = null
let hintTimer: ReturnType<typeof setTimeout> | undefined
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
  if (active.value === null) return '当前为静态姿态，点击动作按钮开始播放'
  return `${activeLabel.value}循环播放中 · 再次点击回到静态`
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
    dismissHint()
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

function dismissHint() {
  hintVisible.value = false
  if (hintTimer) clearTimeout(hintTimer)
}

onMounted(() => {
  mountStage()
  window.addEventListener('message', onMessage)
  hintTimer = setTimeout(() => { hintVisible.value = false }, 7000)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  if (hintTimer) clearTimeout(hintTimer)
  teardown()
})
</script>

<template>
  <div class="relative flex h-[100dvh] min-h-[460px] w-full flex-col overflow-hidden bg-[#070b17] text-slate-100">
    <div class="pointer-events-none absolute inset-0" aria-hidden="true">
      <div class="absolute -left-28 top-0 size-80 rounded-full bg-indigo-500/20 blur-[120px]"></div>
      <div class="absolute -right-24 bottom-0 size-96 rounded-full bg-sky-400/10 blur-[130px]"></div>
      <div
        class="absolute inset-0 opacity-[0.13]"
        style="background-image: linear-gradient(rgba(148,163,184,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.35) 1px, transparent 1px); background-size: 72px 72px; mask-image: radial-gradient(ellipse at 50% 52%, black 5%, transparent 70%); -webkit-mask-image: radial-gradient(ellipse at 50% 52%, black 5%, transparent 70%);"
      ></div>
      <div class="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-[#070b17] to-transparent"></div>
    </div>

    <header v-if="!minimal" class="relative z-10 flex items-start justify-between gap-4 px-5 pt-5 sm:px-7 sm:pt-6">
      <div class="min-w-0">
        <span class="inline-flex items-center gap-1.5 rounded-full border border-indigo-400/25 bg-indigo-500/10 px-2.5 py-1 text-[10px] font-bold tracking-[0.22em] text-indigo-300">SUPERBOX · 3D 互动</span>
        <h1 class="mt-2 text-[22px] font-bold leading-tight tracking-tight text-white sm:text-2xl">凑企鹅</h1>
        <p class="mt-1 text-[11px] leading-5 text-slate-400 sm:text-xs">三段动作随时切换，拖拽旋转视角查看模型细节。</p>
      </div>
      <div class="flex shrink-0 items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] font-semibold backdrop-blur">
        <span
          class="size-1.5 rounded-full"
          :class="active === null ? 'bg-slate-400' : 'animate-pulse bg-emerald-400 motion-reduce:animate-none'"
          aria-hidden="true"
        ></span>
        <span :class="active === null ? 'text-slate-300' : 'text-emerald-200'">{{ active === null ? '静态' : `${activeLabel}播放中` }}</span>
      </div>
    </header>

    <main class="relative z-0 min-h-0 flex-1">
      <div ref="host" class="absolute inset-0 cursor-grab active:cursor-grabbing" @pointerdown="dismissHint"></div>

      <div
        v-if="!minimal"
        class="pointer-events-none absolute left-4 top-3 z-10 inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/50 px-3 py-1.5 text-[11px] font-medium text-slate-300 backdrop-blur transition-opacity duration-500 sm:left-7"
        :class="hintVisible ? 'opacity-100' : 'opacity-0'"
      >
        <span class="size-1.5 rounded-full bg-indigo-400" aria-hidden="true"></span> 拖拽旋转 · 滚轮缩放
      </div>

      <div
        v-if="status === 'loading'"
        class="absolute inset-0 z-20 flex flex-col items-center justify-center gap-4 bg-[#070b17]/60 backdrop-blur-[2px]"
      >
        <div class="relative size-12" aria-hidden="true">
          <div class="absolute inset-0 rounded-full border border-white/10"></div>
          <div class="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-indigo-400 motion-reduce:animate-none"></div>
        </div>
        <div class="text-center">
          <p class="text-xs font-semibold text-slate-200">正在加载 3D 模型</p>
          <p class="mt-1 font-mono text-[11px] text-slate-500">{{ progressLabel }}</p>
        </div>
        <div class="h-1 w-36 overflow-hidden rounded-full bg-white/10">
          <div
            class="h-full rounded-full bg-gradient-to-r from-indigo-400 to-sky-300 transition-[width] duration-300"
            :style="{ width: `${progress}%` }"
          ></div>
        </div>
      </div>

      <div
        v-if="status === 'error'"
        class="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 px-6 text-center"
      >
        <div class="grid size-11 place-items-center rounded-full border border-rose-400/30 bg-rose-500/10 text-lg font-bold text-rose-300" aria-hidden="true">!</div>
        <p class="text-sm font-semibold text-rose-200">3D 模型加载失败</p>
        <p class="max-w-xs text-xs leading-5 text-slate-400">{{ error }}</p>
        <button
          type="button"
          class="mt-2 rounded-xl border border-white/15 bg-white/[0.06] px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-indigo-400/50 hover:text-white active:scale-[0.98]"
          @click="retry"
        >
          重新加载
        </button>
      </div>
    </main>

    <footer v-if="!minimal" class="relative z-10 px-4 pb-4 pt-2 sm:px-7 sm:pb-6">
      <div class="mx-auto w-full max-w-2xl">
        <div class="flex flex-col gap-1 rounded-2xl border border-white/10 bg-white/[0.04] p-1.5 backdrop-blur-xl min-[420px]:flex-row">
          <button
            v-for="action in ACTIONS"
            :key="action.index"
            type="button"
            :disabled="status !== 'ready'"
            class="group flex-1 rounded-xl px-3.5 py-2.5 text-left transition duration-200 disabled:cursor-not-allowed disabled:opacity-40"
            :class="active === action.index
              ? 'bg-gradient-to-br from-indigo-500 to-indigo-600 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_14px_30px_-18px_rgba(79,70,229,0.95)]'
              : 'text-slate-300 hover:bg-white/[0.06]'"
            @click="toggle(action.index)"
          >
            <span class="flex items-baseline justify-between gap-2">
              <span class="text-[13px] font-semibold">{{ action.label }}</span>
              <span class="font-mono text-[10px]" :class="active === action.index ? 'text-white/70' : 'text-slate-500'">{{ action.frames }}</span>
            </span>
            <span class="mt-0.5 block text-[11px]" :class="active === action.index ? 'text-white/75' : 'text-slate-500'">
              {{ active === action.index ? '再次点击回到静态' : action.hint }}
            </span>
          </button>
        </div>
        <div class="mt-2.5 flex items-center justify-between gap-3 text-[10px] text-slate-500">
          <span class="min-w-0 truncate">{{ statusText }}</span>
          <RouterLink v-if="standalone" to="/" class="shrink-0 font-semibold text-indigo-300 transition hover:text-indigo-200">Superbox 返回站点 ↗</RouterLink>
        </div>
      </div>
    </footer>
  </div>
</template>

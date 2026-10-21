<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { IframeInfo } from '../types'

const props = defineProps<{
  item: IframeInfo
  active: boolean
}>()
// 实时预览完全接管画面后，通知卡片隐藏底层的共享预览图，避免透出截图背景。
const emit = defineEmits<{ 'live-change': [visible: boolean] }>()

const playing = ref(false)
const liveReady = ref(false)
const copied = ref<'embed' | 'src' | null>(null)
let copyTimer: ReturnType<typeof setTimeout> | undefined

const isLive = computed(() => props.item.content_type === 'page')

/**
 * 实时预览地址：图片条目走后端嵌入页；网页条目直接加载页面本身。
 * 本地开发时挂件页由 dev server 提供，用同源相对路径避免请求线上尚未部署的地址。
 */
const liveSrc = computed(() => {
  if (!isLive.value) return props.item.embed_url
  if (import.meta.env.DEV) {
    const url = new URL(props.item.content_url)
    return `${url.pathname}${url.search}`
  }
  return props.item.content_url
})

const embedCode = computed(() => {
  const value = props.item
  const attributes = [
    `src="${value.embed_url}"`,
    `title="${value.name}"`,
    `width="${value.width}"`,
    `height="${value.height}"`,
    'loading="lazy"',
    `sandbox="${value.sandbox}"`,
    'style="border:0;max-width:100%;background:transparent"',
  ]
  if (value.allow) attributes.push(`allow="${value.allow}"`)
  return `<iframe ${attributes.join(' ')}></iframe>`
})

// 关闭弹窗时立刻卸载实时预览，避免 3D 挂件在后台继续渲染。
watch(() => props.active, active => {
  if (!active) stopLive()
})
watch(() => playing.value && liveReady.value, visible => emit('live-change', visible))

function play() {
  liveReady.value = false
  playing.value = true
}

function stopLive() {
  playing.value = false
  liveReady.value = false
}

function onLiveLoad() {
  requestAnimationFrame(() => { liveReady.value = true })
}

async function copy(value: string, kind: 'embed' | 'src') {
  try {
    await navigator.clipboard.writeText(value)
    copied.value = kind
  } catch {
    copied.value = null
  }
  if (copyTimer) clearTimeout(copyTimer)
  copyTimer = setTimeout(() => { copied.value = null }, 1800)
}

function openEmbedPage() {
  window.open(props.item.embed_url, '_blank', 'noopener,noreferrer')
}

onBeforeUnmount(() => {
  if (copyTimer) clearTimeout(copyTimer)
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4 overflow-y-auto p-4 sm:p-5 md:flex-row md:overflow-hidden">
    <section class="relative min-h-60 w-full min-w-0 flex-1 md:min-h-0" data-preview-panel>
      <button
        v-if="!playing"
        type="button"
        class="group absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 cursor-pointer rounded-full focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-500"
        @click="play"
      >
        <span class="mx-auto grid size-16 place-items-center rounded-full bg-white/95 text-indigo-600 shadow-[0_18px_40px_-12px_rgba(15,23,42,0.6)] ring-1 ring-white/60 transition duration-200 group-hover:scale-105 group-hover:bg-white group-active:scale-95">
          <svg class="ml-0.5 size-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.2c0-.9 1-1.4 1.7-.9l9 6.1a1.1 1.1 0 0 1 0 1.8l-9 6.1c-.7.5-1.7 0-1.7-.9Z" /></svg>
        </span>
        <span class="mt-3 inline-flex items-center gap-1.5 rounded-full bg-slate-950/70 px-3 py-1.5 text-[11px] font-semibold text-white backdrop-blur">点击播放实时预览</span>
      </button>

      <iframe
        v-if="playing"
        :src="liveSrc"
        :title="item.name"
        :sandbox="item.sandbox"
        :allow="item.allow || undefined"
        class="absolute inset-0 z-20 h-full w-full border-0 transition-opacity duration-500 ease-out"
        :class="liveReady ? 'opacity-100' : 'opacity-0'"
        @load="onLiveLoad"
      />

      <div
        v-if="playing && !liveReady"
        class="pointer-events-none absolute inset-x-0 bottom-3 z-30 flex justify-center"
      >
        <span class="inline-flex items-center gap-2 rounded-full bg-slate-900/75 px-3 py-1.5 text-[10px] font-semibold text-white backdrop-blur">
          <span class="size-1.5 animate-pulse rounded-full bg-white motion-reduce:animate-none" aria-hidden="true"></span> 正在加载实时预览
        </span>
      </div>
    </section>

    <section class="flex w-full shrink-0 flex-col gap-3 md:h-full md:w-72 md:overflow-y-auto md:pr-0.5 lg:w-[342px]">
      <div v-if="playing" class="flex items-center justify-between gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/5 px-3 py-2 text-[11px] font-semibold text-emerald-600 dark:text-emerald-300">
        <span class="inline-flex min-w-0 items-center gap-1.5">
          <span class="size-1.5 shrink-0 animate-pulse rounded-full bg-emerald-400 motion-reduce:animate-none" aria-hidden="true"></span>
          实时预览中
        </span>
        <button type="button" class="shrink-0 underline transition hover:no-underline" @click="stopLive">返回预览图</button>
      </div>

      <div class="overflow-hidden rounded-xl border border-slate-200 dark:border-white/10">
        <div class="flex items-center justify-between border-b border-slate-100 px-3.5 py-2.5 text-[11px] font-semibold text-slate-500 dark:border-white/10 dark:text-slate-400">
          <span>嵌入代码</span>
          <span class="font-mono text-[10px] text-slate-400">{{ isLive ? 'PAGE' : 'IMAGE' }}</span>
        </div>
        <pre class="max-h-36 overflow-auto whitespace-pre-wrap break-all p-3.5 font-mono text-[11px] leading-5 text-slate-700 dark:text-slate-200">{{ embedCode }}</pre>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="inline-flex min-h-10 items-center justify-center rounded-xl bg-indigo-600 px-3.5 text-xs font-semibold text-white transition hover:bg-indigo-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500"
          @click="copy(embedCode, 'embed')"
        >
          {{ copied === 'embed' ? '已复制嵌入代码' : '复制嵌入代码' }}
        </button>
        <button
          type="button"
          class="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-200 bg-white px-3.5 text-xs font-semibold text-slate-600 transition hover:border-indigo-300 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-indigo-400/40 dark:hover:text-indigo-300"
          @click="copy(item.embed_url, 'src')"
        >
          {{ copied === 'src' ? '已复制地址' : '复制嵌入地址' }}
        </button>
        <button
          type="button"
          class="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-200 bg-white px-3.5 text-xs font-semibold text-slate-600 transition hover:border-indigo-300 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-indigo-400/40 dark:hover:text-indigo-300"
          @click="openEmbedPage"
        >
          打开嵌入页 ↗
        </button>
      </div>

      <dl class="overflow-hidden rounded-xl border border-slate-200 text-xs dark:border-white/10">
        <div class="grid grid-cols-[76px_minmax(0,1fr)] gap-2 border-b border-slate-100 px-3.5 py-2.5 dark:border-white/10">
          <dt class="font-semibold text-slate-400">分类</dt>
          <dd class="min-w-0 truncate text-slate-700 dark:text-slate-200">{{ item.category }}</dd>
        </div>
        <div class="grid grid-cols-[76px_minmax(0,1fr)] gap-2 border-b border-slate-100 px-3.5 py-2.5 dark:border-white/10">
          <dt class="font-semibold text-slate-400">内容类型</dt>
          <dd class="text-slate-700 dark:text-slate-200">{{ isLive ? '网页挂件' : '图片' }}</dd>
        </div>
        <div class="grid grid-cols-[76px_minmax(0,1fr)] gap-2 border-b border-slate-100 px-3.5 py-2.5 dark:border-white/10">
          <dt class="font-semibold text-slate-400">推荐尺寸</dt>
          <dd class="font-mono text-slate-700 dark:text-slate-200">{{ item.width }} × {{ item.height }}</dd>
        </div>
        <div class="grid grid-cols-[76px_minmax(0,1fr)] gap-2 border-b border-slate-100 px-3.5 py-2.5 dark:border-white/10">
          <dt class="font-semibold text-slate-400">沙箱</dt>
          <dd class="min-w-0 break-all font-mono text-[11px] text-slate-700 dark:text-slate-200">{{ item.sandbox || '默认（禁止脚本）' }}</dd>
        </div>
        <div class="grid grid-cols-[76px_minmax(0,1fr)] gap-2 px-3.5 py-2.5">
          <dt class="font-semibold text-slate-400">原始地址</dt>
          <dd class="min-w-0">
            <a :href="item.content_url" target="_blank" rel="noopener noreferrer" class="break-all font-semibold text-indigo-600 hover:underline dark:text-indigo-300">打开 ↗</a>
          </dd>
        </div>
      </dl>
    </section>
  </div>
</template>

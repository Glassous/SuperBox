<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { beginCardTransition, cancelCardTransition, finishCardTransition, getOpeningPayload, isPlainNavigation } from '../animations/cardTransition'
import { warmPreviewImage } from '../animations/previewImageCache'
import { apiBaseUrl, getIframe } from '../api/client'
import type { IframeInfo } from '../types'

const route = useRoute()
const item = ref<IframeInfo | null>(null)
const error = ref('')
const detail = ref<HTMLElement | null>(null)
const liveReady = ref(false)
const previewFailed = ref(false)
const liveEnabled = ref(false)
const copied = ref<'embed' | 'src' | null>(null)
let controller: AbortController | undefined
let copyTimer: ReturnType<typeof setTimeout> | undefined
let liveTimer: ReturnType<typeof setTimeout> | undefined

const previewSrc = computed(() => item.value ? item.value.preview_url || item.value.thumbnail_url : '')
const isLive = computed(() => item.value?.content_type === 'page')
const previewStyle = computed(() => item.value
  ? { maxWidth: `${item.value.width}px`, aspectRatio: `${item.value.width} / ${item.value.height}` }
  : {})
const embedUrl = (value: IframeInfo) => `${apiBaseUrl}${value.embed_path}`
const embedCode = computed(() => {
  const value = item.value
  if (!value) return ''
  const attributes = [
    `src="${embedUrl(value)}"`,
    `title="${value.name}"`,
    `width="${value.width}"`,
    `height="${value.height}"`,
    'loading="lazy"',
    `sandbox="${value.sandbox}"`,
    'style="border:0;max-width:100%"',
  ]
  if (value.allow) attributes.push(`allow="${value.allow}"`)
  return `<iframe ${attributes.join(' ')}></iframe>`
})

watch(() => route.params.slug, async slug => {
  controller?.abort()
  controller = new AbortController()
  const current = controller
  item.value = getOpeningPayload<IframeInfo>('iframe', String(slug))
  error.value = ''
  liveReady.value = false
  previewFailed.value = false
  try {
    item.value = await getIframe(String(slug), current.signal)
  } catch (cause) {
    if (!current.signal.aborted) {
      error.value = cause instanceof Error ? cause.message : 'Iframe 加载失败'
      item.value = null
      cancelCardTransition()
    }
  }
}, { immediate: true })

// 预览图与列表卡片同源，提前保留位图供详情页与翻转过渡复用。
watch(previewSrc, url => warmPreviewImage(url), { immediate: true })

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
  if (item.value) window.open(embedUrl(item.value), '_blank', 'noopener,noreferrer')
}

function backToLibrary(event: MouseEvent) {
  if (!detail.value || !isPlainNavigation(event)) return
  beginCardTransition('iframe', 'return', String(route.params.slug), detail.value)
}

onMounted(async () => {
  await nextTick()
  // 详情页的实时预览等翻转结束再加载，避免和预览图飞行重叠。
  const animated = detail.value
    ? finishCardTransition('iframe', 'open', String(route.params.slug), detail.value)
    : false
  liveTimer = setTimeout(() => { liveEnabled.value = true }, animated ? 460 : 0)
})

onBeforeUnmount(() => {
  controller?.abort()
  if (copyTimer) clearTimeout(copyTimer)
  if (liveTimer) clearTimeout(liveTimer)
})
</script>

<template>
  <div>
    <div v-if="error" class="mt-9 rounded-2xl border border-rose-200 bg-rose-50 p-8 text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300" role="alert">
      {{ error }}
      <RouterLink to="/iframes" class="ml-3 font-bold underline">返回 Iframe 仓库</RouterLink>
    </div>
    <div v-else-if="!item" class="mt-9 h-96 animate-pulse rounded-3xl bg-slate-200 dark:bg-white/5" aria-label="正在加载"></div>
    <div v-else ref="detail" data-card-transition-detail>
      <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div class="min-w-0">
          <div data-card-transition="category" class="text-xs font-bold tracking-[0.18em] text-indigo-600 dark:text-indigo-400">{{ item.category }}</div>
          <h1 data-card-transition="title" class="mt-1 text-3xl font-bold tracking-tight text-slate-950 dark:text-white">{{ item.name }}</h1>
          <p data-card-transition="description" class="mt-2 max-w-2xl text-sm leading-6 text-slate-500 dark:text-slate-400">{{ item.description }}</p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <span class="rounded-full bg-slate-100 px-3 py-1 font-mono text-[11px] font-semibold text-slate-500 dark:bg-white/5 dark:text-slate-400">{{ item.width }} × {{ item.height }}</span>
          <RouterLink to="/iframes" class="inline-flex h-9 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-600 transition hover:border-indigo-300 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-indigo-400/40 dark:hover:text-indigo-300" @click.capture="backToLibrary">
            <span aria-hidden="true">←</span> 仓库
          </RouterLink>
        </div>
      </div>

      <div class="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div class="min-w-0">
          <div class="rounded-3xl border border-slate-200/80 bg-white p-3 shadow-[0_30px_70px_-40px_rgba(15,23,42,0.45)] dark:border-white/10 dark:bg-[#141a2c]">
            <div class="mx-auto w-full overflow-hidden rounded-2xl bg-slate-100 dark:bg-[#0c1020]" :style="previewStyle">
              <div class="relative h-full w-full">
                <div data-card-transition="media" class="absolute inset-0 overflow-hidden rounded-xl bg-slate-100 dark:bg-[#0c1020]">
                  <img
                    v-if="previewSrc && !previewFailed"
                    :src="previewSrc"
                    :alt="item.name"
                    loading="eager"
                    decoding="async"
                    class="h-full w-full object-cover"
                    @error="previewFailed = true"
                  />
                  <div v-else class="flex h-full items-center justify-center font-mono text-4xl text-slate-400">▣</div>
                </div>
                <iframe
                  v-if="isLive && liveEnabled"
                  :src="embedUrl(item)"
                  :title="item.name"
                  :sandbox="item.sandbox"
                  :allow="item.allow || undefined"
                  class="absolute inset-0 h-full w-full border-0 bg-white transition-opacity duration-500 ease-out dark:bg-[#0c1020]"
                  :class="liveReady ? 'opacity-100' : 'opacity-0'"
                  @load="onLiveLoad"
                />
                <div v-if="isLive && liveEnabled && !liveReady" class="pointer-events-none absolute bottom-3 right-3 z-10 inline-flex items-center gap-2 rounded-full bg-slate-900/70 px-3 py-1.5 text-[11px] font-semibold text-white backdrop-blur">
                  <span class="size-1.5 animate-pulse rounded-full bg-white" aria-hidden="true"></span> 正在加载实时预览
                </div>
              </div>
            </div>
            <div class="flex flex-wrap items-center justify-between gap-3 px-2 pb-1 pt-3">
              <span class="inline-flex items-center gap-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                <span class="size-1.5 rounded-full" :class="isLive ? 'bg-emerald-400' : 'bg-indigo-400'" aria-hidden="true"></span>
                {{ isLive ? '预览图先行，实时网页淡入覆盖' : '预览图与实际效果为同一张图片' }}
              </span>
              <span class="font-mono text-[11px] text-slate-400">{{ item.slug }} · {{ item.content_type === 'image' ? '图片' : '网页' }}</span>
            </div>
          </div>

          <div class="mt-3 flex flex-wrap items-center gap-2">
            <button type="button" class="tool-button" @click="copy(embedCode, 'embed')">{{ copied === 'embed' ? '已复制嵌入代码' : '复制嵌入代码' }}</button>
            <button type="button" class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-indigo-300 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-indigo-400/40 dark:hover:text-indigo-300" @click="openEmbedPage">打开嵌入页 ↗</button>
            <button type="button" class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-indigo-300 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-indigo-400/40 dark:hover:text-indigo-300" @click="copy(embedUrl(item), 'src')">{{ copied === 'src' ? '已复制地址' : '复制嵌入地址' }}</button>
          </div>
        </div>

        <aside class="min-w-0 space-y-4">
          <section class="overflow-hidden rounded-xl border border-slate-200 dark:border-white/10">
            <div class="border-b border-slate-100 px-4 py-2.5 text-xs font-semibold text-slate-500 dark:border-white/10 dark:text-slate-400">嵌入代码</div>
            <pre class="max-h-48 overflow-auto whitespace-pre-wrap break-all p-4 font-mono text-xs leading-5 text-slate-700 dark:text-slate-200">{{ embedCode }}</pre>
          </section>
          <dl class="overflow-hidden rounded-xl border border-slate-200 text-sm dark:border-white/10">
            <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3 dark:border-white/10">
              <dt class="text-xs font-semibold text-slate-400">slug</dt>
              <dd class="min-w-0 truncate font-mono text-xs text-slate-700 dark:text-slate-200">{{ item.slug }}</dd>
            </div>
            <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3 dark:border-white/10">
              <dt class="text-xs font-semibold text-slate-400">内容类型</dt>
              <dd class="text-xs text-slate-700 dark:text-slate-200">{{ item.content_type === 'image' ? '图片' : '网页' }}</dd>
            </div>
            <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3 dark:border-white/10">
              <dt class="text-xs font-semibold text-slate-400">预览图</dt>
              <dd class="text-xs text-slate-700 dark:text-slate-200">{{ item.content_type === 'image' ? '与嵌入图片相同' : (item.preview_url ? '独立预览截图' : '未提供') }}</dd>
            </div>
            <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3 dark:border-white/10">
              <dt class="text-xs font-semibold text-slate-400">沙箱</dt>
              <dd class="min-w-0 break-all font-mono text-xs text-slate-700 dark:text-slate-200">{{ item.sandbox || '默认（禁止脚本）' }}</dd>
            </div>
            <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3 dark:border-white/10">
              <dt class="text-xs font-semibold text-slate-400">原始地址</dt>
              <dd class="min-w-0"><a :href="item.content_url" target="_blank" rel="noopener noreferrer" class="break-all text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-300">打开 ↗</a></dd>
            </div>
            <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 px-4 py-3">
              <dt class="text-xs font-semibold text-slate-400">嵌入地址</dt>
              <dd class="min-w-0"><a :href="embedUrl(item)" target="_blank" rel="noopener noreferrer" class="break-all text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-300">打开 ↗</a></dd>
            </div>
          </dl>
          <RouterLink to="/api-access" class="inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-300">查看 Iframe API 文档 →</RouterLink>
        </aside>
      </div>
    </div>
  </div>
</template>

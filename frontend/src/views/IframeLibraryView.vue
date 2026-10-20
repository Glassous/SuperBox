<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { isPlainNavigation } from '../animations/toolOpenTransition'
import { apiBaseUrl, getIframe, getIframes } from '../api/client'
import type { IframeInfo } from '../types'

const route = useRoute()
const router = useRouter()
const query = ref('')
const iframes = ref<IframeInfo[]>([])
const loading = ref(true)
const error = ref('')
const selected = ref<IframeInfo | null>(null)
const previewLoading = ref(false)
const previewError = ref('')
const previewPanel = ref<HTMLElement | null>(null)
const copied = ref<'embed' | 'src' | null>(null)
const failedThumbnails = ref(new Set<string>())
let listTimer: ReturnType<typeof setTimeout> | undefined
let copyTimer: ReturnType<typeof setTimeout> | undefined
let listController: AbortController | undefined
let previewController: AbortController | undefined

const previewSlug = computed(() => typeof route.query.preview === 'string' ? route.query.preview : '')
const embedUrl = (item: IframeInfo) => `${apiBaseUrl}${item.embed_path}`
const embedCode = computed(() => {
  const item = selected.value
  if (!item) return ''
  const attributes = [
    `src="${embedUrl(item)}"`,
    `title="${item.name}"`,
    `width="${item.width}"`,
    `height="${item.height}"`,
    'loading="lazy"',
    `sandbox="${item.sandbox}"`,
    'style="border:0;max-width:100%"',
  ]
  if (item.allow) attributes.push(`allow="${item.allow}"`)
  return `<iframe ${attributes.join(' ')}></iframe>`
})

async function loadIframes() {
  listController?.abort()
  const controller = new AbortController()
  listController = controller
  loading.value = true
  error.value = ''
  try {
    iframes.value = (await getIframes(query.value, controller.signal)).iframes
  } catch (cause) {
    if (!controller.signal.aborted) {
      error.value = cause instanceof Error ? cause.message : '加载 Iframe 仓库失败'
      iframes.value = []
    }
  } finally {
    if (!controller.signal.aborted) loading.value = false
  }
}

async function loadPreview(slug: string) {
  previewController?.abort()
  previewError.value = ''
  if (!slug) {
    selected.value = null
    previewLoading.value = false
    return
  }
  const controller = new AbortController()
  previewController = controller
  previewLoading.value = true
  try {
    selected.value = await getIframe(slug, controller.signal)
  } catch (cause) {
    if (!controller.signal.aborted) {
      selected.value = null
      previewError.value = cause instanceof Error ? cause.message : '加载预览失败'
    }
  } finally {
    if (!controller.signal.aborted) previewLoading.value = false
  }
}

async function openPreview(event: MouseEvent, item: IframeInfo) {
  if (!isPlainNavigation(event)) return
  event.preventDefault()
  await router.replace({ query: { ...route.query, preview: item.slug } })
  await nextTick()
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  previewPanel.value?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
}

function closePreview() {
  void router.replace({ query: {} })
}

function markThumbnailFailed(slug: string) {
  failedThumbnails.value = new Set(failedThumbnails.value).add(slug)
}

function openEmbedPage() {
  if (selected.value) window.open(embedUrl(selected.value), '_blank', 'noopener,noreferrer')
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

watch(query, () => {
  if (listTimer) clearTimeout(listTimer)
  listTimer = setTimeout(loadIframes, 250)
})

watch(previewSlug, slug => { void loadPreview(slug) }, { immediate: true })

onMounted(loadIframes)
onBeforeUnmount(() => {
  if (listTimer) clearTimeout(listTimer)
  if (copyTimer) clearTimeout(copyTimer)
  listController?.abort()
  previewController?.abort()
})
</script>

<template>
  <div>
    <section>
      <div class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <div class="text-[11px] font-bold tracking-[0.2em] text-indigo-600 dark:text-indigo-400">SUPERBOX / IFRAME LIBRARY</div>
          <h1 class="mt-2 text-3xl font-bold tracking-tight text-slate-950 dark:text-white">Iframe 仓库</h1>
          <p class="mt-2 max-w-xl text-sm leading-6 text-slate-500 dark:text-slate-400">可直接嵌入任意页面的网页挂件。点击标题预览，复制标准 iframe 代码。</p>
        </div>
        <label class="relative block w-full sm:w-82">
          <span class="sr-only">搜索 Iframe</span>
          <svg class="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
          <input v-model="query" type="search" maxlength="100" placeholder="搜索名称、分类或关键词..." class="w-full rounded-xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100 dark:border-white/10 dark:bg-white/5 dark:text-white dark:focus:ring-indigo-500/10" />
        </label>
      </div>

      <div v-if="error" class="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300" role="alert">
        {{ error }} <button type="button" class="ml-3 font-bold underline" @click="loadIframes">重试</button>
      </div>

      <section v-if="previewSlug" ref="previewPanel" class="mt-7 scroll-mt-24 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#141a2c] sm:p-6">
        <div v-if="previewLoading" class="h-64 animate-pulse rounded-xl bg-slate-200/70 dark:bg-white/5" aria-label="正在加载预览"></div>
        <div v-else-if="previewError" class="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300" role="alert">
          {{ previewError }}
          <button type="button" class="ml-3 font-bold underline" @click="loadPreview(previewSlug)">重试</button>
          <button type="button" class="ml-3 font-bold underline" @click="closePreview">关闭预览</button>
        </div>
        <template v-else-if="selected">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div class="text-xs font-bold tracking-[0.18em] text-indigo-600 dark:text-indigo-400">{{ selected.category }}</div>
              <h2 class="mt-1 text-2xl font-bold tracking-tight text-slate-950 dark:text-white">{{ selected.name }}</h2>
              <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">{{ selected.description }}</p>
            </div>
            <div class="flex items-center gap-2">
              <span class="rounded-full bg-slate-100 px-3 py-1 font-mono text-[11px] font-semibold text-slate-500 dark:bg-white/5 dark:text-slate-400">{{ selected.width }} × {{ selected.height }}</span>
              <button type="button" class="inline-flex size-9 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-500 transition hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900 dark:border-white/10 dark:bg-white/5 dark:text-slate-400 dark:hover:border-white/20 dark:hover:bg-white/10 dark:hover:text-white" aria-label="关闭预览" @click="closePreview">
                <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
              </button>
            </div>
          </div>

          <div class="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
            <div class="min-w-0">
              <div class="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-[#0c1020]">
                <div class="mx-auto w-full overflow-hidden rounded-lg bg-white dark:bg-[#0c1020]" :style="{ maxWidth: `${selected.width}px`, aspectRatio: `${selected.width} / ${selected.height}` }">
                  <iframe :src="embedUrl(selected)" :title="selected.name" :sandbox="selected.sandbox" :allow="selected.allow || undefined" class="h-full w-full border-0" />
                </div>
              </div>
              <div class="mt-3 flex flex-wrap items-center gap-2">
                <button type="button" class="tool-button" @click="copy(embedCode, 'embed')">{{ copied === 'embed' ? '已复制嵌入代码' : '复制嵌入代码' }}</button>
                <button type="button" class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-indigo-300 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-indigo-400/40 dark:hover:text-indigo-300" @click="openEmbedPage">打开嵌入页 ↗</button>
                <button type="button" class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-indigo-300 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-indigo-400/40 dark:hover:text-indigo-300" @click="copy(embedUrl(selected), 'src')">{{ copied === 'src' ? '已复制地址' : '复制嵌入地址' }}</button>
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
                  <dd class="min-w-0 truncate font-mono text-xs text-slate-700 dark:text-slate-200">{{ selected.slug }}</dd>
                </div>
                <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3 dark:border-white/10">
                  <dt class="text-xs font-semibold text-slate-400">内容类型</dt>
                  <dd class="text-xs text-slate-700 dark:text-slate-200">{{ selected.content_type === 'image' ? '图片' : '网页' }}</dd>
                </div>
                <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3 dark:border-white/10">
                  <dt class="text-xs font-semibold text-slate-400">沙箱</dt>
                  <dd class="min-w-0 break-all font-mono text-xs text-slate-700 dark:text-slate-200">{{ selected.sandbox || '默认（禁止脚本）' }}</dd>
                </div>
                <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 border-b border-slate-100 px-4 py-3 dark:border-white/10">
                  <dt class="text-xs font-semibold text-slate-400">原始地址</dt>
                  <dd class="min-w-0"><a :href="selected.content_url" target="_blank" rel="noopener noreferrer" class="break-all text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-300">打开 ↗</a></dd>
                </div>
                <div class="grid grid-cols-[88px_minmax(0,1fr)] gap-3 px-4 py-3">
                  <dt class="text-xs font-semibold text-slate-400">嵌入地址</dt>
                  <dd class="min-w-0"><a :href="embedUrl(selected)" target="_blank" rel="noopener noreferrer" class="break-all text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-300">打开 ↗</a></dd>
                </div>
              </dl>
              <RouterLink to="/api-access" class="inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-300">查看 Iframe API 文档 →</RouterLink>
            </aside>
          </div>
        </template>
      </section>

      <div v-if="loading" class="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-3" aria-label="正在加载">
        <div v-for="i in 3" :key="i" class="h-80 animate-pulse rounded-2xl bg-slate-200/70 dark:bg-white/5"></div>
      </div>
      <div v-else-if="iframes.length === 0" class="mt-7 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center dark:border-white/10 dark:bg-white/5">
        <div class="text-3xl">⌕</div>
        <p class="mt-3 font-semibold">没有找到匹配的 Iframe</p>
        <p class="mt-1 text-sm text-slate-500">试试其他关键词。</p>
      </div>
      <div v-else class="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <a v-for="item in iframes" :key="item.slug" :href="`?preview=${encodeURIComponent(item.slug)}`" :aria-current="previewSlug === item.slug ? 'true' : undefined" class="group flex w-full flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white text-left shadow-sm transition duration-200 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-900/5 dark:border-white/10 dark:bg-[#141a2c] dark:hover:border-indigo-400/30" :class="previewSlug === item.slug ? 'border-indigo-300 ring-2 ring-indigo-100 dark:border-indigo-400/40 dark:ring-indigo-400/10' : ''" @click="openPreview($event, item)">
          <div class="aspect-[16/10] w-full overflow-hidden bg-slate-100 dark:bg-white/5">
            <img v-if="item.thumbnail_url && !failedThumbnails.has(item.slug)" :src="item.thumbnail_url" :alt="item.name" loading="lazy" decoding="async" class="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]" @error="markThumbnailFailed(item.slug)" />
            <div v-else class="flex h-full items-center justify-center font-mono text-3xl text-slate-400">▣</div>
          </div>
          <div class="flex flex-1 flex-col p-5">
            <div class="flex items-center justify-between gap-3">
              <span class="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold text-slate-500 dark:bg-white/5 dark:text-slate-400">{{ item.category }}</span>
              <span class="font-mono text-[11px] text-slate-400">{{ item.width }} × {{ item.height }}</span>
            </div>
            <h2 class="mt-4 text-lg font-bold text-slate-950 group-hover:text-indigo-600 dark:text-white dark:group-hover:text-indigo-300">{{ item.name }}</h2>
            <p class="mt-2 min-h-10 text-sm leading-5 text-slate-500 dark:text-slate-400">{{ item.description }}</p>
            <div class="mt-4 flex items-center gap-2 text-sm font-semibold text-indigo-600 transition group-hover:gap-3 dark:text-indigo-400">预览 iframe <span>→</span></div>
          </div>
        </a>
      </div>
    </section>
  </div>
</template>

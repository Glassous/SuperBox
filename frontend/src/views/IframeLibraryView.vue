<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { beginCardTransition, cancelCardTransition, finishCardTransition, getReturningSlug, isPlainNavigation } from '../animations/cardTransition'
import { warmPreviewImage } from '../animations/previewImageCache'
import { getIframes } from '../api/client'
import type { IframeInfo } from '../types'

const query = ref('')
const iframes = ref<IframeInfo[]>([])
const loading = ref(true)
const error = ref('')
const failedPreviews = ref(new Set<string>())
let timer: ReturnType<typeof setTimeout> | undefined
let activeController: AbortController | undefined

const previewSource = (item: IframeInfo) => item.preview_url || item.thumbnail_url

function beginOpen(event: MouseEvent, item: IframeInfo) {
  if (!isPlainNavigation(event) || !(event.currentTarget instanceof HTMLElement)) return
  beginCardTransition('iframe', 'open', item.slug, event.currentTarget, item)
}

async function finishReturn() {
  const slug = getReturningSlug('iframe')
  if (!slug || loading.value) return
  if (error.value) {
    cancelCardTransition()
    return
  }
  await nextTick()
  if (getReturningSlug('iframe') !== slug) return
  const cards = document.querySelectorAll<HTMLElement>('[data-card-slug]')
  const card = Array.from(cards).find(element => element.dataset.cardSlug === slug)
  if (card) finishCardTransition('iframe', 'return', slug, card)
  else cancelCardTransition()
}

async function loadIframes() {
  activeController?.abort()
  const controller = new AbortController()
  activeController = controller
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

function markPreviewFailed(slug: string) {
  failedPreviews.value = new Set(failedPreviews.value).add(slug)
}

watch(query, () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(loadIframes, 250)
})
watch(loading, () => { void finishReturn() }, { flush: 'post' })
watch(iframes, items => {
  // 预览图先放进内存缓存，详情页与翻转过渡直接复用同一张位图。
  for (const item of items) warmPreviewImage(previewSource(item))
})
onMounted(loadIframes)
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
  activeController?.abort()
})
</script>

<template>
  <div>
    <section>
      <div class="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <div class="text-[11px] font-bold tracking-[0.2em] text-indigo-600 dark:text-indigo-400">SUPERBOX / IFRAME LIBRARY</div>
          <h1 class="mt-2 text-3xl font-bold tracking-tight text-slate-950 dark:text-white">Iframe 仓库</h1>
          <p class="mt-2 max-w-xl text-sm leading-6 text-slate-500 dark:text-slate-400">可直接嵌入任意页面的网页挂件。点击卡片进入详情，以大卡片预览效果并复制标准 iframe 代码。</p>
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

      <div v-if="loading" class="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-3" aria-label="正在加载">
        <div v-for="i in 3" :key="i" class="h-80 animate-pulse rounded-2xl bg-slate-200/70 dark:bg-white/5"></div>
      </div>
      <div v-else-if="iframes.length === 0" class="mt-7 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center dark:border-white/10 dark:bg-white/5">
        <div class="text-3xl">⌕</div>
        <p class="mt-3 font-semibold">没有找到匹配的 Iframe</p>
        <p class="mt-1 text-sm text-slate-500">试试其他关键词。</p>
      </div>
      <div v-else class="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <RouterLink
          v-for="item in iframes"
          :key="item.slug"
          :to="`/iframes/${item.slug}`"
          :data-card-slug="item.slug"
          class="group flex w-full flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white text-left shadow-sm transition duration-200 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-900/5 dark:border-white/10 dark:bg-[#141a2c] dark:hover:border-indigo-400/30"
          @click.capture="beginOpen($event, item)"
          @pointerenter="warmPreviewImage(previewSource(item))"
        >
          <div class="p-2.5 pb-0">
            <div class="aspect-[16/10] w-full overflow-hidden rounded-xl bg-slate-100 dark:bg-white/5">
              <div data-card-transition="media" class="h-full w-full overflow-hidden rounded-xl transition-transform duration-500 group-hover:scale-[1.03]">
                <img
                  v-if="previewSource(item) && !failedPreviews.has(item.slug)"
                  :src="previewSource(item)"
                  :alt="item.name"
                  loading="lazy"
                  decoding="async"
                  class="h-full w-full object-cover"
                  @error="markPreviewFailed(item.slug)"
                />
                <div v-else class="flex h-full items-center justify-center font-mono text-3xl text-slate-400">▣</div>
              </div>
            </div>
          </div>
          <div class="flex flex-1 flex-col p-5">
            <div class="flex items-center justify-between gap-3">
              <span data-card-transition="category" class="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold text-slate-500 dark:bg-white/5 dark:text-slate-400">{{ item.category }}</span>
              <span class="font-mono text-[11px] text-slate-400">{{ item.width }} × {{ item.height }}</span>
            </div>
            <h2 data-card-transition="title" class="mt-4 text-lg font-bold text-slate-950 dark:text-white">{{ item.name }}</h2>
            <p data-card-transition="description" class="mt-2 min-h-10 text-sm leading-5 text-slate-500 dark:text-slate-400">{{ item.description }}</p>
            <div class="mt-4 flex items-center gap-2 text-sm font-semibold text-indigo-600 transition group-hover:gap-3 dark:text-indigo-400">预览 iframe <span>→</span></div>
          </div>
        </RouterLink>
      </div>

      <RouterLink to="/api-access" class="mt-8 inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-300">查看 Iframe API 文档 →</RouterLink>
    </section>
  </div>
</template>

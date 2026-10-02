<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { beginToolTransition, cancelToolTransition, finishToolTransition, getReturningSlug, isPlainNavigation } from '../animations/toolOpenTransition'
import { getTools } from '../api/client'
import ToolMark from '../components/ToolMark.vue'
import type { ToolInfo } from '../types'

const query = ref('')
const tools = ref<ToolInfo[]>([])
const loading = ref(true)
const error = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
let activeController: AbortController | undefined

function beginOpen(event: MouseEvent, tool: ToolInfo) {
  if (!isPlainNavigation(event) || !(event.currentTarget instanceof HTMLElement)) return
  beginToolTransition('open', tool.slug, event.currentTarget, tool)
}

async function finishReturn() {
  const slug = getReturningSlug()
  if (!slug || loading.value) return
  if (error.value) {
    cancelToolTransition()
    return
  }
  await nextTick()
  if (getReturningSlug() !== slug) return
  const cards = document.querySelectorAll<HTMLElement>('[data-tool-slug]')
  const card = Array.from(cards).find(element => element.dataset.toolSlug === slug)
  if (card) finishToolTransition('return', slug, card)
  else cancelToolTransition()
}

async function loadTools() {
  activeController?.abort()
  const controller = new AbortController()
  activeController = controller
  loading.value = true
  error.value = ''
  try {
    tools.value = (await getTools(query.value, controller.signal)).tools
  } catch (cause) {
    if (!controller.signal.aborted) {
      error.value = cause instanceof Error ? cause.message : '加载工具失败'
      tools.value = []
    }
  } finally {
    if (!controller.signal.aborted) loading.value = false
  }
}

watch(query, () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(loadTools, 250)
})
watch(loading, () => { void finishReturn() }, { flush: 'post' })
onMounted(loadTools)
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
          <h1 class="text-3xl font-bold tracking-tight text-slate-950 dark:text-white">全部工具</h1>
        </div>
        <label class="relative block w-full sm:w-82">
          <span class="sr-only">搜索工具</span>
          <svg class="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
          <input v-model="query" type="search" maxlength="100" placeholder="搜索工具名称或关键词..." class="w-full rounded-xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100 dark:border-white/10 dark:bg-white/5 dark:text-white dark:focus:ring-indigo-500/10" />
        </label>
      </div>

      <div v-if="error" class="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300" role="alert">
        {{ error }} <button class="ml-3 font-bold underline" @click="loadTools">重试</button>
      </div>
      <div v-else-if="loading" class="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-4" aria-label="正在处理">
        <div v-for="i in 4" :key="i" class="h-53 animate-pulse rounded-2xl bg-slate-200/70 dark:bg-white/5"></div>
      </div>
      <div v-else-if="tools.length === 0" class="mt-7 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center dark:border-white/10 dark:bg-white/5">
        <div class="text-3xl">⌕</div>
        <p class="mt-3 font-semibold">没有找到匹配的工具</p>
        <p class="mt-1 text-sm text-slate-500">试试其他关键词。</p>
      </div>
      <div v-else class="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <RouterLink v-for="tool in tools" :key="tool.slug" :to="`/tools/${tool.slug}`" :data-tool-slug="tool.slug" class="group rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-900/5 dark:border-white/10 dark:bg-[#141a2c] dark:hover:border-indigo-400/30" @click.capture="beginOpen($event, tool)">
          <div class="flex items-start justify-between">
            <div data-tool-transition="icon"><ToolMark :slug="tool.slug" size="lg" /></div>
            <span data-tool-transition="category" class="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold text-slate-500 dark:bg-white/5 dark:text-slate-400">{{ tool.category }}</span>
          </div>
          <h3 data-tool-transition="title" class="mt-6 text-lg font-bold text-slate-950 dark:text-white">{{ tool.name }}</h3>
          <p data-tool-transition="description" class="mt-2 min-h-10 text-sm leading-5 text-slate-500 dark:text-slate-400">{{ tool.description }}</p>
          <div class="mt-5 flex items-center gap-2 text-sm font-semibold text-indigo-600 transition group-hover:gap-3 dark:text-indigo-400">打开工具 <span>→</span></div>
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { gsap } from 'gsap'
import { apiBaseUrl } from '../api/client'
import { apiOverview, groupApiOverview, isTestableItem, type ApiOverviewItem } from '../data/apiOverview'

const emit = defineEmits<{ 'test-operation': [payload: { slug: string; operationId: string }] }>()
const groups = groupApiOverview()
const root = ref<HTMLElement | null>(null)
const copiedPath = ref<string | null>(null)
let copyTimer: ReturnType<typeof setTimeout> | undefined
let context: gsap.Context | undefined

function fullUrl(path: string) {
  return `${apiBaseUrl}/api/v1${path}`
}

async function copyPath(item: ApiOverviewItem) {
  try {
    await navigator.clipboard.writeText(fullUrl(item.path))
    copiedPath.value = item.path
  } catch {
    copiedPath.value = null
  }
  if (copyTimer) clearTimeout(copyTimer)
  copyTimer = setTimeout(() => { copiedPath.value = null }, 1800)
}

function testOperation(item: ApiOverviewItem) {
  if (item.toolSlug && item.operationId) {
    emit('test-operation', { slug: item.toolSlug, operationId: item.operationId })
  }
}

function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

onMounted(() => {
  if (!root.value || reducedMotion()) return
  context = gsap.context(() => {
    gsap.from('.api-overview-row', { autoAlpha: 0, y: 12, duration: 0.4, ease: 'power2.out', stagger: 0.025 })
  }, root.value)
})

onBeforeUnmount(() => {
  if (copyTimer) clearTimeout(copyTimer)
  context?.revert()
})
</script>

<template>
  <section ref="root" class="mt-10" aria-labelledby="api-overview-title">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 id="api-overview-title" class="text-xl font-bold text-slate-950 dark:text-white">全部功能总览</h2>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">完整能力清单，复制地址即可调用，工具接口可直达在线测试。</p>
      </div>
      <span class="font-mono text-xs text-slate-400">{{ String(apiOverview.length).padStart(2, '0') }} ENDPOINTS</span>
    </div>

    <div class="mt-6 space-y-6">
      <div v-for="group in groups" :key="group.category">
        <div class="flex items-center gap-3">
          <h3 class="text-[11px] font-bold tracking-[0.14em] text-slate-400 dark:text-slate-500">{{ group.category }}</h3>
          <span class="font-mono text-[11px] text-slate-400">{{ String(group.items.length).padStart(2, '0') }}</span>
          <div class="h-px flex-1 bg-slate-200 dark:bg-white/10" aria-hidden="true"></div>
        </div>

        <ul class="mt-3 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#141a2c]">
          <li v-for="item in group.items" :key="`${item.method}-${item.path}`"
            class="api-overview-row flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-slate-100 px-4 py-3 transition-colors last:border-b-0 hover:bg-slate-50 dark:border-white/5 dark:hover:bg-white/5">
            <span class="inline-block w-12 shrink-0 rounded-md py-1 text-center font-mono text-[10px] font-bold"
              :class="item.method === 'GET' ? 'bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300' : 'bg-indigo-50 text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-300'">{{ item.method }}</span>
            <code class="font-mono text-xs font-semibold text-slate-800 dark:text-slate-100">{{ item.path }}</code>
            <p class="w-full min-w-0 text-xs leading-5 text-slate-500 dark:text-slate-400 sm:w-auto sm:flex-1">{{ item.summary }}</p>
            <div class="ml-auto flex shrink-0 items-center gap-2">
              <button type="button" :aria-label="`复制 ${item.name} 的接口地址`"
                class="cursor-pointer rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 outline-none transition hover:border-indigo-200 hover:text-indigo-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:border-indigo-400/30 dark:hover:text-indigo-300"
                @click="copyPath(item)">{{ copiedPath === item.path ? '已复制' : '复制地址' }}</button>
              <button v-if="isTestableItem(item)" type="button" :aria-label="`在线测试 ${item.name}`"
                class="cursor-pointer rounded-lg bg-indigo-600 px-2.5 py-1.5 text-[11px] font-semibold text-white outline-none transition hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 dark:bg-indigo-500 dark:hover:bg-indigo-400"
                @click="testOperation(item)">在线测试</button>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

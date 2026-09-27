<script setup lang="ts">
import { defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { cancelToolTransition, finishToolTransition, getOpeningTool } from '../animations/toolOpenTransition'
import { getTool } from '../api/client'
import ToolMark from '../components/ToolMark.vue'
import type { ToolInfo } from '../types'

const forms = {
  json: defineAsyncComponent(() => import('../tools/JsonTool.vue')),
  base64: defineAsyncComponent(() => import('../tools/Base64Tool.vue')),
  url: defineAsyncComponent(() => import('../tools/UrlTool.vue')),
  timestamp: defineAsyncComponent(() => import('../tools/TimestampTool.vue')),
}

const route = useRoute()
const tool = ref<ToolInfo | null>(null)
const loading = ref(true)
const error = ref('')
const detail = ref<HTMLElement | null>(null)
const body = ref<HTMLElement | null>(null)
let controller: AbortController | undefined

watch(() => route.params.slug, async slug => {
  controller?.abort()
  controller = new AbortController()
  const current = controller
  tool.value = getOpeningTool(String(slug))
  error.value = ''
  loading.value = true
  try {
    tool.value = await getTool(String(slug), current.signal)
  } catch (cause) {
    if (!current.signal.aborted) {
      error.value = cause instanceof Error ? cause.message : '工具加载失败'
      tool.value = null
      cancelToolTransition()
    }
  } finally {
    if (!current.signal.aborted) loading.value = false
  }
}, { immediate: true })

onMounted(async () => {
  await nextTick()
  if (detail.value) finishToolTransition('open', String(route.params.slug), detail.value, body.value)
})

onBeforeUnmount(() => controller?.abort())
</script>

<template>
  <div>
    <div v-if="error" class="mt-9 rounded-2xl border border-rose-200 bg-rose-50 p-8 text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300" role="alert">{{ error }}</div>
    <div v-else-if="!tool" class="mt-9 h-80 animate-pulse rounded-2xl bg-slate-200 dark:bg-white/5" aria-label="正在加载工具"></div>
    <template v-else>
      <div ref="detail" data-tool-transition-detail class="flex flex-col gap-5 sm:flex-row sm:items-center">
        <div data-tool-transition="icon"><ToolMark :slug="tool.slug" size="lg" /></div>
        <div>
          <div data-tool-transition="category" class="text-xs font-bold tracking-[0.18em] text-indigo-600 dark:text-indigo-400">{{ tool.category }}</div>
          <h1 data-tool-transition="title" class="mt-1 text-3xl font-bold tracking-tight text-slate-950 dark:text-white">{{ tool.name }}</h1>
          <p data-tool-transition="description" class="mt-2 text-sm text-slate-500 dark:text-slate-400">{{ tool.description }}</p>
        </div>
      </div>
      <div ref="body" class="mt-9">
        <div v-if="loading" class="h-80 animate-pulse rounded-2xl bg-slate-200 dark:bg-white/5" aria-label="正在加载工具"></div>
        <component :is="forms[tool.slug as keyof typeof forms]" v-else-if="tool.slug in forms" :key="tool.slug" />
        <div v-else class="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500 dark:border-white/10 dark:bg-[#141a2c]">该工具页面暂未配置。</div>
      </div>
    </template>
  </div>
</template>

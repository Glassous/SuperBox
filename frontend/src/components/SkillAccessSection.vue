<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { apiBaseUrl } from '../api/client'

interface SkillEndpoint {
  id: string
  label: string
  name: string
  path: string
  description: string
}

const endpoints: SkillEndpoint[] = [
  {
    id: 'markdown',
    label: 'MARKDOWN',
    name: '官方 Skill 文档',
    path: '/skill',
    description: '单份 Markdown，覆盖全部接口、使用约定、请求与响应示例及错误契约，适合直接交给 AI 助手阅读。',
  },
  {
    id: 'json',
    label: 'JSON',
    name: '结构化 JSON 清单',
    path: '/skill.json',
    description: '与 Markdown 同源的机器可读清单，包含工具列表、功能介绍、请求格式与示例，便于程序化解析与自动接入。',
  },
]

const copiedId = ref<string | null>(null)
let copyTimer: ReturnType<typeof setTimeout> | undefined

function fullUrl(path: string) {
  return `${apiBaseUrl}/api/v1${path}`
}

async function copy(endpoint: SkillEndpoint) {
  try {
    await navigator.clipboard.writeText(fullUrl(endpoint.path))
    copiedId.value = endpoint.id
  } catch {
    copiedId.value = null
  }
  if (copyTimer) clearTimeout(copyTimer)
  copyTimer = setTimeout(() => { copiedId.value = null }, 1800)
}

onBeforeUnmount(() => { if (copyTimer) clearTimeout(copyTimer) })
</script>

<template>
  <section class="mt-10" aria-labelledby="skill-access-title">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 id="skill-access-title" class="text-xl font-bold text-slate-950 dark:text-white">AI 平台 Skill</h2>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">把接口地址交给 AI 平台，即可按官方说明直接接入全部工具。</p>
      </div>
      <span class="font-mono text-xs text-slate-400">{{ String(endpoints.length).padStart(2, '0') }} ENDPOINTS</span>
    </div>

    <div class="mt-6 grid gap-5 md:grid-cols-2">
      <article v-for="endpoint in endpoints" :key="endpoint.id"
        class="flex flex-col rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-900/5 dark:border-white/10 dark:bg-[#141a2c] dark:hover:border-indigo-400/30">
        <div class="flex items-center justify-between gap-3">
          <span class="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-bold tracking-[0.14em] text-slate-500 dark:bg-white/5 dark:text-slate-400">{{ endpoint.label }}</span>
          <span class="font-mono text-[11px] font-bold text-indigo-600 dark:text-indigo-400">GET</span>
        </div>
        <h3 class="mt-5 text-lg font-bold text-slate-950 dark:text-white">{{ endpoint.name }}</h3>
        <code class="mt-3 block overflow-x-auto whitespace-nowrap rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-700 dark:border-white/10 dark:bg-[#0c1020] dark:text-slate-200">/api/v1{{ endpoint.path }}</code>
        <p class="mt-3 min-h-10 flex-1 text-sm leading-6 text-slate-500 dark:text-slate-400">{{ endpoint.description }}</p>
        <div class="mt-5 flex items-center gap-2">
          <button type="button" :aria-label="`复制 ${endpoint.name} 的接口地址`"
            class="cursor-pointer rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white outline-none transition hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 dark:bg-indigo-500 dark:hover:bg-indigo-400"
            @click="copy(endpoint)">{{ copiedId === endpoint.id ? '已复制' : '复制地址' }}</button>
          <a :href="fullUrl(endpoint.path)" target="_blank" rel="noreferrer"
            class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 outline-none transition hover:border-indigo-200 hover:text-indigo-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:border-indigo-400/30 dark:hover:text-indigo-300">查看内容</a>
        </div>
      </article>
    </div>
  </section>
</template>

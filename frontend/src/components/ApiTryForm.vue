<script setup lang="ts">
import { ref, watch } from 'vue'
import { ApiError, postTool } from '../api/client'
import type { ApiOperation } from '../data/apiDocs'

const props = defineProps<{ operation: ApiOperation }>()
const values = ref<Record<string, string>>({})
const responseText = ref('')
const status = ref<number | null>(null)
const error = ref('')
const loading = ref(false)
let requestId = 0

watch(() => props.operation, operation => {
  requestId++
  values.value = { ...operation.exampleBody }
  responseText.value = ''
  status.value = null
  error.value = ''
  loading.value = false
}, { immediate: true })

async function sendRequest() {
  const current = ++requestId
  loading.value = true
  responseText.value = ''
  error.value = ''
  status.value = null
  try {
    const response = await postTool<Record<string, unknown>>(props.operation.path, values.value)
    if (current !== requestId) return
    responseText.value = JSON.stringify(response, null, 2)
    status.value = 200
  } catch (cause) {
    if (current !== requestId) return
    if (cause instanceof ApiError) {
      error.value = cause.message
      status.value = cause.status ?? null
    } else {
      error.value = '请求失败，请稍后重试。'
    }
  } finally {
    if (current === requestId) loading.value = false
  }
}
</script>

<template>
  <section class="rounded-2xl border border-slate-200 bg-slate-50/70 p-5 dark:border-white/10 dark:bg-[#0c1020]/60">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h4 class="text-sm font-bold text-slate-900 dark:text-white">在线测试</h4>
        <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">请求会直接发送至当前配置的 API 服务。</p>
      </div>
      <button type="button" :disabled="loading" class="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60" @click="sendRequest">{{ loading ? '发送中…' : '发送请求' }}</button>
    </div>
    <div class="mt-5 grid gap-4 sm:grid-cols-2">
      <label v-for="field in operation.fields" :key="field.name" class="block" :class="field.multiline ? 'sm:col-span-2' : ''">
        <span class="text-xs font-semibold text-slate-600 dark:text-slate-300">{{ field.label }} <span class="font-mono font-normal text-slate-400">{{ field.name }}</span></span>
        <select v-if="field.options" v-model="values[field.name]" class="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-indigo-400 dark:border-white/10 dark:bg-[#141a2c] dark:text-white">
          <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
        <textarea v-else-if="field.multiline" v-model="values[field.name]" spellcheck="false" rows="3" class="mt-2 w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 font-mono text-sm text-slate-800 outline-none focus:border-indigo-400 dark:border-white/10 dark:bg-[#141a2c] dark:text-white"></textarea>
        <input v-else v-model="values[field.name]" type="text" spellcheck="false" class="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 font-mono text-sm text-slate-800 outline-none focus:border-indigo-400 dark:border-white/10 dark:bg-[#141a2c] dark:text-white" />
      </label>
    </div>
    <div class="mt-5 overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-white/10 dark:bg-[#141a2c]" aria-live="polite">
      <div class="flex items-center justify-between border-b border-slate-100 px-4 py-2.5 dark:border-white/10"><span class="text-xs font-semibold text-slate-500 dark:text-slate-400">响应结果</span><span v-if="status" class="font-mono text-xs font-semibold" :class="status < 400 ? 'text-indigo-600 dark:text-indigo-300' : 'text-rose-600 dark:text-rose-300'">HTTP {{ status }}</span></div>
      <pre v-if="responseText" class="max-h-48 overflow-auto whitespace-pre-wrap break-all p-4 font-mono text-xs leading-5 text-slate-800 dark:text-slate-200">{{ responseText }}</pre>
      <div v-else-if="error" class="p-4 text-sm text-rose-600 dark:text-rose-300" role="alert">{{ error }}</div>
      <div v-else class="p-4 text-xs text-slate-400">填写参数后发送请求，响应会显示在这里。</div>
    </div>
  </section>
</template>

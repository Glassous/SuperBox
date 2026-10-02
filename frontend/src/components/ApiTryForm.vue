<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { ApiError, executeOperation, type FileResult } from '../api/client'
import type { ApiOperation } from '../data/apiDocs'

const props = defineProps<{ operation: ApiOperation }>()
const values = ref<Record<string, string>>({})
const responseText = ref('')
const status = ref<number | null>(null)
const error = ref('')
const loading = ref(false)
const selectedFile = ref<File | null>(null)
const outputFile = ref<FileResult | null>(null)
let requestId = 0
let controller: AbortController | undefined
onBeforeUnmount(() => { requestId++; controller?.abort() })

watch(() => props.operation, operation => {
  requestId++
  controller?.abort()
  values.value = { ...operation.exampleBody }
  responseText.value = ''
  status.value = null
  error.value = ''
  loading.value = false
  selectedFile.value = null
  outputFile.value = null
}, { immediate: true })

async function sendRequest() {
  const current = ++requestId
  loading.value = true
  responseText.value = ''
  outputFile.value = null
  error.value = ''
  status.value = null
  try {
    controller?.abort()
    controller = new AbortController()
    const response = await executeOperation(props.operation, values.value, selectedFile.value, controller.signal)
    if (current !== requestId) return
    if (response && typeof response === 'object' && 'url' in response && 'expires_at' in response && 'filename' in response) {
      outputFile.value = response as FileResult
    }
    responseText.value = JSON.stringify(response, null, 2)
    status.value = 200
  } catch (cause) {
    if (current !== requestId) return
    if (cause instanceof ApiError) {
      error.value = cause.message
      status.value = cause.status ?? null
    } else {
      error.value = cause instanceof Error && cause.message ? cause.message : '请求失败，请稍后重试。'
      status.value = null
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
        <input v-else-if="field.type === 'file'" type="file" :accept="field.accept" class="mt-2 block w-full text-sm" @change="selectedFile = ($event.target as HTMLInputElement).files?.[0] ?? null" />
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
    <p v-if="outputFile" class="mt-3 text-xs text-slate-500">文件保留 2 小时，到期时间：{{ new Date(outputFile.expires_at).toLocaleString() }}。<a :href="outputFile.url" target="_blank" rel="noopener noreferrer" class="text-indigo-600 underline">下载 {{ outputFile.filename }}</a></p>
  </section>
</template>

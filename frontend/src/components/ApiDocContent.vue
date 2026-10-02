<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import ApiTryForm from './ApiTryForm.vue'
import { apiBaseUrl } from '../api/client'
import { apiExampleBody, makeAiPrompt, type ApiToolDoc } from '../data/apiDocs'

const props = defineProps<{ doc: ApiToolDoc }>()
const selectedOperationId = ref(props.doc.operations[0]?.id ?? '')
const operationContent = ref<HTMLElement | null>(null)
const copied = ref<'endpoint' | 'example' | 'prompt' | null>(null)
const currentOperation = computed(() => props.doc.operations.find(operation => operation.id === selectedOperationId.value) ?? props.doc.operations[0])
const aiPrompt = computed(() => makeAiPrompt(props.doc, apiBaseUrl))
const endpointUrl = computed(() => currentOperation.value ? `${apiBaseUrl}/api/v1${currentOperation.value.path}` : '')
const fetchExample = computed(() => {
  if (!currentOperation.value) return ''
  const operation = currentOperation.value
  if (operation.method === 'GET') {
    const query = new URLSearchParams(operation.exampleBody).toString()
    return `const response = await fetch('${endpointUrl.value}${query ? '?' + query : ''}');\nconst data = await response.json();`
  }
  if (operation.multipart) {
    const fields = operation.fields.map(field => field.type === 'file'
      ? `form.append('${field.name}', selectedFile); // 上传文件或改用下面的公开链接，二选一`
      : field.type === 'url' ? `// form.append('${field.name}', 'https://example.com/file');`
      : `form.append('${field.name}', ${JSON.stringify(operation.exampleBody[field.name] ?? '')});`).join('\n')
    return `const form = new FormData();\n${fields}\nconst response = await fetch('${endpointUrl.value}', { method: 'POST', body: form });\n${operation.binaryResponse ? 'const file = await response.blob();' : 'const data = await response.json();'}`
  }
  const example = Object.fromEntries(operation.fields.map(field => [field.name, field.type === 'integer' ? Number(operation.exampleBody[field.name]) : operation.exampleBody[field.name]]))
  const body = JSON.stringify(example, null, 2).replace(/\n/g, '\n  ')
  return `const response = await fetch('${endpointUrl.value}', {\n  method: 'POST',\n  headers: { 'Content-Type': 'application/json' },\n  body: JSON.stringify(${body}),\n});\nconst data = await response.json();`
})

let copyTimer: ReturnType<typeof setTimeout> | undefined
onBeforeUnmount(() => { if (copyTimer) clearTimeout(copyTimer) })
function selectOperation(id: string) {
  selectedOperationId.value = id
  operationContent.value?.scrollTo({ top: 0 })
}
async function copy(value: string, kind: 'endpoint' | 'example' | 'prompt') {
  try {
    await navigator.clipboard.writeText(value)
    copied.value = kind
  } catch {
    copied.value = null
  }
  if (copyTimer) clearTimeout(copyTimer)
  copyTimer = setTimeout(() => { copied.value = null }, 1800)
}
</script>

<template>
        <div class="flex min-h-0 flex-1 flex-col h-full overflow-hidden lg:flex-row">
            <nav class="flex shrink-0 gap-2 overflow-x-auto border-b border-slate-100 px-5 py-3 dark:border-white/10 lg:w-52 lg:flex-col lg:overflow-x-visible lg:overflow-y-auto lg:border-b-0 lg:border-r lg:px-4 lg:py-6" aria-label="选择接口">
              <button v-for="operation in doc.operations" :key="operation.id" type="button" class="shrink-0 rounded-xl px-4 py-2.5 text-left text-sm font-semibold transition" :class="selectedOperationId === operation.id ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-300' : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-white/5'" @click="selectOperation(operation.id)">{{ operation.name }}</button>
            </nav>

            <div v-if="currentOperation" ref="operationContent" class="min-h-0 min-w-0 flex-1 space-y-6 overflow-y-auto px-5 py-6 sm:px-7">
              <section>
                <h3 class="text-lg font-bold text-slate-950 dark:text-white">{{ currentOperation.name }}</h3>
                <p class="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">{{ currentOperation.summary }}</p>
                <div class="mt-4 flex min-w-0 items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-2.5 dark:border-white/10 dark:bg-[#0c1020]">
                  <span class="rounded-md bg-indigo-100 px-2 py-1 font-mono text-[11px] font-bold text-indigo-700 dark:bg-indigo-400/15 dark:text-indigo-300">{{ currentOperation.method ?? 'POST' }}</span>
                  <code class="min-w-0 flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs text-slate-700 dark:text-slate-200">{{ endpointUrl }}</code>
                  <button type="button" class="shrink-0 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200" @click="copy(endpointUrl, 'endpoint')">{{ copied === 'endpoint' ? '已复制' : '复制' }}</button>
                </div>
                <p class="mt-3 text-xs text-slate-500 dark:text-slate-400">{{ currentOperation.multipart ? '使用 multipart/form-data，图片文件与图片链接二选一，由浏览器设置 Content-Type。' : currentOperation.method === 'GET' ? '查询参数通过 URL 传递。' : '请求头：Content-Type: application/json。' }}当前接口无需认证。</p>
              </section>

              <section>
                <h4 class="text-sm font-bold text-slate-900 dark:text-white">请求字段</h4>
                <div class="mt-3 overflow-hidden rounded-xl border border-slate-200 dark:border-white/10">
                  <div v-for="field in currentOperation.fields" :key="field.name" class="grid gap-1 border-b border-slate-100 px-4 py-3 last:border-b-0 dark:border-white/10 sm:grid-cols-[160px_1fr]">
                    <div><code class="font-mono text-xs font-semibold text-indigo-700 dark:text-indigo-300">{{ field.name }}</code><span class="ml-2 text-[11px] text-slate-400">{{ field.type }}</span></div>
                    <p class="text-xs leading-5 text-slate-500 dark:text-slate-400">{{ field.description }}</p>
                  </div>
                </div>
                <p v-if="currentOperation.note" class="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">{{ currentOperation.note }}</p>
              </section>

              <div class="grid gap-4 xl:grid-cols-2">
                <section class="min-w-0 overflow-hidden rounded-xl border border-slate-200 dark:border-white/10">
                  <div class="border-b border-slate-100 px-4 py-2.5 text-xs font-semibold text-slate-500 dark:border-white/10 dark:text-slate-400">请求示例</div>
                  <pre class="max-h-40 overflow-auto p-4 font-mono text-xs leading-5 text-slate-700 dark:text-slate-200">{{ JSON.stringify(apiExampleBody(currentOperation), null, 2) }}</pre>
                </section>
                <section class="min-w-0 overflow-hidden rounded-xl border border-slate-200 dark:border-white/10">
                  <div class="border-b border-slate-100 px-4 py-2.5 text-xs font-semibold text-slate-500 dark:border-white/10 dark:text-slate-400">成功响应示例</div>
                  <pre class="max-h-40 overflow-auto p-4 font-mono text-xs leading-5 text-slate-700 dark:text-slate-200">{{ JSON.stringify(currentOperation.exampleResponse, null, 2) }}</pre>
                </section>
              </div>

              <section class="min-w-0 overflow-hidden rounded-xl border border-slate-200 dark:border-white/10">
                <div class="flex items-center justify-between border-b border-slate-100 px-4 py-2.5 dark:border-white/10"><h4 class="text-xs font-semibold text-slate-500 dark:text-slate-400">调用示例 · JavaScript</h4><button type="button" class="text-xs font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-300" @click="copy(fetchExample, 'example')">{{ copied === 'example' ? '已复制' : '复制代码' }}</button></div>
                <pre class="overflow-x-auto p-4 font-mono text-xs leading-5 text-slate-700 dark:text-slate-200">{{ fetchExample }}</pre>
              </section>

              <ApiTryForm :key="currentOperation.id" :operation="currentOperation" />

              <section class="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-5 dark:border-indigo-400/15 dark:bg-indigo-400/5">
                <div class="flex flex-wrap items-center justify-between gap-3"><div><h4 class="text-sm font-bold text-slate-900 dark:text-white">交给你的 AI 助手接入</h4><p class="mt-1 text-xs text-slate-500 dark:text-slate-400">复制提示词，再告诉它你的项目技术栈和目标页面。</p></div><button type="button" class="rounded-lg border border-indigo-200 bg-white px-3 py-2 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-100 dark:border-indigo-400/20 dark:bg-white/5 dark:text-indigo-300" @click="copy(aiPrompt, 'prompt')">{{ copied === 'prompt' ? '已复制' : '复制提示词' }}</button></div>
                <pre class="mt-4 max-h-44 overflow-y-auto whitespace-pre-wrap break-words font-mono text-xs leading-6 text-slate-600 dark:text-slate-300">{{ aiPrompt }}</pre>
              </section>

              <p class="pb-1 text-xs leading-5 text-slate-400">错误响应：400 / INVALID_INPUT；422 / VALIDATION_ERROR；上传超限 413 / FILE_TOO_LARGE；文档容量超限 413 / DOCUMENT_LIMIT_EXCEEDED；繁忙 429 / TOOL_BUSY；汇率不可用 503 / EXCHANGE_RATE_UNAVAILABLE；文档处理不可用 503 / DOCUMENT_UNAVAILABLE；文档超时 504 / DOCUMENT_TIMEOUT；ExifTool 不可用 503 / EXIF_UNAVAILABLE。</p>
            </div>
        </div>
</template>

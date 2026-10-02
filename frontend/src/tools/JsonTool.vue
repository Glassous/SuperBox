<script setup lang="ts">
import { ref } from 'vue'
import ResultBox from '../components/ResultBox.vue'
import { useOperation } from '../composables/useOperation'
import type { JsonValidationResult, TextResult } from '../types'

const text = ref('')
const { result, error, loading, run, reset } = useOperation()

async function execute(action: 'format' | 'minify' | 'validate') {
  if (action === 'validate') {
    await run<JsonValidationResult>('/json/validate', { text: text.value }, data => {
      if (!data.valid) throw new Error(data.message)
      return data.message
    })
  } else {
    await run<TextResult>(`/json/${action}`, { text: text.value }, data => data.result)
  }
}

function clear() {
  text.value = ''
  reset()
}
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-2">
    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#141a2c]">
      <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4 dark:border-white/10"><h2 class="text-sm font-bold">输入 JSON</h2><button class="text-xs font-semibold text-slate-400 hover:text-rose-500" @click="clear">清空</button></div>
      <div class="p-6">
        <label for="json-input" class="sr-only">JSON 内容</label>
        <textarea id="json-input" v-model="text" spellcheck="false" placeholder='例如：{"name":"Superbox","ready":true}' class="min-h-72 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-sm leading-6 text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100 dark:border-white/10 dark:bg-[#0c1020] dark:text-slate-200 dark:focus:ring-indigo-400/10"></textarea>
        <p class="mt-3 text-xs text-slate-400">支持标准 JSON，可验证、格式化与压缩。</p>
        <div class="mt-5 flex flex-wrap gap-2">
          <button :disabled="loading" class="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50" @click="execute('format')">格式化</button>
          <button :disabled="loading" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-indigo-300 hover:text-indigo-600 disabled:opacity-50 dark:border-white/15 dark:text-slate-200" @click="execute('minify')">压缩</button>
          <button :disabled="loading" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-indigo-300 hover:text-indigo-600 disabled:opacity-50 dark:border-white/15 dark:text-slate-200" @click="execute('validate')">校验</button>
        </div>
      </div>
    </section>
    <ResultBox :value="result" :error="error" :loading="loading" placeholder="选择一个操作后，结果将显示在这里" />
  </div>
</template>

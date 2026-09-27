<script setup lang="ts">
import { ref } from 'vue'
import ResultBox from '../components/ResultBox.vue'
import { useOperation } from '../composables/useOperation'
import type { TextResult } from '../types'

const action = ref<'encode' | 'decode'>('encode')
const text = ref('')
const { result, error, loading, run, reset } = useOperation()

function select(next: 'encode' | 'decode') {
  action.value = next
  reset()
}

function execute() {
  run<TextResult>(`/url/${action.value}`, { text: text.value }, data => data.result)
}
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-2">
    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#141a2c]">
      <div class="border-b border-slate-100 px-6 py-4 text-sm font-bold dark:border-white/10">操作设置</div>
      <div class="p-6">
        <div class="inline-flex rounded-xl bg-slate-100 p-1 dark:bg-white/5" role="group" aria-label="编解码模式">
          <button v-for="mode in (['encode', 'decode'] as const)" :key="mode" class="rounded-lg px-5 py-2 text-sm font-semibold transition" :class="action === mode ? 'bg-white text-indigo-600 shadow-sm dark:bg-[#252d47] dark:text-indigo-300' : 'text-slate-500 dark:text-slate-400'" @click="select(mode)">{{ mode === 'encode' ? '编码' : '解码' }}</button>
        </div>
        <label for="url-input" class="mt-6 block text-sm font-semibold">{{ action === 'encode' ? '输入参数值' : '输入已编码内容' }}</label>
        <textarea id="url-input" v-model="text" spellcheck="false" :placeholder="action === 'encode' ? '例如：你好 & Vue' : '例如：%E4%BD%A0%E5%A5%BD'" class="mt-3 min-h-60 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-sm leading-6 text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100 dark:border-white/10 dark:bg-[#0c1020] dark:text-slate-200 dark:focus:ring-indigo-400/10"></textarea>
        <p class="mt-3 text-xs text-slate-400">适用于 URL 参数值，不会把输入当作完整网址处理。</p>
        <button :disabled="loading" class="mt-5 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50" @click="execute">{{ action === 'encode' ? '开始编码' : '开始解码' }} →</button>
      </div>
    </section>
    <ResultBox :value="result" :error="error" :loading="loading" />
  </div>
</template>

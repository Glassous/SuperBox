<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  label?: string
  value: string
  error: string
  loading: boolean
  placeholder?: string
}>()

const copied = ref(false)

async function copy(value: string) {
  try {
    await navigator.clipboard.writeText(value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1800)
  } catch {
    copied.value = false
  }
}
</script>

<template>
  <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#141a2c]">
    <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4 dark:border-white/10">
      <div class="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-white"><span class="h-2 w-2 rounded-full bg-emerald-400"></span>{{ label || '输出结果' }}</div>
      <button v-if="value && !error" class="rounded-lg px-3 py-1.5 text-xs font-semibold text-indigo-600 transition hover:bg-indigo-50 dark:text-indigo-300 dark:hover:bg-indigo-400/10" @click="copy(value)">{{ copied ? '已复制' : '复制结果' }}</button>
    </div>
    <div class="min-h-52 p-6" aria-live="polite">
      <div v-if="loading" class="flex items-center gap-3 text-sm text-slate-500"><span class="h-4 w-4 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600"></span>正在由后端处理...</div>
      <div v-else-if="error" class="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300" role="alert">{{ error }}</div>
      <pre v-else-if="value" class="whitespace-pre-wrap break-all font-mono text-sm leading-6 text-slate-800 dark:text-slate-200">{{ value }}</pre>
      <div v-else class="flex min-h-36 flex-col items-center justify-center text-center text-slate-400"><span class="text-3xl">◇</span><span class="mt-3 text-sm">{{ placeholder || '处理结果将在这里显示' }}</span></div>
    </div>
  </div>
</template>

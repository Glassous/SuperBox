<script setup lang="ts">
import { ref } from 'vue'
import ResultBox from '../components/ResultBox.vue'
import { useOperation } from '../composables/useOperation'
import type { DateTimeResult, UnixTimestampResult } from '../types'

const action = ref<'to-datetime' | 'to-unix'>('to-datetime')
const value = ref('')
const unit = ref<'seconds' | 'milliseconds'>('seconds')
const { result, error, loading, run, reset } = useOperation()

function select(next: 'to-datetime' | 'to-unix') {
  action.value = next
  value.value = ''
  reset()
}

function execute() {
  if (action.value === 'to-datetime') {
    run<DateTimeResult>('/timestamp/to-datetime', { value: value.value, unit: unit.value }, data => data.iso_utc)
  } else {
    run<UnixTimestampResult>('/timestamp/to-unix', { iso_datetime: value.value }, data => `UTC 时间：${data.iso_utc}\n秒：${data.seconds}\n毫秒：${data.milliseconds}`)
  }
}
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-2">
    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#141a2c]">
      <div class="border-b border-slate-100 px-6 py-4 text-sm font-bold dark:border-white/10">转换方向</div>
      <div class="p-6">
        <div class="inline-flex max-w-full rounded-xl bg-slate-100 p-1 dark:bg-white/5" role="group" aria-label="转换方向">
          <button class="rounded-lg px-4 py-2 text-sm font-semibold transition" :class="action === 'to-datetime' ? 'bg-white text-indigo-600 shadow-sm dark:bg-[#252d47] dark:text-indigo-300' : 'text-slate-500 dark:text-slate-400'" @click="select('to-datetime')">时间戳 → 日期</button>
          <button class="rounded-lg px-4 py-2 text-sm font-semibold transition" :class="action === 'to-unix' ? 'bg-white text-indigo-600 shadow-sm dark:bg-[#252d47] dark:text-indigo-300' : 'text-slate-500 dark:text-slate-400'" @click="select('to-unix')">日期 → 时间戳</button>
        </div>
        <label for="timestamp-input" class="mt-6 block text-sm font-semibold">{{ action === 'to-datetime' ? 'Unix 时间戳' : 'ISO 8601 日期时间' }}</label>
        <input id="timestamp-input" v-model="value" type="text" spellcheck="false" :placeholder="action === 'to-datetime' ? '例如：1758931200' : '例如：2026-09-27T12:30:00+08:00'" class="mt-3 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100 dark:border-white/10 dark:bg-[#0c1020] dark:text-slate-200 dark:focus:ring-indigo-400/10" />
        <div v-if="action === 'to-datetime'" class="mt-5">
          <label for="timestamp-unit" class="block text-sm font-semibold">时间戳单位</label>
          <select id="timestamp-unit" v-model="unit" class="mt-3 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none focus:border-indigo-400 dark:border-white/10 dark:bg-[#0c1020] dark:text-slate-200"><option value="seconds">秒</option><option value="milliseconds">毫秒</option></select>
        </div>
        <p class="mt-5 text-xs leading-5 text-slate-400">{{ action === 'to-datetime' ? '请输入整数时间戳，结果以 UTC 时间显示。' : '请输入带 Z 或 ±HH:MM 时区偏移的日期时间。' }}</p>
        <button :disabled="loading" class="mt-5 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50" @click="execute">开始转换 →</button>
      </div>
    </section>
    <ResultBox :value="result" :error="error" :loading="loading" />
  </div>
</template>

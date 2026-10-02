<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import CurrencySelect from '../components/CurrencySelect.vue'
import { convertCurrencies, getToolResult, postTool, type CurrencyResult, type CurrencyBatchItem } from '../api/client'
import { currencyName, sortCurrencies } from '../data/currencyNames'

const amount = ref('1'), from = ref('CNY'), to = ref('USD'), precision = ref(2)
const mode = ref<'single' | 'multiple'>('single'), targets = ref<string[]>([]), query = ref('')
const currencies = ref<{ code: string; name: string }[]>([])
const directoryError = ref(''), fetching = ref(false), error = ref(''), loading = ref(false)
const results = ref<CurrencyBatchItem[]>([]), copied = ref(''), copyError = ref('')
const directoryController = new AbortController()
let controller: AbortController | undefined, requestId = 0, copyTimer: ReturnType<typeof setTimeout> | undefined
const filtered = computed(() => currencies.value.filter(item =>
  (item.code + ' ' + item.name + ' ' + currencyName(item.code, item.name)).toLowerCase().includes(query.value.trim().toLowerCase())))
function name(code: string) { return currencyName(code, currencies.value.find(item => item.code === code)?.name ?? code) }
function reset() {
  requestId++; controller?.abort(); controller = undefined
  results.value = []; error.value = ''; loading.value = false; copied.value = ''; copyError.value = ''
}
watch([amount, from, to, precision, mode, targets], reset, { deep: true, flush: 'sync' })
async function load() {
  if (fetching.value) return
  directoryError.value = ''; fetching.value = true
  try {
    currencies.value = sortCurrencies((await getToolResult<{ currencies: typeof currencies.value }>('/currency/currencies', directoryController.signal)).currencies)
    const supported = new Set(currencies.value.map(item => item.code))
    if (!supported.has(from.value)) from.value = currencies.value[0]?.code ?? ''
    if (!supported.has(to.value)) to.value = currencies.value[0]?.code ?? ''
    targets.value = ['USD', 'EUR', 'JPY'].filter(code => supported.has(code))
  } catch (cause) { if (!directoryController.signal.aborted) directoryError.value = cause instanceof Error ? cause.message : '货币列表加载失败' }
  finally { fetching.value = false }
}
function toggle(code: string) {
  targets.value = targets.value.includes(code) ? targets.value.filter(value => value !== code)
    : targets.value.length < 50 ? [...targets.value, code] : targets.value
}
async function calculate() {
  reset()
  const current = requestId, active = new AbortController()
  controller = active; loading.value = true
  const a = amount.value, f = from.value, p = Number(precision.value), selected = [...targets.value], t = to.value
  try {
    const items: CurrencyBatchItem[] = mode.value === 'multiple'
      ? (await convertCurrencies(a, f, selected, p, active.signal)).results
      : [{ ...(await postTool<CurrencyResult>('/currency/convert', { amount: a, from_currency: f, to_currency: t, precision: p }, active.signal)), status: 'success' }]
    if (current === requestId) results.value = items
  } catch (cause) { if (current === requestId && !active.signal.aborted) error.value = cause instanceof Error ? cause.message : '计算失败，请稍后重试' }
  finally { if (current === requestId) loading.value = false }
}
function display(item: CurrencyBatchItem) {
  return item.status === 'error' ? item.to_currency + '：' + item.message
    : item.amount + ' ' + item.from_currency + ' = ' + item.result + ' ' + item.to_currency
      + '\n参考汇率：' + item.rate + '\n参考日期：' + (item.rate_date ?? '同币种')
      + '\n来源：' + (item.source === 'identity' ? '同币种' : item.source)
      + (item.stale ? '\n暂用上次获取的数据' : '')
}
async function copy(items: CurrencyBatchItem[], key: string) {
  try {
    await navigator.clipboard.writeText(items.map(display).join('\n\n'))
    copied.value = key; copyError.value = ''; clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copied.value = '' }, 1800)
  } catch { copyError.value = '复制失败，请重试' }
}
function updateTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
}
onMounted(load)
onBeforeUnmount(() => { reset(); directoryController.abort(); clearTimeout(copyTimer) })
</script>
<template>
  <div class="grid items-start gap-6 xl:grid-cols-2">
    <section class="tool-panel space-y-5">
      <div class="flex gap-2" role="group" aria-label="转换模式">
        <button v-for="item in ([['single', '单币种'], ['multiple', '多币种']] as const)" :key="item[0]" class="rounded-xl px-4 py-2 text-sm font-semibold" :class="mode === item[0] ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300'" :aria-pressed="mode === item[0]" @click="mode = item[0]">{{ item[1] }}</button>
      </div>
      <label class="block text-sm text-slate-500">金额<input v-model="amount" class="tool-input !text-3xl !font-semibold" inputmode="decimal" maxlength="24" /></label>
      <p v-if="fetching" role="status" class="text-sm text-slate-500">正在处理…</p>
      <p v-if="directoryError" role="alert">{{ directoryError }} <button class="text-indigo-600" @click="load">重试</button></p>
      <CurrencySelect v-model="from" label="原币种" :items="currencies" />
      <template v-if="mode === 'single'">
        <button class="text-sm font-semibold text-indigo-600 dark:text-indigo-300" :disabled="!currencies.length" @click="[from, to] = [to, from]">交换币种 ⇄</button>
        <CurrencySelect v-model="to" label="目标币种" :items="currencies" />
      </template>
      <section v-else class="space-y-3" aria-label="目标币种选择">
        <div class="flex items-center justify-between text-sm"><strong>已选 {{ targets.length }} / 50</strong><button class="text-indigo-600 dark:text-indigo-300" :disabled="!targets.length" @click="targets = []">清空</button></div>
        <div v-if="targets.length" class="flex flex-wrap gap-2"><button v-for="code in targets" :key="code" class="rounded-lg bg-indigo-50 px-2 py-1 text-xs text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-200" :aria-label="'移除 ' + code" @click="toggle(code)">{{ code }} ×</button></div>
        <label class="block text-xs text-slate-500">搜索目标币种<input v-model="query" class="tool-input" placeholder="输入代码或名称" /></label>
        <div class="max-h-64 overflow-auto rounded-xl border border-slate-200 p-2 dark:border-white/10">
          <label v-for="item in filtered" :key="item.code" class="flex cursor-pointer items-center gap-3 rounded-lg p-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5" :class="!targets.includes(item.code) && targets.length >= 50 ? 'opacity-50' : ''">
            <input type="checkbox" :checked="targets.includes(item.code)" :disabled="!targets.includes(item.code) && targets.length >= 50" @change="toggle(item.code)" />
            <span class="w-10 font-mono font-semibold">{{ item.code }}</span><span>{{ currencyName(item.code, item.name) }}</span>
          </label>
          <p v-if="!filtered.length" class="p-2 text-sm text-slate-500">没有匹配的货币</p>
        </div>
        <p v-if="targets.length === 50" class="text-xs text-slate-500">最多选择 50 种货币，可移除后重新选择。</p>
      </section>
      <details class="text-sm"><summary class="cursor-pointer text-slate-500">小数位数：{{ precision }}</summary><label class="mt-2 block">小数位数<select v-model="precision" class="tool-input"><option v-for="n in 9" :key="n" :value="n - 1">{{ n - 1 }}</option></select></label></details>
      <button class="tool-button w-full" :disabled="loading || !currencies.length || (mode === 'multiple' && !targets.length)" @click="calculate">{{ loading ? '正在处理…' : '计算' }}</button>
      <p class="text-xs text-slate-500">每日参考汇率，实际兑换金额可能因手续费等因素有所不同。</p>
    </section>
    <section class="tool-panel space-y-4" aria-live="polite" aria-label="兑换结果">
      <div class="flex items-center justify-between"><h2 class="font-bold">兑换结果</h2><button v-if="results.length" class="text-sm text-indigo-600 dark:text-indigo-300" @click="copy(results, 'all')">{{ copied === 'all' ? '已复制' : '复制全部' }}</button></div>
      <p v-if="loading" role="status" class="py-8 text-sm text-slate-500">正在处理…</p>
      <p v-else-if="error" role="alert" class="text-sm text-rose-600 dark:text-rose-300">{{ error }}</p>
      <p v-else-if="!results.length" class="py-12 text-center text-sm text-slate-400">输入金额，选择货币后点击计算</p>
      <article v-for="item in results" :key="item.to_currency" class="space-y-2 rounded-xl border border-slate-200 p-4 dark:border-white/10">
        <div class="flex items-center justify-between gap-2"><h3 class="text-sm font-semibold">{{ item.to_currency }} · {{ name(item.to_currency) }}</h3><button class="text-xs text-indigo-600 dark:text-indigo-300" :aria-label="'复制 ' + item.to_currency" @click="copy([item], item.to_currency)">{{ copied === item.to_currency ? '已复制' : '复制' }}</button></div>
        <template v-if="item.status === 'success'">
          <p class="break-all font-mono text-3xl font-semibold">{{ item.result }}</p>
          <p class="text-xs text-slate-500">{{ item.amount }} {{ item.from_currency }} · 参考汇率 {{ item.rate }}</p>
          <p class="text-xs text-slate-500">参考日期：{{ item.rate_date ?? '同币种' }} · 来源：{{ item.source === 'identity' ? '同币种' : item.source }}</p>
          <p v-if="item.fetched_at" class="text-xs text-slate-500">更新时间：{{ updateTime(item.fetched_at) }}</p>
          <p v-if="item.stale" class="text-xs text-amber-700 dark:text-amber-300">暂用上次获取的数据</p>
        </template>
        <p v-else class="text-sm text-rose-600 dark:text-rose-300">{{ item.message }}</p>
      </article>
      <p v-if="copyError" role="alert" class="text-sm text-rose-600">{{ copyError }}</p>
    </section>
  </div>
</template>

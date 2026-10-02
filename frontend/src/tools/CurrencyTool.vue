<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import ResultBox from '../components/ResultBox.vue'
import { getToolResult, postTool, type CurrencyResult } from '../api/client'
import { useToolTask } from '../composables/useToolTask'
const amount = ref('1'), from = ref('CNY'), to = ref('USD'), precision = ref(2)
const currencies = ref<{ code: string; name: string }[]>([]), directoryError = ref('')
const { result, error, loading, run } = useToolTask()
const directoryController = new AbortController()
async function load() {
  directoryError.value = ''
  try { currencies.value = (await getToolResult<{ currencies: typeof currencies.value }>('/currency/currencies', directoryController.signal)).currencies }
  catch (cause) { if (!directoryController.signal.aborted) directoryError.value = cause instanceof Error ? cause.message : '货币目录加载失败' }
}
function convert() {
  const body = { amount: amount.value, from_currency: from.value, to_currency: to.value, precision: Number(precision.value) }
  return run(async signal => {
    const data = await postTool<CurrencyResult>('/currency/convert', body, signal)
    return `${data.amount} ${data.from_currency} = ${data.result} ${data.to_currency}\n汇率：${data.rate}\n汇率日期：${data.rate_date ?? '同币种，无需汇率'}\n来源：${data.source}\n${data.stale ? '使用缓存：供应商暂不可用，返回获取时间不超过 24 小时的缓存' : data.cached ? '使用缓存汇率' : '最新获取'}${data.fetched_at ? '\n获取时间：' + data.fetched_at : ''}`
  })
}
onMounted(load)
onBeforeUnmount(() => directoryController.abort())
</script>
<template>
  <div class="grid gap-6 xl:grid-cols-2">
    <section class="tool-panel space-y-4">
      <p class="text-sm text-slate-500">每日参考汇率，实际日期以返回结果为准。</p>
      <p v-if="directoryError" role="alert">{{ directoryError }} <button class="text-indigo-600" @click="load">重试</button></p>
      <label class="block">金额<input v-model="amount" class="tool-input" inputmode="decimal" maxlength="24" /></label>
      <label class="block">原币种<select v-model="from" class="tool-input"><option v-for="item in currencies" :key="item.code" :value="item.code">{{ item.code }} · {{ item.name }}</option></select></label>
      <button class="text-indigo-600" @click="[from, to] = [to, from]">交换币种 ⇄</button>
      <label class="block">目标币种<select v-model="to" class="tool-input"><option v-for="item in currencies" :key="item.code" :value="item.code">{{ item.code }} · {{ item.name }}</option></select></label>
      <label class="block">小数位数<select v-model="precision" class="tool-input"><option v-for="n in 9" :key="n" :value="n - 1">{{ n - 1 }}</option></select></label>
      <button class="tool-button" :disabled="loading || !currencies.length" @click="convert">转换金额</button>
    </section>
    <ResultBox :value="result" :error="error" :loading="loading" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import ResultBox from '../components/ResultBox.vue'
import { getToolResult } from '../api/client'
import { useToolTask } from '../composables/useToolTask'
const { result, error, loading, run } = useToolTask()
function refresh() {
  return run(async signal => {
    const data = await getToolResult<{ iso_datetime: string; weekday: number; unix_seconds: string; unix_milliseconds: string }>('/time/now', signal)
    return `获取时间：${data.iso_datetime}\n时区：东八区（UTC+08:00）\n星期：${['一', '二', '三', '四', '五', '六', '日'][data.weekday - 1]}\nUnix 秒：${data.unix_seconds}\nUnix 毫秒：${data.unix_milliseconds}`
  })
}
onMounted(refresh)
</script>
<template>
  <div class="space-y-6">
    <p class="text-sm text-slate-500">显示东八区日期和时间，点击刷新可获取最新时间。</p>
    <button class="tool-button" :disabled="loading" @click="refresh">刷新时间</button>
    <ResultBox :value="result" :error="error" :loading="loading" />
  </div>
</template>

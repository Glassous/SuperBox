<script setup lang="ts">
import { ref, watch } from 'vue'
import ResultBox from '../components/ResultBox.vue'
import { convertDocument, saveBlob, type DocumentResult } from '../api/client'
import { useToolTask } from '../composables/useToolTask'
const mode = ref('upload'), file = ref<File | null>(null), link = ref(''), format = ref('markdown')
const output = ref<DocumentResult | null>(null)
const { result, error, loading, run, reset } = useToolTask()
watch([mode, file, link, format], () => { reset(); output.value = null })
function convert() {
  output.value = null
  const source = mode.value === 'upload' ? file.value : link.value.trim()
  const selectedFormat = format.value
  return run(async signal => {
    if (!source) throw new Error('请选择文件或填写公开链接。')
    if (source instanceof File && source.size > 5 * 1024 * 1024) throw new Error('文件不能超过 5 MiB。')
    const data = await convertDocument(source, selectedFormat, signal)
    if (!signal.aborted) output.value = data
    return data.result
  })
}
function save() {
  if (output.value) saveBlob(new Blob([output.value.result], { type: `${output.value.format === 'markdown' ? 'text/markdown' : 'text/plain'};charset=utf-8` }), output.value.filename)
}
</script>
<template>
  <div class="grid gap-6 xl:grid-cols-2">
    <section class="tool-panel space-y-4">
      <p class="text-sm text-slate-500">支持 PDF、DOCX、XLSX，最大 5 MiB。提取文字和表格；不支持扫描件 OCR、旧版 DOC/XLS、宏、加密或复杂排版。</p>
      <label class="block">文件来源<select v-model="mode" class="tool-input"><option value="upload">上传文件</option><option value="url">公开文件链接</option></select></label>
      <label v-if="mode === 'upload'" class="block">选择文档<input class="tool-input" type="file" accept=".pdf,.docx,.xlsx" @change="file = ($event.target as HTMLInputElement).files?.[0] ?? null" /></label>
      <label v-else class="block">公开 HTTP/HTTPS 链接<input v-model="link" class="tool-input" type="url" maxlength="2048" /></label>
      <label class="block">输出格式<select v-model="format" class="tool-input"><option value="markdown">Markdown</option><option value="txt">TXT</option></select></label>
      <p class="text-xs text-slate-500">最多 100 页 PDF、20 个工作表、50,000 单元格、500,000 输出字符。Office 解压上限 50 MiB。超限会报错，不会截断；繁忙时请稍后重试。</p>
      <button class="tool-button" :disabled="loading" @click="convert">开始转换</button>
      <button v-if="output" class="tool-button ml-3" @click="save">保存 {{ output.filename }}</button>
      <p v-if="output" class="text-sm text-slate-500">{{ output.stats.characters }} 字符 · {{ output.stats.pages }} 页 · {{ output.stats.worksheets }} 工作表</p>
      <p v-for="warning in output?.warnings" :key="warning" class="text-sm text-amber-700 dark:text-amber-300">{{ warning }}</p>
    </section>
    <ResultBox :value="result" :error="error" :loading="loading" />
  </div>
</template>

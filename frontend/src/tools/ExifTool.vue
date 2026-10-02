<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { downloadFile, editExif, inspectExif, searchExifTags, type FileResult } from '../api/client'
import type { ExifCatalogTag, ExifChange, ExifTag } from '../types'

const MAX_BYTES = 20 * 1024 * 1024
const MAX_URL_LENGTH = 2048
const fileInput = ref<HTMLInputElement | null>(null)
const file = ref<File | null>(null)
const imageUrl = ref('')
const sourceUrl = ref('')
const sourceName = ref('')
const previewUrl = ref('')
const format = ref('')
const tags = ref<ExifTag[]>([])
const drafts = ref<Record<string, string>>({})
const deleted = ref<string[]>([])
const catalog = ref<ExifCatalogTag[]>([])
const search = ref('')
const tagSearch = ref('')
const error = ref('')
const message = ref('')
const loading = ref(false)
const saving = ref(false)
const output = ref<FileResult | null>(null)
const searching = ref(false)
let inspectController: AbortController | undefined
let searchController: AbortController | undefined
let searchTimer: ReturnType<typeof setTimeout> | undefined
let generation = 0

const preview = computed(() => (file.value ? previewUrl.value : sourceUrl.value))

const displayed = computed(() => {
  const existing = tags.value.filter(tag => `${tag.group} ${tag.name}`.toLowerCase().includes(search.value.toLowerCase()))
  const added = Object.keys(drafts.value).filter(key => !tags.value.some(tag => tag.key === key))
    .filter(key => key.toLowerCase().includes(search.value.toLowerCase()))
    .map(key => ({ key, group: key.split(':')[0]!, name: key.split(':')[1]!, value: '', writable: true, reason: '' }))
  return [...existing, ...added]
})

const changes = computed<ExifChange[]>(() => {
  const result: ExifChange[] = deleted.value.map(key => ({ key, action: 'delete' }))
  for (const [key, value] of Object.entries(drafts.value)) {
    if (deleted.value.includes(key)) continue
    const original = tags.value.find(tag => tag.key === key)?.value
    if (value !== original) result.push({ key, action: 'set', value })
  }
  return result
})

function inputValue(tag: ExifTag): string {
  return drafts.value[tag.key] ?? tag.value
}

function setValue(key: string, value: string) {
  drafts.value = { ...drafts.value, [key]: value }
  deleted.value = deleted.value.filter(item => item !== key)
  message.value = ''
}

function toggleDelete(key: string) {
  if (!tags.value.some(tag => tag.key === key)) {
    const next = { ...drafts.value }
    delete next[key]
    drafts.value = next
    return
  }
  deleted.value = deleted.value.includes(key)
    ? deleted.value.filter(item => item !== key)
    : [...deleted.value, key]
  message.value = ''
}

function discard() {
  drafts.value = {}
  deleted.value = []
  message.value = ''
}

function nameFromUrl(target: URL): string {
  try {
    return decodeURIComponent(target.pathname.split('/').filter(Boolean).pop() ?? '') || target.hostname
  } catch {
    return target.hostname
  }
}

async function loadSource(source: File | string, name: string) {
  inspectController?.abort()
  const controller = new AbortController()
  inspectController = controller
  const current = ++generation
  output.value = null
  discard()
  tags.value = []
  format.value = ''
  catalog.value = []
  tagSearch.value = ''
  search.value = ''
  error.value = ''
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  file.value = null
  sourceUrl.value = ''
  sourceName.value = name
  if (typeof source === 'string') {
    sourceUrl.value = source
  } else {
    file.value = source
    previewUrl.value = URL.createObjectURL(source)
    imageUrl.value = ''
  }
  loading.value = true
  try {
    const result = await inspectExif(source, controller.signal)
    if (current !== generation) return
    format.value = result.format
    tags.value = result.tags
  } catch (cause) {
    if (current !== generation || controller.signal.aborted) return
    error.value = cause instanceof Error ? cause.message : '读取图片失败。'
    if (typeof source === 'string') {
      sourceUrl.value = ''
      sourceName.value = ''
    }
  } finally {
    if (current === generation) loading.value = false
  }
}

function chooseFile(event: Event) {
  const selected = (event.target as HTMLInputElement).files?.[0]
  if (fileInput.value) fileInput.value.value = ''
  if (!selected) return
  if (selected.size > MAX_BYTES) { error.value = '图片不能超过 20 MB。'; return }
  if (!/\.(jpe?g|png|webp)$/i.test(selected.name)) { error.value = '请选择 JPEG、PNG 或 WebP 图片。'; return }
  void loadSource(selected, selected.name)
}

function loadUrl() {
  const value = imageUrl.value.trim()
  if (!value || value.length > MAX_URL_LENGTH) { error.value = '请输入不超过 2048 字符的图片链接。'; return }
  let target: URL
  try {
    target = new URL(value)
  } catch {
    error.value = '请输入有效的图片链接。'
    return
  }
  if (target.protocol !== 'http:' && target.protocol !== 'https:') {
    error.value = '图片链接必须以 http:// 或 https:// 开头。'
    return
  }
  void loadSource(value, nameFromUrl(target))
}

async function findTags() {
  if (!format.value) return
  searchController?.abort()
  const controller = new AbortController()
  searchController = controller
  searching.value = true
  try {
    catalog.value = (await searchExifTags(tagSearch.value, controller.signal)).tags
  } catch (cause) {
    if (!controller.signal.aborted) error.value = cause instanceof Error ? cause.message : '标签搜索失败。'
  } finally {
    if (!controller.signal.aborted) searching.value = false
  }
}

function queueSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { void findTags() }, 250)
}

function addTag(tag: ExifCatalogTag) {
  if (!tag.writable) return
  drafts.value = { ...drafts.value, [tag.key]: '' }
  search.value = ''
  catalog.value = catalog.value.filter(item => item.key !== tag.key)
  message.value = ''
}

async function download() {
  const source = file.value ?? sourceUrl.value
  if (!source || !changes.value.length || saving.value) return
  const pending = changes.value
  if (pending.some(change => change.action === 'set' && !change.value?.trim())) {
    error.value = '新增或修改的标签值不能为空；如需移除，请使用“删除”。'
    return
  }
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    const result = await editExif(source, pending)
    const extension = format.value === 'JPEG' ? 'jpg' : format.value.toLowerCase()
    const stem = sourceName.value.replace(/\.[^.]+$/, '') || 'image'
    downloadFile(result)
    await loadSource(result.url, result.filename)
    output.value = result
    sourceName.value = stem + '.' + extension
    message.value = error.value ? '编辑后的图片已生成，但重新读取 EXIF 失败。可通过文件地址下载。' : '已生成编辑后的图片并发起下载，当前内容已更新。'
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '编辑或下载失败，请重试。'
  } finally {
    saving.value = false
  }
}

onBeforeUnmount(() => {
  inspectController?.abort()
  searchController?.abort()
  if (searchTimer) clearTimeout(searchTimer)
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
    <section class="h-fit overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#141a2c]">
      <div class="border-b border-slate-100 px-6 py-4 text-sm font-bold dark:border-white/10">图片</div>
      <div class="p-6">
        <input ref="fileInput" class="sr-only" type="file" :disabled="saving" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" aria-label="选择图片" @change="chooseFile" />
        <button type="button" :disabled="saving" class="w-full rounded-xl border-2 border-dashed border-indigo-200 px-5 py-5 text-sm font-semibold text-indigo-600 hover:bg-indigo-50 disabled:opacity-50 dark:border-indigo-400/30 dark:hover:bg-indigo-400/5" @click="fileInput?.click()">选择 JPEG、PNG 或 WebP 图片</button>
        <p class="mt-2 text-xs text-slate-500">单张图片，最大 20 MB。也可使用图片链接，编辑后的文件保留 2 小时。</p>
        <div class="mt-5 border-t border-slate-100 pt-5 dark:border-white/10">
          <label for="exif-image-url" class="text-xs font-semibold text-slate-600 dark:text-slate-300">或使用图片链接</label>
          <div class="mt-2 flex gap-2">
            <input id="exif-image-url" v-model="imageUrl" type="url" inputmode="url" spellcheck="false" :disabled="saving" placeholder="https://example.com/photo.jpg" class="min-w-0 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-400 disabled:opacity-50 dark:border-white/10 dark:bg-[#0c1020]" @keyup.enter="loadUrl" />
            <button type="button" :disabled="loading || saving" class="shrink-0 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold hover:bg-slate-50 disabled:opacity-50 dark:border-white/15 dark:hover:bg-white/5" @click="loadUrl">读取链接</button>
          </div>
          <p class="mt-2 text-xs text-slate-500">支持公开图片链接，最多 20 MB。</p>
        </div>
        <div v-if="preview" class="mt-5 overflow-hidden rounded-xl bg-slate-100 dark:bg-[#0c1020]">
          <img :src="preview" :alt="`图片预览：${sourceName}`" class="max-h-72 w-full object-contain" />
        </div>
        <div v-if="sourceName" class="mt-3 break-all text-xs text-slate-500">{{ sourceName }} <span v-if="format">· {{ format }} · {{ tags.length }} 个 EXIF 标签</span></div>
        <div v-if="loading" class="mt-4 text-sm text-slate-500" role="status">正在处理…</div>
        <div v-if="error" class="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-500/10 dark:text-rose-300" role="alert">{{ error }}</div>
        <div v-if="message" class="mt-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300" role="status">{{ message }}</div>
        <p v-if="output" class="mt-3 text-xs text-slate-500">文件保留 2 小时，到期时间：{{ new Date(output.expires_at).toLocaleString() }}。<a :href="output.url" target="_blank" rel="noopener noreferrer" class="text-indigo-600 underline">下载文件</a></p>
        <div class="mt-5 flex flex-wrap items-center gap-2">
          <button type="button" :disabled="!format || !changes.length || loading || saving" class="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50" @click="download">{{ saving ? '编辑中…' : `编辑并下载${changes.length ? `（${changes.length} 项）` : ''}` }}</button>
          <button v-if="changes.length" type="button" :disabled="saving" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold dark:border-white/15" @click="discard">撤销修改</button>
        </div>
        <p v-if="changes.length" class="mt-2 text-xs text-amber-600 dark:text-amber-300">{{ changes.length }} 项修改尚未下载。</p>
      </div>
    </section>

    <section class="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#141a2c]">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-6 py-4 dark:border-white/10">
        <h2 class="text-sm font-bold">EXIF 标签</h2>
        <input v-if="format" v-model="search" type="search" aria-label="筛选现有标签" placeholder="筛选标签…" class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-400 dark:border-white/10 dark:bg-white/5" />
      </div>
      <div v-if="!sourceName" class="p-10 text-center text-sm text-slate-500">选择图片或填写图片链接后，可查看和编辑 EXIF 标签。</div>
      <div v-else-if="format" class="p-6">
        <div v-if="!tags.length && !Object.keys(drafts).length" class="rounded-xl bg-slate-50 p-5 text-sm text-slate-500 dark:bg-white/5">这张图片没有 EXIF 标签。可在下方添加。</div>
        <div v-else-if="!displayed.length" class="py-5 text-sm text-slate-500">没有匹配的标签。</div>
        <div v-else class="max-h-[560px] space-y-3 overflow-y-auto pr-1">
          <div v-for="tag in displayed" :key="tag.key" class="rounded-xl border border-slate-200 p-4 dark:border-white/10" :class="deleted.includes(tag.key) ? 'opacity-55' : ''">
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div class="min-w-0"><div class="break-all font-mono text-xs font-semibold text-indigo-700 dark:text-indigo-300">{{ tag.key }}</div><div v-if="!tag.writable" class="mt-1 text-xs text-slate-500">{{ tag.reason }}</div></div>
              <button v-if="tag.writable" type="button" class="text-xs font-semibold text-rose-600 hover:underline dark:text-rose-300" @click="toggleDelete(tag.key)">{{ deleted.includes(tag.key) ? '撤销删除' : '删除' }}</button>
              <span v-else class="text-xs text-slate-400">只读</span>
            </div>
            <textarea v-if="tag.writable" :value="inputValue(tag)" :disabled="deleted.includes(tag.key)" :aria-label="`编辑 ${tag.key}`" rows="2" maxlength="4096" class="mt-3 w-full resize-y rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-sm outline-none focus:border-indigo-400 disabled:opacity-50 dark:border-white/10 dark:bg-[#0c1020]" @input="setValue(tag.key, ($event.target as HTMLTextAreaElement).value)" />
            <div v-else class="mt-3 max-h-28 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-50 p-3 font-mono text-xs dark:bg-[#0c1020]">{{ tag.value }}</div>
          </div>
        </div>
        <div class="mt-7 border-t border-slate-100 pt-6 dark:border-white/10">
          <h3 class="text-sm font-bold">添加标签</h3>
          <p class="mt-1 text-xs text-slate-500">搜索 ExifTool 支持的安全可写 EXIF 标签。二进制和受限字段仅可查看。</p>
          <div class="mt-3 flex gap-2">
            <input v-model="tagSearch" type="search" aria-label="搜索可添加标签" placeholder="例如 DateTimeOriginal 或 GPS" class="min-w-0 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-400 dark:border-white/10 dark:bg-[#0c1020]" @input="queueSearch" @focus="findTags" />
            <button type="button" class="rounded-lg border border-slate-200 px-3 text-sm font-semibold dark:border-white/10" @click="findTags">搜索</button>
          </div>
          <div v-if="searching" class="mt-3 text-xs text-slate-500">正在处理…</div>
          <div v-else-if="catalog.length" class="mt-3 max-h-48 overflow-y-auto rounded-lg border border-slate-200 dark:border-white/10">
            <button v-for="tag in catalog.filter(item => !tags.some(existing => existing.key === item.key) && !(item.key in drafts))" :key="tag.key" type="button" class="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-3 py-2 text-left hover:bg-indigo-50 last:border-b-0 dark:border-white/10 dark:hover:bg-white/5" @click="addTag(tag)"><span class="break-all font-mono text-xs">{{ tag.key }}</span><span class="shrink-0 text-xs text-indigo-600 dark:text-indigo-300">添加</span></button>
          </div>
          <p v-else-if="tagSearch" class="mt-3 text-xs text-slate-500">没有找到可添加的标签。</p>
        </div>
      </div>
    </section>
  </div>
</template>

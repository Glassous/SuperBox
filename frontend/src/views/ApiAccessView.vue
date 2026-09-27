<script setup lang="ts">
import { ref } from 'vue'
import ExpandableApiCard from '../components/ExpandableApiCard.vue'
import SiteHeader from '../components/SiteHeader.vue'
import { apiBaseUrl } from '../api/client'
import { apiDocs } from '../data/apiDocs'

const overlayHost = ref<HTMLElement | null>(null)
const activeSlug = ref<string | null>(null)
</script>

<template>
  <div class="min-h-screen">
    <!-- The teleport target stays under the theme root, outside the inert page. -->
    <div ref="overlayHost" />
    <SiteHeader :inert="Boolean(activeSlug)" />

    <main :inert="Boolean(activeSlug)" class="mx-auto w-full max-w-7xl px-5 pb-18 pt-10 sm:px-9 sm:pt-14">
      <div class="flex flex-col justify-between gap-6 border-b border-slate-200 pb-9 dark:border-white/10 sm:flex-row sm:items-end">
        <div>
          <div class="text-[11px] font-bold tracking-[0.2em] text-indigo-600 dark:text-indigo-400">SUPERBOX / DEVELOPERS</div>
          <h1 class="mt-3 text-4xl font-bold tracking-tight text-slate-950 dark:text-white">API 接入</h1>
          <p class="mt-3 max-w-xl text-sm leading-6 text-slate-500 dark:text-slate-400">按工具查看接口契约、复制接入代码，也可以直接发送请求验证结果。</p>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-white/10 dark:bg-[#141a2c]"><div class="text-[10px] font-bold tracking-[0.14em] text-slate-400">BASE URL</div><code class="mt-1 block max-w-full overflow-x-auto whitespace-nowrap font-mono text-xs font-semibold text-slate-700 dark:text-slate-200">{{ apiBaseUrl }}/api/v1</code></div>
      </div>

      <div class="mt-10 flex items-end justify-between gap-4"><div><h2 class="text-xl font-bold text-slate-950 dark:text-white">选择接口能力</h2><p class="mt-1 text-sm text-slate-500 dark:text-slate-400">点击卡片查看完整接入方式。</p></div><span class="font-mono text-xs text-slate-400">{{ String(apiDocs.length).padStart(2, '0') }} TOOLS</span></div>
      <div class="mt-6 grid items-start gap-5 md:grid-cols-2 xl:grid-cols-4">
        <ExpandableApiCard v-for="doc in apiDocs" :key="doc.slug" :doc="doc" :overlay-host="overlayHost"
          :disabled="Boolean(activeSlug)" @opened="activeSlug = doc.slug" @closed="activeSlug = null" />
      </div>
    </main>
  </div>
</template>

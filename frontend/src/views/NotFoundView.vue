<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="flex min-h-[65vh] flex-col items-center justify-center text-center">
    <div class="text-7xl font-black tracking-tight text-indigo-200 dark:text-indigo-400/30">404</div>
    <h1 class="mt-5 text-2xl font-bold">页面没有找到</h1>
    <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">这个地址可能已失效，返回工具首页继续探索。</p>
    <RouterLink to="/" class="mt-7 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700">返回首页</RouterLink>
  </div>
</template>

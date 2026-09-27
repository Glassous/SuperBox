<script setup lang="ts">
defineProps<{ slug: string; size?: 'sm' | 'lg' }>()
</script>

<template>
  <div
    class="flex shrink-0 items-center justify-center rounded-2xl font-mono font-bold"
    :class="[
      size === 'lg' ? 'h-14 w-14 text-xl' : 'h-11 w-11 text-base',
      slug === 'json' ? 'bg-indigo-100 text-indigo-600 dark:bg-indigo-400/15 dark:text-indigo-300' : '',
      slug === 'base64' ? 'bg-violet-100 text-violet-600 dark:bg-violet-400/15 dark:text-violet-300' : '',
      slug === 'url' ? 'bg-sky-100 text-sky-600 dark:bg-sky-400/15 dark:text-sky-300' : '',
      slug === 'timestamp' ? 'bg-amber-100 text-amber-600 dark:bg-amber-400/15 dark:text-amber-300' : '',
    ]"
  >
    <span v-if="slug === 'json'">{ }</span>
    <span v-else-if="slug === 'base64'" class="text-sm">64</span>
    <span v-else-if="slug === 'url'">↗</span>
    <span v-else-if="slug === 'timestamp'">◷</span>
    <span v-else>✦</span>
  </div>
</template>

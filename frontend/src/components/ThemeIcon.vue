<script setup lang="ts">
defineProps<{ mode: 'system' | 'light' | 'dark' }>()
</script>

<template>
  <svg v-if="mode === 'system'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <rect x="3" y="4" width="18" height="13" rx="2.2" />
    <path d="M8 21h8M12 17v4" />
    <path d="M7.5 9.5h9" opacity=".55" />
  </svg>
  <svg v-else-if="mode === 'light'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="3.7" />
    <path d="M12 2.5v2M12 19.5v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2.5 12h2m15 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" />
  </svg>
  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M20.4 15.2A8.5 8.5 0 0 1 8.8 3.6 8.7 8.7 0 1 0 20.4 15.2Z" />
    <path d="M16.8 3.3v3.3m-1.65-1.65h3.3M19.8 8v2m-1-1h2" stroke-width="1.4" />
  </svg>
</template>

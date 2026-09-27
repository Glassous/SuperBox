<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import SiteHeader from './components/SiteHeader.vue'
import { useTheme } from './composables/useTheme'

const route = useRoute()
const { dark } = useTheme()
</script>

<template>
  <div :class="dark ? 'dark' : ''" class="min-h-screen bg-[#f6f8fc] text-slate-900 dark:bg-[#0c1020] dark:text-slate-100">
    <RouterView v-if="route.name === 'api-access'" />
    <div v-else class="min-h-screen">
      <div>
        <SiteHeader />

        <main class="mx-auto w-full max-w-7xl px-5 pb-14 pt-9 sm:px-9 sm:pt-11">
          <RouterView />
        </main>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { cancelToolTransition, cancelTransitionOutsideRoute, setToolTransitionHost } from './animations/toolOpenTransition'
import SiteHeader from './components/SiteHeader.vue'
import { useTheme } from './composables/useTheme'

const route = useRoute()
const { dark } = useTheme()
const transitionHost = ref<HTMLElement | null>(null)

onMounted(() => setToolTransitionHost(transitionHost.value))
onBeforeUnmount(() => {
  cancelToolTransition()
  setToolTransitionHost(null)
})
watch(() => route.fullPath, () => cancelTransitionOutsideRoute(route.name, route.params.slug))
</script>

<template>
  <div :class="dark ? 'dark' : ''" class="min-h-screen bg-[#f6f8fc] text-slate-900 dark:bg-[#0c1020] dark:text-slate-100">
    <div ref="transitionHost" class="pointer-events-none fixed inset-0 z-40" aria-hidden="true"></div>
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

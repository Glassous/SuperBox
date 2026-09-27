<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import ThemeIcon from './components/ThemeIcon.vue'

type ThemeMode = 'system' | 'light' | 'dark'

const route = useRoute()
const savedTheme = localStorage.getItem('superbox-theme-mode')
const theme = ref<ThemeMode>(savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : 'system')
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)')
const systemDark = ref(systemTheme.matches)
const dark = computed(() => theme.value === 'system' ? systemDark.value : theme.value === 'dark')
const themeMenuOpen = ref(false)
const themeMenu = ref<HTMLElement | null>(null)
const themeLabels: Record<ThemeMode, string> = { system: '跟随系统', light: '浅色模式', dark: '深色模式' }

onMounted(() => {
  systemTheme.addEventListener('change', onSystemThemeChange)
  document.addEventListener('pointerdown', closeThemeMenuOutside)
})

onBeforeUnmount(() => {
  systemTheme.removeEventListener('change', onSystemThemeChange)
  document.removeEventListener('pointerdown', closeThemeMenuOutside)
})

function onSystemThemeChange(event: MediaQueryListEvent) {
  systemDark.value = event.matches
}

function closeThemeMenuOutside(event: PointerEvent) {
  if (themeMenu.value && !themeMenu.value.contains(event.target as Node)) themeMenuOpen.value = false
}

function chooseTheme(next: ThemeMode) {
  theme.value = next
  localStorage.setItem('superbox-theme-mode', next)
  themeMenuOpen.value = false
}
</script>

<template>
  <div :class="dark ? 'dark' : ''" class="min-h-screen bg-[#f6f8fc] text-slate-900 dark:bg-[#0c1020] dark:text-slate-100">
    <RouterView v-if="route.name === 'api-access'" />
    <div v-else class="min-h-screen">
      <div>
        <header class="sticky top-0 z-20 flex h-18 items-center justify-between border-b border-slate-200/70 bg-[#f6f8fc]/90 px-5 backdrop-blur-xl dark:border-white/10 dark:bg-[#0c1020]/90 sm:px-9">
          <div class="flex min-w-0 items-center gap-3">
            <RouterLink v-if="route.name === 'tool'" to="/" class="inline-flex min-h-9 items-center gap-1.5 text-sm font-semibold text-slate-600 transition hover:text-indigo-600 dark:text-slate-300 dark:hover:text-indigo-300">
              <svg class="relative top-px h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m10.5 3.5-5 4.5 5 4.5" /></svg>
              <span>返回全部工具</span>
            </RouterLink>
            <RouterLink v-else to="/" class="flex items-center gap-2.5">
              <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-base font-bold text-white shadow-sm shadow-indigo-500/20">S</span>
              <span class="text-base font-bold tracking-tight text-slate-950 dark:text-white">Superbox</span>
            </RouterLink>
          </div>
          <div class="flex items-center gap-2 sm:gap-3">
            <RouterLink to="/api-access" target="_blank" rel="noopener noreferrer" class="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-600 shadow-sm transition hover:border-indigo-300 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-indigo-400/40 dark:hover:text-indigo-300 sm:text-sm">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 3.5h8l3 3V20a1 1 0 0 1-1 1H7a2 2 0 0 1-2-2V5.5a2 2 0 0 1 2-2Z"/><path d="M15 3.5V7h3M8.5 11h7M8.5 14.5h7M8.5 18h4"/></svg>
              API 接入
            </RouterLink>
            <div ref="themeMenu" class="relative" @keydown.esc="themeMenuOpen = false">
              <button class="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 text-slate-600 shadow-sm transition hover:border-indigo-300 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-indigo-400/40" :aria-label="`主题：${themeLabels[theme]}`" aria-haspopup="menu" :aria-expanded="themeMenuOpen" @click="themeMenuOpen = !themeMenuOpen">
                <ThemeIcon :mode="theme" class="h-4.5 w-4.5" />
                <svg class="h-3 w-3 text-slate-400" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg>
              </button>
              <div v-if="themeMenuOpen" class="absolute right-0 z-30 mt-2 w-42 rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl shadow-slate-900/10 dark:border-white/10 dark:bg-[#1b2236]" role="menu" aria-label="选择主题">
                <button v-for="mode in (['system', 'light', 'dark'] as const)" :key="mode" class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition hover:bg-slate-100 dark:hover:bg-white/5" :class="theme === mode ? 'font-semibold text-indigo-600 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-200'" role="menuitemradio" :aria-checked="theme === mode" @click="chooseTheme(mode)">
                  <ThemeIcon :mode="mode" class="h-4.5 w-4.5" />
                  <span class="flex-1">{{ themeLabels[mode] }}</span>
                  <svg v-if="theme === mode" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 4.5 4.5L19 7" /></svg>
                </button>
              </div>
            </div>
          </div>
        </header>

        <main class="mx-auto w-full max-w-7xl px-5 pb-14 pt-9 sm:px-9 sm:pt-11">
          <RouterView />
        </main>
      </div>
    </div>
  </div>
</template>

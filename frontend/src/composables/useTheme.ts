import { computed, ref } from 'vue'

export type ThemeMode = 'system' | 'light' | 'dark'

const savedTheme = localStorage.getItem('superbox-theme-mode')
const theme = ref<ThemeMode>(savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : 'system')
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)')
const systemDark = ref(systemTheme.matches)
const themeLabels: Record<ThemeMode, string> = { system: '跟随系统', light: '浅色模式', dark: '深色模式' }

let watchingSystemTheme = false

export function useTheme() {
  if (!watchingSystemTheme) {
    watchingSystemTheme = true
    systemTheme.addEventListener('change', (event) => {
      systemDark.value = event.matches
    })
  }

  const dark = computed(() => (theme.value === 'system' ? systemDark.value : theme.value === 'dark'))

  function setTheme(next: ThemeMode) {
    theme.value = next
    localStorage.setItem('superbox-theme-mode', next)
  }

  return { theme, dark, themeLabels, setTheme }
}

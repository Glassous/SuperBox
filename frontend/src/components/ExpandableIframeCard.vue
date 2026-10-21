<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useExpandableOverlay } from '../composables/useExpandableOverlay'
import IframeDialogContent from './IframeDialogContent.vue'
import type { IframeInfo } from '../types'

const props = defineProps<{
  item: IframeInfo
  overlayHost: HTMLElement | null
  disabled: boolean
}>()
const emit = defineEmits<{ opened: []; closed: [] }>()

const slot = ref<HTMLElement | null>(null)
const card = ref<HTMLElement | null>(null)
const shade = ref<HTMLElement | null>(null)
const body = ref<HTMLElement | null>(null)
const header = ref<HTMLElement | null>(null)
const collapsed = ref<HTMLElement | null>(null)
const media = ref<HTMLElement | null>(null)
const previewImage = ref<HTMLImageElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)
const previewFailed = ref(false)
const previewAspect = ref(0)
const liveVisible = ref(false)
const titleId = `iframe-title-${props.item.slug}`
const expandedTitleId = `${titleId}-expanded`
const previewSrc = computed(() => props.item.preview_url || props.item.thumbnail_url)

function aspectRatio(): number {
  if (previewAspect.value > 0) return previewAspect.value
  if (props.item.width > 0 && props.item.height > 0) return props.item.width / props.item.height
  return 1
}

function onPreviewLoad() {
  const image = previewImage.value
  if (image && image.naturalWidth > 0 && image.naturalHeight > 0) {
    previewAspect.value = image.naturalWidth / image.naturalHeight
  }
}

const { phase, floating, slotHeight, open, close } = useExpandableOverlay(
  { slot, card, shade, body, header, collapsed, media, trigger },
  {
    overlayHost: () => props.overlayHost,
    disabled: () => props.disabled,
    aspectRatio,
    onOpened: () => emit('opened'),
    onClosed: () => emit('closed'),
  },
)

onMounted(() => {
  if (previewImage.value?.complete) onPreviewLoad()
})

watch(phase, value => {
  if (value === 'collapsed') liveVisible.value = false
})
</script>

<template>
  <div ref="slot" class="min-w-0" :style="slotHeight === undefined ? undefined : { height: `${slotHeight}px` }">
    <Teleport :to="overlayHost ?? 'body'" :disabled="!floating">
      <div v-if="floating" ref="shade" class="fixed inset-0 z-50 bg-slate-950/60 opacity-0" aria-hidden="true" @click="close" />
      <article
        ref="card"
        class="relative w-full overflow-hidden rounded-2xl border border-slate-200/80 bg-white text-left shadow-sm outline-none dark:border-white/10 dark:bg-[#141a2c]"
        :class="floating
          ? 'shadow-2xl shadow-slate-950/25'
          : 'group transition duration-200 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-900/5 dark:hover:border-indigo-400/30'"
        :role="floating ? 'dialog' : undefined"
        :aria-modal="floating ? true : undefined"
        :aria-labelledby="floating ? expandedTitleId : titleId"
        :tabindex="floating ? -1 : undefined"
      >
        <div :class="floating ? '' : 'p-2.5 pb-0'">
          <div
            ref="media"
            class="relative w-full overflow-hidden rounded-xl bg-slate-100 dark:bg-white/5"
            :class="floating
              ? ['transition-opacity duration-300', liveVisible ? 'opacity-0' : 'opacity-100']
              : 'aspect-[16/10]'"
          >
            <img
              v-if="previewSrc && !previewFailed"
              ref="previewImage"
              :src="previewSrc"
              :alt="item.name"
              loading="lazy"
              decoding="async"
              class="h-full w-full object-contain"
              :class="floating ? '' : 'transition duration-500 group-hover:scale-[1.03]'"
              @load="onPreviewLoad"
              @error="previewFailed = true"
            />
            <div v-else class="flex h-full items-center justify-center font-mono text-3xl text-slate-400">▣</div>
          </div>
        </div>

        <div ref="collapsed" :class="floating ? 'pointer-events-none absolute inset-0' : ''">
          <div class="flex flex-1 flex-col p-5">
            <div class="flex items-center justify-between gap-3">
              <span class="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold text-slate-500 dark:bg-white/5 dark:text-slate-400">{{ item.category }}</span>
              <span class="font-mono text-[11px] text-slate-400">{{ item.width }} × {{ item.height }}</span>
            </div>
            <h3 :id="titleId" class="mt-4 text-lg font-bold text-slate-950 dark:text-white">{{ item.name }}</h3>
            <p class="mt-2 min-h-10 text-sm leading-5 text-slate-500 dark:text-slate-400">{{ item.description }}</p>
            <div class="mt-4 flex items-center gap-2 text-sm font-semibold text-indigo-600 transition group-hover:gap-3 dark:text-indigo-400">
              预览挂件 <span aria-hidden="true">→</span>
            </div>
          </div>
        </div>

        <header v-if="floating" ref="header" class="flex items-start gap-4 px-5 pb-4 pr-16 pt-5 sm:px-6 sm:pr-20">
          <div class="min-w-0 flex-1">
            <span class="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-1 text-[10px] font-bold tracking-[0.14em] text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300">{{ item.category }}</span>
            <h3 :id="expandedTitleId" class="mt-2 text-xl font-bold tracking-tight text-slate-950 dark:text-white">{{ item.name }}</h3>
            <p class="mt-1.5 max-w-2xl text-xs leading-5 text-slate-500 dark:text-slate-400">{{ item.description }}</p>
          </div>
          <span class="mt-1 hidden shrink-0 rounded-full border border-slate-200 px-3 py-1 font-mono text-[11px] text-slate-500 dark:border-white/10 dark:text-slate-400 sm:inline-flex">{{ item.width }} × {{ item.height }}</span>
        </header>

        <div
          v-if="floating"
          ref="body"
          class="absolute left-0 overflow-hidden border-t border-slate-100 opacity-0 dark:border-white/10"
          :inert="phase !== 'open'"
        >
          <IframeDialogContent :item="item" :active="phase === 'open'" @live-change="liveVisible = $event" />
        </div>

        <button
          v-show="!floating"
          ref="trigger"
          type="button"
          class="absolute inset-0 rounded-2xl focus-visible:outline-2 focus-visible:-outline-offset-4 focus-visible:outline-indigo-500"
          :aria-label="`预览${item.name}`"
          :disabled="disabled"
          @click="open"
        />

        <button
          v-if="phase === 'open'"
          type="button"
          class="absolute right-5 top-5 z-10 inline-flex size-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-0 text-slate-500 outline-none transition-colors hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 dark:border-white/10 dark:bg-white/5 dark:text-slate-400 dark:hover:border-white/20 dark:hover:bg-white/10 dark:hover:text-white dark:focus-visible:ring-offset-[#141a2c]"
          aria-label="关闭预览"
          @click="close"
        >
          <svg class="pointer-events-none block size-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
        </button>
      </article>
    </Teleport>
  </div>
</template>

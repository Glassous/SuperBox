<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { gsap } from 'gsap'
import ToolMark from './ToolMark.vue'
import ApiDocContent from './ApiDocContent.vue'
import type { ApiToolDoc } from '../data/apiDocs'

const props = defineProps<{ doc: ApiToolDoc; overlayHost: HTMLElement | null; disabled: boolean }>()
const emit = defineEmits<{ opened: []; closed: [] }>()
type Phase = 'collapsed' | 'opening' | 'open' | 'closing'
const phase = ref<Phase>('collapsed')
const floating = computed(() => phase.value !== 'collapsed')
const slot = ref<HTMLElement | null>(null)
const card = ref<HTMLElement | null>(null)
const icon = ref<HTMLElement | null>(null)
const heading = ref<HTMLElement | null>(null)
const category = ref<HTMLElement | null>(null)
const footer = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)
const closeButton = ref<HTMLButtonElement | null>(null)
const body = ref<HTMLElement | null>(null)
const shade = ref<HTMLElement | null>(null)
const slotHeight = ref<number>()
const titleId = `api-title-${props.doc.slug}`
let context: gsap.Context | undefined
let timeline: gsap.core.Timeline | undefined
let reversible = false
let disposed = false
let returning = false
let resizeFrame = 0
let scrollStyle: { overflow: string; paddingRight: string } | undefined
let textWidth = 0
let baseHeight = 0
let baseTextHeight = 0
let source: DOMRect
type Part = { element: HTMLElement; x: number; y: number; width: number; height: number }
let parts: Part[] = []

function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function unlockScroll() {
  if (!scrollStyle) return
  document.body.style.overflow = scrollStyle.overflow
  document.body.style.paddingRight = scrollStyle.paddingRight
  scrollStyle = undefined
}

function expandedGeometry() {
  const width = Math.min(1024, window.innerWidth - 32)
  const height = Math.min(780, window.innerHeight - 32)
  // Keep the exact same text wrapping in both states; only move the text block.
  // Reserve a separate 40px close control, 24px edge inset and 16px gap.
  const horizontal = width >= textWidth + 184
  const headingX = horizontal ? 104 : 24
  const headingY = horizontal ? 24 : parts[1]!.y
  const headerHeight = Math.max(80, headingY + heading.value!.offsetHeight) + 24
  return { x: (window.innerWidth - width) / 2, y: (window.innerHeight - height) / 2,
    width, height, headingX, headingY, headerHeight }
}

function prepareBody() {
  const target = expandedGeometry()
  gsap.set(body.value, { top: target.headerHeight, width: target.width - 2,
    height: Math.max(0, target.height - target.headerHeight - 2) })
  return target
}

async function markOpen() {
  if (disposed || phase.value !== 'opening') return
  phase.value = 'open'
  await nextTick()
  if (!disposed && phase.value === 'open') closeButton.value?.focus({ preventScroll: true })
}

async function returnToSlot() {
  if (disposed || returning) return
  returning = true
  timeline?.kill()
  context?.revert()
  context = undefined
  // Restore flow and move the same nodes back before the next paint.
  phase.value = 'collapsed'
  slotHeight.value = undefined
  unlockScroll()
  emit('closed')
  await nextTick()
  if (!disposed) trigger.value?.focus({ preventScroll: true })
  returning = false
}

async function open() {
  if (floating.value || props.disabled || !props.overlayHost || !card.value || !slot.value) return
  source = card.value.getBoundingClientRect()
  const elements = [icon.value!, heading.value!, category.value!, footer.value!]
  // Batch all geometry reads before detaching the card from the grid.
  parts = elements.map(element => {
    const rect = element.getBoundingClientRect()
    return { element, x: rect.left - source.left - 1, y: rect.top - source.top - 1,
      width: rect.width, height: rect.height }
  })
  textWidth = parts[1]!.width
  baseTextHeight = parts[1]!.height
  baseHeight = source.height
  slotHeight.value = source.height
  scrollStyle = { overflow: document.body.style.overflow, paddingRight: document.body.style.paddingRight }
  const gutter = window.innerWidth - document.documentElement.clientWidth
  const padding = parseFloat(getComputedStyle(document.body).paddingRight) || 0
  document.body.style.paddingRight = `${padding + gutter}px`
  document.body.style.overflow = 'hidden'
  phase.value = 'opening'
  emit('opened')
  await nextTick()
  if (disposed || phase.value !== 'opening') return
  context = gsap.context(() => {
    gsap.set(card.value, { position: 'fixed', left: 0, top: 0, x: source.x, y: source.y,
      width: source.width, height: source.height, minHeight: 0, padding: 0, margin: 0,
      borderRadius: 16, willChange: 'transform,width,height', zIndex: 51 })
    for (const part of parts) {
      gsap.set(part.element, { position: 'absolute', left: 0, top: 0, margin: 0,
        x: part.x, y: part.y, width: part.width })
    }
    gsap.set([body.value, shade.value], { autoAlpha: 0 })
    const target = prepareBody()
    timeline = gsap.timeline({ paused: true, defaults: { ease: 'power3.inOut' },
      onComplete: markOpen, onReverseComplete: () => { void returnToSlot() } })
      .to(card.value, { x: target.x, y: target.y, width: target.width, height: target.height,
        borderRadius: 24, duration: 0.5 }, 0)
      .to(icon.value, { x: 24, y: 24, duration: 0.5 }, 0)
      .to(heading.value, { x: target.headingX, y: target.headingY, duration: 0.5 }, 0)
      .to(category.value, { autoAlpha: 0, duration: 0.12 }, 0)
      .to(footer.value, { autoAlpha: 0, duration: 0.12 }, 0)
      .to(shade.value, { autoAlpha: 1, duration: 0.5 }, 0)
      .to(body.value, { autoAlpha: 1, duration: 0.24 }, 0.26)
    reversible = true
    if (reducedMotion()) timeline.progress(1)
    else timeline.play()
  }, card.value!)
  if (phase.value === 'opening') card.value?.focus({ preventScroll: true })
}

function close() {
  if (!floating.value || phase.value === 'closing' || returning) return
  phase.value = 'closing'
  card.value?.focus({ preventScroll: true })
  if (reducedMotion() || !timeline || timeline.time() === 0) {
    void returnToSlot()
  } else if (reversible) {
    // Reverse from the current frame, including a partially expanded card.
    timeline.reverse()
  } else {
    animateFromCurrent(false)
  }
}

// A viewport change invalidates the old endpoints. Retarget from the rendered
// frame instead of seeking the old timeline (which would introduce a jump).
function animateFromCurrent(expand: boolean) {
  timeline?.kill()
  reversible = false
  context?.add(() => {
    const target = prepareBody()
    const duration = 0.35
    timeline = gsap.timeline({ paused: true, defaults: { duration, ease: 'power2.inOut' },
      onComplete: expand ? markOpen : () => { void returnToSlot() } })
      .to(card.value, expand
        ? { x: target.x, y: target.y, width: target.width, height: target.height, borderRadius: 24 }
        : { x: source.x, y: source.y, width: source.width, height: slotHeight.value, borderRadius: 16 }, 0)
      .to(icon.value, { x: expand ? 24 : parts[0]!.x, y: expand ? 24 : parts[0]!.y }, 0)
      .to(heading.value, { x: expand ? target.headingX : parts[1]!.x, y: expand ? target.headingY : parts[1]!.y }, 0)
      .to([category.value, footer.value], { autoAlpha: expand ? 0 : 1, duration: duration * 0.3 }, expand ? 0 : duration * 0.7)
      .to(shade.value, { autoAlpha: expand ? 1 : 0 }, 0)
      .to(body.value, { autoAlpha: expand ? 1 : 0, duration: duration * 0.4 }, expand ? duration * 0.6 : 0)
    if (reducedMotion()) timeline.progress(1)
    else timeline.play()
  })
}

function onResize() {
  if (!floating.value || returning) return
  cancelAnimationFrame(resizeFrame)
  resizeFrame = requestAnimationFrame(() => {
    if (!floating.value || returning || !context || !slot.value) return
    const rect = slot.value.getBoundingClientRect()
    source = rect
    textWidth = Math.max(0, rect.width - 50)
    context.add(() => {
      gsap.set(heading.value, { width: textWidth })
      const delta = heading.value!.offsetHeight - baseTextHeight
      slotHeight.value = baseHeight + delta
      gsap.set(category.value, { x: rect.width - 25 - parts[2]!.width })
      gsap.set(footer.value, { y: parts[3]!.y + delta, width: textWidth })
    })
    const expand = phase.value !== 'closing'
    if (expand) phase.value = 'opening'
    animateFromCurrent(expand)
  })
}

function onKeydown(event: KeyboardEvent) {
  if (!floating.value) return
  if (event.key === 'Escape') { event.preventDefault(); close(); return }
  if (event.key !== 'Tab' || !card.value) return
  if (phase.value !== 'open') { event.preventDefault(); return }
  const focusable = Array.from(card.value.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href]'))
    .filter(element => element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden')
  const first = focusable[0]
  const last = focusable.at(-1)
  if (!first || !last) { event.preventDefault(); card.value.focus(); return }
  if (!card.value.contains(document.activeElement) || document.activeElement === card.value) {
    event.preventDefault(); (event.shiftKey ? last : first).focus()
  } else if (event.shiftKey && document.activeElement === first) {
    event.preventDefault(); last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault(); first.focus()
  }
}

// The listener is scoped by floating state; no global animation selectors.
onMounted(() => {
  window.addEventListener('resize', onResize)
  document.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  disposed = true
  cancelAnimationFrame(resizeFrame)
  timeline?.kill()
  context?.revert()
  unlockScroll()
  window.removeEventListener('resize', onResize)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div ref="slot" class="min-w-0" :style="slotHeight === undefined ? undefined : { height: `${slotHeight}px` }">
    <Teleport :to="overlayHost ?? 'body'" :disabled="!floating">
      <div v-if="floating" ref="shade" class="fixed inset-0 z-50 bg-slate-950/60 opacity-0" aria-hidden="true" @click="close" />
      <article ref="card" class="relative min-h-58 w-full overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-6 text-left shadow-sm outline-none dark:border-white/10 dark:bg-[#141a2c]"
        :class="floating ? 'shadow-2xl shadow-slate-950/25' : 'hover:border-indigo-300 dark:hover:border-indigo-400/30'"
        :role="floating ? 'dialog' : undefined" :aria-modal="floating ? true : undefined" :aria-labelledby="titleId" :tabindex="floating ? -1 : undefined">
        <div class="flex items-start justify-between">
          <div ref="icon"><ToolMark :slug="doc.slug" size="lg" /></div>
          <span ref="category" class="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold text-slate-500 dark:bg-white/5 dark:text-slate-400">{{ doc.category }}</span>
        </div>
        <div ref="heading" class="mt-6">
          <h3 :id="titleId" class="text-lg font-bold text-slate-950 dark:text-white">{{ doc.name }}</h3>
          <p class="mt-2 min-h-10 text-sm leading-5 text-slate-500 dark:text-slate-400">{{ doc.description }}</p>
        </div>
        <div ref="footer" class="flex items-center gap-2 pt-5 text-sm font-semibold text-indigo-600 dark:text-indigo-400" aria-hidden="true">查看接入方式 <span>→</span></div>
        <button v-show="!floating" ref="trigger" type="button" class="absolute inset-0 rounded-2xl focus-visible:outline-2 focus-visible:-outline-offset-4 focus-visible:outline-indigo-500"
          :aria-label="`查看${doc.name} API 接入`" :disabled="disabled" @click="open" />
        <button v-if="phase === 'open'" ref="closeButton" type="button" class="absolute right-6 top-6 z-10 inline-flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-0 text-slate-500 outline-none transition-colors hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 dark:border-white/10 dark:bg-white/5 dark:text-slate-400 dark:hover:border-white/20 dark:hover:bg-white/10 dark:hover:text-white dark:focus-visible:ring-offset-[#141a2c]"
          aria-label="关闭 API 详情" @click="close">
          <svg class="pointer-events-none block size-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
        </button>
        <div v-if="floating" ref="body" class="absolute left-0 overflow-hidden border-t border-slate-100 opacity-0 dark:border-white/10" :inert="phase !== 'open'">
          <ApiDocContent :doc="doc" />
        </div>
      </article>
    </Teleport>
  </div>
</template>

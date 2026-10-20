import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Ref } from 'vue'
import { gsap } from 'gsap'

export type OverlayPhase = 'collapsed' | 'opening' | 'open' | 'closing'

interface Box { x: number; y: number; width: number; height: number }

export interface OverlayElements {
  slot: Ref<HTMLElement | null>
  card: Ref<HTMLElement | null>
  shade: Ref<HTMLElement | null>
  body: Ref<HTMLElement | null>
  header: Ref<HTMLElement | null>
  collapsed: Ref<HTMLElement | null>
  media: Ref<HTMLElement | null>
  trigger: Ref<HTMLButtonElement | null>
}

export interface OverlayOptions {
  overlayHost: () => HTMLElement | null
  disabled: () => boolean
  /** 预览图的宽高比，用于把预览框按图片比例放进弹窗。 */
  aspectRatio: () => number
  onOpened: () => void
  onClosed: () => void
}

/**
 * 卡片原位放大为居中浮层的通用逻辑：卡片、预览框与内容区共用一条 gsap 时间线，
 * 关闭时反向播放。负责滚动锁、焦点回收、Esc/Tab 与视口变化后的重新贴合。
 */
export function useExpandableOverlay(elements: OverlayElements, options: OverlayOptions) {
  const phase = ref<OverlayPhase>('collapsed')
  const floating = computed(() => phase.value !== 'collapsed')
  const slotHeight = ref<number>()

  let context: gsap.Context | undefined
  let timeline: gsap.core.Timeline | undefined
  let sourceRect: DOMRect
  let mediaStart: Box | undefined
  let resizeFrame = 0
  let disposed = false
  let returning = false
  let scrollStyle: { overflow: string; paddingRight: string } | undefined

  function reducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }

  function unlockScroll() {
    if (!scrollStyle) return
    document.body.style.overflow = scrollStyle.overflow
    document.body.style.paddingRight = scrollStyle.paddingRight
    scrollStyle = undefined
  }

  function targetGeometry() {
    const width = Math.min(1024, Math.max(320, window.innerWidth - 32))
    const height = Math.min(780, Math.max(360, window.innerHeight - 32))
    return { x: (window.innerWidth - width) / 2, y: (window.innerHeight - height) / 2, width, height }
  }

  /** 固定高度、按图片比例算宽度的取景框，居中放在预览区内并保证完整显示。 */
  function fitBox(panel: DOMRect, cardRect: DOMRect, aspect: number): Box {
    let height = panel.height
    let width = height * aspect
    if (width > panel.width) {
      width = panel.width
      height = width / aspect
    }
    return {
      x: panel.left - cardRect.left + (panel.width - width) / 2,
      y: panel.top - cardRect.top + (panel.height - height) / 2,
      width,
      height,
    }
  }

  function retargetMedia() {
    if (!elements.card.value || !elements.media.value || phase.value === 'collapsed') return
    const panel = elements.card.value.querySelector<HTMLElement>('[data-preview-panel]')
    if (!panel) return
    const box = fitBox(panel.getBoundingClientRect(), elements.card.value.getBoundingClientRect(), options.aspectRatio())
    gsap.set(elements.media.value, { x: box.x, y: box.y, width: box.width, height: box.height })
  }

  async function open() {
    const card = elements.card.value
    if (floating.value || options.disabled() || !options.overlayHost() || !card || !elements.slot.value) return
    sourceRect = card.getBoundingClientRect()
    const mediaRect = elements.media.value?.getBoundingClientRect()
    mediaStart = mediaRect
      ? {
          x: mediaRect.left - sourceRect.left,
          y: mediaRect.top - sourceRect.top,
          width: mediaRect.width,
          height: mediaRect.height,
        }
      : undefined
    slotHeight.value = sourceRect.height
    scrollStyle = { overflow: document.body.style.overflow, paddingRight: document.body.style.paddingRight }
    const gutter = window.innerWidth - document.documentElement.clientWidth
    const padding = parseFloat(getComputedStyle(document.body).paddingRight) || 0
    document.body.style.paddingRight = `${padding + gutter}px`
    document.body.style.overflow = 'hidden'
    phase.value = 'opening'
    options.onOpened()
    await nextTick()
    if (disposed || phase.value !== 'opening' || !elements.card.value || !elements.body.value) return

    const mediaElement = elements.media.value
    context = gsap.context(() => {
      const target = targetGeometry()
      // 先把卡片摆到最终尺寸，量出头部高度与预览区几何，再回到卡片原位起播。
      gsap.set(elements.card.value!, {
        position: 'fixed', left: 0, top: 0, margin: 0, zIndex: 51,
        x: target.x, y: target.y, width: target.width, height: target.height, borderRadius: 24,
      })
      const headerHeight = elements.header.value?.offsetHeight ?? 112
      const bodyHeight = Math.max(0, target.height - headerHeight - 1)
      gsap.set(elements.body.value!, { top: headerHeight, left: 0, width: target.width - 2, height: bodyHeight })

      const panel = elements.card.value!.querySelector<HTMLElement>('[data-preview-panel]')
      const mediaTarget = panel && mediaStart
        ? fitBox(panel.getBoundingClientRect(), elements.card.value!.getBoundingClientRect(), options.aspectRatio())
        : undefined

      gsap.set([elements.header.value, elements.body.value, elements.shade.value], { autoAlpha: 0 })
      gsap.set(elements.card.value!, {
        x: sourceRect.left, y: sourceRect.top, width: sourceRect.width, height: sourceRect.height, borderRadius: 16,
      })
      if (mediaElement && mediaStart) {
        gsap.set(mediaElement, {
          position: 'absolute', left: 0, top: 0, margin: 0, zIndex: 0,
          x: mediaStart.x, y: mediaStart.y, width: mediaStart.width, height: mediaStart.height,
        })
      }

      timeline = gsap.timeline({
        paused: true,
        defaults: { ease: 'power3.inOut' },
        onComplete: markOpen,
        onReverseComplete: () => { void returnToSlot() },
      })
        .to(elements.card.value, {
          x: target.x, y: target.y, width: target.width, height: target.height, borderRadius: 24, duration: 0.5,
        }, 0)
        .to(elements.shade.value, { autoAlpha: 1, duration: 0.4 }, 0)
        .to(elements.collapsed.value, { autoAlpha: 0, duration: 0.16 }, 0)
        .to([elements.header.value, elements.body.value], { autoAlpha: 1, duration: 0.24 }, 0.26)

      if (mediaElement && mediaTarget) {
        timeline.to(mediaElement, {
          x: mediaTarget.x, y: mediaTarget.y, width: mediaTarget.width, height: mediaTarget.height, duration: 0.5,
        }, 0)
      }

      if (reducedMotion()) timeline.progress(1)
      else timeline.play()
    }, card)
    if (phase.value === 'opening') card.focus({ preventScroll: true })
  }

  async function markOpen() {
    if (disposed || phase.value !== 'opening') return
    phase.value = 'open'
    await nextTick()
    // 焦点落在对话框容器上，避免鼠标打开时关闭按钮出现高亮焦点环。
    if (!disposed && phase.value === 'open') elements.card.value?.focus({ preventScroll: true })
  }

  function close() {
    if (!floating.value || phase.value === 'closing' || returning) return
    phase.value = 'closing'
    elements.card.value?.focus({ preventScroll: true })
    if (reducedMotion() || !timeline || timeline.time() === 0) void returnToSlot()
    else timeline.reverse()
  }

  async function returnToSlot() {
    if (returning) return
    returning = true
    timeline?.kill()
    timeline = undefined
    context?.revert()
    context = undefined
    phase.value = 'collapsed'
    slotHeight.value = undefined
    unlockScroll()
    options.onClosed()
    await nextTick()
    if (!disposed) elements.trigger.value?.focus({ preventScroll: true })
    returning = false
  }

  // 视口尺寸变化后重新贴合展开几何；动画途中直接结束到目标状态，避免旧端点失效。
  function onResize() {
    if (!floating.value || returning) return
    cancelAnimationFrame(resizeFrame)
    resizeFrame = requestAnimationFrame(() => {
      if (!floating.value || returning || !elements.card.value || !elements.body.value) return
      if (phase.value !== 'open') {
        timeline?.progress(phase.value === 'closing' ? 0 : 1)
        return
      }
      const target = targetGeometry()
      gsap.set(elements.card.value, { x: target.x, y: target.y, width: target.width, height: target.height })
      const headerHeight = elements.header.value?.offsetHeight ?? 112
      gsap.set(elements.body.value, {
        top: headerHeight, width: target.width - 2, height: Math.max(0, target.height - headerHeight - 1),
      })
      retargetMedia()
    })
  }

  function onKeydown(event: KeyboardEvent) {
    const card = elements.card.value
    if (!floating.value) return
    if (event.key === 'Escape') { event.preventDefault(); close(); return }
    if (event.key !== 'Tab' || !card) return
    if (phase.value !== 'open') { event.preventDefault(); return }
    const focusable = Array.from(card.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href]',
    )).filter(element => element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden')
    const first = focusable[0]
    const last = focusable.at(-1)
    if (!first || !last) { event.preventDefault(); card.focus(); return }
    if (!card.contains(document.activeElement) || document.activeElement === card) {
      event.preventDefault(); (event.shiftKey ? last : first).focus()
    } else if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus()
    }
  }

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

  return { phase, floating, slotHeight, open, close }
}

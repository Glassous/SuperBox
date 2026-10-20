import { gsap } from 'gsap'
import type { IframeInfo, ToolInfo } from '../types'

export type CardKind = 'tool' | 'iframe'
export type CardPayload = ToolInfo | IframeInfo

type Direction = 'open' | 'return'
type PartName = 'icon' | 'media' | 'title' | 'description' | 'category'

const partNames: PartName[] = ['icon', 'media', 'title', 'description', 'category']
const detailRoutes: Record<CardKind, string> = { tool: 'tool', iframe: 'iframe' }
const listRoutes: Record<CardKind, string> = { tool: 'home', iframe: 'iframes' }

interface FloatingPart {
  name: PartName
  clone: HTMLElement
  source: HTMLElement
  sourceVisibility: string
  rect: DOMRect
  fontSize: number
}

interface Session {
  kind: CardKind
  direction: Direction
  slug: string
  payload?: CardPayload
  parts: FloatingPart[]
  targetStyles: Map<HTMLElement, string>
  timeline?: gsap.core.Timeline
  timeout: ReturnType<typeof setTimeout>
}

let host: HTMLElement | null = null
let session: Session | null = null

function findParts(root: HTMLElement) {
  const result = new Map<PartName, HTMLElement>()
  for (const name of partNames) {
    const element = root.querySelector<HTMLElement>(`[data-card-transition="${name}"]`)
    if (element) result.set(name, element)
  }
  return result
}

function onResize() {
  cancelCardTransition()
}

export function setCardTransitionHost(element: HTMLElement | null) {
  if (!element) cancelCardTransition()
  host = element
}

export function isPlainNavigation(event: MouseEvent) {
  return event.button === 0 && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.defaultPrevented
}

/**
 * 从卡片抓取带 `data-card-transition` 的元素，生成固定定位副本等待翻转。
 * `media` 用于预览图：副本保留已加载的图片位图，过渡期间不会重新请求。
 */
export function beginCardTransition(
  kind: CardKind,
  direction: Direction,
  slug: string,
  root: HTMLElement,
  payload?: CardPayload,
) {
  cancelCardTransition()
  if (!host || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  const sourceParts = findParts(root)
  if (!sourceParts.has('title')) return

  const parts: FloatingPart[] = []
  for (const [name, source] of sourceParts) {
    const rect = source.getBoundingClientRect()
    if (!rect.width || !rect.height) continue
    const clone = source.cloneNode(true) as HTMLElement
    host.appendChild(clone)
    const style = getComputedStyle(source)
    gsap.set(clone, {
      position: 'fixed',
      left: rect.left,
      top: rect.top,
      right: 'auto',
      bottom: 'auto',
      width: rect.width,
      height: rect.height,
      margin: 0,
      transformOrigin: 'top left',
      pointerEvents: 'none',
      color: style.color,
    })
    parts.push({
      name, clone, source, rect,
      sourceVisibility: source.style.visibility,
      fontSize: parseFloat(style.fontSize) || 16,
    })
  }

  if (!parts.length) return

  for (const part of parts) part.source.style.visibility = 'hidden'
  session = {
    kind, direction, slug, payload, parts, targetStyles: new Map(),
    timeout: setTimeout(cancelCardTransition, 6000),
  }
  window.addEventListener('resize', onResize)
}

export function getOpeningPayload<T extends CardPayload>(kind: CardKind, slug: string): T | null {
  if (!session || session.direction !== 'open' || session.kind !== kind || session.slug !== slug) return null
  return (session.payload as T | undefined) ?? null
}

export function getReturningSlug(kind?: CardKind): string | null {
  if (!session || session.direction !== 'return') return null
  if (kind && session.kind !== kind) return null
  return session.slug
}

export function cancelTransitionOutsideRoute(name: unknown, slug: unknown) {
  if (!session) return
  const valid = session.direction === 'open'
    ? name === detailRoutes[session.kind] && slug === session.slug
    : name === listRoutes[session.kind]
  if (!valid) cancelCardTransition()
}

export function finishCardTransition(
  kind: CardKind,
  direction: Direction,
  slug: string,
  root: HTMLElement,
  body?: HTMLElement | null,
): boolean {
  const current = session
  if (!current || current.kind !== kind || current.direction !== direction || current.slug !== slug || current.timeline) return false
  const targets = findParts(root)
  if (!targets.has('title')) {
    cancelCardTransition()
    return false
  }

  // The router also scrolls to the top; do it before measuring the destination
  // so the first animation frame uses the same coordinates as the final page.
  window.scrollTo(0, 0)

  const remember = (element: HTMLElement) => {
    current.targetStyles.set(element, element.style.cssText)
  }
  for (const part of current.parts) {
    const target = targets.get(part.name)
    if (target) remember(target)
  }
  if (direction === 'open' && body) remember(body)

  const timeline = gsap.timeline({
    defaults: { ease: 'power3.inOut' },
    onComplete: () => { if (session === current) cancelCardTransition() },
  })
  current.timeline = timeline

  for (const part of current.parts) {
    const target = targets.get(part.name)
    if (!target) {
      timeline.to(part.clone, { autoAlpha: 0, duration: 0.2 }, 0)
      continue
    }
    const rect = target.getBoundingClientRect()

    if (part.name === 'media') {
      // 预览图按实际几何尺寸翻转，保持图片比例与内容连续。
      gsap.set(target, { autoAlpha: 0 })
      timeline.to(part.clone, {
        left: rect.left, top: rect.top, width: rect.width, height: rect.height, duration: 0.45,
      }, 0)
        .to(part.clone, { autoAlpha: 0, duration: 0.1 }, 0.34)
        .to(target, { autoAlpha: 1, duration: 0.1 }, 0.34)
    } else if (part.name === 'icon' || part.name === 'title') {
      const x = rect.left - part.rect.left
      const y = rect.top - part.rect.top
      const targetFontSize = parseFloat(getComputedStyle(target).fontSize) || part.fontSize
      const scale = part.name === 'title' ? targetFontSize / part.fontSize : 1
      gsap.set(target, { autoAlpha: 0 })
      timeline.to(part.clone, { x, y, scale, duration: 0.45 }, 0)
        .to(part.clone, { autoAlpha: 0, duration: 0.12 }, 0.33)
        .to(target, { autoAlpha: 1, duration: 0.12 }, 0.33)
    } else {
      const x = rect.left - part.rect.left
      const y = rect.top - part.rect.top
      gsap.set(target, { autoAlpha: 0, y: part.name === 'category' ? 4 : 8 })
      timeline.to(part.clone, { x, y, autoAlpha: 0, duration: 0.32 }, 0)
        .to(target, { autoAlpha: 1, y: 0, duration: 0.26, ease: 'power2.out' }, part.name === 'category' ? 0.16 : 0.19)
    }
  }

  if (direction === 'open' && body) {
    gsap.set(body, { autoAlpha: 0, y: 12 })
    timeline.to(body, { autoAlpha: 1, y: 0, duration: 0.28, ease: 'power2.out' }, 0.22)
  }
  return true
}

export function cancelCardTransition() {
  const current = session
  if (!current) return
  session = null
  clearTimeout(current.timeout)
  window.removeEventListener('resize', onResize)
  current.timeline?.kill()
  for (const [element, style] of current.targetStyles) element.style.cssText = style
  for (const part of current.parts) {
    part.source.style.visibility = part.sourceVisibility
    part.clone.remove()
  }
}

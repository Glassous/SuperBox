import { gsap } from 'gsap'
import type { ToolInfo } from '../types'

type Direction = 'open' | 'return'
type PartName = 'icon' | 'title' | 'description' | 'category'
type Parts = Record<PartName, HTMLElement>

const partNames: PartName[] = ['icon', 'title', 'description', 'category']

interface FloatingPart {
  name: PartName
  clone: HTMLElement
  source: HTMLElement
  sourceVisibility: string
  rect: DOMRect
  fontSize: number
}

interface Session {
  direction: Direction
  slug: string
  tool?: ToolInfo
  parts: FloatingPart[]
  targetStyles: Map<HTMLElement, string>
  timeline?: gsap.core.Timeline
  timeout: ReturnType<typeof setTimeout>
}

let host: HTMLElement | null = null
let session: Session | null = null

function findParts(root: HTMLElement): Parts | null {
  const result = {} as Parts
  for (const name of partNames) {
    const element = root.querySelector<HTMLElement>(`[data-tool-transition="${name}"]`)
    if (!element) return null
    result[name] = element
  }
  return result
}

function onResize() {
  cancelToolTransition()
}

export function setToolTransitionHost(element: HTMLElement | null) {
  if (!element) cancelToolTransition()
  host = element
}

export function isPlainNavigation(event: MouseEvent) {
  return event.button === 0 && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.defaultPrevented
}

export function beginToolTransition(direction: Direction, slug: string, root: HTMLElement, tool?: ToolInfo) {
  cancelToolTransition()
  if (!host || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  const sourceParts = findParts(root)
  if (!sourceParts) return

  const parts: FloatingPart[] = partNames.map(name => {
    const source = sourceParts[name]
    const rect = source.getBoundingClientRect()
    const clone = source.cloneNode(true) as HTMLElement
    host!.appendChild(clone)
    gsap.set(clone, {
      position: 'fixed', left: rect.left, top: rect.top,
      width: rect.width, height: rect.height, margin: 0,
      transformOrigin: 'top left', pointerEvents: 'none',
    })
    return {
      name, clone, source, rect,
      sourceVisibility: source.style.visibility,
      fontSize: parseFloat(getComputedStyle(source).fontSize) || 16,
    }
  })

  for (const part of parts) part.source.style.visibility = 'hidden'
  session = {
    direction, slug, tool, parts, targetStyles: new Map(),
    timeout: setTimeout(cancelToolTransition, 6000),
  }
  window.addEventListener('resize', onResize)
}

export function getOpeningTool(slug: string): ToolInfo | null {
  return session?.direction === 'open' && session.slug === slug ? session.tool ?? null : null
}

export function getReturningSlug(): string | null {
  return session?.direction === 'return' ? session.slug : null
}

export function cancelTransitionOutsideRoute(name: unknown, slug: unknown) {
  if (!session) return
  const valid = session.direction === 'open'
    ? name === 'tool' && slug === session.slug
    : name === 'home'
  if (!valid) cancelToolTransition()
}

export function finishToolTransition(direction: Direction, slug: string, root: HTMLElement, body?: HTMLElement | null) {
  const current = session
  if (!current || current.direction !== direction || current.slug !== slug || current.timeline) return
  const targets = findParts(root)
  if (!targets) {
    cancelToolTransition()
    return
  }

  // The router also scrolls to the top; do it before measuring the destination
  // so the first animation frame uses the same coordinates as the final page.
  window.scrollTo(0, 0)

  const remember = (element: HTMLElement) => {
    current.targetStyles.set(element, element.style.cssText)
  }
  for (const name of partNames) remember(targets[name])
  if (direction === 'open' && body) remember(body)

  const timeline = gsap.timeline({
    defaults: { ease: 'power3.inOut' },
    onComplete: () => { if (session === current) cancelToolTransition() },
  })
  current.timeline = timeline

  for (const part of current.parts) {
    const target = targets[part.name]
    const rect = target.getBoundingClientRect()
    const x = rect.left - part.rect.left
    const y = rect.top - part.rect.top

    if (part.name === 'icon' || part.name === 'title') {
      const targetFontSize = parseFloat(getComputedStyle(target).fontSize) || part.fontSize
      const scale = part.name === 'title' ? targetFontSize / part.fontSize : 1
      gsap.set(target, { autoAlpha: 0 })
      timeline.to(part.clone, { x, y, scale, duration: 0.45 }, 0)
        .to(part.clone, { autoAlpha: 0, duration: 0.12 }, 0.33)
        .to(target, { autoAlpha: 1, duration: 0.12 }, 0.33)
    } else {
      gsap.set(target, { autoAlpha: 0, y: part.name === 'category' ? 4 : 8 })
      timeline.to(part.clone, { x, y, autoAlpha: 0, duration: 0.32 }, 0)
        .to(target, { autoAlpha: 1, y: 0, duration: 0.26, ease: 'power2.out' }, part.name === 'category' ? 0.16 : 0.19)
    }
  }

  if (direction === 'open' && body) {
    gsap.set(body, { autoAlpha: 0, y: 12 })
    timeline.to(body, { autoAlpha: 1, y: 0, duration: 0.28, ease: 'power2.out' }, 0.22)
  }
}

export function cancelToolTransition() {
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

import type { AnimationClip } from 'three'

/** 模型关键帧按 30fps 采样（1671 个键覆盖 55.6667s），帧区间同样按 30fps 换算。 */
export const PENGUIN_FPS = 30

export interface PenguinActionMeta {
  index: 0 | 1 | 2
  label: string
  frames: string
  hint: string
  /** 片段起点（秒，含起始帧） */
  start: number
  /** 片段终点（秒，含结束帧） */
  end: number
}

function segment(startFrame: number, endFrame: number) {
  return {
    start: (startFrame - 1) / PENGUIN_FPS,
    end: (endFrame - 1) / PENGUIN_FPS,
  }
}

/**
 * 三段动作共用 `Action` 这一条时间轴，按帧区间定位播放：
 * 播到区间末尾后停止并回到绑定姿态，不做整体循环。
 */
export const PENGUIN_ACTIONS: readonly PenguinActionMeta[] = [
  { index: 0, label: '动作一', frames: '1–63 帧', hint: '开场短动作', ...segment(1, 63) },
  { index: 1, label: '动作二', frames: '70–149 帧', hint: '衔接片段', ...segment(70, 149) },
  { index: 2, label: '动作三', frames: '150–1670 帧', hint: '全身长动作', ...segment(150, 1670) },
]

/** 优先使用名为 Action 的片段，否则退到时长最长的一条。 */
export function resolvePenguinClip(clips: AnimationClip[]): AnimationClip {
  const action = clips.find(clip => clip.name === 'Action')
  if (action) return action
  const longest = clips.reduce<AnimationClip | null>(
    (best, clip) => (!best || clip.duration > best.duration ? clip : best),
    null,
  )
  if (!longest) throw new Error('模型缺少动画片段')
  return longest
}

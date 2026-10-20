import { AnimationClip, AnimationUtils } from 'three'

/**
 * 凑企鹅.glb 的关键帧按 30fps 采样（1671 个键覆盖 55.6667s），
 * 用户给出的帧区间同为 30fps，因此剪辑统一按 30fps 换算。
 */
export const PENGUIN_FPS = 30

const BONE_CLIP = '动作_bone'
const FACIAL_CLIP = '咕咕嘎嘎_facial'
const LONG_CLIP = 'Action'

const LONG_START_FRAME = 150
const LONG_END_FRAME = 1670

export interface PenguinActionMeta {
  index: 0 | 1 | 2
  label: string
  frames: string
  hint: string
}

export const PENGUIN_ACTIONS: readonly PenguinActionMeta[] = [
  { index: 0, label: '动作一', frames: '1–63 帧', hint: '骨骼片段' },
  { index: 1, label: '动作二', frames: '70 帧起', hint: '面部表情' },
  { index: 2, label: '动作三', frames: '150–1670 帧', hint: '全身长动作' },
]

export type PenguinClipSet = [AnimationClip, AnimationClip, AnimationClip]

function findClip(clips: AnimationClip[], name: string): AnimationClip {
  const clip = clips.find(item => item.name === name)
  if (!clip) throw new Error(`模型缺少动画片段：${name}`)
  return clip
}

/**
 * 模型网格高度约 0.42，而骨骼位移轨道把上半身推到 2.19–3.85、根骨推到 -3.59，
 * 量级相差约一个数量级，直接播放会把角色甩出取景。这里只保留旋转轨道，
 * 让动作在原地完成；表情权重轨道名不含 `.position`，不受影响。
 */
function keepRotationTracks(clip: AnimationClip): AnimationClip {
  clip.tracks = clip.tracks.filter(track => !track.name.endsWith('.position'))
  clip.resetDuration()
  return clip
}

/** subclip 会保留原始时间轴，必须整体左移，否则起播前会静止等待。 */
function shiftToZero(clip: AnimationClip): AnimationClip {
  const start = clip.tracks.reduce((earliest, track) => {
    const first = track.times[0]
    return first === undefined ? earliest : Math.min(earliest, first)
  }, Number.POSITIVE_INFINITY)

  if (Number.isFinite(start) && start > 0) {
    for (const track of clip.tracks) track.shift(-start)
  }
  clip.resetDuration()
  return clip
}

/**
 * 三段动作沿用模型自带的片段：
 * 一、动作_bone 全段（第 1–63 帧骨骼动画）
 * 二、咕咕嘎嘎_facial 全段（第 70 帧起的面部表情，骨骼保持绑定姿态）
 * 三、Action 的第 150–1670 帧（末尾关键帧在 1670 帧上，需包含端点）
 */
export function buildPenguinClips(clips: AnimationClip[]): PenguinClipSet {
  const bone = findClip(clips, BONE_CLIP).clone()
  bone.name = 'penguin-action-one'

  const facial = findClip(clips, FACIAL_CLIP).clone()
  facial.name = 'penguin-action-two'

  const long = AnimationUtils.subclip(
    findClip(clips, LONG_CLIP),
    'penguin-action-three',
    LONG_START_FRAME,
    LONG_END_FRAME + 1,
    PENGUIN_FPS,
  )

  return [
    shiftToZero(keepRotationTracks(bone)),
    shiftToZero(facial),
    shiftToZero(keepRotationTracks(long)),
  ]
}

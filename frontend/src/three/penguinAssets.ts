import { PerspectiveCamera, Texture, Vector3 } from 'three'
import type { Material, Mesh, Object3D } from 'three'
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js'

export interface PenguinStageHandlers {
  onProgress: (loaded: number, total: number) => void
  onReady: () => void
  onError: (message: string) => void
  /** 当前片段播放到区间末尾并回到静止姿态后触发。 */
  onSegmentEnd?: () => void
}

export interface PenguinStage {
  play: (index: 0 | 1 | 2) => void
  stop: () => void
  dispose: () => void
}

export const noopStage: PenguinStage = {
  play: () => {},
  stop: () => {},
  dispose: () => {},
}

function disposeMaterial(material: Material): void {
  for (const value of Object.values(material)) {
    if (value instanceof Texture) value.dispose()
  }
  material.dispose()
}

/** 递归释放模型几何、材质与贴图，避免反复打开弹窗时显存累积。 */
export function disposeObject(object: Object3D): void {
  object.traverse(child => {
    const mesh = child as Mesh
    if (!mesh.isMesh) return
    mesh.geometry.dispose()
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
    for (const material of materials) disposeMaterial(material)
  })
}

/** 按模型盒子尺寸贴满取景框（留 4% 边距），并限制轨道控件的缩放范围避免穿模。 */
export function framePenguinCamera(camera: PerspectiveCamera, controls: OrbitControls, size: Vector3): void {
  const verticalFov = (camera.fov * Math.PI) / 180
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect)
  const halfHeight = Math.max(size.y / 2, 0.01)
  const halfWidth = Math.max(size.x / 2, 0.01)
  const distance = Math.max(
    halfHeight / Math.tan(verticalFov / 2),
    halfWidth / Math.tan(horizontalFov / 2),
  ) * 1.04
  const direction = new Vector3(0.18, 0.12, 1).normalize()
  camera.position.copy(direction.multiplyScalar(distance))
  camera.near = Math.max(distance / 120, 0.01)
  camera.far = distance * 12
  camera.updateProjectionMatrix()
  controls.target.set(0, 0, 0)
  controls.minDistance = distance * 0.45
  controls.maxDistance = distance * 2.4
  controls.update()
}

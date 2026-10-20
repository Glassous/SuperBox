import {
  CanvasTexture,
  PerspectiveCamera,
  SRGBColorSpace,
  Texture,
  Vector3,
} from 'three'
import type { Material, Mesh, Object3D } from 'three'
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js'

export interface PenguinStageHandlers {
  onProgress: (loaded: number, total: number) => void
  onReady: () => void
  onError: (message: string) => void
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

/** 展台底部的靛蓝光晕，用程序化径向渐变代替真实阴影，避免阴影贴图的额外开销。 */
export function createGlowTexture(): CanvasTexture {
  const size = 256
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const context = canvas.getContext('2d')
  if (context) {
    const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
    gradient.addColorStop(0, 'rgba(129, 140, 248, 0.55)')
    gradient.addColorStop(0.4, 'rgba(79, 70, 229, 0.2)')
    gradient.addColorStop(1, 'rgba(79, 70, 229, 0)')
    context.fillStyle = gradient
    context.fillRect(0, 0, size, size)
  }
  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  return texture
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

/** 按包围球半径与相机视锥自动取景，同时限制轨道控件的缩放范围避免穿模。 */
export function framePenguinCamera(camera: PerspectiveCamera, controls: OrbitControls, radius: number): void {
  const verticalFov = (camera.fov * Math.PI) / 180
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect)
  const distance = (radius / Math.sin(Math.min(verticalFov, horizontalFov) / 2)) * 1.12
  const direction = new Vector3(0.36, 0.22, 1).normalize()
  camera.position.copy(direction.multiplyScalar(distance))
  camera.near = Math.max(distance / 120, 0.01)
  camera.far = distance * 12
  camera.updateProjectionMatrix()
  controls.target.set(0, 0, 0)
  controls.minDistance = distance * 0.4
  controls.maxDistance = distance * 2.6
  controls.update()
}

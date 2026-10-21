import {
  ACESFilmicToneMapping,
  AnimationMixer,
  Box3,
  DirectionalLight,
  Group,
  HemisphereLight,
  LoopOnce,
  Mesh,
  PerspectiveCamera,
  PMREMGenerator,
  SRGBColorSpace,
  Scene,
  Timer,
  Vector3,
  WebGLRenderer,
} from 'three'
import type { AnimationAction, AnimationClip, Bone, Object3D, Quaternion } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { PENGUIN_ACTIONS, resolvePenguinClip } from './penguinClips'
import { disposeObject, framePenguinCamera, noopStage } from './penguinAssets'
import type { PenguinStage, PenguinStageHandlers } from './penguinAssets'

export type { PenguinStage, PenguinStageHandlers } from './penguinAssets'

/**
 * 挂件舞台：负责渲染器、取景、灯光、控件与模型生命周期。
 * 渲染按需进行，页面不可见或离开视口时暂停动画帧，避免嵌入页面常驻占用 GPU。
 */
export function createPenguinStage(
  host: HTMLElement,
  modelUrl: string,
  handlers: PenguinStageHandlers,
): PenguinStage {
  const canvas = document.createElement('canvas')
  Object.assign(canvas.style, { display: 'block', width: '100%', height: '100%', touchAction: 'none' })
  const context = canvas.getContext('webgl2') ?? canvas.getContext('webgl')
  if (!context) {
    handlers.onError('当前浏览器不支持 WebGL，无法显示 3D 模型')
    return noopStage
  }

  const renderer = new WebGLRenderer({
    canvas,
    context: context as WebGLRenderingContext,
    antialias: true,
    alpha: true,
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.outputColorSpace = SRGBColorSpace
  renderer.toneMapping = ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.08
  renderer.setClearColor(0x000000, 0)
  host.appendChild(canvas)

  const scene = new Scene()
  const camera = new PerspectiveCamera(34, 1, 0.05, 200)
  camera.position.set(0, 0.4, 5)

  const controls = new OrbitControls(camera, canvas)
  controls.enableDamping = true
  controls.dampingFactor = 0.07
  controls.enablePan = false
  controls.rotateSpeed = 0.85
  controls.zoomSpeed = 0.8
  controls.minPolarAngle = Math.PI * 0.12
  controls.maxPolarAngle = Math.PI * 0.58

  const hemisphere = new HemisphereLight(0xc7d7ff, 0x0a0f1f, 1.15)
  const keyLight = new DirectionalLight(0xffffff, 2.6)
  keyLight.position.set(3.2, 5.4, 4.2)
  const rimLight = new DirectionalLight(0x818cf8, 2.1)
  rimLight.position.set(-3.6, 2.4, -3.4)
  const fillLight = new DirectionalLight(0x93c5fd, 0.75)
  fillLight.position.set(-2.4, 1.2, 3.2)
  scene.add(hemisphere, keyLight, rimLight, fillLight)

  const pmrem = new PMREMGenerator(renderer)
  const environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  scene.environment = environment
  scene.environmentIntensity = 0.5
  pmrem.dispose()

  const root = new Group()
  scene.add(root)

  let mixer: AnimationMixer | null = null
  let action: AnimationAction | null = null
  let model: Object3D | null = null
  let restPose: { bone: Bone; position: Vector3; quaternion: Quaternion; scale: Vector3 }[] = []
  let activeIndex = -1
  let playing = false
  let frame = 0
  let running = false
  let needsRender = true
  let disposed = false
  const timer = new Timer()
  timer.connect(document)

  function resize(): void {
    const width = Math.max(host.clientWidth, 1)
    const height = Math.max(host.clientHeight, 1)
    renderer.setSize(width, height, false)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    needsRender = true
  }
  function tick(): void {
    if (disposed) return
    frame = requestAnimationFrame(tick)
    timer.update()
    const delta = Math.min(timer.getDelta(), 0.05)
    if (playing && mixer) {
      mixer.update(delta)
      const segment = activeIndex >= 0 ? PENGUIN_ACTIONS[activeIndex] : undefined
      if (action && segment && action.time >= segment.end - 1e-4) finishSegment()
      needsRender = true
    }
    controls.update()
    if (needsRender) {
      needsRender = false
      renderer.render(scene, camera)
    }
  }

  function startLoop(): void {
    if (running || disposed) return
    running = true
    timer.update()
    frame = requestAnimationFrame(tick)
  }
  function stopLoop(): void {
    if (!running) return
    running = false
    cancelAnimationFrame(frame)
  }
  function setupModel(source: Object3D, clips: AnimationClip[]): void {
    model = source
    const bones: Bone[] = []

    source.traverse(child => {
      const mesh = child as Mesh
      if (mesh.isMesh) mesh.frustumCulled = false
      if ((child as Bone).isBone) bones.push(child as Bone)
    })
    restPose = bones.map(bone => ({
      bone,
      position: bone.position.clone(),
      quaternion: bone.quaternion.clone(),
      scale: bone.scale.clone(),
    }))

    root.add(source)
    const bounds = new Box3().setFromObject(source)
    const size = bounds.getSize(new Vector3())
    const center = bounds.getCenter(new Vector3())
    source.position.sub(center)

    mixer = new AnimationMixer(source)
    action = mixer.clipAction(resolvePenguinClip(clips))
    action.clampWhenFinished = true

    resize()
    framePenguinCamera(camera, controls, size)
    controls.addEventListener('change', requestRender)
    needsRender = true
    handlers.onReady()
    startLoop()
  }

  function requestRender(): void {
    needsRender = true
  }

  function loadModel(): void {
    const loader = new GLTFLoader()
    loader.load(
      modelUrl,
      gltf => {
        if (disposed) return
        try {
          setupModel(gltf.scene, gltf.animations)
        } catch (cause) {
          console.error(cause)
          handlers.onError(cause instanceof Error ? cause.message : '模型解析失败')
        }
      },
      event => {
        if (disposed) return
        handlers.onProgress(event.loaded, event.total)
      },
      cause => {
        if (disposed) return
        console.error(cause)
        handlers.onError('模型加载失败，请检查网络后重试')
      },
    )
  }

  /** 与 GlLab 的 v1.0 处理一致：定位到片段起点、只播一次，播完回到绑定姿态。 */
  function play(index: 0 | 1 | 2): void {
    const segment = PENGUIN_ACTIONS[index]
    if (!mixer || !action || !segment) return
    action.stop()
    action.reset()
    action.setLoop(LoopOnce, 1)
    action.clampWhenFinished = true
    action.play()
    action.time = segment.start
    mixer.update(0)
    activeIndex = index
    playing = true
    needsRender = true
    startLoop()
  }
  function resetPose(): void {
    for (const pose of restPose) {
      pose.bone.position.copy(pose.position)
      pose.bone.quaternion.copy(pose.quaternion)
      pose.bone.scale.copy(pose.scale)
    }
  }
  function finishSegment(): void {
    if (!playing) return
    action?.stop()
    resetPose()
    playing = false
    activeIndex = -1
    needsRender = true
    handlers.onSegmentEnd?.()
  }
  function stop(): void {
    finishSegment()
  }
  function dispose(): void {
    if (disposed) return
    disposed = true
    stopLoop()
    resizeObserver.disconnect()
    intersectionObserver.disconnect()
    document.removeEventListener('visibilitychange', onVisibilityChange)
    controls.removeEventListener('change', requestRender)
    controls.dispose()
    timer.disconnect()
    mixer?.stopAllAction()
    if (mixer && model) mixer.uncacheRoot(model)
    disposeObject(root)
    environment.dispose()
    renderer.dispose()
    canvas.remove()
  }

  function onVisibilityChange(): void {
    if (document.hidden) stopLoop()
    else startLoop()
  }

  const resizeObserver = new ResizeObserver(() => {
    resize()
    if (!playing) needsRender = true
    startLoop()
  })
  resizeObserver.observe(host)

  const intersectionObserver = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) startLoop()
    else stopLoop()
  }, { threshold: 0.01 })
  intersectionObserver.observe(host)

  document.addEventListener('visibilitychange', onVisibilityChange)
  resize()
  startLoop()
  loadModel()

  return { play, stop, dispose }
}

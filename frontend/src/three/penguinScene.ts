import {
  ACESFilmicToneMapping,
  AdditiveBlending,
  AnimationMixer,
  Box3,
  CircleGeometry,
  DirectionalLight,
  Group,
  HemisphereLight,
  LoopRepeat,
  Mesh,
  MeshBasicMaterial,
  PerspectiveCamera,
  PMREMGenerator,
  SRGBColorSpace,
  Scene,
  SkinnedMesh,
  Timer,
  Vector3,
  WebGLRenderer,
} from 'three'
import type { AnimationAction, AnimationClip, Object3D } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { buildPenguinClips } from './penguinClips'
import { createGlowTexture, disposeObject, framePenguinCamera, noopStage } from './penguinAssets'
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

  const glowTexture = createGlowTexture()
  const glowMaterial = new MeshBasicMaterial({
    map: glowTexture,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
    opacity: 0.85,
  })
  const glow = new Mesh(new CircleGeometry(1, 64), glowMaterial)
  glow.rotation.x = -Math.PI / 2
  glow.visible = false
  root.add(glow)

  let mixer: AnimationMixer | null = null
  let actions: AnimationAction[] = []
  let model: Object3D | null = null
  let skinnedMeshes: SkinnedMesh[] = []
  let morphMeshes: Mesh[] = []
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
    skinnedMeshes = []
    morphMeshes = []

    source.traverse(child => {
      const mesh = child as Mesh
      if (!mesh.isMesh) return
      mesh.frustumCulled = false
      if ((mesh as SkinnedMesh).isSkinnedMesh) skinnedMeshes.push(mesh as SkinnedMesh)
      if (mesh.morphTargetInfluences?.length) morphMeshes.push(mesh)
    })

    root.add(source)
    const bounds = new Box3().setFromObject(source)
    const size = bounds.getSize(new Vector3())
    const center = bounds.getCenter(new Vector3())
    source.position.sub(center)

    const radius = Math.max(size.length() * 0.5, 0.4)
    glow.scale.setScalar(radius * 1.7)
    glow.position.set(0, -size.y * 0.5 - radius * 0.02, 0)
    glow.visible = true

    mixer = new AnimationMixer(source)
    actions = buildPenguinClips(clips).map(clip => {
      const action = mixer!.clipAction(clip)
      action.setLoop(LoopRepeat, Number.POSITIVE_INFINITY)
      action.clampWhenFinished = false
      return action
    })

    resize()
    framePenguinCamera(camera, controls, radius)
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

  function play(index: 0 | 1 | 2): void {
    if (!mixer) return
    const next = actions[index]
    if (!next) return
    for (const action of actions) {
      if (action !== next && action.isRunning()) action.fadeOut(0.18)
    }
    next.reset()
    next.setEffectiveTimeScale(1)
    next.setEffectiveWeight(1)
    next.fadeIn(0.18)
    next.play()
    // 表情片段只驱动 morph 轨道，切换回骨骼动作时需要把表情复位。
    if (index !== 1) {
      for (const mesh of morphMeshes) mesh.morphTargetInfluences?.fill(0)
    }
    playing = true
    needsRender = true
    startLoop()
  }

  function stop(): void {
    if (!mixer) return
    mixer.stopAllAction()
    mixer.setTime(0)
    for (const skinned of skinnedMeshes) skinned.skeleton.pose()
    for (const mesh of morphMeshes) mesh.morphTargetInfluences?.fill(0)
    playing = false
    needsRender = true
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
    glowTexture.dispose()
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

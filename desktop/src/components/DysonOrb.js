/**
 * ASTRA — Esfera de Dyson con Babylon.js
 * 
 * Orbe 3D con:
 * - 7 anillos toroidales en ejes diferentes (giroscopio)
 * - Bloom/glow real (post-processing)
 * - Partículas GPU
 * - Pulsos de energía
 * - Reacciona a estados: idle, thinking, speaking
 */
import * as BABYLON from 'babylonjs'

export function initBabylonScene(canvas) {
  const engine = new BABYLON.Engine(canvas, true, { preserveDrawingBuffer: true, stencil: true })
  const scene = new BABYLON.Scene(engine)
  scene.clearColor = new BABYLON.Color4(0.012, 0.024, 0.032, 1)

  // Camera
  const camera = new BABYLON.ArcRotateCamera('cam', Math.PI/2, Math.PI/2, 6, BABYLON.Vector3.Zero(), scene)
  camera.lowerRadiusLimit = 4
  camera.upperRadiusLimit = 10
  camera.attachControl(canvas, true)
  camera.inputs.attached.pointers.buttons = [0] // solo click izquierdo para rotar

  // === NÚCLEO CENTRAL ===
  const core = BABYLON.MeshBuilder.CreateSphere('core', { diameter: 0.6, segments: 64 }, scene)
  const coreMat = new BABYLON.StandardMaterial('coreMat', scene)
  coreMat.emissiveColor = new BABYLON.Color3(0.31, 0.76, 0.97)
  coreMat.diffuseColor = new BABYLON.Color3(0.1, 0.3, 0.5)
  coreMat.alpha = 0.8
  core.material = coreMat

  // Núcleo interior brillante
  const innerCore = BABYLON.MeshBuilder.CreateSphere('innerCore', { diameter: 0.25, segments: 32 }, scene)
  const innerMat = new BABYLON.StandardMaterial('innerMat', scene)
  innerMat.emissiveColor = new BABYLON.Color3(0.88, 0.96, 1.0)
  innerMat.alpha = 0.9
  innerCore.material = innerMat

  // Glow exterior
  const glowSphere = BABYLON.MeshBuilder.CreateSphere('glow', { diameter: 0.9, segments: 32 }, scene)
  const glowMat = new BABYLON.StandardMaterial('glowMat', scene)
  glowMat.emissiveColor = new BABYLON.Color3(0.31, 0.76, 0.97)
  glowMat.alpha = 0.06
  glowSphere.material = glowMat

  // === ANILLOS ESFERA DE DYSON ===
  const ringConfigs = [
    { radius: 1.0, tube: 0.015, axis: new BABYLON.Vector3(1, 0, 0), speed: 0.008, dir: 1 },
    { radius: 1.2, tube: 0.012, axis: new BABYLON.Vector3(0, 1, 0), speed: 0.012, dir: -1 },
    { radius: 1.4, tube: 0.010, axis: new BABYLON.Vector3(0.7, 0.7, 0).normalize(), speed: 0.006, dir: 1 },
    { radius: 1.6, tube: 0.013, axis: new BABYLON.Vector3(0, 0.5, 1).normalize(), speed: 0.010, dir: -1 },
    { radius: 1.8, tube: 0.008, axis: new BABYLON.Vector3(1, 0, 0.7).normalize(), speed: 0.014, dir: 1 },
    { radius: 2.0, tube: 0.011, axis: new BABYLON.Vector3(0.5, 1, 0.3).normalize(), speed: 0.005, dir: -1 },
    { radius: 2.2, tube: 0.007, axis: new BABYLON.Vector3(0.3, 0.7, 1).normalize(), speed: 0.009, dir: 1 },
  ]

  const rings = []
  ringConfigs.forEach((cfg, i) => {
    const torus = BABYLON.MeshBuilder.CreateTorus(`ring${i}`, {
      diameter: cfg.radius * 2,
      thickness: cfg.tube * 2,
      tessellation: 128,
    }, scene)
    const mat = new BABYLON.StandardMaterial(`ringMat${i}`, scene)
    mat.emissiveColor = new BABYLON.Color3(0.31, 0.76, 0.97)
    mat.alpha = 0.2
    mat.wireframe = false
    torus.material = mat
    
    // Orientación inicial
    torus.rotationQuaternion = BABYLON.Quaternion.RotationAxis(cfg.axis, Math.random() * Math.PI * 2)
    
    rings.push({ mesh: torus, ...cfg })
  })

  // === PARTÍCULAS ===
  const particleSystem = new BABYLON.ParticleSystem('particles', 500, scene)
  particleSystem.particleTexture = new BABYLON.Texture('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAKElEQVQYV2P8////fwYkwMjIyIjMZkJmMCHTGJFNYERxA6oJjOgmAACDYAkRU1xWKQAAAABJRU5ErkJggg==', scene)
  particleSystem.emitter = BABYLON.Vector3.Zero()
  particleSystem.minEmitBox = new BABYLON.Vector3(-3, -3, -3)
  particleSystem.maxEmitBox = new BABYLON.Vector3(3, 3, 3)
  particleSystem.color1 = new BABYLON.Color4(0.31, 0.76, 0.97, 0.5)
  particleSystem.color2 = new BABYLON.Color4(0.5, 0.87, 0.93, 0.3)
  particleSystem.minSize = 0.02
  particleSystem.maxSize = 0.05
  particleSystem.minLifeTime = 3
  particleSystem.maxLifeTime = 8
  particleSystem.emitRate = 30
  particleSystem.gravity = new BABYLON.Vector3(0, 0, 0)
  particleSystem.minEmitPower = 0.01
  particleSystem.maxEmitPower = 0.05
  particleSystem.start()

  // === BLOOM (Glow Layer) ===
  const gl = new BABYLON.GlowLayer('glow', scene, { mainTextureSamples: 4 })
  gl.intensity = 0.6

  // === ESTADO Y ANIMACIÓN ===
  let state = 'idle' // idle, thinking, speaking
  let speedMultiplier = 1
  let targetSpeed = 1
  let glowTarget = 0.6

  scene.registerBeforeRender(() => {
    const t = performance.now() * 0.001
    
    // Suavizar velocidad
    speedMultiplier += (targetSpeed - speedMultiplier) * 0.02
    gl.intensity += (glowTarget - gl.intensity) * 0.02

    // Anillos Dyson: rotar en sus propios ejes
    rings.forEach((ring, i) => {
      const speed = ring.speed * speedMultiplier * ring.dir
      const wobble = Math.sin(t * 0.3 + i) * 0.0005
      const rotQuat = BABYLON.Quaternion.RotationAxis(ring.axis, speed + wobble)
      ring.mesh.rotationQuaternion = ring.mesh.rotationQuaternion.multiply(rotQuat)
      ring.mesh.material.alpha = 0.15 + (speedMultiplier > 3 ? 0.15 : 0)
    })

    // Núcleo pulsa
    const pulse = 1 + Math.sin(t * 2) * 0.03 * speedMultiplier
    core.scaling.set(pulse, pulse, pulse)
    coreMat.emissiveColor = new BABYLON.Color3(
      0.31 + Math.sin(t) * 0.05 * speedMultiplier,
      0.76,
      0.97
    )

    // Partículas más activas al pensar/hablar
    particleSystem.emitRate = 30 + speedMultiplier * 20
    particleSystem.minEmitPower = 0.01 * speedMultiplier
    particleSystem.maxEmitPower = 0.05 * speedMultiplier
  })

  // Render loop
  engine.runRenderLoop(() => scene.render())
  window.addEventListener('resize', () => engine.resize())

  // API pública
  return {
    setState(newState) {
      state = newState
      switch(newState) {
        case 'thinking':
          targetSpeed = 8  // MUY rápido cuando piensa
          glowTarget = 1.0
          break
        case 'speaking':
          targetSpeed = 3  // Rápido al hablar
          glowTarget = 1.2
          break
        case 'idle':
        default:
          targetSpeed = 1  // Suave cuando idle
          glowTarget = 0.6
          break
      }
    },
    getState() { return state },
    dispose() { engine.dispose() }
  }
}

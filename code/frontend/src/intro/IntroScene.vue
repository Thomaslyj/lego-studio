<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as THREE from 'three'
import * as CANNON from 'cannon-es'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { makePiece, disposePieces } from './pieces.js'
import legoLogo from '../assets/lego-logo.svg'

const emit = defineEmits(['enter'])
const canvasBox = ref(null)
const done = ref(false)
const leaving = ref(false)

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const SPAWN_SECONDS = 3.2
const SETTLE_SECONDS = 1.4
const WALL = 2 // 碰撞分组：侧墙

let renderer, scene, camera, world, raf, pmrem
const bodies = []

function enter() {
  if (leaving.value) return
  leaving.value = true
  setTimeout(() => emit('enter'), 380)
}

function onClick() {
  if (done.value) enter()
}
function onKey(e) {
  if (e.key === 'Enter' && done.value) enter()
}

onMounted(() => {
  const el = canvasBox.value
  const w = el.clientWidth, h = el.clientHeight
  const narrow = w < 720

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, narrow ? 1.5 : 2))
  renderer.setSize(w, h)
  renderer.shadowMap.enabled = !narrow
  renderer.shadowMap.type = THREE.PCFShadowMap
  // Neutral 色调映射保留塑料的饱和度，ACES 会把红色和珊瑚色压成粉色
  renderer.toneMapping = THREE.NeutralToneMapping
  renderer.toneMappingExposure = 1
  el.appendChild(renderer.domElement)

  scene = new THREE.Scene()
  pmrem = new THREE.PMREMGenerator(renderer)
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  scene.environmentIntensity = 0.55

  // 相机略高于地面平视，地面位于画面底边
  camera = new THREE.PerspectiveCamera(30, w / h, 0.1, 100)
  camera.position.set(0, 3, 32)
  camera.lookAt(0, 0, 0)
  const halfH = Math.tan(THREE.MathUtils.degToRad(15)) * 32
  const halfW = halfH * camera.aspect
  // 透视下离镜头最近的一层可见宽度最窄，侧墙按这一层收进，零件不会越出左右边缘
  const DEPTH = 3
  const sideX = Math.tan(THREE.MathUtils.degToRad(15)) * (32 - DEPTH) * camera.aspect - 0.3
  const floorY = -halfH + 2

  const sun = new THREE.DirectionalLight('#fff6dc', 2.2)
  sun.position.set(8, 18, 14)
  sun.castShadow = true
  sun.shadow.mapSize.set(1024, 1024)
  Object.assign(sun.shadow.camera, { left: -halfW, right: halfW, top: 10, bottom: -10, near: 1, far: 60 })
  scene.add(sun, new THREE.HemisphereLight('#fff8e0', '#c98f00', 0.6))

  const floor = new THREE.Mesh(new THREE.PlaneGeometry(halfW * 3, 20), new THREE.ShadowMaterial({ opacity: 0.18 }))
  floor.rotation.x = -Math.PI / 2
  floor.position.y = floorY
  floor.receiveShadow = true
  scene.add(floor)

  world = new CANNON.World({ gravity: new CANNON.Vec3(0, -30, 0) })
  world.allowSleep = true
  world.defaultContactMaterial.friction = 0.45
  world.defaultContactMaterial.restitution = 0.28
  const ground = new CANNON.Body({ mass: 0, shape: new CANNON.Plane() })
  ground.quaternion.setFromEuler(-Math.PI / 2, 0, 0)
  ground.position.y = floorY
  world.addBody(ground)
  const wall = (pos, euler) => {
    const b = new CANNON.Body({ mass: 0, shape: new CANNON.Plane(), collisionFilterGroup: WALL })
    b.position.copy(pos)
    b.quaternion.setFromEuler(...euler)
    world.addBody(b)
  }
  wall(new CANNON.Vec3(-sideX, 0, 0), [0, Math.PI / 2, 0]) // 左
  wall(new CANNON.Vec3(sideX, 0, 0), [0, -Math.PI / 2, 0]) // 右：零件进入画面后才启用
  wall(new CANNON.Vec3(0, 0, -DEPTH), [0, 0, 0]) // 后
  wall(new CANNON.Vec3(0, 0, DEPTH), [0, Math.PI, 0]) // 前

  // 堆积高度控制在画面底部约四分之一，中央标志和提示保持清晰
  const total = narrow ? 36 : 72
  const scale = narrow ? 0.8 : 1.0

  function spawn() {
    const { group, shape } = makePiece()
    group.scale.setScalar(scale)
    scaleShape(shape, scale)
    const body = new CANNON.Body({
      mass: 1, shape, linearDamping: 0.05, angularDamping: 0.08,
      sleepSpeedLimit: 0.25, sleepTimeLimit: 0.6,
      collisionFilterGroup: 1, collisionFilterMask: 1, // 先不碰侧墙，从右上角外侧飞入
    })
    body.position.set(halfW + 1.5 + Math.random() * 3, halfH + 2 + Math.random() * 4, (Math.random() - 0.5) * DEPTH)
    body.velocity.set(-(8 + Math.random() * 16), -(2 + Math.random() * 6), (Math.random() - 0.5) * 2)
    body.angularVelocity.set((Math.random() - 0.5) * 12, (Math.random() - 0.5) * 12, (Math.random() - 0.5) * 12)
    body.quaternion.setFromEuler(Math.random() * 6, Math.random() * 6, Math.random() * 6)
    world.addBody(body)
    scene.add(group)
    bodies.push({ body, group, inside: false })
  }

  function sync() {
    for (const b of bodies) {
      if (!b.inside) {
        if (b.body.position.x < sideX - 1.5) {
          b.inside = true
          b.body.collisionFilterMask = 1 | WALL
        } else if (b.body.velocity.x > -6) {
          // 还在画面右侧外时被弹回或停住的零件，继续推入画面，避免卡在右边缘被裁切
          b.body.wakeUp()
          b.body.velocity.x = -6
        }
      }
      b.group.position.copy(b.body.position)
      b.group.quaternion.copy(b.body.quaternion)
    }
  }

  if (reduceMotion) {
    // 减少动态效果：后台算完堆积，只显示最终画面
    for (let i = 0; i < total; i++) spawn()
    bodies.forEach((b, i) => { b.body.position.x -= halfW * 0.4 + (i % 10) * 1.2; b.body.position.y += (i / 10) * 1.5 })
    for (let i = 0; i < 600; i++) { world.step(1 / 60); sync() }
    renderer.render(scene, camera)
    done.value = true
  } else {
    let last = performance.now()
    let elapsed = 0, spawned = 0
    const loop = (now) => {
      const dt = Math.min((now - last) / 1000, 1 / 30)
      last = now
      elapsed += dt
      const target = Math.min(total, Math.floor((elapsed / SPAWN_SECONDS) * total))
      while (spawned < target) { spawn(); spawned++ }
      world.step(1 / 60, dt, 3)
      sync()
      renderer.render(scene, camera)
      if (!done.value && elapsed > SPAWN_SECONDS + SETTLE_SECONDS) done.value = true
      // 全部静止或超时后停止渲染，保留最后一帧
      const settled = spawned === total && bodies.every((b) => b.body.sleepState === CANNON.Body.SLEEPING)
      if (settled || elapsed > 12) return
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
  }

  window.addEventListener('keydown', onKey)
})

function scaleShape(shape, s) {
  if (shape instanceof CANNON.Box) {
    shape.halfExtents.scale(s, shape.halfExtents)
    shape.updateConvexPolyhedronRepresentation()
    shape.updateBoundingSphereRadius()
  } else if (shape instanceof CANNON.ConvexPolyhedron) {
    shape.vertices.forEach((v) => v.scale(s, v))
    shape.updateBoundingSphereRadius()
  }
}

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('keydown', onKey)
  scene?.traverse((o) => { if (o.isMesh && o.geometry?.type === 'PlaneGeometry') o.geometry.dispose() })
  disposePieces()
  scene?.environment?.dispose()
  pmrem?.dispose()
  renderer?.dispose()
  renderer?.domElement.remove()
})
</script>

<template>
  <div class="intro" :class="{ leaving }" @click="onClick">
    <div ref="canvasBox" class="intro-canvas" />
    <img class="intro-logo" :src="legoLogo" alt="LEGO" draggable="false" />
    <p class="intro-hint" :class="{ show: done }" aria-live="polite">
      {{ done ? '点击任意位置进入' : '' }}
      <small v-if="done">或按回车键</small>
    </p>
    <button class="intro-skip" type="button" @click.stop="enter">跳过</button>
  </div>
</template>

<style scoped>
.intro {
  position: fixed; inset: 0; z-index: 100;
  background: radial-gradient(120% 90% at 50% 35%, #ffdb1f 0%, var(--lego-yellow) 55%, #f5c400 100%);
  transition: opacity .38s ease, transform .38s ease;
  user-select: none;
}
.intro.leaving { opacity: 0; transform: scale(1.02); }
.intro-canvas, .intro-canvas :deep(canvas) { position: absolute; inset: 0; width: 100%; height: 100%; }

.intro-logo {
  position: absolute; left: 50%; top: 40%;
  transform: translate(-50%, -50%);
  width: clamp(120px, 16vw, 188px); height: auto; display: block;
  filter: drop-shadow(0 12px 0 rgba(120, 70, 0, .22));
}

.intro-hint {
  position: absolute; left: 50%; top: calc(40% + clamp(84px, 10vw, 120px));
  transform: translate(-50%, 8px);
  margin: 0; text-align: center; white-space: nowrap;
  font: 700 18px/1.4 var(--font-body); color: var(--ink);
  opacity: 0; transition: opacity .4s ease, transform .4s ease;
}
.intro-hint.show {
  opacity: 1; transform: translate(-50%, 0);
  padding: 8px 18px; border-radius: 10px; background: rgba(255, 255, 255, .88);
  box-shadow: 0 3px 0 rgba(160, 120, 0, .35);
}
.intro-hint small { display: block; font-size: 13px; font-weight: 500; color: rgba(27, 27, 27, .65); }

.intro-skip {
  position: absolute; top: 20px; right: 20px;
  padding: 8px 18px; border: 2px solid var(--ink); border-radius: 999px;
  background: rgba(255, 255, 255, .55); color: var(--ink);
  font: 700 14px/1 var(--font-body); cursor: pointer;
}
.intro-skip:hover { background: #fff; }
.intro-skip:focus-visible { outline: 3px solid var(--lego-blue); outline-offset: 2px; }

@media (prefers-reduced-motion: reduce) {
  .intro, .intro-hint { transition: none; }
}
</style>

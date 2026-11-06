// 程序生成的积木与人仔零件：返回 three.js 网格组 + cannon-es 碰撞形状
import * as THREE from 'three'
import * as CANNON from 'cannon-es'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'

export const PALETTE = {
  red: '#C91A09',
  coral: '#D0563F',
  dark: '#4F5559',
  grey: '#A0A5A9',
  white: '#F2F3F2',
  blue: '#0A5CC2',
  head: '#F2C200',
  black: '#1B1B1B',
}

const materials = new Map()
function plastic(color) {
  if (!materials.has(color)) {
    materials.set(color, new THREE.MeshPhysicalMaterial({
      color, roughness: 0.38, metalness: 0, clearcoat: 0.5, clearcoatRoughness: 0.2,
    }))
  }
  return materials.get(color)
}

const STUD = 0.8 // 一个凸点间距
function studGeo(nx, nz, top) {
  const parts = []
  for (let i = 0; i < nx; i++) {
    for (let j = 0; j < nz; j++) {
      const g = new THREE.CylinderGeometry(0.25, 0.25, 0.18, 20)
      g.translate((i - (nx - 1) / 2) * STUD, top + 0.09, (j - (nz - 1) / 2) * STUD)
      parts.push(g)
    }
  }
  return parts
}

function bevelBox(w, h, d) {
  // 轻微收边，让棱角不那么生硬
  const g = new THREE.BoxGeometry(w, h, d, 2, 2, 2)
  const p = g.attributes.position
  const k = 0.04
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i)
    const ex = Math.abs(Math.abs(x) - w / 2) < 1e-4, ey = Math.abs(Math.abs(y) - h / 2) < 1e-4, ez = Math.abs(Math.abs(z) - d / 2) < 1e-4
    if ((ex && ey) || (ey && ez) || (ex && ez)) {
      p.setXYZ(i, x - Math.sign(x) * k * (ex ? 1 : 0), y - Math.sign(y) * k * (ey ? 1 : 0), z - Math.sign(z) * k * (ez ? 1 : 0))
    }
  }
  g.computeVertexNormals()
  return g
}

// 每类几何体只生成一次
const geoCache = {}
function cached(key, build) {
  if (!geoCache[key]) geoCache[key] = build()
  return geoCache[key]
}

function brickGeo(nx, nz) {
  return cached(`brick${nx}x${nz}`, () => {
    const w = nx * STUD, d = nz * STUD, h = 0.96
    return mergeGeometries([bevelBox(w, h, d), ...studGeo(nx, nz, h / 2)])
  })
}

function headGeo() {
  return cached('head', () => {
    const pts = [[0, -0.5], [0.42, -0.5], [0.55, -0.42], [0.6, -0.28], [0.6, 0.28], [0.55, 0.42], [0.42, 0.5], [0, 0.5]]
      .map(([x, y]) => new THREE.Vector2(x, y))
    const head = new THREE.LatheGeometry(pts, 28)
    const top = new THREE.CylinderGeometry(0.3, 0.3, 0.22, 20); top.translate(0, 0.6, 0)
    const neck = new THREE.CylinderGeometry(0.28, 0.28, 0.14, 20); neck.translate(0, -0.56, 0)
    return mergeGeometries([head, top, neck].map((g) => g.toNonIndexed()))
  })
}

function torsoGeo() {
  return cached('torso', () => {
    const g = new THREE.BoxGeometry(1.5, 1.3, 0.75)
    const p = g.attributes.position
    for (let i = 0; i < p.count; i++) if (p.getY(i) > 0) p.setX(i, p.getX(i) * 0.72)
    g.computeVertexNormals()
    const neck = new THREE.CylinderGeometry(0.26, 0.26, 0.2, 18); neck.translate(0, 0.75, 0)
    return mergeGeometries([g.toNonIndexed(), neck.toNonIndexed()])
  })
}

function legsGeo() {
  return cached('legs', () => {
    const hip = bevelBox(1.5, 0.36, 0.75); hip.translate(0, 0.62, 0)
    const l = bevelBox(0.7, 1.0, 0.75); l.translate(-0.38, -0.06, 0)
    const r = bevelBox(0.7, 1.0, 0.75); r.translate(0.38, -0.06, 0)
    const fl = bevelBox(0.7, 0.24, 0.95); fl.translate(-0.38, -0.66, 0.1)
    const fr = bevelBox(0.7, 0.24, 0.95); fr.translate(0.38, -0.66, 0.1)
    return mergeGeometries([hip, l, r, fl, fr].map((g) => g.toNonIndexed()))
  })
}

function armGeo() {
  return cached('arm', () => {
    const upper = new THREE.CylinderGeometry(0.24, 0.28, 0.9, 16); upper.rotateZ(0.35); upper.translate(0.1, 0.25, 0)
    const shoulder = new THREE.SphereGeometry(0.3, 16, 12); shoulder.translate(0.25, 0.65, 0)
    return mergeGeometries([upper, shoulder].map((g) => g.toNonIndexed()))
  })
}

function handGeo() {
  return cached('hand', () => {
    const g = new THREE.TorusGeometry(0.2, 0.09, 10, 18, Math.PI * 1.45)
    g.rotateY(Math.PI / 2); g.translate(-0.08, -0.33, 0)
    return g
  })
}

function eyeGeo() {
  return cached('eye', () => new THREE.SphereGeometry(0.06, 10, 8))
}

const pick = (arr) => arr[Math.floor(Math.random() * arr.length)]

// 类型权重：人仔零件为主，配少量普通积木
const TYPES = ['head', 'head', 'torso', 'torso', 'legs', 'legs', 'arm', 'arm', 'brick2x2', 'brick2x4', 'brick1x2']

export function makePiece() {
  const type = pick(TYPES)
  const group = new THREE.Group()
  let shape
  const add = (geo, color) => {
    const m = new THREE.Mesh(geo, plastic(color))
    m.castShadow = true
    group.add(m)
    return m
  }
  if (type === 'head') {
    add(headGeo(), pick([PALETTE.head, PALETTE.head, PALETTE.coral, PALETTE.grey]))
    for (const x of [-0.2, 0.2]) {
      const e = add(eyeGeo(), PALETTE.black)
      e.position.set(x, 0.1, 0.57)
      e.castShadow = false
    }
    const smile = new THREE.Mesh(cached('smile', () => new THREE.TorusGeometry(0.2, 0.03, 6, 12, Math.PI)), plastic(PALETTE.black))
    smile.rotation.z = Math.PI; smile.position.set(0, -0.08, 0.57)
    group.add(smile)
    shape = new CANNON.Cylinder(0.6, 0.6, 1.3, 10)
  } else if (type === 'torso') {
    add(torsoGeo(), pick([PALETTE.red, PALETTE.dark, PALETTE.coral, PALETTE.blue, PALETTE.white]))
    shape = new CANNON.Box(new CANNON.Vec3(0.68, 0.72, 0.38))
  } else if (type === 'legs') {
    add(legsGeo(), pick([PALETTE.dark, PALETTE.grey, PALETTE.blue, PALETTE.coral]))
    shape = new CANNON.Box(new CANNON.Vec3(0.75, 0.8, 0.45))
  } else if (type === 'arm') {
    const color = pick([PALETTE.red, PALETTE.coral, PALETTE.dark, PALETTE.white])
    add(armGeo(), color)
    add(handGeo(), pick([PALETTE.head, PALETTE.grey]))
    shape = new CANNON.Box(new CANNON.Vec3(0.32, 0.55, 0.3))
  } else {
    const [nx, nz] = type === 'brick2x2' ? [2, 2] : type === 'brick2x4' ? [2, 4] : [1, 2]
    add(brickGeo(nx, nz), pick([PALETTE.red, PALETTE.white, PALETTE.blue, PALETTE.dark, PALETTE.coral]))
    shape = new CANNON.Box(new CANNON.Vec3(nx * STUD / 2, 0.57, nz * STUD / 2))
  }
  return { group, shape }
}

export function disposePieces() {
  for (const g of Object.values(geoCache)) g.dispose()
  for (const m of materials.values()) m.dispose()
  for (const k of Object.keys(geoCache)) delete geoCache[k]
  materials.clear()
}

import { useMemo, useState, useCallback, useEffect, useRef } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls, Html } from '@react-three/drei'
import { ConvexGeometry } from 'three/examples/jsm/geometries/ConvexGeometry.js'
import * as THREE from 'three'
import { Circle, Box, Eye, EyeOff, RotateCcw, Camera, Tag, RotateCw, Layers, Grid3x3, Info } from 'lucide-react'
import { ELEMENT_COLORS, ELEMENT_INFO, METAL_ELEMENTS, VDW_RADII, ANION_ELEMENTS, COORDINATION_COLORS } from './elementData'
import type { Atom, Lattice } from '../../types'

type DisplayMode = 'ball-stick' | 'space-filling' | 'wireframe' | 'polyhedral' | 'unit-cell' | 'polyhedral-only' | 'atoms-only'

interface CrystalViewerProps {
  atoms: Atom[]
  lattice: Lattice
  className?: string
  showBonds?: boolean
  bondCutoff?: number
  initialMode?: DisplayMode
  supercell?: [number, number, number]
  showElementInfo?: boolean
  showLatticeParams?: boolean
}

function latticeMatrix(a: number, b: number, c: number, alpha: number, beta: number, gamma: number): THREE.Matrix4 {
  const toRad = Math.PI / 180
  const ar = alpha * toRad, br = beta * toRad, gr = gamma * toRad
  const cosA = Math.cos(ar), cosB = Math.cos(br), cosG = Math.cos(gr)
  const sinG = Math.sin(gr)
  const ax = a
  const ay = 0
  const az = 0
  const bx = b * cosG
  const by = b * sinG
  const bz = 0
  const cx = c * cosB
  const cy = c * (cosA - cosB * cosG) / sinG
  const cz = c * Math.sqrt(Math.max(0, 1 - cosB * cosB - ((cosA - cosB * cosG) / sinG) ** 2))
  return new THREE.Matrix4().set(
    ax, bx, cx, 0,
    ay, by, cy, 0,
    az, bz, cz, 0,
    0, 0, 0, 1
  )
}

function getBallStickRadius(element: string): number {
  if (element === 'O' || element === 'F' || element === 'Cl' || element === 'Br' || element === 'I') return 0.25
  if (element === 'H') return 0.15
  if (element === 'B' || element === 'C' || element === 'N' || element === 'S' || element === 'P' || element === 'Si') return 0.3
  if (METAL_ELEMENTS.has(element)) return 0.4
  return 0.3
}

function getSpaceFillingRadius(element: string): number {
  return (VDW_RADII[element] ?? 2.0) * 0.5
}

function getWireframeRadius(element: string): number {
  if (element === 'O' || element === 'F' || element === 'Cl' || element === 'Br' || element === 'I') return 0.1
  if (element === 'H') return 0.06
  if (METAL_ELEMENTS.has(element)) return 0.15
  return 0.1
}

function getBondColor(dist: number, cutoff: number): string {
  if (dist < cutoff * 0.4) return '#ef4444'
  if (dist < cutoff * 0.7) return '#f59e0b'
  return '#6b7280'
}

function getBondThickness(dist: number, cutoff: number): number {
  if (dist < cutoff * 0.5) return 3
  if (dist < cutoff * 0.8) return 2
  return 1
}

function expandToSupercell(atoms: Atom[], supercell: [number, number, number]): Atom[] {
  const [sx, sy, sz] = supercell
  if (sx === 1 && sy === 1 && sz === 1) return atoms

  const expandedAtoms: Atom[] = []
  for (let i = 0; i < sx; i++) {
    for (let j = 0; j < sy; j++) {
      for (let k = 0; k < sz; k++) {
        for (const atom of atoms) {
          expandedAtoms.push({
            ...atom,
            x: (atom.x + i) / sx,
            y: (atom.y + j) / sy,
            z: (atom.z + k) / sz,
          })
        }
      }
    }
  }
  return expandedAtoms
}

function detectCrystalSystem(lattice: Lattice): string {
  const { a, b, c, alpha, beta, gamma } = lattice
  const angleTol = 0.5
  const lenTol = 0.01

  if (Math.abs(alpha - 90) < angleTol && Math.abs(beta - 90) < angleTol && Math.abs(gamma - 90) < angleTol) {
    if (Math.abs(a - b) < lenTol && Math.abs(b - c) < lenTol) return 'cubic'
    if (Math.abs(a - b) > lenTol || Math.abs(b - c) > lenTol) return 'orthorhombic'
    return 'tetragonal'
  }

  if (Math.abs(alpha - 90) < angleTol && Math.abs(beta - 90) < angleTol && Math.abs(gamma - 120) < angleTol) return 'hexagonal'

  if (Math.abs(alpha - 90) < angleTol && Math.abs(gamma - 90) < angleTol && Math.abs(beta - 120) < angleTol) return 'hexagonal'

  return 'monoclinic'
}

interface ElementTooltipProps {
  element: string
  position: { x: number; y: number }
}

function ElementTooltip({ element, position }: ElementTooltipProps) {
  const info = ELEMENT_INFO[element]
  if (!info) return null

  return (
    <div
      className="fixed z-50 bg-gray-900/95 border border-gray-600 rounded-lg p-3 text-white text-xs shadow-xl pointer-events-none"
      style={{
        left: position.x + 15,
        top: position.y - 10,
        minWidth: '160px'
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <div
          className="w-6 h-6 rounded flex items-center justify-center text-xs font-bold"
          style={{ backgroundColor: ELEMENT_COLORS[element] || '#ff69b4', color: getContrastColor(ELEMENT_COLORS[element] || '#ff69b4') }}
        >
          {element}
        </div>
        <span className="font-bold text-base">{element}</span>
      </div>
      <div className="space-y-1 text-gray-300">
        <div className="flex justify-between">
          <span>原子序数:</span>
          <span className="font-mono">{info.atomicNumber}</span>
        </div>
        <div className="flex justify-between">
          <span>原子质量:</span>
          <span className="font-mono">{info.atomicMass.toFixed(3)}</span>
        </div>
        <div className="flex justify-between">
          <span>电负性:</span>
          <span className="font-mono">{info.electronegativity > 0 ? info.electronegativity.toFixed(2) : 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span>类别:</span>
          <span className="font-mono text-cyan-400">{info.category}</span>
        </div>
      </div>
    </div>
  )
}

function getContrastColor(hexColor: string): string {
  const r = parseInt(hexColor.slice(1, 3), 16)
  const g = parseInt(hexColor.slice(3, 5), 16)
  const b = parseInt(hexColor.slice(5, 7), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? '#000000' : '#ffffff'
}





function AtomSphere({ atom, cartesian, radius, onHover, showElementInfo }: {
  atom: Atom
  cartesian: THREE.Vector3
  radius: number
  onHover: (element: string | null, position: THREE.Vector3 | null, screenPos: { x: number; y: number } | null) => void
  showElementInfo: boolean
}) {
  const color = ELEMENT_COLORS[atom.element] || '#ff69b4'
  return (
    <mesh
      position={[cartesian.x, cartesian.y, cartesian.z]}
      onPointerOver={(e) => {
        if (showElementInfo) {
          e.stopPropagation()
          onHover(atom.element, cartesian, { x: e.clientX, y: e.clientY })
        }
      }}
      onPointerOut={() => onHover(null, null, null)}
    >
      <sphereGeometry args={[radius, 32, 32]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.15}
        roughness={0.35}
        metalness={0.5}
      />
    </mesh>
  )
}

function AtomLabel({ atom, cartesian }: { atom: Atom; cartesian: THREE.Vector3 }) {
  const color = ELEMENT_COLORS[atom.element] || '#ff69b4'
  return (
    <Html position={[cartesian.x, cartesian.y + 0.4, cartesian.z]} center distanceFactor={10}>
      <div className="pointer-events-none whitespace-nowrap text-xs font-mono font-bold" style={{ color }}>
        {atom.element}
      </div>
    </Html>
  )
}

function UnitCellWireframe({ matrix, visible }: { matrix: THREE.Matrix4; visible: boolean }) {
  const geometry = useMemo(() => {
    const m = new THREE.Matrix4().copy(matrix)
    const origin = new THREE.Vector3(0, 0, 0)
    const a = new THREE.Vector3(1, 0, 0).applyMatrix4(m)
    const b = new THREE.Vector3(0, 1, 0).applyMatrix4(m)
    const c = new THREE.Vector3(0, 0, 1).applyMatrix4(m)
    const ab = a.clone().add(b)
    const ac = a.clone().add(c)
    const bc = b.clone().add(c)
    const abc = a.clone().add(b).add(c)
    const corners = [origin, a, b, c, ab, ac, bc, abc]
    const edges: [number, number][] = [
      [0, 1], [0, 2], [0, 3],
      [1, 4], [1, 5],
      [2, 4], [2, 6],
      [3, 5], [3, 6],
      [4, 7], [5, 7], [6, 7],
    ]
    const positions: number[] = []
    for (const [i, j] of edges) {
      positions.push(corners[i].x, corners[i].y, corners[i].z)
      positions.push(corners[j].x, corners[j].y, corners[j].z)
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return geo
  }, [matrix])

  if (!visible) return null

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color="#4a5568" transparent opacity={0.6} />
    </lineSegments>
  )
}

function LatticeParameters({ matrix, lattice, visible }: { matrix: THREE.Matrix4; lattice: Lattice; visible: boolean }) {
  if (!visible) return null

  const a = new THREE.Vector3(1, 0, 0).applyMatrix4(matrix)
  const b = new THREE.Vector3(0, 1, 0).applyMatrix4(matrix)
  const c = new THREE.Vector3(0, 0, 1).applyMatrix4(matrix)

  const midA = a.clone().multiplyScalar(0.5)
  const midB = b.clone().multiplyScalar(0.5)
  const midC = c.clone().multiplyScalar(0.5)

  return (
    <>
      <Html position={[midA.x, midA.y + 0.3, midA.z]} center distanceFactor={12}>
        <div className="bg-gray-800/90 border border-gray-600 rounded px-1.5 py-0.5 text-xs text-cyan-400 font-mono whitespace-nowrap">
          a={lattice.a.toFixed(2)}
        </div>
      </Html>
      <Html position={[midB.x, midB.y + 0.3, midB.z]} center distanceFactor={12}>
        <div className="bg-gray-800/90 border border-gray-600 rounded px-1.5 py-0.5 text-xs text-green-400 font-mono whitespace-nowrap">
          b={lattice.b.toFixed(2)}
        </div>
      </Html>
      <Html position={[midC.x, midC.y + 0.3, midC.z]} center distanceFactor={12}>
        <div className="bg-gray-800/90 border border-gray-600 rounded px-1.5 py-0.5 text-xs text-yellow-400 font-mono whitespace-nowrap">
          c={lattice.c.toFixed(2)}
        </div>
      </Html>
    </>
  )
}

function OriginMarker({ visible }: { visible: boolean }) {
  if (!visible) return null

  return (
    <mesh position={[0, 0, 0]}>
      <sphereGeometry args={[0.15, 16, 16]} />
      <meshBasicMaterial color="#ef4444" />
    </mesh>
  )
}

interface BondData {
  start: THREE.Vector3
  end: THREE.Vector3
  dist: number
  color: string
  thickness: number
}

function Bonds({ cartPositions, atoms, cutoff, mode }: {
  cartPositions: THREE.Vector3[]
  atoms: Atom[]
  cutoff: number
  mode: DisplayMode
}) {
  const bondData = useMemo(() => {
    const bonds: BondData[] = []
    for (let i = 0; i < cartPositions.length; i++) {
      for (let j = i + 1; j < cartPositions.length; j++) {
        const dist = cartPositions[i].distanceTo(cartPositions[j])
        if (dist < cutoff) {
          const isMetalO = (METAL_ELEMENTS.has(atoms[i].element) && ANION_ELEMENTS.has(atoms[j].element)) ||
            (METAL_ELEMENTS.has(atoms[j].element) && ANION_ELEMENTS.has(atoms[i].element))
          const isMetalMetal = METAL_ELEMENTS.has(atoms[i].element) && METAL_ELEMENTS.has(atoms[j].element)
          if (isMetalO || (!isMetalMetal && dist < cutoff * 0.85)) {
            bonds.push({
              start: cartPositions[i].clone(),
              end: cartPositions[j].clone(),
              dist,
              color: getBondColor(dist, cutoff),
              thickness: getBondThickness(dist, cutoff),
            })
          }
        }
      }
    }
    return bonds
  }, [cartPositions, atoms, cutoff])

  const geometry = useMemo(() => {
    const positions: number[] = []
    const colors: number[] = []
    bondData.forEach(bond => {
      positions.push(bond.start.x, bond.start.y, bond.start.z)
      positions.push(bond.end.x, bond.end.y, bond.end.z)
      const color = new THREE.Color(bond.color)
      colors.push(color.r, color.g, color.b)
      colors.push(color.r, color.g, color.b)
    })
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    return geo
  }, [bondData])

  if (bondData.length === 0) return null

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial vertexColors transparent opacity={mode === 'wireframe' ? 0.9 : 0.6} linewidth={mode === 'wireframe' ? 2 : 1} />
    </lineSegments>
  )
}

function PolyhedronMesh({ center, neighbors, element, coordination }: {
  center: THREE.Vector3
  neighbors: THREE.Vector3[]
  element: string
  coordination: number
}) {
  const geometry = useMemo(() => {
    const points = neighbors.map(n => n.clone().sub(center))
    if (points.length < 4) return null
    try {
      return new ConvexGeometry(points)
    } catch {
      return null
    }
  }, [center, neighbors])

  if (!geometry) return null

  const color = COORDINATION_COLORS[coordination] || ELEMENT_COLORS[element] || '#ff69b4'

  return (
    <>
      <mesh position={[center.x, center.y, center.z]} geometry={geometry}>
        <meshStandardMaterial color={color} transparent opacity={0.2} side={THREE.DoubleSide} roughness={0.6} metalness={0.2} wireframe={false} />
      </mesh>
      <Html position={[center.x, center.y + 0.6, center.z]} center distanceFactor={10}>
        <div
          className="bg-gray-900/90 border rounded px-1.5 py-0.5 text-xs font-bold text-white whitespace-nowrap pointer-events-none"
          style={{ borderColor: color }}
        >
          CN={coordination}
        </div>
      </Html>
    </>
  )
}

function Polyhedra({ cartPositions, atoms, cutoff, showOnlyMetal }: {
  cartPositions: THREE.Vector3[]
  atoms: Atom[]
  cutoff: number
  showOnlyMetal: boolean
}) {
  const polyhedraData = useMemo(() => {
    const result: { center: THREE.Vector3; neighbors: THREE.Vector3[]; element: string; coordination: number }[] = []
    for (let i = 0; i < atoms.length; i++) {
      if (!METAL_ELEMENTS.has(atoms[i].element)) {
        if (showOnlyMetal) continue
      }
      const neighbors: THREE.Vector3[] = []
      for (let j = 0; j < atoms.length; j++) {
        if (i === j) continue
        if (showOnlyMetal && !ANION_ELEMENTS.has(atoms[j].element)) continue
        const dist = cartPositions[i].distanceTo(cartPositions[j])
        if (dist < cutoff) {
          neighbors.push(cartPositions[j])
        }
      }
      if (neighbors.length >= 3) {
        result.push({ center: cartPositions[i], neighbors, element: atoms[i].element, coordination: neighbors.length })
      }
    }
    return result
  }, [cartPositions, atoms, cutoff, showOnlyMetal])

  return (
    <>
      {polyhedraData.map((poly, i) => (
        <PolyhedronMesh key={i} center={poly.center} neighbors={poly.neighbors} element={poly.element} coordination={poly.coordination} />
      ))}
    </>
  )
}

type CameraView = 'auto' | 'a' | 'b' | 'c'

interface CameraControllerProps {
  latticeMat: THREE.Matrix4
  lattice: Lattice
  resetKey: number
  view: CameraView
}

function CameraController({ latticeMat, lattice, resetKey, view }: CameraControllerProps) {
  const { camera } = useThree()
  const targetRef = useRef(new THREE.Vector3())
  const animatingRef = useRef(false)
  const currentViewRef = useRef(view)

  useEffect(() => {
    currentViewRef.current = view
  }, [view])

  useEffect(() => {
    if (animatingRef.current) return
    animatingRef.current = true

    const a = new THREE.Vector3(1, 0, 0).applyMatrix4(latticeMat)
    const b = new THREE.Vector3(0, 1, 0).applyMatrix4(latticeMat)
    const c = new THREE.Vector3(0, 0, 1).applyMatrix4(latticeMat)
    const center = a.clone().add(b).add(c).multiplyScalar(0.5)
    targetRef.current.copy(center)

    const maxDim = Math.max(a.length(), b.length(), c.length())
    const dist = maxDim * 2.5

    let newPos: THREE.Vector3
    const crystalSystem = detectCrystalSystem(lattice)

    if (view === 'auto' || view === 'a') {
      if (crystalSystem === 'cubic') {
        newPos = new THREE.Vector3(center.x + dist, center.y + dist, center.z + dist)
      } else if (crystalSystem === 'hexagonal') {
        newPos = new THREE.Vector3(center.x + dist, center.y + dist * 0.5, center.z + dist)
      } else {
        newPos = new THREE.Vector3(center.x + dist, center.y + dist * 0.8, center.z + dist * 0.6)
      }
    } else if (view === 'b') {
      newPos = new THREE.Vector3(center.x - dist * 0.5, center.y + dist, center.z + dist * 0.5)
    } else if (view === 'c') {
      newPos = new THREE.Vector3(center.x, center.y, center.z + dist * 1.5)
    } else {
      newPos = new THREE.Vector3(center.x + dist * 0.6, center.y + dist * 0.6, center.z + dist * 0.6)
    }

    const startPos = camera.position.clone()
    const startTime = performance.now()
    const duration = 800

    const animate = () => {
      const elapsed = performance.now() - startTime
      const t = Math.min(elapsed / duration, 1)
      const easeT = 1 - Math.pow(1 - t, 3)

      camera.position.lerpVectors(startPos, newPos, easeT)
      camera.lookAt(center)

      if (t < 1 && currentViewRef.current === view) {
        requestAnimationFrame(animate)
      } else {
        animatingRef.current = false
      }
    }

    animate()
  }, [latticeMat, camera, resetKey, view])

  return null
}

interface CrystalSceneProps {
  atoms: Atom[]
  lattice: Lattice
  mode: DisplayMode
  showBonds: boolean
  showLabels: boolean
  autoRotate: boolean
  bondCutoff: number
  resetKey: number
  supercell: [number, number, number]
  showElementInfo: boolean
  showLatticeParams: boolean
  showUnitCell: boolean
  showOrigin: boolean
  view: CameraView
  polyhedralOnlyMetal: boolean
  onHoverElement?: (element: string | null, screenPos: { x: number; y: number } | null) => void
}

function CrystalScene({
  atoms: originalAtoms,
  lattice,
  mode,
  showBonds,
  showLabels,
  autoRotate,
  bondCutoff,
  resetKey,
  supercell,
  showElementInfo,
  showLatticeParams,
  showUnitCell,
  showOrigin,
  view,
  polyhedralOnlyMetal,
  onHoverElement,
}: CrystalSceneProps) {
  const atoms = useMemo(() => expandToSupercell(originalAtoms, supercell), [originalAtoms, supercell])

  const latticeMat = useMemo(
    () => latticeMatrix(lattice.a * supercell[0], lattice.b * supercell[1], lattice.c * supercell[2], lattice.alpha, lattice.beta, lattice.gamma),
    [lattice, supercell]
  )

  const cartPositions = useMemo(() => {
    return atoms.map((atom) => {
      const frac = new THREE.Vector3(atom.x, atom.y, atom.z)
      return frac.applyMatrix4(latticeMat)
    })
  }, [atoms, latticeMat])

  const handleHover = useCallback((element: string | null, _position: THREE.Vector3 | null, screenPos: { x: number; y: number } | null) => {
    onHoverElement?.(element, screenPos)
  }, [onHoverElement])

  const getRadius = useCallback((atom: Atom) => {
    switch (mode) {
      case 'ball-stick': return getBallStickRadius(atom.element)
      case 'space-filling': return getSpaceFillingRadius(atom.element)
      case 'wireframe': return getWireframeRadius(atom.element)
      case 'polyhedral':
      case 'polyhedral-only':
        return METAL_ELEMENTS.has(atom.element) ? getBallStickRadius(atom.element) : getBallStickRadius(atom.element) * 0.5
      case 'atoms-only': return getBallStickRadius(atom.element)
      default: return getBallStickRadius(atom.element)
    }
  }, [mode])

  const shouldShowAtoms = mode !== 'unit-cell' && mode !== 'polyhedral-only'
  const shouldShowPolyhedra = mode === 'polyhedral' || mode === 'polyhedral-only'

  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 10]} intensity={0.9} />
      <directionalLight position={[-5, -5, -5]} intensity={0.3} />
      <pointLight position={[0, 10, 0]} intensity={0.2} />
      <CameraController latticeMat={latticeMat} lattice={lattice} resetKey={resetKey} view={view} />
      <UnitCellWireframe matrix={latticeMat} visible={showUnitCell} />
      <LatticeParameters matrix={latticeMat} lattice={lattice} visible={showLatticeParams} />
      <OriginMarker visible={showOrigin} />

      {shouldShowPolyhedra && (
        <Polyhedra cartPositions={cartPositions} atoms={atoms} cutoff={bondCutoff} showOnlyMetal={polyhedralOnlyMetal} />
      )}

      {shouldShowAtoms && showBonds && mode !== 'space-filling' && (
        <Bonds cartPositions={cartPositions} atoms={atoms} cutoff={bondCutoff} mode={mode} />
      )}

      {shouldShowAtoms && atoms.map((atom, i) => {
        return (
          <AtomSphere
            key={`${atom.element}-${i}`}
            atom={atom}
            cartesian={cartPositions[i]}
            radius={getRadius(atom)}
            onHover={handleHover}
            showElementInfo={showElementInfo}
          />
        )
      })}

      {showLabels && atoms.map((atom, i) => (
        <AtomLabel key={`label-${atom.element}-${i}`} atom={atom} cartesian={cartPositions[i]} />
      ))}

      <OrbitControls enableDamping dampingFactor={0.1} autoRotate={autoRotate} autoRotateSpeed={2} />
    </>
  )
}

const MODE_OPTIONS: { key: DisplayMode; label: string; icon: typeof Circle }[] = [
  { key: 'ball-stick', label: '球棍', icon: Circle },
  { key: 'space-filling', label: '填充', icon: Circle },
  { key: 'wireframe', label: '线框', icon: Box },
  { key: 'polyhedral', label: '多面体', icon: Layers },
  { key: 'unit-cell', label: '单胞', icon: Grid3x3 },
  { key: 'polyhedral-only', label: '仅金属多面体', icon: Layers },
  { key: 'atoms-only', label: '仅原子', icon: Circle },
]

export default function CrystalViewer({
  atoms,
  lattice,
  className,
  showBonds = true,
  bondCutoff = 2.5,
  initialMode = 'ball-stick',
  supercell: initialSupercell = [1, 1, 1],
  showElementInfo: initialShowElementInfo = true,
  showLatticeParams: initialShowLatticeParams = false,
}: CrystalViewerProps) {
  const [mode, setMode] = useState<DisplayMode>(initialMode)
  const [showBondsState, setShowBondsState] = useState(showBonds)
  const [showLabels, setShowLabels] = useState(false)
  const [autoRotate, setAutoRotate] = useState(false)
  const [resetKey, setResetKey] = useState(0)
  const [supercell, setSupercell] = useState<[number, number, number]>(initialSupercell)
  const [showElementInfo, setShowElementInfo] = useState(initialShowElementInfo)
  const [showLatticeParams, setShowLatticeParams] = useState(initialShowLatticeParams)
  const [showUnitCell, setShowUnitCell] = useState(true)
  const [showOrigin, setShowOrigin] = useState(false)
  const [polyhedralOnlyMetal, setPolyhedralOnlyMetal] = useState(false)
  const [view, setView] = useState<CameraView>('auto')
  const [isLoading, setIsLoading] = useState(true)
  const [hoveredElement, setHoveredElement] = useState<string | null>(null)
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 500)
    return () => clearTimeout(timer)
  }, [])

  const handleExportPng = useCallback(() => {
    const canvas = containerRef.current?.querySelector('canvas')
    if (canvas) {
      const url = canvas.toDataURL('image/png')
      const a = document.createElement('a')
      a.href = url
      a.download = 'crystal-structure.png'
      a.click()
    }
  }, [])

  const handleResetView = useCallback(() => {
    setResetKey(k => k + 1)
    setView('auto')
  }, [])

  const handleViewChange = useCallback((newView: CameraView) => {
    setView(newView)
    setResetKey(k => k + 1)
  }, [])

  const handleSupercellChange = useCallback((sc: [number, number, number]) => {
    setSupercell(sc)
  }, [])

  const handleHoverElement = useCallback((element: string | null, screenPos: { x: number; y: number } | null) => {
    setHoveredElement(element)
    setTooltipPosition(screenPos)
  }, [])

  const btnCls = (active: boolean) =>
    `flex items-center gap-1 px-2 py-1.5 sm:py-1 rounded text-xs font-medium transition-all duration-150 touch-manipulation select-none ${
      active
        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-sm'
        : 'bg-gray-800/80 text-gray-400 border border-gray-700/50 hover:text-gray-200 hover:bg-gray-700/50 active:bg-gray-600/50'
    }`

  const sectionSeparator = <div className="w-px h-5 sm:h-6 bg-gray-700/50 mx-0.5 sm:mx-1 shrink-0" />

  const expandedAtomCount = atoms.length * supercell[0] * supercell[1] * supercell[2]

  return (
    <div ref={containerRef} className={`bg-gray-900 rounded-lg overflow-hidden flex flex-col ${className ?? ''}`}>
      <div className="flex items-center gap-1 px-2 sm:px-3 py-1.5 sm:py-2 bg-gray-950/90 border-b border-gray-800 overflow-x-auto scrollbar-none -webkit-overflow-scrolling-touch">
        <div className="flex items-center gap-1 shrink-0">
          {MODE_OPTIONS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setMode(key)}
              className={btnCls(mode === key)}
              title={label}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {sectionSeparator}

        <div className="flex items-center gap-1 shrink-0">
          {([[1, 1, 1], [2, 2, 2], [3, 3, 3]] as [number, number, number][]).map((sc, i) => {
            const labels = ['1×1×1', '2×2×2', '3×3×3']
            const isActive = supercell[0] === sc[0] && supercell[1] === sc[1] && supercell[2] === sc[2]
            return (
              <button
                key={i}
                onClick={() => handleSupercellChange(sc)}
                className={btnCls(isActive)}
                title={`显示${labels[i]}超晶胞`}
              >
                {labels[i]}
              </button>
            )
          })}
        </div>

        {sectionSeparator}

        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowBondsState(!showBondsState)}
            className={btnCls(showBondsState)}
            title="显示/隐藏键"
          >
            {showBondsState ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">键</span>
          </button>

          <button
            onClick={() => setShowLabels(!showLabels)}
            className={btnCls(showLabels)}
            title="显示/隐藏元素标签"
          >
            <Tag className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">标签</span>
          </button>
        </div>

        {sectionSeparator}

        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowUnitCell(!showUnitCell)}
            className={btnCls(showUnitCell)}
            title="显示/隐藏晶胞"
          >
            <Grid3x3 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">晶胞</span>
          </button>

          <button
            onClick={() => setShowLatticeParams(!showLatticeParams)}
            className={btnCls(showLatticeParams)}
            title="显示/隐藏晶格参数"
          >
            <Info className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">参数</span>
          </button>

          <button
            onClick={() => setShowOrigin(!showOrigin)}
            className={btnCls(showOrigin)}
            title="显示/隐藏原点"
          >
            <Box className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">原点</span>
          </button>

          <button
            onClick={() => setPolyhedralOnlyMetal(!polyhedralOnlyMetal)}
            className={btnCls(polyhedralOnlyMetal)}
            title="仅显示金属多面体"
          >
            <Layers className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">仅金属</span>
          </button>
        </div>

        {sectionSeparator}

        <div className="flex items-center gap-1">
          <button
            onClick={() => handleViewChange('a')}
            className={btnCls(view === 'a')}
            title="沿a轴观看"
          >
            a轴
          </button>

          <button
            onClick={() => handleViewChange('b')}
            className={btnCls(view === 'b')}
            title="沿b轴观看"
          >
            b轴
          </button>

          <button
            onClick={() => handleViewChange('c')}
            className={btnCls(view === 'c')}
            title="沿c轴观看"
          >
            c轴
          </button>
        </div>

        {sectionSeparator}

        <div className="flex items-center gap-1">
          <button
            onClick={() => setAutoRotate(!autoRotate)}
            className={btnCls(autoRotate)}
            title="自动旋转"
          >
            <RotateCw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">旋转</span>
          </button>

          <button
            onClick={() => setShowElementInfo(!showElementInfo)}
            className={btnCls(showElementInfo)}
            title="悬停显示元素信息"
          >
            <Info className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">信息</span>
          </button>

          <button onClick={handleResetView} className={btnCls(false)} title="重置视角">
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">重置</span>
          </button>

          <button onClick={handleExportPng} className={btnCls(false)} title="导出PNG">
            <Camera className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">导出</span>
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-10">
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-gray-400 text-sm">加载中...</span>
            </div>
          </div>
        )}
        <Canvas
          camera={{ position: [5, 5, 5], fov: 50 }}
          gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
        >
          <CrystalScene
            atoms={atoms}
            lattice={lattice}
            mode={mode}
            showBonds={showBondsState}
            showLabels={showLabels}
            autoRotate={autoRotate}
            bondCutoff={bondCutoff}
            resetKey={resetKey}
            supercell={supercell}
            showElementInfo={showElementInfo}
            showLatticeParams={showLatticeParams}
            showUnitCell={showUnitCell}
            showOrigin={showOrigin}
            view={view}
            polyhedralOnlyMetal={polyhedralOnlyMetal}
            onHoverElement={handleHoverElement}
          />
        </Canvas>

        {hoveredElement && tooltipPosition && showElementInfo && (
          <ElementTooltip element={hoveredElement} position={tooltipPosition} />
        )}
      </div>

      <div className="flex items-center justify-between px-2 sm:px-3 py-1 sm:py-1.5 bg-gray-950/80 border-t border-gray-800 text-[10px] sm:text-xs text-gray-500 gap-2">
        <span className="shrink-0">
          原子: {expandedAtomCount} {supercell[0] > 1 || supercell[1] > 1 || supercell[2] > 1 ? `(×${supercell[0]}×${supercell[1]}×${supercell[2]})` : ''}
        </span>
        <span className="truncate text-[9px] sm:text-xs">
          a={lattice.a.toFixed(2)} b={lattice.b.toFixed(2)} c={lattice.c.toFixed(2)} α={lattice.alpha.toFixed(1)}° β={lattice.beta.toFixed(1)}° γ={lattice.gamma.toFixed(1)}°
        </span>
      </div>
    </div>
  )
}

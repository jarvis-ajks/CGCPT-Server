import { WEAS, parseCIF } from 'weas'
import { startMolWeasFrame } from './MolWeasFrameBridge'

interface WeasDisposable {
  dispose: () => void
}

interface WeasMaterial extends WeasDisposable {
  [key: string]: unknown
}

interface WeasScene {
  traverse: (visit: (object: { geometry?: WeasDisposable; material?: WeasMaterial | WeasMaterial[] }) => void) => void
  clear: () => void
}

interface WeasRuntime {
  controls?: WeasDisposable
  _resizeObserver?: ResizeObserver
  _resizeRaf?: number
  scene: WeasScene
  coordScene?: WeasScene
  legendScene?: WeasScene
  renderers: Record<string, { renderer: { dispose?: () => void; domElement: HTMLElement } }>
}

let viewer: WEAS | undefined

startMolWeasFrame((cifText) => {
  const atoms = parseCIF(cifText)
  if (!atoms.positions.length || atoms.positions.some((position) => position.some((coordinate) => !Number.isFinite(coordinate)))) {
    throw new Error('WEAS could not parse finite atom coordinates from the CIF')
  }
  const element = document.getElementById('viewer')
  if (!element) throw new Error('Viewer container is unavailable')
  viewer = new WEAS({
    domElement: element,
    atoms: [atoms],
    viewerConfig: {
      modelStyle: 1, // WEAS's documented Ball + Stick model.
      colorBy: 'Element',
      colorType: 'JMOL',
      atomScale: 0.4,
      backgroundColor: '#ffffff',
      autoResetCameraOnAtomsUpdate: true,
      cellSettings: { showCell: true, showAxes: true, cellColor: 0x64748b },
      boundary: [[0, 1], [0, 1], [0, 1]],
    },
    guiConfig: {
      controls: { enabled: false },
      buttons: { enabled: false },
      timeline: { enabled: false },
      atomLegend: { enabled: false },
      meshLegend: { enabled: false },
    },
  })
  // The comparison exposes structure interaction, not WEAS's editing GUI.
  // Remove dat.gui's hidden auto-placed panel (all its CSS is iframe-local).
  viewer.guiManager.gui.destroy()
  viewer.tjs.updateCameraAndControls({ direction: [1, 1, 1] })
  viewer.render()
}, () => {
  if (!viewer) return
  viewer.avr.isPlaying = false
  const runtime: WeasRuntime = viewer.tjs
  runtime._resizeObserver?.disconnect()
  if (runtime._resizeRaf) cancelAnimationFrame(runtime._resizeRaf)
  runtime.controls?.dispose()
  const released = new Set<WeasDisposable>()
  for (const scene of [runtime.scene, runtime.coordScene, runtime.legendScene]) {
    scene?.traverse((object) => {
      if (object.geometry && !released.has(object.geometry)) {
        released.add(object.geometry)
        object.geometry.dispose()
      }
      const materials = Array.isArray(object.material) ? object.material : object.material ? [object.material] : []
      for (const material of materials) {
        if (released.has(material)) continue
        released.add(material)
        for (const value of Object.values(material)) {
          if (value && typeof value === 'object' && 'isTexture' in value && 'dispose' in value && typeof value.dispose === 'function' && !released.has(value as WeasDisposable)) {
            released.add(value as WeasDisposable)
            value.dispose()
          }
        }
        material.dispose()
      }
    })
    scene?.clear()
  }
  for (const { renderer } of Object.values(runtime.renderers)) renderer.dispose?.()
  viewer = undefined
})

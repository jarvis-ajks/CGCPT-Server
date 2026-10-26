import { useEffect, useRef, useState } from 'react'
import CrystVis from '@ccp-nc/crystvis-js'
import type { ViewerAdapterProps } from './types'

type SceneNode = CrystVis['_renderer']['_s']
type Disposable = { dispose(): void }

function disposeViewer(viewer: CrystVis) {
  // The library stops its RAF, controls and ResizeObserver, but does not
  // dispose model geometry/materials. Include meshes detached by selection.
  const renderer = viewer._renderer._r
  const resources = new Set<Disposable>()
  const nodes = new Set<SceneNode>()
  const collectTexture = (value: unknown) => {
    if (typeof value === 'object' && value !== null && 'isTexture' in value &&
      value.isTexture === true && 'dispose' in value && typeof value.dispose === 'function') {
      resources.add(value as Disposable)
    }
  }
  const collect = (root: SceneNode | null) => root?.traverse((node) => {
    if (nodes.has(node)) return
    nodes.add(node)
    if (node.geometry) resources.add(node.geometry)
    const materials = Array.isArray(node.material) ? node.material : node.material ? [node.material] : []
    for (const material of materials) {
      resources.add(material)
      for (const value of Object.values(material)) collectTexture(value)
      for (const uniform of Object.values(material.uniforms ?? {})) collectTexture(uniform.value)
    }
  })
  collect(viewer._renderer._s)
  for (const model of Object.values(viewer._models)) {
    for (const image of model._atom_images) collect(image._mesh)
    for (const image of model._bond_images) collect(image._mesh)
  }
  for (const resource of resources) resource.dispose()
  viewer.dispose()
  renderer.forceContextLoss()
}

function frameModel(viewer: CrystVis) {
  const positions = viewer.model.positions
  if (positions.length === 0) throw new Error('The CIF contains no atoms.')
  const min = [Infinity, Infinity, Infinity]
  const max = [-Infinity, -Infinity, -Infinity]
  for (const position of positions) {
    for (let axis = 0; axis < 3; axis += 1) {
      min[axis] = Math.min(min[axis], position[axis])
      max[axis] = Math.max(max[axis], position[axis])
    }
  }
  const center = min.map((value, axis) => (value + max[axis]) / 2)
  let radius = 1
  for (const position of positions) {
    radius = Math.max(radius, Math.hypot(position[0] - center[0], position[1] - center[1], position[2] - center[2]) + 2)
  }
  // CrystVis uses a square orthographic camera with initial half-width 20.
  viewer.centerCamera(center)
  viewer.setCameraState({ zoom: 16 / radius })
}

export default function CrystvisAdapter({ cifText, size }: ViewerAdapterProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState('Loading crystvis-js…')

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    let cancelled = false
    let viewer: CrystVis | undefined

    void Promise.resolve().then(() => {
      if (cancelled) return
      setStatus('Loading crystvis-js…')
      // The maintained scoped release is native ESM. jQuery accepts this DOM
      // element directly, avoiding global selector IDs and any global CSS.
      viewer = new CrystVis(container, 0, 0)
      viewer.theme = 'light'
      const canvas = container.querySelector('canvas')
      if (canvas) {
        canvas.style.touchAction = 'none'
        canvas.setAttribute('aria-label', 'crystvis-js crystal structure')
      }
      const loaded = viewer.loadModels(cifText, 'cif', 'structure')
      const modelName = Object.keys(loaded)[0]
      if (!modelName) throw new Error('The CIF contains no structure datablock.')
      if (loaded[modelName] !== 0) throw new Error(String(loaded[modelName]))
      viewer.displayModel(modelName)
      frameModel(viewer)
      setStatus('')
    }).catch((error: unknown) => {
      if (cancelled) return
      if (viewer) disposeViewer(viewer)
      viewer = undefined
      setStatus(`crystvis-js: ${error instanceof Error ? error.message : String(error)}`)
    })

    return () => {
      cancelled = true
      if (viewer) disposeViewer(viewer)
      container.replaceChildren()
    }
  }, [cifText, size])

  return (
    <div style={{ width: size, height: size, maxWidth: '100%', position: 'relative', overflow: 'hidden', background: '#fff' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative' }} />
      {status && (
        <div role={status.startsWith('Loading') ? 'status' : 'alert'} style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', padding: 20, color: '#334155', background: '#fff', textAlign: 'center', overflow: 'auto' }}>
          {status}
        </div>
      )}
    </div>
  )
}

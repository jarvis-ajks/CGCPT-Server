import { createViewer } from '3dmol'
import type { GLViewer } from '3dmol'
import { startMolWeasFrame } from './MolWeasFrameBridge'

let viewer: GLViewer | undefined

startMolWeasFrame((cifText) => {
  const element = document.getElementById('viewer')
  if (!element) throw new Error('Viewer container is unavailable')
  viewer = createViewer(element, { backgroundColor: 'white', antialias: true, disableFog: true })
  // Parse a single crystallographic cell; the supplied comparison CIF already
  // contains the full set of symmetry-expanded sites.
  const model = viewer.addModel(cifText, 'cif', { doAssembly: false, duplicateAssemblyAtoms: false })
  const atoms = model.selectedAtoms({})
  if (!atoms.length || atoms.some((atom) => !Number.isFinite(atom.x) || !Number.isFinite(atom.y) || !Number.isFinite(atom.z))) {
    throw new Error('3Dmol.js could not parse finite atom coordinates from the CIF')
  }
  viewer.setStyle({}, { sphere: { scale: 0.3 }, stick: { radius: 0.15 } })
  viewer.addUnitCell(model, { box: { color: '#64748b', linewidth: 1 } })
  viewer.setProjection('orthographic')
  viewer.zoomTo()
  viewer.rotate(20, 'x')
  viewer.rotate(25, 'y')
  viewer.render()
}, () => {
  if (!viewer) return
  viewer.stopAnimate()
  viewer.spin(false)
  // The library's observer is private and has no public disconnect API.
  const lifecycle = viewer as unknown as { divwatcher?: ResizeObserver }
  lifecycle.divwatcher?.disconnect()
  viewer.clear()
  viewer = undefined
})

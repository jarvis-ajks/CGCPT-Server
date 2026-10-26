// Narrow declarations for the APIs used from the pinned, JavaScript-only packages.
declare module 'cifvis' {
  export class CrystalViewer {
    constructor(container: HTMLElement, options?: { renderMode?: 'constant' | 'onDemand' })
    options: { renderMode: 'constant' | 'onDemand' }
    needsRender: boolean
    scene: object
    camera: object
    renderer: {
      domElement: HTMLCanvasElement
      render(scene: object, camera: object): void
      forceContextLoss(): void
    }
    animate(): void
    loadStructure(cifText: string): Promise<{ success: boolean; error?: string }>
    dispose(): void
  }
}

declare module '@ccp-nc/crystvis-js' {
  interface Disposable {
    dispose(): void
  }
  interface SceneMaterial extends Disposable {
    [key: string]: unknown
    uniforms?: Record<string, { value: unknown }>
  }
  interface SceneNode {
    geometry?: Disposable
    material?: SceneMaterial | SceneMaterial[]
    traverse(callback: (node: SceneNode) => void): void
  }
  interface Model {
    positions: number[][]
    _atom_images: { _mesh: SceneNode | null }[]
    _bond_images: { _mesh: SceneNode | null }[]
  }
  export default class CrystVis {
    constructor(target: string | HTMLElement, width?: number, height?: number)
    theme: string
    model: Model
    _models: Record<string, Model>
    _renderer: {
      _s: SceneNode
      _r: { forceContextLoss(): void }
    }
    loadModels(cifText: string, format: 'cif', prefix: string): Record<string, 0 | string>
    displayModel(name: string): void
    centerCamera(center: number[]): void
    setCameraState(state: { zoom: number }): void
    dispose(): void
  }
}

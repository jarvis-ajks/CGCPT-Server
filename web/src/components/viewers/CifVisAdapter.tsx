import { useEffect, useRef, useState } from 'react'
import { CrystalViewer } from 'cifvis'
import type { ViewerAdapterProps } from './types'

// cifvis 0.9.4's dispose() does not stop its animation loop. Override the
// constructor-invoked hook so this instance owns and cancels every frame.
class DisposableCrystalViewer extends CrystalViewer {
  declare private frame: number | undefined
  declare private stopped: boolean | undefined

  override animate() {
    if (this.stopped) return
    if (this.options.renderMode === 'constant' || this.needsRender) {
      this.renderer.render(this.scene, this.camera)
      this.needsRender = false
    }
    this.frame = requestAnimationFrame(() => this.animate())
  }

  override dispose() {
    if (this.stopped) return
    this.stopped = true
    if (this.frame !== undefined) cancelAnimationFrame(this.frame)
    const renderer = this.renderer
    super.dispose()
    renderer.forceContextLoss()
  }
}

export default function CifVisAdapter({ cifText, size }: ViewerAdapterProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState('Loading CifVis…')

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    let cancelled = false
    let viewer: DisposableCrystalViewer | undefined

    void Promise.resolve().then(async () => {
      if (cancelled) return
      setStatus('Loading CifVis…')
      // The imperative API has no stylesheet; unlike CifViewWidget it never
      // inserts the package's global widget CSS into document.head.
      viewer = new DisposableCrystalViewer(container, { renderMode: 'onDemand' })
      viewer.renderer.domElement.style.touchAction = 'none'
      viewer.renderer.domElement.setAttribute('aria-label', 'CifVis crystal structure')
      const result = await viewer.loadStructure(cifText)
      if (cancelled) return
      if (!result.success) throw new Error(result.error || 'CifVis could not load this CIF.')
      setStatus('')
    }).catch((error: unknown) => {
      if (cancelled) return
      viewer?.dispose()
      viewer = undefined
      setStatus(`CifVis: ${error instanceof Error ? error.message : String(error)}`)
    })

    return () => {
      cancelled = true
      viewer?.dispose()
      container.replaceChildren()
    }
  }, [cifText, size])

  return (
    <div style={{ width: size, height: size, maxWidth: '100%', position: 'relative', overflow: 'hidden', background: '#fafafa' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      {status && (
        <div role={status.startsWith('Loading') ? 'status' : 'alert'} style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', padding: 20, color: '#334155', background: '#fafafa', textAlign: 'center', overflow: 'auto' }}>
          {status}
        </div>
      )}
    </div>
  )
}

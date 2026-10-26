import { Component, useCallback, useState } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import {
  AddBonds,
  ensureThemeTokens,
  LoadStructure,
  Pipeline,
  PipelineViewer,
  ViewportNode,
} from 'megane-viewer/lib'
import type { SerializedPipeline } from 'megane-viewer/lib'
import meganeStyles from 'megane-viewer/styles.css?inline'
import type { ViewerAdapterProps } from './types'

interface MountedMegane {
  root: ShadowRoot
  pipeline?: SerializedPipeline
  url?: string
  error?: string
}

class MeganeRenderBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  state: { error: string | null } = { error: null }

  static getDerivedStateFromError(error: unknown) {
    return { error: error instanceof Error ? error.message : String(error) }
  }

  render() {
    return this.state.error
      ? <div role="alert" style={{ padding: 16, color: '#b91c1c' }}>Megane could not render this CIF: {this.state.error}</div>
      : this.props.children
  }
}

function makePipeline(url: string) {
  const pipeline = new Pipeline()
  const structure = pipeline.addNode(new LoadStructure('structure.cif'))
  const bonds = pipeline.addNode(new AddBonds({ source: 'distance' }))
  const viewport = pipeline.addNode(new ViewportNode({ cellAxesVisible: true }))
  pipeline.addEdge(structure.out.particle, viewport.inp.particle)
  pipeline.addEdge(structure.out.cell, viewport.inp.cell)
  pipeline.addEdge(structure.out.particle, bonds.inp.particle)
  pipeline.addEdge(bonds.out.bond, viewport.inp.bond)
  const serialized = pipeline.toObject()
  for (const node of serialized.nodes) {
    // Keep the .cif filename: the parser dispatches by filename, not blob MIME.
    if (node.type === 'load_structure') node.fileUrl = url
  }
  return serialized
}

export default function MeganeAdapter({ cifText, size }: ViewerAdapterProps) {
  const [mounted, setMounted] = useState<MountedMegane | null>(null)
  const attachHost = useCallback((host: HTMLDivElement | null) => {
    if (!host) return
    const root = host.shadowRoot ?? host.attachShadow({ mode: 'open' })
    if (!root.firstChild) {
      // MeganeViewer injects theme CSS into the page. Its official embeddable
      // PipelineViewer avoids that side effect; copy official tokens from an
      // inert document rather than changing the application's root/theme.
      const themeDocument = document.implementation.createHTMLDocument('')
      ensureThemeTokens(themeDocument)
      const tokens = (themeDocument.getElementById('megane-theme-tokens')?.textContent ?? '')
        .replaceAll(':root', ':host')
        .replaceAll('html[data-theme="dark"]', ':host([data-theme="dark"])')
      const styles = document.createElement('style')
      styles.textContent = `${meganeStyles}\n${tokens}\n:host { display:block; font-family:system-ui,sans-serif; } * { box-sizing:border-box; }`
      root.append(styles)
    }

    let url: string | undefined
    try {
      url = URL.createObjectURL(new Blob([cifText], { type: 'chemical/x-cif' }))
      const pipeline = makePipeline(url)
      setMounted({ root, pipeline, url })
    } catch (error) {
      if (url) URL.revokeObjectURL(url)
      setMounted({ root, error: error instanceof Error ? error.message : String(error) })
    }
    // React 19 ref cleanup also runs before a changed CIF attaches, and during
    // StrictMode replay. PipelineViewer aborts fetches and disposes its renderer
    // and playback effects when its URL-keyed instance is unmounted.
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [cifText])

  return (
    <>
      <div ref={attachHost} data-theme="light" style={{ width: size, height: size, overflow: 'hidden' }} aria-label="Megane crystal structure viewer" />
      {mounted && createPortal(
        mounted.pipeline
          ? <MeganeRenderBoundary key={mounted.url}>
              <PipelineViewer pipeline={mounted.pipeline} width={size} height={size} />
            </MeganeRenderBoundary>
          : <div role="alert" style={{ padding: 16, color: '#b91c1c' }}>Megane could not load this CIF: {mounted.error}</div>,
        mounted.root,
      )}
    </>
  )
}

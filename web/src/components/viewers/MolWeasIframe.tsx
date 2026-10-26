import { useEffect, useRef, useState } from 'react'
import type { ViewerAdapterProps } from './types'
import type { MolWeasFrameRealm } from './MolWeasFrameBridge'

interface MolWeasIframeProps extends ViewerAdapterProps {
  entryUrl: string
  label: string
}

// A separate document also owns library-created global listeners, injected CSS,
// and observers for libraries that do not expose a complete destroy method.
export default function MolWeasIframe({ cifText, size, entryUrl, label }: MolWeasIframeProps) {
  const frameRef = useRef<HTMLIFrameElement>(null)
  const [status, setStatus] = useState<{ error?: string; loading: boolean }>({ loading: true })

  useEffect(() => {
    const frame = frameRef.current
    if (!frame) return
    const id = crypto.randomUUID()
    const scriptUrl = new URL(entryUrl, window.location.href)
    // Vite's worker bundler produces a self-contained browser asset. In dev,
    // request its module variant because it is executed in a document, not a worker.
    if (scriptUrl.searchParams.has('worker_file')) scriptUrl.searchParams.set('type', 'module')
    const escapedUrl = scriptUrl.href.replaceAll('&', '&amp;').replaceAll('"', '&quot;')
    setStatus({ loading: true })

    let active = true
    const onFrameLoad = () => {
      if (frame.contentDocument?.documentElement.dataset.cgcptFrameId !== id) return
      const realm = frame.contentWindow as MolWeasFrameRealm | null
      if (!realm?.__cgcptLoad) {
        setStatus({ loading: false, error: 'Viewer module did not initialize' })
        return
      }
      realm.__cgcptLoad(cifText, () => {
        if (active) setStatus({ loading: false })
      }, (message) => {
        if (active) setStatus({ loading: false, error: message })
      })
    }
    frame.addEventListener('load', onFrameLoad)
    // CIF is passed directly to the trusted same-origin realm, never into HTML.
    frame.srcdoc = `<!doctype html><html data-cgcpt-frame-id="${id}"><head><meta charset="utf-8"><style>
      html,body,#viewer{width:100%;height:100%;margin:0;overflow:hidden;background:#fff}
      #viewer{position:relative;touch-action:none}canvas{display:block}
      body{font:12px system-ui,sans-serif;color:#172033}
    </style></head><body><div id="viewer"></div><script type="module" src="${escapedUrl}"></script></body></html>`

    return () => {
      active = false
      frame.removeEventListener('load', onFrameLoad)
      const realm = frame.contentWindow as MolWeasFrameRealm | null
      try {
        realm?.__cgcptDispose?.()
      } finally {
        // Navigation discards bound global handlers and pending callbacks too.
        frame.srcdoc = ''
      }
    }
  }, [cifText, entryUrl])

  return (
    <div style={{ width: size, height: size, position: 'relative', background: '#fff' }}>
      <iframe ref={frameRef} title={`${label} crystal comparison viewer`} style={{ width: '100%', height: '100%', display: 'block', border: 0 }} />
      {(status.loading || status.error) && (
        <div role={status.error ? 'alert' : 'status'} style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', padding: 20, textAlign: 'center', background: '#fff', color: status.error ? '#b42318' : '#475569' }}>
          {status.error ? `${label}: ${status.error}` : `Loading ${label}…`}
        </div>
      )}
    </div>
  )
}

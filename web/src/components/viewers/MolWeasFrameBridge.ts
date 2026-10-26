export type MolWeasFrameRealm = Window & {
  __cgcptLoad?: (cifText: string, onLoaded: () => void, onError: (message: string) => void) => void
  __cgcptDispose?: () => void
}

export function startMolWeasFrame(load: (cifText: string) => void, dispose: () => void) {
  const realm = window as MolWeasFrameRealm
  let disposed = false
  let initialized = false
  let failed = false
  let reportError: ((message: string) => void) | undefined
  const onError = (event: ErrorEvent) => {
    failed = true
    reportError?.(event.message || 'Viewer runtime failed')
  }
  const onRejection = (event: PromiseRejectionEvent) => {
    failed = true
    reportError?.(String(event.reason?.message || event.reason))
  }
  const cleanup = () => {
    if (disposed) return
    disposed = true
    window.removeEventListener('error', onError)
    window.removeEventListener('unhandledrejection', onRejection)
    try {
      dispose()
    } finally {
      // Explicitly release GPU contexts before the document is discarded.
      for (const canvas of document.querySelectorAll('canvas')) {
        canvas.remove()
        const taggedCanvas = canvas as HTMLCanvasElement & { _3dmol_viewer?: unknown }
        delete taggedCanvas._3dmol_viewer
        const gl = canvas.getContext('webgl2') || canvas.getContext('webgl')
        gl?.getExtension('WEBGL_lose_context')?.loseContext()
      }
    }
  }
  // This API is only accessed through our trusted same-origin iframe document.
  // Its load event waits for module scripts, so there is no message handshake.
  realm.__cgcptLoad = (cifText, onLoaded, onFailure) => {
    if (disposed || initialized) return
    initialized = true
    reportError = onFailure
    try {
      if (!cifText.trim()) throw new Error('No CIF structure supplied')
      load(cifText)
      requestAnimationFrame(() => {
        if (!disposed && !failed) onLoaded()
      })
    } catch (error) {
      failed = true
      onFailure(error instanceof Error ? error.message : String(error))
      cleanup()
    }
  }
  realm.__cgcptDispose = cleanup
  window.addEventListener('pagehide', cleanup, { once: true })
  window.addEventListener('error', onError)
  window.addEventListener('unhandledrejection', onRejection)
}

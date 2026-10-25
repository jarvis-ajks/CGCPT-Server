import { useEffect, useMemo, useRef, useState } from 'react'
import { CrystalToolkitScene } from '@materialsproject/mp-react-components'
import type { Atom, Lattice } from '../../types'
import './CrystalScene.css'

const SCENE_URL = '/CGCPT/api/structure/scene'

export interface CrystalSceneProps {
  /** Raw CIF text. Takes precedence over `atoms`/`lattice` when provided. */
  cifText?: string
  atoms?: Atom[]
  lattice?: Lattice
  className?: string
  /** Square size in px. Defaults to the largest square that fits the wrapper. */
  sceneSize?: number
}

interface ScenePayload {
  cif_text?: string
  structure?: { atoms: Atom[]; lattice: Lattice }
}

/**
 * Materials Project `CrystalToolkitScene` bound to the local `crystal_toolkit`
 * scene service. The payload is the exact JSON that materialsproject.org feeds
 * its viewer, so the rendering code is upstream and untouched.
 */
export default function CrystalScene({
  cifText,
  atoms,
  lattice,
  className,
  sceneSize,
}: CrystalSceneProps) {
  const [scene, setScene] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [measuredSize, setMeasuredSize] = useState(0)
  const requestId = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)

  // The upstream viewer renders a fixed square; size it from the layout box.
  useEffect(() => {
    const element = containerRef.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setMeasuredSize(Math.floor(Math.min(width, height)))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const size = sceneSize ?? measuredSize

  const payload = useMemo<ScenePayload | null>(() => {
    if (cifText?.trim()) return { cif_text: cifText }
    if (atoms?.length && lattice) return { structure: { atoms, lattice } }
    return null
  }, [atoms, cifText, lattice])

  // Stable dependency: callers often rebuild the arrays on unrelated renders.
  const payloadKey = useMemo(() => (payload ? JSON.stringify(payload) : ''), [payload])

  useEffect(() => {
    if (!payloadKey) {
      setScene(null)
      setError(null)
      setLoading(false)
      return
    }
    const id = ++requestId.current
    const controller = new AbortController()
    setLoading(true)
    setError(null)

    fetch(SCENE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payloadKey,
      signal: controller.signal,
    })
      .then(async (res) => {
        const body = await res.json().catch(() => null)
        if (id !== requestId.current) return
        if (!res.ok || !body || body.error) {
          throw new Error(body?.error || `场景服务返回 HTTP ${res.status}`)
        }
        setScene(body)
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted || id !== requestId.current) return
        setScene(null)
        setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false)
      })

    return () => controller.abort()
  }, [payloadKey])

  return (
    <div ref={containerRef} className={`cgcpt-scene ${className ?? ''}`}>
      {scene && size > 0 ? <CrystalToolkitScene data={scene} sceneSize={size} /> : null}
      {loading && !scene && (
        <div className="cgcpt-scene-overlay">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      {error && !scene && (
        <div className="cgcpt-scene-overlay px-4 text-center text-sm text-red-300">
          三维结构加载失败：{error}
        </div>
      )}
    </div>
  )
}

import { useEffect, useMemo, useRef, useState } from 'react'
import { CrystalToolkitScene } from '@materialsproject/mp-react-components'
import type { Atom, Lattice } from '../../types'
import './scene-vendor.css'
import './CrystalScene.css'

const SCENE_URL = '/CGCPT/api/structure/scene'

// Crystal Toolkit's StructureMoleculeComponent passes exactly these scene
// settings (crystal_toolkit/components/structure.py default_scene_settings).
// `extractAxis` matters most: without it the compass/axes object is part of
// the fitted bounding box, which zooms the structure out.
const SCENE_SETTINGS = {
  extractAxis: true,
  secondaryObjectView: false,
  renderer: 'webgl',
}

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

interface SceneResult {
  key: string
  scene?: unknown
  error?: string
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
  const [result, setResult] = useState<SceneResult | null>(null)
  const [measuredWidth, setMeasuredWidth] = useState(0)
  const [expanded, setExpanded] = useState(false)
  const [viewport, setViewport] = useState(() => ({
    width: window.innerWidth,
    height: window.innerHeight,
  }))
  const containerRef = useRef<HTMLDivElement>(null)

  // Crystal Toolkit lays the scene out in a 500px square; keep that as the
  // ceiling and shrink only when the card is narrower than the viewport allows.
  useEffect(() => {
    const element = containerRef.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      setMeasuredWidth(Math.floor(entry.contentRect.width))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const onResize = () => setViewport({ width: window.innerWidth, height: window.innerHeight })
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const payload = useMemo<ScenePayload | null>(() => {
    if (cifText?.trim()) return { cif_text: cifText }
    if (atoms?.length && lattice) return { structure: { atoms, lattice } }
    return null
  }, [atoms, cifText, lattice])

  // Stable dependency: callers often rebuild the arrays on unrelated renders.
  const payloadKey = useMemo(() => (payload ? JSON.stringify(payload) : ''), [payload])

  useEffect(() => {
    if (!payloadKey) return
    const controller = new AbortController()

    fetch(SCENE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payloadKey,
      signal: controller.signal,
    })
      .then(async (res) => {
        const body = await res.json().catch(() => null)
        if (!res.ok || !body || body.error) {
          throw new Error(body?.error || `场景服务返回 HTTP ${res.status}`)
        }
        setResult({ key: payloadKey, scene: body })
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setResult({ key: payloadKey, error: err instanceof Error ? err.message : String(err) })
      })

    return () => controller.abort()
  }, [payloadKey])

  // Ignore results for a payload that is no longer rendered.
  const current = result?.key === payloadKey ? result : null
  const scene = current?.scene ?? null
  const error = current?.error ?? null
  const loading = Boolean(payloadKey) && !current

  // The white panel stays at the card size; the scene inside grows in the
  // fullscreen modal (which is position: fixed and its own layout box).
  const boxSize = sceneSize ?? Math.min(measuredWidth, 500)
  const scenePixels =
    sceneSize ??
    (expanded
      ? Math.max(120, Math.floor(Math.min(viewport.width * 0.95, viewport.height * 0.95 - 48)))
      : boxSize)

  // Follow the viewer's own fullscreen toggle (it flips `.is-active` on the
  // wrapper it renders) so the square can grow to the modal instead of
  // staying at the card size. Attach only once the viewer is actually mounted.
  const viewerMounted = Boolean(scene) && boxSize > 0
  useEffect(() => {
    if (!viewerMounted) return
    const modal = containerRef.current?.querySelector('.mpc-expandable')
    if (!modal) return
    setExpanded(modal.classList.contains('is-active'))
    const observer = new MutationObserver(() =>
      setExpanded(modal.classList.contains('is-active')),
    )
    observer.observe(modal, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [viewerMounted])

  return (
    <div ref={containerRef} className={`cgcpt-scene-host ${className ?? ''}`}>
      <div className="cgcpt-scene" style={boxSize > 0 ? { width: boxSize, height: boxSize } : undefined}>
        {scene && boxSize > 0 ? (
          <CrystalToolkitScene data={scene} sceneSize={scenePixels} settings={SCENE_SETTINGS} />
        ) : null}
        {loading && (
          <div className="cgcpt-scene-overlay">
            <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {error && (
          <div className="cgcpt-scene-overlay px-4 text-center text-sm text-red-300">
            三维结构加载失败：{error}
          </div>
        )}
      </div>
    </div>
  )
}

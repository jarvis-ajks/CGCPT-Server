import { Component, lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import type { CrystalSceneProps } from '../mp/CrystalScene'

const adapters = {
  matterviz: lazy(() => import('./MatterVizAdapter')),
  megane: lazy(() => import('./MeganeAdapter')),
  cifvis: lazy(() => import('./CifVisAdapter')),
  crystvis: lazy(() => import('./CrystvisAdapter')),
  threedmol: lazy(() => import('./ThreeDmolAdapter')),
  weas: lazy(() => import('./WeasAdapter')),
}
const labels = {
  mp: 'Materials Project（官方默认）',
  matterviz: 'MatterViz',
  megane: 'Megane',
  cifvis: 'CifVis',
  crystvis: 'crystvis-js',
  threedmol: '3Dmol.js',
  weas: 'WEAS',
}
type Viewer = keyof typeof labels

class ViewerErrorBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  state: { error: string | null } = { error: null }
  static getDerivedStateFromError(error: Error) {
    return { error: error.message }
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Comparison viewer failed', error, info.componentStack)
  }
  render() {
    return this.state.error
      ? <p role="alert" className="p-4 text-sm text-red-400">查看器加载失败：{this.state.error}。可切回 Materials Project。</p>
      : this.props.children
  }
}

export default function ViewerSwitcher({ cifText, atoms, lattice, sceneSize, className, children }: CrystalSceneProps & { children: ReactNode }) {
  const [viewer, setViewer] = useState<Viewer>('mp')
  const [width, setWidth] = useState(0)
  const [normalised, setNormalised] = useState<{ key: string; cifText?: string; error?: string } | null>(null)
  const host = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!host.current) return
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)))
    observer.observe(host.current)
    return () => observer.disconnect()
  }, [])
  const payloadKey = useMemo(() => {
    const source = cifText?.trim() ? { cif_text: cifText } : atoms?.length && lattice ? { structure: { atoms, lattice } } : null
    return source ? JSON.stringify({ ...source, output: 'cif' }) : ''
  }, [cifText, atoms, lattice])
  const comparison = viewer !== 'mp'
  useEffect(() => {
    if (!comparison || !payloadKey || normalised?.key === payloadKey) return
    const controller = new AbortController()
    fetch('/CGCPT/api/structure/scene', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payloadKey,
      signal: controller.signal,
    }).then(async (response) => {
      const body = await response.json()
      if (!response.ok || !body.cif_text) throw new Error(body.error || `CIF 规范化失败：HTTP ${response.status}`)
      setNormalised({ key: payloadKey, cifText: body.cif_text })
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setNormalised({ key: payloadKey, error: error instanceof Error ? error.message : String(error) })
    })
    return () => controller.abort()
  }, [comparison, payloadKey, normalised?.key])
  const current = normalised?.key === payloadKey ? normalised : null
  const cif = current?.cifText ?? ''
  const size = Math.min(width, sceneSize ?? 500)
  const Adapter = viewer === 'mp' ? null : adapters[viewer]

  return (
    <section ref={host} className={`w-full min-w-0 ${className ?? ''}`} aria-label="晶体结构查看器">
      <label className="mb-2 flex flex-wrap items-center gap-2 text-sm text-slate-300">
        <span>显示引擎</span>
        <select aria-label="显示引擎" value={viewer} onChange={(event) => setViewer(event.target.value as Viewer)} className="max-w-full rounded border border-slate-600 bg-slate-900 px-2 py-1 text-sm text-slate-100">
          {Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <p className="mb-3 text-xs text-slate-400">
        {viewer === 'mp'
          ? '官方 Crystal Toolkit 默认场景逻辑与相机；500px 上限，窄屏自适应。'
          : '对比模式：输入经官方 pymatgen 展开为 P1 CIF；各引擎的成键、配色、角度与缩放不同，不代表 Materials Project。'}
        {' '}<a className="underline" href={`${import.meta.env.BASE_URL}viewer-licenses.txt`} target="_blank" rel="noreferrer">引擎许可与源码</a>
      </p>
      {viewer === 'mp' ? children : (
        <div className="mx-auto overflow-hidden bg-white text-slate-900" style={{ width: size, height: size }} data-viewer={viewer}>
          {!payloadKey ? <p role="status" className="p-4 text-sm">没有可显示的结构数据</p> : current?.error ? (
            <p role="alert" className="p-4 text-sm text-red-600">{current.error}</p>
          ) : !cif ? <p role="status" className="p-4 text-sm">正在用 pymatgen 展开 CIF…</p> : size > 0 && Adapter ? (
            <ViewerErrorBoundary key={`${viewer}:${cif}`}>
              <Suspense fallback={<p role="status" className="p-4 text-sm">正在加载 {labels[viewer]}…</p>}>
                <Adapter cifText={cif} size={size} />
              </Suspense>
            </ViewerErrorBoundary>
          ) : null}
        </div>
      )}
    </section>
  )
}

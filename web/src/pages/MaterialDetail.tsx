import { useEffect, useState, useCallback, lazy, Suspense } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Atom, FileText, Download, X, Heart, GitCompare } from 'lucide-react'
import { fetchMaterial, fetchCifContent } from '../api/client'
import type { Material } from '../types'

const CrystalViewer = lazy(() => import('../components/three/CrystalViewer'))

interface FavoriteItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  addedAt: number
  elements: string[]
  verified: boolean
}

interface RecentItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  viewedAt: number
}

function loadFavorites(): FavoriteItem[] {
  try {
    const data = localStorage.getItem('cgcpt_favorites')
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveFavorites(items: FavoriteItem[]): void {
  localStorage.setItem('cgcpt_favorites', JSON.stringify(items))
}

function isFavorite(materialId: string): boolean {
  return loadFavorites().some(f => f.materialId === materialId)
}

function addFavorite(material: Material): void {
  const favorites = loadFavorites()
  if (favorites.some(f => f.materialId === material.material_id)) return
  favorites.unshift({
    materialId: material.material_id,
    formula: material.formula,
    spaceGroup: material.space_group,
    topology: material.topology,
    addedAt: Date.now(),
    elements: material.elements || [],
    verified: material.verified,
  })
  saveFavorites(favorites)
}

function removeFavorite(materialId: string): void {
  const favorites = loadFavorites().filter(f => f.materialId !== materialId)
  saveFavorites(favorites)
}

function addRecent(material: Material): void {
  try {
    const data = localStorage.getItem('cgcpt_recent')
    let recents: RecentItem[] = data ? JSON.parse(data) : []
    recents = recents.filter(r => r.materialId !== material.material_id)
    recents.unshift({
      materialId: material.material_id,
      formula: material.formula,
      spaceGroup: material.space_group,
      topology: material.topology,
      viewedAt: Date.now(),
    })
    recents = recents.slice(0, 100)
    localStorage.setItem('cgcpt_recent', JSON.stringify(recents))
  } catch {}
}

export default function MaterialDetail() {
  const { id } = useParams<{ id: string }>()
  const [material, setMaterial] = useState<Material | null>(null)
  const [loading, setLoading] = useState(true)
  const [cifContent, setCifContent] = useState<string | null>(null)
  const [showCif, setShowCif] = useState(false)
  const [cifLoading, setCifLoading] = useState(false)
  const [favorited, setFavorited] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchMaterial(id)
      .then((m) => {
        setMaterial(m)
        setFavorited(isFavorite(m.material_id))
        addRecent(m)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  const toggleFavorite = useCallback(() => {
    if (!material) return
    if (favorited) {
      removeFavorite(material.material_id)
      setFavorited(false)
    } else {
      addFavorite(material)
      setFavorited(true)
    }
  }, [material, favorited])

  const handleLoadCif = () => {
    if (!id) return
    setCifLoading(true)
    fetchCifContent(id)
      .then((content) => {
        setCifContent(content)
        setShowCif(true)
      })
      .catch(() => {})
      .finally(() => setCifLoading(false))
  }

  const handleExportCif = () => {
    if (!cifContent) {
      if (!id) return
      fetchCifContent(id).then((content) => {
        const blob = new Blob([content], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${material?.formula ?? 'crystal'}.cif`
        a.click()
        URL.revokeObjectURL(url)
      })
      return
    }
    const blob = new Blob([cifContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${material?.formula ?? 'crystal'}.cif`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!material) {
    return (
      <div className="text-center py-20 text-gray-500">
        <Atom className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>未找到该材料</p>
      </div>
    )
  }

  const atomSites = material.cif_data?.atom_sites || []
  const lattice = material.cif_data?.lattice

  if (!lattice || atomSites.length === 0) {
    return (
      <div className="space-y-6 px-4 sm:px-0">
        <Link
          to="/materials"
          className="inline-flex items-center gap-2 text-gray-400 hover:text-cyan-400 text-sm transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回材料列表
        </Link>
        <div className="text-center py-16 sm:py-20 text-gray-500">
          <Atom className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 opacity-50" />
          <p>该材料暂无晶体结构数据</p>
          <p className="text-sm mt-2">材料编号: {material.material_id}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link
        to="/materials"
        className="inline-flex items-center gap-2 text-gray-400 hover:text-cyan-400 text-sm transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        返回材料列表
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">{material.formula}</h1>
          <p className="text-gray-400 mt-1">
            {material.space_group} · {material.topology}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <span
            className={`inline-flex items-center px-2.5 py-1 sm:px-3 sm:py-1 rounded-full text-xs font-medium ${
              material.verified
                ? 'bg-emerald-500/10 text-emerald-400'
                : 'bg-amber-500/10 text-amber-400'
            }`}
          >
            {material.verified ? '已验证' : '原始'}
          </span>
          <button
            onClick={toggleFavorite}
            className={`flex items-center gap-1.5 px-3 py-2 sm:px-3 sm:py-1.5 rounded-lg text-sm transition-colors min-h-[44px] sm:min-h-0 ${
              favorited
                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20'
                : 'bg-gray-800 border border-gray-700 text-gray-300 hover:border-rose-500/50 hover:text-rose-400'
            }`}
            title={favorited ? '取消收藏' : '添加收藏'}
          >
            <Heart className={`w-4 h-4 ${favorited ? 'fill-current' : ''}`} />
            {favorited ? '已收藏' : '收藏'}
          </button>
          <Link
            to={`/compare?ids=${material.material_id}`}
            className="flex items-center gap-1.5 px-3 py-2 sm:px-3 sm:py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:border-cyan-500/50 hover:text-cyan-400 transition-colors min-h-[44px] sm:min-h-0"
            title="添加到对比"
          >
            <GitCompare className="w-4 h-4" />
            对比
          </Link>
          <button
            onClick={handleLoadCif}
            disabled={cifLoading}
            className="flex items-center gap-1.5 px-3 py-2 sm:px-3 sm:py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:border-cyan-500/50 transition-colors disabled:opacity-50 min-h-[44px] sm:min-h-0"
          >
            <FileText className="w-4 h-4" />
            {cifLoading ? '加载中...' : '查看CIF'}
          </button>
          <button
            onClick={handleExportCif}
            className="flex items-center gap-1.5 px-3 py-2 sm:px-3 sm:py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:border-cyan-500/50 transition-colors min-h-[44px] sm:min-h-0"
          >
            <Download className="w-4 h-4" />
            导出CIF
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
          <h2 className="text-lg font-semibold text-white mb-4">
            三维结构
          </h2>
          <Suspense fallback={<div className="h-64 sm:h-96 bg-gray-900 rounded-lg flex items-center justify-center"><div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>}>
            <CrystalViewer atoms={atomSites} lattice={lattice} className="h-64 sm:h-96" showBonds showElementInfo />
          </Suspense>
        </div>

        <div className="space-y-4">
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
            <h2 className="text-lg font-semibold text-white mb-3">
              晶格参数
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {(['a', 'b', 'c', 'alpha', 'beta', 'gamma'] as const).map(
                (key) => (
                  <div key={key} className="bg-gray-900/50 rounded-lg p-3">
                    <p className="text-xs text-gray-500 uppercase">{key}</p>
                    <p className="text-lg font-mono text-white">
                      {lattice[key].toFixed(4)}
                      {['alpha', 'beta', 'gamma'].includes(key) ? '°' : ' Å'}
                    </p>
                  </div>
                )
              )}
            </div>
          </div>

          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
            <h2 className="text-lg font-semibold text-white mb-3">
              属性信息
            </h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">材料编号</span>
                <span className="text-cyan-400">{material.material_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">化学式</span>
                <span className="text-white">{material.formula}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">空间群</span>
                <span className="text-white">{material.space_group}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">拓扑</span>
                <span className="text-white">{material.topology}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">元素</span>
                <span className="text-white">{material.elements.join(', ')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">验证状态</span>
                <span
                  className={
                    material.verified ? 'text-emerald-400' : 'text-amber-400'
                  }
                >
                  {material.verified ? '已验证' : '未验证'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">CIF文件</span>
                <span className="text-white font-mono text-xs">{material.cif_file}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">目录</span>
                <span className="text-white font-mono text-xs">{material.directory}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
        <h2 className="text-lg font-semibold text-white mb-3">
          原子位置（共 {atomSites.length} 个原子）
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700/50">
                <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium">
                  元素
                </th>
                <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium">
                  x
                </th>
                <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium">
                  y
                </th>
                <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium">
                  z
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/30">
              {atomSites.map((atom, i) => (
                <tr key={i} className="hover:bg-gray-700/20">
                  <td className="px-2 py-1.5 sm:px-3 sm:py-2 text-white font-mono">
                    {atom.element}
                  </td>
                  <td className="px-2 py-1.5 sm:px-3 sm:py-2 text-gray-300 font-mono">
                    {atom.x.toFixed(6)}
                  </td>
                  <td className="px-2 py-1.5 sm:px-3 sm:py-2 text-gray-300 font-mono">
                    {atom.y.toFixed(6)}
                  </td>
                  <td className="px-2 py-1.5 sm:px-3 sm:py-2 text-gray-300 font-mono">
                    {atom.z.toFixed(6)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showCif && cifContent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowCif(false)}>
          <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-4xl max-h-[90vh] sm:max-h-[80vh] mx-2 sm:mx-0 flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
              <h3 className="text-lg font-semibold text-white">CIF 文件内容</h3>
              <button onClick={() => setShowCif(false)} className="p-1 text-gray-400 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-5">
              <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">{cifContent}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

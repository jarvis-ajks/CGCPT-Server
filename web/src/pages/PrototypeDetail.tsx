import { useEffect, useState, useCallback, useMemo, lazy, Suspense } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Hexagon, Atom, Network, Layers, Heart, GitCompare,
  Search, ChevronLeft, ChevronRight, CheckSquare, Square,
  FlaskConical, BarChart3, Loader2, Box
} from 'lucide-react'
import { fetchPrototype, fetchMaterial } from '../api/client'
import type { Prototype, MaterialListItem, Material } from '../types'

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

function toggleFavoriteItem(m: MaterialListItem): boolean {
  const favorites = loadFavorites()
  const idx = favorites.findIndex(f => f.materialId === m.material_id)
  if (idx >= 0) {
    favorites.splice(idx, 1)
    saveFavorites(favorites)
    return false
  }
  favorites.unshift({
    materialId: m.material_id,
    formula: m.formula,
    spaceGroup: m.space_group,
    topology: m.topology,
    addedAt: Date.now(),
    elements: extractElements(m.formula),
    verified: m.verified,
  })
  saveFavorites(favorites)
  return true
}

function extractElements(formula: string): string[] {
  const matches = formula.match(/[A-Z][a-z]?/g)
  return matches ? [...new Set(matches)] : []
}

const PAGE_SIZE = 20

export default function PrototypeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [prototype, setPrototype] = useState<Prototype | null>(null)
  const [loading, setLoading] = useState(true)

  const [previewMaterial, setPreviewMaterial] = useState<Material | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchPrototype(id)
      .then((p) => {
        setPrototype(p)
        const favs = loadFavorites()
        const allMats = [...(p.raw_materials || []), ...(p.verified_materials || [])]
        const favSet = new Set<string>()
        allMats.forEach(m => {
          if (favs.some(f => f.materialId === m.material_id)) favSet.add(m.material_id)
        })
        setFavoriteIds(favSet)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (!prototype) return
    const allMats = [...(prototype.verified_materials || []), ...(prototype.raw_materials || [])]
    if (allMats.length === 0) return
    const firstMat = allMats[0]
    setPreviewLoading(true)
    fetchMaterial(firstMat.material_id)
      .then(setPreviewMaterial)
      .catch(() => {})
      .finally(() => setPreviewLoading(false))
  }, [prototype])

  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery])

  const allMaterials = useMemo(() => {
    if (!prototype) return []
    const raw = prototype.raw_materials || []
    const verified = prototype.verified_materials || []
    const verifiedIds = new Set(verified.map(m => m.material_id))
    const uniqueRaw = raw.filter(m => !verifiedIds.has(m.material_id))
    return [...verified, ...uniqueRaw]
  }, [prototype])

  const filteredMaterials = useMemo(() => {
    if (!searchQuery.trim()) return allMaterials
    const q = searchQuery.toLowerCase()
    return allMaterials.filter(m =>
      m.formula.toLowerCase().includes(q) ||
      m.space_group.toLowerCase().includes(q) ||
      m.topology.toLowerCase().includes(q) ||
      extractElements(m.formula).some(e => e.toLowerCase().includes(q))
    )
  }, [allMaterials, searchQuery])

  const totalPages = Math.max(1, Math.ceil(filteredMaterials.length / PAGE_SIZE))
  const safeCurrentPage = Math.min(currentPage, totalPages)
  const pagedMaterials = filteredMaterials.slice(
    (safeCurrentPage - 1) * PAGE_SIZE,
    safeCurrentPage * PAGE_SIZE
  )

  const toggleSelect = useCallback((materialId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(materialId)) next.delete(materialId)
      else if (next.size < 4) next.add(materialId)
      return next
    })
  }, [])

  const toggleFav = useCallback((m: MaterialListItem) => {
    const nowFav = toggleFavoriteItem(m)
    setFavoriteIds(prev => {
      const next = new Set(prev)
      if (nowFav) next.add(m.material_id)
      else next.delete(m.material_id)
      return next
    })
  }, [])

  const handleCompare = useCallback(() => {
    if (selectedIds.size < 2) return
    navigate(`/compare?ids=${Array.from(selectedIds).join(',')}`)
  }, [selectedIds, navigate])

  const verifiedCount = useMemo(() => {
    if (!prototype) return 0
    return (prototype.verified_materials || []).length
  }, [prototype])

  const verifyRate = prototype && prototype.material_count > 0
    ? (verifiedCount / prototype.material_count) * 100
    : 0

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!prototype) {
    return (
      <div className="text-center py-20 text-gray-500">
        <Hexagon className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>未找到该原型</p>
      </div>
    )
  }

  const tt = prototype.topology_theory
  const pc = prototype.prototype_crystallography
  const inputMainShifts = tt.input_main_shifts || []
  const expandedModes = tt.expanded_modes || []
  const expandedShifts = tt.expanded_shifts || []
  const realCompounds = prototype.real_compounds || []

  return (
    <div className="space-y-4 sm:space-y-6">
      <Link
        to="/prototypes"
        className="inline-flex items-center gap-2 text-gray-400 hover:text-cyan-400 text-sm transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        返回原型列表
      </Link>

      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{tt.prototype_id}</h1>
          <p className="text-gray-400 mt-1">
            {pc.ideal_space_group} · {pc.crystal_system} · {prototype.material_count} 个材料
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to={`/generate?topology=${encodeURIComponent(tt.prototype_id)}`}
            className="flex items-center gap-1.5 px-2 py-1 sm:px-3 sm:py-1.5 bg-violet-500/10 border border-violet-500/30 rounded-lg text-xs sm:text-sm text-violet-400 hover:bg-violet-500/20 transition-colors"
          >
            <FlaskConical className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            生成类似结构
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 mb-1">
            <Atom className="w-4 h-4 text-cyan-400" />
            <span className="text-gray-400 text-sm">总材料数</span>
          </div>
          <p className="text-2xl font-bold text-white">{prototype.material_count}</p>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-4 h-4 text-emerald-400" />
            <span className="text-gray-400 text-sm">已验证数</span>
          </div>
          <p className="text-2xl font-bold text-emerald-400">{verifiedCount}</p>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 mb-1">
            <Hexagon className="w-4 h-4 text-amber-400" />
            <span className="text-gray-400 text-sm">验证率</span>
          </div>
          <p className="text-2xl font-bold text-white">{verifyRate.toFixed(1)}%</p>
          <div className="mt-2 w-full bg-gray-700/50 rounded-full h-2">
            <div
              className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(verifyRate, 100)}%` }}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
          <h2 className="text-base sm:text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Network className="w-5 h-5 text-cyan-400" />
            拓扑理论
          </h2>
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-gray-400">原型编号</span>
              <p className="text-white font-mono mt-0.5">{tt.prototype_id}</p>
            </div>
            <div>
              <span className="text-gray-400">参考网格</span>
              <p className="text-white font-mono mt-0.5">{tt.reference_grid}</p>
            </div>
            <div>
              <span className="text-gray-400">输入主位移</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {inputMainShifts.map((s, i) => (
                  <span key={i} className="bg-cyan-500/10 text-cyan-400 px-2 py-0.5 rounded text-xs font-mono">
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <span className="text-gray-400">展开模式</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {expandedModes.map((m, i) => (
                  <span key={i} className="bg-violet-500/10 text-violet-400 px-2 py-0.5 rounded text-xs font-mono">
                    {m}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <span className="text-gray-400">展开位移</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {expandedShifts.map((s, i) => (
                  <span key={i} className="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded text-xs font-mono">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <h2 className="text-base sm:text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Layers className="w-5 h-5 text-violet-400" />
              晶体学信息
            </h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">理想空间群</span>
                <span className="text-white">{pc.ideal_space_group} (#{pc.space_group_number})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">晶系</span>
                <span className="text-white">{pc.crystal_system}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">电中性</span>
                <span className={pc.is_neutral ? 'text-emerald-400' : 'text-amber-400'}>
                  {pc.is_neutral ? '是' : '否'}
                </span>
              </div>
            </div>
            {Object.keys(pc.wyckoff_signature).length > 0 && (
              <div className="mt-4 pt-3 border-t border-gray-700/50">
                <span className="text-gray-400 text-sm">Wyckoff 签名</span>
                <div className="space-y-1 mt-2 text-sm">
                  {Object.entries(pc.wyckoff_signature).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-400">{key}</span>
                      <span className="text-white font-mono">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {realCompounds.length > 0 && (
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
              <h2 className="text-base sm:text-lg font-semibold text-white mb-3">
                实际化合物（{realCompounds.length}）
              </h2>
              <div className="space-y-2">
                {realCompounds.map((rc, i) => (
                  <div key={i} className="bg-gray-900/50 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-white font-medium">{rc.formula}</span>
                      {rc.mineral_name && (
                        <span className="text-violet-400 text-xs">{rc.mineral_name}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                      <span>来源: {rc.source_id}</span>
                      <span>RMSD: {rc.rmsd_to_ideal.toFixed(4)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
        <h2 className="text-base sm:text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Box className="w-5 h-5 text-cyan-400" />
          三维结构预览
        </h2>
        {previewLoading ? (
          <div className="flex items-center justify-center h-80">
            <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
            <span className="ml-2 text-gray-400 text-sm">加载结构数据...</span>
          </div>
        ) : previewMaterial && previewMaterial.cif_data?.atom_sites && previewMaterial.cif_data?.lattice ? (
          <div>
            <div className="mb-3 flex items-center gap-3 text-sm text-gray-400">
              <span>预览材料：</span>
              <Link
                to={`/materials/${previewMaterial.material_id}`}
                className="text-cyan-400 hover:text-cyan-300 font-medium"
              >
                {previewMaterial.formula}
              </Link>
              <span>·</span>
              <span>{previewMaterial.space_group}</span>
            </div>
            <Suspense fallback={<div className="h-64 sm:h-96 bg-gray-900 rounded-lg flex items-center justify-center"><div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>}>
              <CrystalViewer
                atoms={previewMaterial.cif_data.atom_sites}
                lattice={previewMaterial.cif_data.lattice}
                className="h-64 sm:h-96"
                showBonds
                showElementInfo
              />
            </Suspense>
          </div>
        ) : (
          <div className="flex items-center justify-center h-40 text-gray-500 text-sm">
            暂无材料数据可供预览
          </div>
        )}
      </div>

      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <h2 className="text-base sm:text-lg font-semibold text-white flex items-center gap-2">
            <Atom className="w-5 h-5 text-cyan-400" />
            材料列表（{filteredMaterials.length}）
          </h2>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="搜索化学式、空间群、元素..."
                className="pl-9 pr-3 py-1.5 bg-gray-900/50 border border-gray-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 w-full sm:w-64"
              />
            </div>
            {selectedIds.size >= 2 && (
              <button
                onClick={handleCompare}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-sm text-cyan-400 hover:bg-cyan-500/20 transition-colors"
              >
                <GitCompare className="w-4 h-4" />
                对比所选（{selectedIds.size}）
              </button>
            )}
          </div>
        </div>

        {filteredMaterials.length === 0 ? (
          <div className="text-center py-10 text-gray-500 text-sm">
            {searchQuery ? '未找到匹配的材料' : '暂无材料数据'}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700/50">
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium w-10">
                      <button
                        onClick={() => {
                          if (selectedIds.size === pagedMaterials.length && pagedMaterials.length > 0) {
                            setSelectedIds(new Set())
                          } else {
                            const next = new Set<string>()
                            pagedMaterials.forEach(m => {
                              if (next.size < 4) next.add(m.material_id)
                            })
                            setSelectedIds(next)
                          }
                        }}
                        className="text-gray-400 hover:text-cyan-400 transition-colors"
                        title="全选/取消全选（最多4个）"
                      >
                        {pagedMaterials.length > 0 && selectedIds.size === pagedMaterials.length
                          ? <CheckSquare className="w-4 h-4" />
                          : <Square className="w-4 h-4" />
                        }
                      </button>
                    </th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium">化学式</th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium">元素</th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium">空间群</th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium">拓扑</th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium">状态</th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium w-16">收藏</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/30">
                  {pagedMaterials.map((m) => {
                    const elements = extractElements(m.formula)
                    const isFav = favoriteIds.has(m.material_id)
                    const isSelected = selectedIds.has(m.material_id)
                    return (
                      <tr key={m.material_id} className={`hover:bg-gray-700/20 ${isSelected ? 'bg-cyan-500/5' : ''}`}>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                          <button
                            onClick={() => toggleSelect(m.material_id)}
                            className="text-gray-400 hover:text-cyan-400 transition-colors"
                            title={isSelected ? '取消选择' : '选择对比（最多4个）'}
                          >
                            {isSelected
                              ? <CheckSquare className="w-4 h-4 text-cyan-400" />
                              : <Square className="w-4 h-4" />
                            }
                          </button>
                        </td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                          <Link to={`/materials/${m.material_id}`} className="text-cyan-400 hover:text-cyan-300 font-medium">
                            {m.formula}
                          </Link>
                        </td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                          <div className="flex flex-wrap gap-1">
                            {elements.map(el => (
                              <span key={el} className="bg-gray-700/50 text-gray-300 px-1.5 py-0.5 rounded text-xs">
                                {el}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-2 text-gray-300">{m.space_group}</td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-2 text-gray-300">{m.topology}</td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            m.verified ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                          }`}>
                            {m.verified ? '已验证' : '原始'}
                          </span>
                        </td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                          <button
                            onClick={() => toggleFav(m)}
                            className={`transition-colors ${
                              isFav ? 'text-rose-400 hover:text-rose-300' : 'text-gray-500 hover:text-rose-400'
                            }`}
                            title={isFav ? '取消收藏' : '添加收藏'}
                          >
                            <Heart className={`w-4 h-4 ${isFav ? 'fill-current' : ''}`} />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mt-4 pt-3 border-t border-gray-700/50">
                <span className="text-xs sm:text-sm text-gray-400">
                  第 {safeCurrentPage} / {totalPages} 页，共 {filteredMaterials.length} 条
                </span>
                <div className="flex items-center gap-0.5 sm:gap-1">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={safeCurrentPage <= 1}
                    className="p-1 sm:p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  </button>
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(p => p === 1 || p === totalPages || Math.abs(p - safeCurrentPage) <= 1)
                    .reduce<(number | string)[]>((acc, p, idx, arr) => {
                      if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push('...')
                      acc.push(p)
                      return acc
                    }, [])
                    .map((p, i) =>
                      typeof p === 'string' ? (
                        <span key={`ellipsis-${i}`} className="px-0.5 sm:px-1 text-gray-600 text-xs sm:text-sm">...</span>
                      ) : (
                        <button
                          key={p}
                          onClick={() => setCurrentPage(p)}
                          className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
                            p === safeCurrentPage
                              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                              : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
                          }`}
                        >
                          {p}
                        </button>
                      )
                    )
                  }
                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={safeCurrentPage >= totalPages}
                    className="p-1 sm:p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

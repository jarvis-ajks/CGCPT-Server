import { useEffect, useState, useCallback, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Atom, Search, LayoutGrid, List, ArrowUpDown, Heart, GitCompare,
  ChevronLeft, ChevronRight, CheckSquare, Square, Filter, X
} from 'lucide-react'
import { fetchMaterials } from '../api/client'
import type { MaterialListItem } from '../types'

const ELEMENT_COLORS: Record<string, string> = {
  H: '#ffffff', O: '#ff0d0d', F: '#90e050', N: '#3050f8', C: '#909090',
  B: '#ffb5b5', Si: '#f0c8a0', P: '#ff8000', S: '#ffff30', Cl: '#1ff01f',
  Li: '#cc80ff', Na: '#ab5cf2', K: '#8f40d4', Rb: '#702eb0', Cs: '#57178f',
  Be: '#c2ff00', Mg: '#8aff00', Ca: '#3dff00', Sr: '#00ff00', Ba: '#00c900',
  Ti: '#bfc2c7', V: '#a6a6ab', Cr: '#8a99c7', Mn: '#9c7ac7', Fe: '#e06633',
  Co: '#f090a0', Ni: '#50d050', Cu: '#c88033', Zn: '#7d80b0', Al: '#bfa6a6',
  Ga: '#c28f8f', In: '#a67573', Sn: '#668080', Pb: '#575961', Bi: '#9e4fb5',
}

type ViewMode = 'table' | 'card'
type SortKey = 'formula' | 'space_group' | 'topology'
type SortDir = 'asc' | 'desc'
type FilterStatus = 'all' | 'verified' | 'raw'

function extractElements(formula: string): string[] {
  return formula.match(/[A-Z][a-z]?/g) || []
}

function loadFavorites(): string[] {
  try {
    return JSON.parse(localStorage.getItem('cgcpt_favorites') || '[]')
  } catch {
    return []
  }
}

function saveFavorites(ids: string[]) {
  localStorage.setItem('cgcpt_favorites', JSON.stringify(ids))
}

function isFavorite(materialId: string): boolean {
  return loadFavorites().includes(materialId)
}

function toggleFavorite(materialId: string) {
  const favs = loadFavorites()
  if (favs.includes(materialId)) {
    saveFavorites(favs.filter((id) => id !== materialId))
  } else {
    saveFavorites([...favs, materialId])
  }
}

function ElementTag({ element }: { element: string }) {
  const color = ELEMENT_COLORS[element] || '#888888'
  return (
    <span
      className="inline-flex items-center justify-center px-1.5 py-1 sm:px-1.5 sm:py-0.5 rounded text-[10px] sm:text-xs font-bold leading-none min-w-[24px] sm:min-w-0"
      style={{
        backgroundColor: color + '25',
        color: color,
        border: `1px solid ${color}40`,
      }}
    >
      {element}
    </span>
  )
}

function ElementTags({ formula }: { formula: string }) {
  const elements = extractElements(formula)
  return (
    <div className="flex flex-wrap gap-1">
      {elements.map((el, i) => (
        <ElementTag key={`${el}-${i}`} element={el} />
      ))}
    </div>
  )
}

export default function MaterialsBrowser() {
  const navigate = useNavigate()
  const [materials, setMaterials] = useState<MaterialListItem[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [formulaSearch, setFormulaSearch] = useState('')
  const [topologyFilter, setTopologyFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all')
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [sortKey, setSortKey] = useState<SortKey>('formula')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const perPage = 20

  useEffect(() => {
    setLoading(true)
    const params: Record<string, string> = {
      page: String(page),
      per_page: String(perPage),
    }
    if (topologyFilter) params.topology = topologyFilter
    if (formulaSearch) params.formula = formulaSearch
    if (statusFilter === 'verified') params.verified = 'true'
    else if (statusFilter === 'raw') params.verified = 'false'
    fetchMaterials(params)
      .then((res) => {
        setMaterials(res.materials)
        setTotal(res.total)
        setTotalPages(res.total_pages)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [page, topologyFilter, formulaSearch, statusFilter])

  const sortedMaterials = useMemo(() => {
    const sorted = [...materials].sort((a, b) => {
      let cmp = 0
      if (sortKey === 'formula') cmp = a.formula.localeCompare(b.formula)
      else if (sortKey === 'space_group') cmp = a.space_group.localeCompare(b.space_group)
      else if (sortKey === 'topology') cmp = a.topology.localeCompare(b.topology)
      return sortDir === 'asc' ? cmp : -cmp
    })
    return sorted
  }, [materials, sortKey, sortDir])

  const handleSort = useCallback((key: SortKey) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
      } else {
        setSortDir('asc')
      }
      return key
    })
  }, [])

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === sortedMaterials.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(sortedMaterials.map((m) => m.material_id)))
    }
  }, [sortedMaterials, selectedIds])

  const handleCompare = useCallback(() => {
    if (selectedIds.size === 0) return
    navigate(`/compare?ids=${Array.from(selectedIds).join(',')}`)
  }, [selectedIds, navigate])

  const handleToggleFav = useCallback((materialId: string) => {
    toggleFavorite(materialId)
  }, [])

  const resetFilters = useCallback(() => {
    setFormulaSearch('')
    setTopologyFilter('')
    setStatusFilter('all')
    setPage(1)
  }, [])

  const hasActiveFilters = formulaSearch || topologyFilter || statusFilter !== 'all'

  const startIdx = (page - 1) * perPage + 1
  const endIdx = Math.min(page * perPage, total)

  const SortHeader = ({ label, sortKeyValue }: { label: string; sortKeyValue: SortKey }) => (
    <button
      onClick={() => handleSort(sortKeyValue)}
      className="inline-flex items-center gap-1 text-xs font-medium text-gray-400 uppercase tracking-wider hover:text-gray-200 transition-colors"
    >
      {label}
      <ArrowUpDown
        className={`w-3 h-3 ${sortKey === sortKeyValue ? 'text-cyan-400' : 'text-gray-600'}`}
      />
      {sortKey === sortKeyValue && (
        <span className="text-[10px] text-cyan-400">{sortDir === 'asc' ? '↑' : '↓'}</span>
      )}
    </button>
  )

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-base sm:text-lg font-bold text-white">材料浏览</h1>
        <p className="text-gray-400 mt-1">浏览数据库中的晶体结构（共 {total} 条）</p>
      </div>

      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4 space-y-4">
        <div className="flex flex-col sm:flex-row flex-wrap items-center gap-3">
          <div className="relative w-full sm:flex-1 sm:min-w-[200px] sm:max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={formulaSearch}
              onChange={(e) => { setFormulaSearch(e.target.value); setPage(1) }}
              placeholder="搜索化学式..."
              className="w-full bg-gray-900 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <div className="relative w-full sm:flex-1 sm:min-w-[200px] sm:max-w-xs">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={topologyFilter}
              onChange={(e) => { setTopologyFilter(e.target.value); setPage(1) }}
              placeholder="按拓扑筛选..."
              className="w-full bg-gray-900 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
            <div className="flex items-center gap-1 bg-gray-900 border border-gray-700 rounded-lg p-0.5">
              {(['all', 'verified', 'raw'] as FilterStatus[]).map((s) => (
                <button
                  key={s}
                  onClick={() => { setStatusFilter(s); setPage(1) }}
                  className={`px-2 py-1.5 sm:px-3 sm:py-1.5 rounded-md text-xs font-medium transition-colors min-h-[36px] ${
                    statusFilter === s
                      ? 'bg-cyan-500/20 text-cyan-400'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {s === 'all' ? '全部' : s === 'verified' ? '已验证' : '原始'}
                </button>
              ))}
            </div>
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="flex items-center gap-1 px-2 py-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              <X className="w-3 h-3" />
              清除筛选
            </button>
          )}
          <div className="ml-auto flex items-center gap-2">
            {selectedIds.size > 0 && (
              <button
                onClick={handleCompare}
                className="flex items-center gap-1.5 px-2 py-1 sm:px-3 sm:py-1.5 bg-cyan-500/20 text-cyan-400 rounded-lg text-xs font-medium hover:bg-cyan-500/30 transition-colors"
              >
                <GitCompare className="w-3.5 h-3.5" />
                对比 ({selectedIds.size})
              </button>
            )}
            <div className="flex items-center gap-1 bg-gray-900 border border-gray-700 rounded-lg p-0.5">
              <button
                onClick={() => setViewMode('table')}
                className={`p-2 rounded-md transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center ${
                  viewMode === 'table' ? 'bg-gray-700 text-cyan-400' : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                <List className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('card')}
                className={`p-2 rounded-md transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center ${
                  viewMode === 'card' ? 'bg-gray-700 text-cyan-400' : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : materials.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <Atom className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>未找到材料</p>
        </div>
      ) : viewMode === 'table' ? (
        <>
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700/50">
                  <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 w-10">
                    <button onClick={toggleSelectAll} className="touch-icon-btn text-gray-400 hover:text-gray-200 transition-colors">
                      {selectedIds.size === sortedMaterials.length && sortedMaterials.length > 0 ? (
                        <CheckSquare className="w-4 h-4 text-cyan-400" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                    </button>
                  </th>
                  <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2">
                    <SortHeader label="化学式" sortKeyValue="formula" />
                  </th>
                  <th className="hidden sm:table-cell text-left px-2 py-1.5 sm:px-3 sm:py-2">
                    <SortHeader label="空间群" sortKeyValue="space_group" />
                  </th>
                  <th className="hidden sm:table-cell text-left px-2 py-1.5 sm:px-3 sm:py-2">
                    <SortHeader label="拓扑" sortKeyValue="topology" />
                  </th>
                  <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-xs font-medium text-gray-400 uppercase tracking-wider">
                    元素
                  </th>
                  <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-xs font-medium text-gray-400 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="text-right px-2 py-1.5 sm:px-3 sm:py-2 text-xs font-medium text-gray-400 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/30">
                {sortedMaterials.map((m) => (
                  <tr
                    key={m.material_id}
                    className={`hover:bg-gray-700/20 transition-colors ${
                      selectedIds.has(m.material_id) ? 'bg-cyan-500/5' : ''
                    }`}
                  >
                    <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                      <button
                        onClick={() => toggleSelect(m.material_id)}
                        className="touch-icon-btn text-gray-400 hover:text-gray-200 transition-colors"
                      >
                        {selectedIds.has(m.material_id) ? (
                          <CheckSquare className="w-4 h-4 text-cyan-400" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                    <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                      <Link
                        to={`/materials/${m.material_id}`}
                        className="text-cyan-400 hover:text-cyan-300 font-medium"
                      >
                        {m.formula}
                      </Link>
                    </td>
                    <td className="hidden sm:table-cell px-2 py-1.5 sm:px-3 sm:py-2 text-gray-300 text-sm">{m.space_group}</td>
                    <td className="hidden sm:table-cell px-2 py-1.5 sm:px-3 sm:py-2 text-gray-300 text-sm">{m.topology}</td>
                    <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                      <ElementTags formula={m.formula} />
                    </td>
                    <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          m.verified
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : 'bg-amber-500/10 text-amber-400'
                        }`}
                      >
                        {m.verified ? '已验证' : '原始'}
                      </span>
                    </td>
                    <td className="px-2 py-1.5 sm:px-3 sm:py-2">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleToggleFav(m.material_id)}
                          className="touch-icon-btn rounded transition-colors hover:bg-gray-700/50"
                        >
                          <Heart
                            className={`w-4 h-4 ${
                              isFavorite(m.material_id) ? 'text-rose-500 fill-rose-500' : 'text-gray-500'
                            }`}
                          />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs sm:text-sm text-gray-400">
                显示第 {startIdx}-{endIdx} 条，共 {total} 条
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2.5 sm:p-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:border-cyan-500/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs sm:text-sm text-gray-400">
                  第 {page} 页 / 共 {totalPages} 页
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2.5 sm:p-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:border-cyan-500/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedMaterials.map((m) => (
              <div
                key={m.material_id}
                className={`bg-gray-800/50 border rounded-xl p-3 sm:p-4 transition-colors hover:border-gray-600 ${
                  selectedIds.has(m.material_id) ? 'border-cyan-500/50' : 'border-gray-700/50'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <Link
                    to={`/materials/${m.material_id}`}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold text-sm"
                  >
                    {m.formula}
                  </Link>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => toggleSelect(m.material_id)}
                      className="touch-icon-btn rounded transition-colors hover:bg-gray-700/50"
                    >
                      {selectedIds.has(m.material_id) ? (
                        <CheckSquare className="w-3.5 h-3.5 text-cyan-400" />
                      ) : (
                        <Square className="w-3.5 h-3.5 text-gray-500" />
                      )}
                    </button>
                    <button
                      onClick={() => handleToggleFav(m.material_id)}
                      className="touch-icon-btn rounded transition-colors hover:bg-gray-700/50"
                    >
                      <Heart
                        className={`w-3.5 h-3.5 ${
                          isFavorite(m.material_id) ? 'text-rose-500 fill-rose-500' : 'text-gray-500'
                        }`}
                      />
                    </button>
                  </div>
                </div>

                <div className="mb-3">
                  <ElementTags formula={m.formula} />
                </div>

                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">空间群</span>
                    <span className="text-gray-300">{m.space_group}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">拓扑</span>
                    <span className="text-gray-300">{m.topology}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">状态</span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${
                        m.verified
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : 'bg-amber-500/10 text-amber-400'
                      }`}
                    >
                      {m.verified ? '已验证' : '原始'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs sm:text-sm text-gray-400">
                显示第 {startIdx}-{endIdx} 条，共 {total} 条
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2.5 sm:p-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:border-cyan-500/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs sm:text-sm text-gray-400">
                  第 {page} 页 / 共 {totalPages} 页
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2.5 sm:p-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:border-cyan-500/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

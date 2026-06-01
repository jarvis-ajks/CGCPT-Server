import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search, Filter, X, ChevronLeft, ChevronRight, Save, FolderOpen, ArrowUpDown, LayoutGrid, List, GitCompare, CheckSquare, Square } from 'lucide-react'
import { fetchMaterials } from '../api/client'
import type { MaterialListItem } from '../types'
import ElementPicker from '../components/ElementPicker'

interface SearchFilters {
  elements: string[]
  excludeElements: string[]
  crystalSystems: string[]
  topology: string
  formulaPattern: string
  verifiedOnly: boolean
}

interface SavedSearch {
  id: string
  name: string
  filters: SearchFilters
  createdAt: number
}

const CRYSTAL_SYSTEMS = [
  { value: 'cubic', label: '立方晶系' },
  { value: 'hexagonal', label: '六方晶系' },
  { value: 'trigonal', label: '三方晶系' },
  { value: 'tetragonal', label: '四方晶系' },
  { value: 'orthorhombic', label: '正交晶系' },
  { value: 'monoclinic', label: '单斜晶系' },
  { value: 'triclinic', label: '三斜晶系' },
]

const CRYSTAL_SYSTEM_KEYWORDS: Record<string, string[]> = {
  cubic: ['Fm-3m', 'Fm3m', 'Pm-3m', 'Pm3m', 'Im-3m', 'Im3m', 'Fd-3m', 'Fd3m', 'Pn-3m', 'Pn3m', 'Pm-3', 'Pm3', 'Ia-3', 'Pa-3'],
  hexagonal: ['P6/mmm', 'P63/mmc', 'P6_3/mmc', 'P6_3mc', 'P6_3cm', 'P6_3/mcm', 'P-6m2', 'P-62m', 'P6mm', 'P6/m', 'P6_3/m'],
  trigonal: ['R-3m', 'R3m', 'R-3c', 'R3c', 'R-3', 'R3', 'P3m1', 'P-3m1', 'P31m', 'P312', 'P321'],
  tetragonal: ['I4/mmm', 'P4/mmm', 'I4/mcm', 'P4_2/mnm', 'P4_2/nmc', 'P4mm', 'I4mm', 'P4/m', 'I4/m', 'P4_2/m', 'I-42m', 'P-4m2', 'P-421m'],
  orthorhombic: ['Pnma', 'Pbam', 'Pcmn', 'Pnma', 'Cmcm', 'Fmmm', 'Immm', 'Pmmm', 'Pnnm', 'Cccm', 'Pnma', 'Amm2', 'Pma2', 'Cmc2_1'],
  monoclinic: ['P2_1/c', 'P2_1/m', 'C2/c', 'C2/m', 'P2/c', 'P2/m', 'I2/m', 'Cc', 'P2_1', 'C2'],
  triclinic: ['P-1', 'P1'],
}

const ELEMENT_COLORS: Record<string, string> = {
  H: '#ffffff', O: '#ff0d0d', F: '#90e050', N: '#3050f8', C: '#909090',
  B: '#ffb5b5', Si: '#f0c8a0', P: '#ff8000', S: '#ffff30', Cl: '#1ff01f',
  Li: '#cc80ff', Na: '#ab5cf2', K: '#8f40d4', Rb: '#702eb0', Cs: '#57178f',
  Be: '#c2ff00', Mg: '#8aff00', Ca: '#3dff00', Sr: '#00ff00', Ba: '#00c900',
  Ti: '#bfc2c7', V: '#a6a6ab', Cr: '#8a99c7', Mn: '#9c7ac7', Fe: '#e06633',
  Co: '#f090a0', Ni: '#50d050', Cu: '#c88033', Zn: '#7d80b0', Al: '#bfa6a6',
}

const defaultFilters: SearchFilters = {
  elements: [],
  excludeElements: [],
  crystalSystems: [],
  topology: '',
  formulaPattern: '',
  verifiedOnly: false,
}

function extractElements(formula: string): string[] {
  return formula.match(/[A-Z][a-z]?/g) || []
}

function loadSavedSearches(): SavedSearch[] {
  try {
    const data = localStorage.getItem('cgcpt_saved_searches')
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveSavedSearches(searches: SavedSearch[]): void {
  localStorage.setItem('cgcpt_saved_searches', JSON.stringify(searches))
}

type SortKey = 'formula' | 'space_group' | 'topology'
type SortDir = 'asc' | 'desc'
type ViewMode = 'table' | 'card'

export default function AdvancedSearch() {
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters)
  const [results, setResults] = useState<MaterialListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [showSavedSearches, setShowSavedSearches] = useState(false)
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>(loadSavedSearches)
  const [searchName, setSearchName] = useState('')
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey>('formula')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const perPage = 20
  const navigate = useNavigate()

  useEffect(() => {
    performSearch()
  }, [page])

  const performSearch = async () => {
    setLoading(true)
    try {
      const res = await fetchMaterials({ page: String(page), per_page: '500' })
      let filtered = res.materials

      if (filters.elements.length > 0) {
        filtered = filtered.filter(m => {
          const els = extractElements(m.formula)
          return filters.elements.every(fe => els.includes(fe))
        })
      }

      if (filters.excludeElements.length > 0) {
        filtered = filtered.filter(m => {
          const els = extractElements(m.formula)
          return !filters.excludeElements.some(fe => els.includes(fe))
        })
      }

      if (filters.crystalSystems.length > 0) {
        filtered = filtered.filter(m => {
          return filters.crystalSystems.some(cs => {
            const keywords = CRYSTAL_SYSTEM_KEYWORDS[cs] || []
            return keywords.some(kw => m.space_group.includes(kw))
          })
        })
      }

      if (filters.topology) {
        const topoLower = filters.topology.toLowerCase()
        filtered = filtered.filter(m =>
          m.topology?.toLowerCase().includes(topoLower)
        )
      }

      if (filters.formulaPattern) {
        try {
          const regex = new RegExp(filters.formulaPattern, 'i')
          filtered = filtered.filter(m => regex.test(m.formula))
        } catch {}
      }

      if (filters.verifiedOnly) {
        filtered = filtered.filter(m => m.verified)
      }

      setResults(filtered)
      setTotal(filtered.length)
      setHasSearched(true)
    } catch {
      setResults([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    setPage(1)
    performSearch()
  }

  const toggleElement = (element: string, exclude: boolean = false) => {
    if (exclude) {
      setFilters(prev => ({
        ...prev,
        excludeElements: prev.excludeElements.includes(element)
          ? prev.excludeElements.filter(e => e !== element)
          : [...prev.excludeElements, element]
      }))
    } else {
      setFilters(prev => ({
        ...prev,
        elements: prev.elements.includes(element)
          ? prev.elements.filter(e => e !== element)
          : [...prev.elements, element]
      }))
    }
  }

  const toggleCrystalSystem = (cs: string) => {
    setFilters(prev => ({
      ...prev,
      crystalSystems: prev.crystalSystems.includes(cs)
        ? prev.crystalSystems.filter(c => c !== cs)
        : [...prev.crystalSystems, cs]
    }))
  }

  const clearFilters = () => {
    setFilters(defaultFilters)
    setHasSearched(false)
  }

  const saveSearch = () => {
    if (!searchName.trim()) return
    const newSearch: SavedSearch = {
      id: Date.now().toString(),
      name: searchName,
      filters: { ...filters },
      createdAt: Date.now()
    }
    const updated = [newSearch, ...savedSearches]
    setSavedSearches(updated)
    saveSavedSearches(updated)
    setShowSaveDialog(false)
    setSearchName('')
  }

  const loadSearch = (search: SavedSearch) => {
    setFilters(search.filters)
    setShowSavedSearches(false)
    setPage(1)
    setTimeout(() => performSearch(), 0)
  }

  const deleteSearch = (id: string) => {
    const updated = savedSearches.filter(s => s.id !== id)
    setSavedSearches(updated)
    saveSavedSearches(updated)
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleCompare = () => {
    const ids = Array.from(selectedIds).slice(0, 4)
    if (ids.length < 2) return
    navigate(`/compare?ids=${ids.join(',')}`)
  }

  const sortedResults = useMemo(() => {
    const result = [...results]
    result.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'formula': cmp = a.formula.localeCompare(b.formula); break
        case 'space_group': cmp = a.space_group.localeCompare(b.space_group); break
        case 'topology': cmp = (a.topology || '').localeCompare(b.topology || ''); break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
    return result
  }, [results, sortKey, sortDir])

  const totalPages = Math.ceil(total / perPage)
  const activeFilterCount = filters.elements.length + filters.excludeElements.length + filters.crystalSystems.length + (filters.topology ? 1 : 0) + (filters.formulaPattern ? 1 : 0) + (filters.verifiedOnly ? 1 : 0)

  const SortButton = ({ field, label }: { field: SortKey; label: string }) => (
    <button
      onClick={() => handleSort(field)}
      className={`flex items-center gap-1 text-xs font-medium transition-colors ${
        sortKey === field ? 'text-cyan-400' : 'text-gray-500 hover:text-gray-300'
      }`}
    >
      {label}
      <ArrowUpDown className="w-3 h-3" />
    </button>
  )

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2 sm:gap-3">
            <Filter className="w-6 h-6 sm:w-7 sm:h-7 text-cyan-400" />
            高级搜索
          </h1>
          <p className="text-gray-400 mt-1 text-sm">
            通过多种条件筛选材料
            {activeFilterCount > 0 && (
              <span className="ml-2 text-cyan-400">({activeFilterCount} 个活跃条件)</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {selectedIds.size >= 2 && (
            <button
              onClick={handleCompare}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors text-sm"
            >
              <GitCompare className="w-4 h-4" />
              对比 ({selectedIds.size})
            </button>
          )}
          <button
            onClick={() => setShowSavedSearches(!showSavedSearches)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:text-white hover:border-cyan-500/50 transition-colors text-sm"
          >
            <FolderOpen className="w-4 h-4" />
            <span className="hidden sm:inline">已保存搜索</span>
            <span className="sm:hidden">已保存</span>
          </button>
          <button
            onClick={() => setShowSaveDialog(true)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-medium hover:bg-cyan-500/20 transition-colors text-sm"
          >
            <Save className="w-4 h-4" />
            <span className="hidden sm:inline">保存搜索</span>
            <span className="sm:hidden">保存</span>
          </button>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-4 sm:gap-6">
        <div className="w-full lg:w-80 flex-shrink-0 space-y-4">
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-white">筛选条件</h3>
              <button
                onClick={clearFilters}
                className="text-xs text-gray-400 hover:text-white transition-colors px-2 py-1 touch-manipulation"
              >
                重置
              </button>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">
                必须包含元素
              </label>
              <div className="flex flex-wrap gap-2">
                {filters.elements.map(el => (
                  <button
                    key={el}
                    onClick={() => toggleElement(el)}
                    className="px-2.5 py-1.5 sm:px-2 sm:py-1 rounded text-xs font-medium transition-colors min-h-[36px] sm:min-h-0"
                    style={{
                      backgroundColor: (ELEMENT_COLORS[el] || '#888') + '25',
                      color: ELEMENT_COLORS[el] || '#888'
                    }}
                  >
                    {el} ×
                  </button>
                ))}
              </div>
              <div className="mt-2">
                <ElementPicker
                  value=""
                  onChange={(el) => toggleElement(el)}
                  label="添加元素"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">
                排除元素
              </label>
              <div className="flex flex-wrap gap-2">
                {filters.excludeElements.map(el => (
                  <button
                    key={el}
                    onClick={() => toggleElement(el, true)}
                    className="px-2.5 py-1.5 sm:px-2 sm:py-1 rounded bg-rose-500/20 text-rose-400 text-xs hover:bg-rose-500/30 transition-colors min-h-[36px] sm:min-h-0"
                  >
                    {el} ×
                  </button>
                ))}
              </div>
              <div className="mt-2">
                <ElementPicker
                  value=""
                  onChange={(el) => toggleElement(el, true)}
                  label="添加排除"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">
                拓扑类型
              </label>
              <input
                type="text"
                value={filters.topology}
                onChange={(e) => setFilters(prev => ({ ...prev, topology: e.target.value }))}
                placeholder="输入拓扑名称..."
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">
                晶系
              </label>
              <div className="space-y-2">
                {CRYSTAL_SYSTEMS.map(cs => (
                  <label key={cs.value} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.crystalSystems.includes(cs.value)}
                      onChange={() => toggleCrystalSystem(cs.value)}
                      className="w-5 h-5 rounded border-gray-600 bg-gray-900 text-cyan-500 focus:ring-cyan-500"
                    />
                    <span className="text-sm text-gray-300">{cs.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">
                化学式模式 (正则表达式)
              </label>
              <input
                type="text"
                value={filters.formulaPattern}
                onChange={(e) => setFilters(prev => ({ ...prev, formulaPattern: e.target.value }))}
                placeholder="如: ^A.*B$ 或 ABO"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.verifiedOnly}
                onChange={(e) => setFilters(prev => ({ ...prev, verifiedOnly: e.target.checked }))}
                className="w-5 h-5 rounded border-gray-600 bg-gray-900 text-cyan-500 focus:ring-cyan-500"
              />
              <span className="text-sm text-gray-300">仅显示已验证</span>
            </label>

            <button
              onClick={handleSearch}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors"
            >
              <Search className="w-4 h-4" />
              搜索
            </button>
          </div>

          {showSavedSearches && (
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
              <h3 className="text-sm font-medium text-white mb-3">已保存的搜索</h3>
              {savedSearches.length === 0 ? (
                <p className="text-sm text-gray-500">暂无保存的搜索</p>
              ) : (
                <div className="space-y-2">
                  {savedSearches.map(s => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between p-2 rounded bg-gray-900/50"
                    >
                      <button
                        onClick={() => loadSearch(s)}
                        className="text-sm text-gray-300 hover:text-cyan-400 transition-colors"
                      >
                        {s.name}
                      </button>
                      <button
                        onClick={() => deleteSearch(s.id)}
                        className="touch-icon-btn text-gray-500 hover:text-rose-400 transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex-1 space-y-4">
          {hasSearched && (
            <div className="bg-gray-800/30 border border-gray-700/50 rounded-lg px-3 sm:px-4 py-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <p className="text-sm text-gray-400">
                匹配结果: <span className="text-cyan-400 font-medium">{total}</span> 个材料
              </p>
              <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                  <SortButton field="formula" label="化学式" />
                  <SortButton field="space_group" label="空间群" />
                  <SortButton field="topology" label="拓扑" />
                </div>
                <div className="flex items-center gap-1 bg-gray-800/50 border border-gray-700/50 rounded-lg p-0.5">
                  <button
                    onClick={() => setViewMode('table')}
                    className={`p-2 rounded transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center ${viewMode === 'table' ? 'bg-cyan-500/20 text-cyan-400' : 'text-gray-500 hover:text-white'}`}
                  >
                    <List className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setViewMode('card')}
                    className={`p-2 rounded transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center ${viewMode === 'card' ? 'bg-cyan-500/20 text-cyan-400' : 'text-gray-500 hover:text-white'}`}
                  >
                    <LayoutGrid className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : !hasSearched ? (
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-8 sm:p-12 text-center">
              <Search className="w-12 h-12 mx-auto mb-3 text-gray-600" />
              <p className="text-gray-400">设置筛选条件并点击搜索</p>
              <p className="text-gray-600 text-sm mt-2">支持按元素、拓扑、晶系、化学式正则等多种条件组合筛选</p>
            </div>
          ) : results.length === 0 ? (
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-8 sm:p-12 text-center">
              <Search className="w-12 h-12 mx-auto mb-3 text-gray-600" />
              <p className="text-gray-400">未找到匹配的材料</p>
              <p className="text-gray-600 text-sm mt-2">尝试调整筛选条件</p>
            </div>
          ) : viewMode === 'table' ? (
            <>
              <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-700/50">
                        <th className="px-2 py-1.5 sm:px-3 sm:py-3 w-10"></th>
                        <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                          化学式
                        </th>
                        <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                          元素
                        </th>
                        <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider hidden md:table-cell">
                          空间群
                        </th>
                        <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider hidden lg:table-cell">
                          拓扑
                        </th>
                        <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                          状态
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/30">
                      {sortedResults.slice((page - 1) * perPage, page * perPage).map((m) => {
                        const els = extractElements(m.formula)
                        return (
                          <tr key={m.material_id} className="hover:bg-gray-700/20 transition-colors">
                            <td className="px-2 py-1.5 sm:px-3 sm:py-3">
                              <button onClick={() => toggleSelect(m.material_id)} className="touch-icon-btn">
                                {selectedIds.has(m.material_id)
                                  ? <CheckSquare className="w-4 h-4 text-cyan-400" />
                                  : <Square className="w-4 h-4 text-gray-600 hover:text-gray-400" />
                                }
                              </button>
                            </td>
                            <td className="px-2 py-1.5 sm:px-3 sm:py-3">
                              <Link to={`/materials/${m.material_id}`} className="text-cyan-400 hover:text-cyan-300 font-medium text-sm">
                                {m.formula}
                              </Link>
                              <div className="sm:hidden text-xs text-gray-500 mt-0.5">{m.space_group}</div>
                            </td>
                            <td className="px-2 py-1.5 sm:px-3 sm:py-3 hidden sm:table-cell">
                              <div className="flex gap-1">
                                {els.slice(0, 5).map(el => (
                                  <span
                                    key={el}
                                    className="w-6 h-6 sm:w-5 sm:h-5 rounded text-[10px] font-bold flex items-center justify-center"
                                    style={{
                                      backgroundColor: (ELEMENT_COLORS[el] || '#888') + '25',
                                      color: ELEMENT_COLORS[el] || '#888'
                                    }}
                                  >
                                    {el}
                                  </span>
                                ))}
                                {els.length > 5 && <span className="text-xs text-gray-500">+{els.length - 5}</span>}
                              </div>
                            </td>
                            <td className="px-2 py-1.5 sm:px-3 sm:py-3 text-gray-300 text-sm hidden md:table-cell">{m.space_group}</td>
                            <td className="px-2 py-1.5 sm:px-3 sm:py-3 text-gray-300 text-sm hidden lg:table-cell">{m.topology}</td>
                            <td className="px-2 py-1.5 sm:px-3 sm:py-3">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                m.verified ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                              }`}>
                                {m.verified ? '已验证' : '原始'}
                              </span>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:border-cyan-500/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-sm text-gray-400">
                    第 {page} 页 / 共 {totalPages} 页
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:border-cyan-500/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
              {sortedResults.slice((page - 1) * perPage, page * perPage).map((m) => {
                const els = extractElements(m.formula)
                return (
                  <div
                    key={m.material_id}
                    className={`bg-gray-800/50 border rounded-xl p-3 sm:p-4 transition-all group ${
                      selectedIds.has(m.material_id)
                        ? 'border-cyan-500/50 bg-cyan-500/5'
                        : 'border-gray-700/50 hover:border-cyan-500/30'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <Link to={`/materials/${m.material_id}`} className="flex-1 min-w-0">
                        <h3 className="text-base font-semibold text-white group-hover:text-cyan-400 transition-colors truncate">
                          {m.formula}
                        </h3>
                      </Link>
                      <button onClick={() => toggleSelect(m.material_id)} className="flex-shrink-0 ml-2 touch-icon-btn">
                        {selectedIds.has(m.material_id)
                          ? <CheckSquare className="w-4 h-4 text-cyan-400" />
                          : <Square className="w-4 h-4 text-gray-600 hover:text-gray-400" />
                        }
                      </button>
                    </div>
                    <div className="flex gap-1 mb-2">
                      {els.slice(0, 6).map(el => (
                        <span
                          key={el}
                          className="w-7 h-7 sm:w-6 sm:h-6 rounded text-xs font-bold flex items-center justify-center"
                          style={{
                            backgroundColor: (ELEMENT_COLORS[el] || '#888') + '25',
                            color: ELEMENT_COLORS[el] || '#888'
                          }}
                        >
                          {el}
                        </span>
                      ))}
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">{m.space_group}</span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded font-medium ${
                        m.verified ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                      }`}>
                        {m.verified ? '已验证' : '原始'}
                      </span>
                    </div>
                    {m.topology && (
                      <p className="text-xs text-gray-500 mt-1 truncate">拓扑: {m.topology}</p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-[90%] max-w-sm sm:w-96">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-white">保存搜索</h3>
              <button
                onClick={() => setShowSaveDialog(false)}
                className="p-1 text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <input
              type="text"
              value={searchName}
              onChange={(e) => setSearchName(e.target.value)}
              placeholder="输入搜索名称..."
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500 mb-4"
              autoFocus
            />
            <div className="flex gap-3">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="flex-1 px-4 py-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
              >
                取消
              </button>
              <button
                onClick={saveSearch}
                disabled={!searchName.trim()}
                className="flex-1 px-4 py-2 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

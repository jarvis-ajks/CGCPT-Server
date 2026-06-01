import { useEffect, useState, useMemo, useCallback } from 'react'
import { useSearchParams, Link, useNavigate } from 'react-router-dom'
import { Search, X, Heart, CheckSquare, Square, GitCompare, History, FlaskConical, Network, Layers } from 'lucide-react'
import { searchMaterials } from '../api/client'
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

interface FavoriteItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  addedAt: number
  elements: string[]
  verified: boolean
}

type SearchType = 'formula' | 'topology' | 'space_group'

function extractElements(formula: string): string[] {
  return formula.match(/[A-Z][a-z]?/g) || []
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

function loadSearchHistory(): string[] {
  try {
    const data = localStorage.getItem('cgcpt_search_history')
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveSearchHistory(history: string[]): void {
  localStorage.setItem('cgcpt_search_history', JSON.stringify(history.slice(0, 20)))
}

const SEARCH_TYPE_CONFIG: Record<SearchType, { label: string; icon: typeof FlaskConical; placeholder: string }> = {
  formula: { label: '化学式', icon: FlaskConical, placeholder: '输入化学式搜索，如 MgO、TiO2...' },
  topology: { label: '拓扑', icon: Network, placeholder: '输入拓扑名称搜索...' },
  space_group: { label: '空间群', icon: Layers, placeholder: '输入空间群搜索，如 Fm-3m、Pnma...' },
}

export default function SearchResults() {
  const [searchParams, setSearchParams] = useSearchParams()
  const query = searchParams.get('q') ?? ''
  const [results, setResults] = useState<MaterialListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [searchType, setSearchType] = useState<SearchType>('formula')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [favorites, setFavorites] = useState<FavoriteItem[]>(loadFavorites)
  const [searchHistory, setSearchHistory] = useState<string[]>(loadSearchHistory)
  const [showHistory, setShowHistory] = useState(false)
  const [inputValue, setInputValue] = useState(query)
  const navigate = useNavigate()

  useEffect(() => {
    setInputValue(query)
  }, [query])

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      setTotal(0)
      return
    }
    setLoading(true)
    searchMaterials(query)
      .then((res) => {
        setResults(res.results)
        setTotal(res.total)
      })
      .catch(() => {
        setResults([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [query])

  const isFavorite = useCallback((materialId: string) => {
    return favorites.some(f => f.materialId === materialId)
  }, [favorites])

  const toggleFavorite = (m: MaterialListItem) => {
    const current = loadFavorites()
    const exists = current.find(f => f.materialId === m.material_id)
    let updated: FavoriteItem[]
    if (exists) {
      updated = current.filter(f => f.materialId !== m.material_id)
    } else {
      updated = [{
        materialId: m.material_id,
        formula: m.formula,
        spaceGroup: m.space_group,
        topology: m.topology,
        addedAt: Date.now(),
        elements: extractElements(m.formula),
        verified: m.verified,
      }, ...current]
    }
    saveFavorites(updated)
    setFavorites(updated)
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

  const handleSearch = (value: string) => {
    const trimmed = value.trim()
    if (!trimmed) return
    const history = loadSearchHistory()
    const filtered = history.filter(h => h !== trimmed)
    const newHistory = [trimmed, ...filtered].slice(0, 20)
    saveSearchHistory(newHistory)
    setSearchHistory(newHistory)
    setSearchParams({ q: trimmed })
    setShowHistory(false)
  }

  const clearHistory = () => {
    saveSearchHistory([])
    setSearchHistory([])
  }

  const filteredResults = useMemo(() => {
    if (searchType === 'formula') return results
    if (searchType === 'topology') {
      return results.filter(m => m.topology?.toLowerCase().includes(query.toLowerCase()))
    }
    if (searchType === 'space_group') {
      return results.filter(m => m.space_group?.toLowerCase().includes(query.toLowerCase()))
    }
    return results
  }, [results, searchType, query])

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2 sm:gap-3">
          <Search className="w-6 h-6 sm:w-7 sm:h-7 text-cyan-400" />
          搜索结果
        </h1>
        <p className="text-gray-400 mt-1 text-sm">
          {query ? `搜索 "${query}" — 找到 ${total} 个结果` : '请输入搜索关键词'}
        </p>
      </div>

      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-1 bg-gray-800/50 border border-gray-700/50 rounded-lg p-1 self-start">
            {(Object.entries(SEARCH_TYPE_CONFIG) as [SearchType, typeof SEARCH_TYPE_CONFIG[SearchType]][]).map(([type, config]) => {
              const Icon = config.icon
              return (
                <button
                  key={type}
                  onClick={() => setSearchType(type)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                    searchType === type
                      ? 'bg-cyan-500/20 text-cyan-400'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {config.label}
                </button>
              )
            })}
          </div>

          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(inputValue) }}
              onFocus={() => setShowHistory(true)}
              onBlur={() => setTimeout(() => setShowHistory(false), 200)}
              placeholder={SEARCH_TYPE_CONFIG[searchType].placeholder}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-9 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
            />
            {inputValue && (
              <button
                onClick={() => setInputValue('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            {showHistory && searchHistory.length > 0 && !inputValue && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50">
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <History className="w-3 h-3" />
                    搜索历史
                  </span>
                  <button
                    onClick={clearHistory}
                    className="text-xs text-gray-500 hover:text-white transition-colors"
                  >
                    清除
                  </button>
                </div>
                {searchHistory.slice(0, 8).map((h, i) => (
                  <button
                    key={i}
                    onMouseDown={() => {
                      setInputValue(h)
                      handleSearch(h)
                    }}
                    className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-gray-700/50 hover:text-white transition-colors"
                  >
                    {h}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={() => handleSearch(inputValue)}
            className="px-4 py-2 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors text-sm self-start"
          >
            搜索
          </button>
        </div>

        <div className="flex items-center gap-3">
          {selectedIds.size >= 2 && (
            <button
              onClick={handleCompare}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors text-sm"
            >
              <GitCompare className="w-4 h-4" />
              对比 ({selectedIds.size})
            </button>
          )}
          {selectedIds.size > 0 && (
            <button
              onClick={() => setSelectedIds(new Set())}
              className="text-xs text-gray-500 hover:text-white transition-colors"
            >
              取消选择
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filteredResults.length > 0 ? (
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
                  <th className="px-2 py-1.5 sm:px-3 sm:py-3 w-20 hidden sm:table-cell"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/30">
                {filteredResults.map((m) => {
                  const els = extractElements(m.formula)
                  const fav = isFavorite(m.material_id)
                  return (
                    <tr key={m.material_id} className="hover:bg-gray-700/20 transition-colors group">
                      <td className="px-2 py-1.5 sm:px-3 sm:py-3">
                        <button onClick={() => toggleSelect(m.material_id)}>
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
                              className="w-5 h-5 rounded text-[10px] font-bold flex items-center justify-center"
                              style={{
                                backgroundColor: (ELEMENT_COLORS[el] || '#888') + '25',
                                color: ELEMENT_COLORS[el] || '#888'
                              }}
                            >
                              {el}
                            </span>
                          ))}
                          {els.length > 5 && <span className="text-xs text-gray-500 ml-1">+{els.length - 5}</span>}
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
                      <td className="px-2 py-1.5 sm:px-3 sm:py-3 hidden sm:table-cell">
                        <button
                          onClick={() => toggleFavorite(m)}
                          className={`p-1.5 rounded transition-colors ${
                            fav
                              ? 'text-rose-400 hover:text-rose-300'
                              : 'text-gray-600 hover:text-rose-400 opacity-0 group-hover:opacity-100'
                          }`}
                        >
                          <Heart className={`w-4 h-4 ${fav ? 'fill-current' : ''}`} />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : query ? (
        <div className="text-center py-20 text-gray-500">
          <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>未找到与 "{query}" 相关的结果</p>
          <p className="text-sm mt-2">尝试切换搜索类型或修改关键词</p>
        </div>
      ) : (
        <div className="text-center py-20 text-gray-500">
          <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>请在搜索框中输入关键词</p>
          {searchHistory.length > 0 && (
            <div className="mt-6 max-w-md mx-auto">
              <p className="text-xs text-gray-600 mb-3 flex items-center justify-center gap-1">
                <History className="w-3 h-3" />
                最近搜索
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {searchHistory.slice(0, 6).map((h, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInputValue(h)
                      handleSearch(h)
                    }}
                    className="px-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700/50 text-sm text-gray-400 hover:text-white hover:border-cyan-500/50 transition-colors"
                  >
                    {h}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
